import base64
import hashlib
import hmac
from datetime import datetime
from decimal import Decimal
from typing import Mapping

import requests
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from system.payments.providers.base import (
    PaymentProviderError,
    PaymentProviderIgnoredEvent,
    PaymentProviderVerificationError,
    ProviderAttemptRequest,
    ProviderAttemptResult,
    VerifiedProviderPayment,
)
from system.payments.providers.registry import register_provider


def _money(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except Exception as exc:
        raise PaymentProviderVerificationError("Invalid Monnify amount.") from exc


def _header(headers: Mapping[str, str], name: str):
    wanted = name.lower()
    for key, value in headers.items():
        if str(key).lower() == wanted:
            return str(value)
    return ""


def _paid_at(value):
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value or "").strip()
        parsed = parse_datetime(text)
        if parsed is None:
            for fmt in ("%d/%m/%Y %I:%M:%S %p", "%Y-%m-%d %H:%M:%S"):
                try:
                    parsed = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
    if parsed is None:
        raise PaymentProviderVerificationError("Invalid Monnify paidOn timestamp.")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


class MonnifyProvider:
    name = "monnify"

    @property
    def base_url(self):
        return settings.MONNIFY_BASE_URL.rstrip("/")

    @property
    def timeout(self):
        return (settings.MONNIFY_CONNECT_TIMEOUT, settings.MONNIFY_RESPONSE_TIMEOUT)

    def _credentials(self):
        api_key = (settings.MONNIFY_API_KEY or "").strip()
        secret = (settings.MONNIFY_SECRET_KEY or "").strip()
        contract = (settings.MONNIFY_CONTRACT_CODE or "").strip()
        if not api_key or not secret or not contract:
            raise PaymentProviderError(
                "Monnify API key, secret key and contract code must be configured."
            )
        return api_key, secret, contract

    def _token(self):
        api_key, secret, _ = self._credentials()
        basic = base64.b64encode(f"{api_key}:{secret}".encode()).decode()
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/login",
                headers={"Authorization": f"Basic {basic}", "Content-Type": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            raise PaymentProviderError("Monnify authentication request failed.") from exc
        except ValueError as exc:
            raise PaymentProviderError("Monnify authentication returned invalid JSON.") from exc
        if not data.get("requestSuccessful"):
            raise PaymentProviderError(data.get("responseMessage") or "Monnify authentication failed.")
        token = (data.get("responseBody") or {}).get("accessToken")
        if not token:
            raise PaymentProviderError("Monnify authentication response has no accessToken.")
        return str(token)

    def create_attempt(self, request: ProviderAttemptRequest):
        _, _, contract = self._credentials()
        email = str(request.metadata.get("customer_email") or "").strip()
        name = str(request.metadata.get("customer_name") or "").strip() or email
        if not email:
            raise PaymentProviderError("Monnify Dynamic Invoice requires customer_email.")

        payload = {
            "invoiceReference": request.attempt_reference,
            "amount": str(request.amount),
            "invoiceDescription": request.description or request.attempt_reference,
            "contractCode": contract,
            "customerEmail": email,
            "customerName": name,
            "currencyCode": request.currency,
        }
        if request.expires_at:
            payload["expiryDate"] = timezone.localtime(request.expires_at).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/invoice/create",
                headers={"Authorization": f"Bearer {self._token()}", "Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            raise PaymentProviderError("Monnify Dynamic Invoice request failed.") from exc
        except ValueError as exc:
            raise PaymentProviderError("Monnify Dynamic Invoice returned invalid JSON.") from exc
        if not data.get("requestSuccessful"):
            raise PaymentProviderError(data.get("responseMessage") or "Monnify invoice creation failed.")
        body = data.get("responseBody") or {}
        checkout = str(body.get("checkoutUrl") or body.get("checkoutURL") or "")
        return ProviderAttemptResult(
            provider_reference=request.attempt_reference,
            status="pending",
            checkout_url=checkout,
            metadata={"invoice_reference": request.attempt_reference, "dynamic_invoice": body},
        )

    def _signature(self, raw_body, headers):
        _, secret, _ = self._credentials()
        supplied = _header(headers, "monnify-signature").strip().lower()
        if not supplied:
            allow = bool(getattr(settings, "MONNIFY_ALLOW_UNSIGNED_SANDBOX_WEBHOOKS", False))
            if allow and "sandbox.monnify.com" in self.base_url.lower():
                return
            raise PaymentProviderVerificationError("Missing Monnify webhook signature.")
        expected = hmac.new(secret.encode(), raw_body, hashlib.sha512).hexdigest()
        if not hmac.compare_digest(expected.lower(), supplied):
            raise PaymentProviderVerificationError("Invalid Monnify webhook signature.")

    def _verify_transaction(self, payment_reference):
        try:
            response = requests.get(
                f"{self.base_url}/api/v2/merchant/transactions/query",
                headers={"Authorization": f"Bearer {self._token()}"},
                params={"paymentReference": payment_reference},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            raise PaymentProviderError("Monnify transaction verification request failed.") from exc
        except ValueError as exc:
            raise PaymentProviderError("Monnify transaction verification returned invalid JSON.") from exc
        if not data.get("requestSuccessful"):
            raise PaymentProviderVerificationError(
                data.get("responseMessage") or "Monnify transaction verification failed."
            )
        return data.get("responseBody") or {}

    def verify_event(self, *, payload, headers, raw_body=None):
        if raw_body is None:
            raise PaymentProviderVerificationError("Exact raw webhook body is required.")
        self._signature(raw_body, headers)

        event_type = str(payload.get("eventType") or "").strip()
        if event_type != "SUCCESSFUL_TRANSACTION":
            raise PaymentProviderIgnoredEvent(f"Ignored Monnify event: {event_type or 'unknown'}.")
        event = payload.get("eventData") or {}
        if str(event.get("paymentStatus") or "").upper() != "PAID":
            raise PaymentProviderIgnoredEvent("Ignored non-PAID Monnify collection.")

        payment_ref = str(event.get("paymentReference") or "").strip()
        tx_ref = str(event.get("transactionReference") or "").strip()
        product = event.get("product") or {}
        attempt_ref = str(
            product.get("reference") or event.get("invoiceReference") or payment_ref
        ).strip()
        if not payment_ref or not tx_ref or not attempt_ref:
            raise PaymentProviderVerificationError("Monnify webhook is missing transaction identity.")

        verified = self._verify_transaction(payment_ref)
        status = str(
            verified.get("paymentStatus") or verified.get("transactionStatus") or ""
        ).upper()
        if status not in {"PAID", "COMPLETED"}:
            raise PaymentProviderVerificationError("Monnify server verification is not paid.")

        web_amount = _money(event.get("amountPaid"))
        api_amount = _money(verified.get("amountPaid"))
        if web_amount != api_amount:
            raise PaymentProviderVerificationError("Monnify amount verification mismatch.")
        web_currency = str(event.get("currency") or event.get("currencyCode") or "").upper()
        api_currency = str(verified.get("currencyCode") or verified.get("currency") or "").upper()
        if not web_currency or web_currency != api_currency:
            raise PaymentProviderVerificationError("Monnify currency verification mismatch.")
        api_tx_ref = str(verified.get("transactionReference") or "").strip()
        if api_tx_ref and api_tx_ref != tx_ref:
            raise PaymentProviderVerificationError("Monnify transaction reference mismatch.")

        return VerifiedProviderPayment(
            event_key=f"{event_type}:{tx_ref}",
            event_type=event_type,
            provider_reference=attempt_ref,
            transaction_reference=tx_ref,
            intent_reference="",
            amount=api_amount,
            currency=api_currency,
            paid_at=_paid_at(verified.get("paidOn") or event.get("paidOn") or event.get("transactionTime")),
            payment_method=str(verified.get("paymentMethod") or event.get("paymentMethod") or ""),
            metadata={
                "payment_reference": payment_ref,
                "transaction_reference": tx_ref,
                "verified_transaction": verified,
            },
        )


_PROVIDER = MonnifyProvider()


def ensure_monnify_provider_registered():
    return register_provider(_PROVIDER, replace=True)
