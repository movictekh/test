import json

from django.core.exceptions import ValidationError
from django.http import HttpRequest
from ninja import Router, Schema

from system.payments.providers import (
    PaymentProviderError,
    PaymentProviderIgnoredEvent,
    PaymentProviderVerificationError,
)
from system.payments.providers.monnify import ensure_monnify_provider_registered
from system.payments.services import verify_and_apply_provider_event

class PaymentWebhookResponse(Schema):
    detail: str
    receipt_reference: str | None = None
    ignored: bool | None = None


payment_webhook_router = Router(tags=["Payment Webhooks"])


@payment_webhook_router.post(
    "/monnify/",
    auth=None,
    response={
        200: PaymentWebhookResponse,
        400: PaymentWebhookResponse,
        401: PaymentWebhookResponse,
        503: PaymentWebhookResponse,
    },
)
def monnify_webhook(request: HttpRequest):
    raw_body = request.body
    try:
        payload = json.loads(raw_body)
    except (TypeError, ValueError):
        return 400, {"detail": "Invalid JSON payload."}
    ensure_monnify_provider_registered()
    try:
        receipt = verify_and_apply_provider_event(
            provider_name="monnify",
            payload=payload,
            headers={str(k): str(v) for k, v in request.headers.items()},
            raw_body=raw_body,
            confirmed_by=None,
        )
        return 200, {"detail": "Payment confirmed.", "receipt_reference": receipt.reference}
    except PaymentProviderIgnoredEvent as exc:
        return 200, {"detail": str(exc), "ignored": True}
    except PaymentProviderVerificationError as exc:
        return 401, {"detail": str(exc)}
    except ValidationError as exc:
        return 400, {"detail": str(exc)}
    except PaymentProviderError as exc:
        return 503, {"detail": str(exc)}
