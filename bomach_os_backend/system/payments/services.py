import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from finance.service import post_external_receipt_journal, resolve_receipt_finance_account
from system.payments.models import (
    ConfirmedReceipt,
    PaymentAttempt,
    PaymentIntent,
    PaymentProviderEvent,
)
from system.payments.providers import (
    ProviderAttemptRequest,
    VerifiedProviderPayment,
    get_provider,
)

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value) -> Decimal:
    try:
        return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
    except Exception as exc:
        raise ValidationError("Payment amounts must be valid decimal values.") from exc


def _normalize_payload(payload: dict) -> dict:
    try:
        return json.loads(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        )
    except Exception as exc:
        raise ValidationError("Provider event payload is not JSON serializable.") from exc


def _payload_digest(payload: dict) -> tuple[dict, str]:
    normalized = _normalize_payload(payload)
    encoded = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return normalized, hashlib.sha256(encoded).hexdigest()


def _intent_values(
    *,
    purpose_type,
    purpose_id,
    amount,
    currency,
    description,
    metadata,
    expires_at,
    branch,
    created_by,
    accounting_total_due,
    accounting_total_tax,
    accounting_prior_paid,
    revenue_account_code,
):
    normalized_amount = money(amount)
    total_due = money(
        normalized_amount if accounting_total_due is None else accounting_total_due
    )
    return {
        "purpose_type": (purpose_type or "").strip(),
        "purpose_id": str(purpose_id).strip(),
        "amount": normalized_amount,
        "currency": (currency or "NGN").upper(),
        "description": (description or "").strip(),
        "metadata": _normalize_payload(metadata or {}),
        "expires_at": expires_at,
        "branch": branch,
        "created_by": created_by,
        "accounting_total_due": total_due,
        "accounting_total_tax": money(accounting_total_tax),
        "accounting_prior_paid": money(accounting_prior_paid),
        "revenue_account_code": (revenue_account_code or "").strip().upper(),
    }


def _assert_same_intent(existing, expected):
    comparable = (
        "purpose_type",
        "purpose_id",
        "amount",
        "currency",
        "description",
        "metadata",
        "expires_at",
        "branch_id",
        "created_by_id",
        "accounting_total_due",
        "accounting_total_tax",
        "accounting_prior_paid",
        "revenue_account_code",
    )
    expected_values = {
        **expected,
        "branch_id": expected["branch"].id if expected["branch"] else None,
        "created_by_id": expected["created_by"].id if expected["created_by"] else None,
    }
    for field in comparable:
        if getattr(existing, field) != expected_values[field]:
            raise ValidationError(
                "Payment intent idempotency key was reused with different request data."
            )


def create_payment_intent(
    *,
    idempotency_key,
    purpose_type,
    purpose_id,
    amount,
    currency="NGN",
    description="",
    metadata=None,
    expires_at=None,
    branch=None,
    created_by=None,
    accounting_total_due=None,
    accounting_total_tax=ZERO,
    accounting_prior_paid=ZERO,
    revenue_account_code,
):
    key = (idempotency_key or "").strip()
    if not key:
        raise ValidationError("Payment intent idempotency key is required.")
    if expires_at is not None and expires_at <= timezone.now():
        raise ValidationError("Payment intent expiry must be in the future.")
    values = _intent_values(
        purpose_type=purpose_type,
        purpose_id=purpose_id,
        amount=amount,
        currency=currency,
        description=description,
        metadata=metadata,
        expires_at=expires_at,
        branch=branch,
        created_by=created_by,
        accounting_total_due=accounting_total_due,
        accounting_total_tax=accounting_total_tax,
        accounting_prior_paid=accounting_prior_paid,
        revenue_account_code=revenue_account_code,
    )
    try:
        with transaction.atomic():
            existing = (
                PaymentIntent.objects.select_for_update()
                .filter(idempotency_key=key)
                .first()
            )
            if existing:
                _assert_same_intent(existing, values)
                return existing, False
            intent = PaymentIntent(idempotency_key=key, **values)
            intent.full_clean()
            intent.save()
            return intent, True
    except IntegrityError:
        existing = PaymentIntent.objects.get(idempotency_key=key)
        _assert_same_intent(existing, values)
        return existing, False


def _expire_locked_intent_if_due(intent, *, at=None):
    now = at or timezone.now()
    if (
        intent.status in {PaymentIntent.STATUS.CREATED, PaymentIntent.STATUS.PROCESSING}
        and intent.expires_at
        and intent.expires_at <= now
    ):
        intent.status = PaymentIntent.STATUS.EXPIRED
        intent.save(update_fields=["status", "updated_at"])
        intent.attempts.filter(
            status__in=[PaymentAttempt.STATUS.CREATED, PaymentAttempt.STATUS.PENDING]
        ).update(
            status=PaymentAttempt.STATUS.EXPIRED,
            completed_at=now,
            updated_at=now,
        )
        return True
    return False


def start_payment_attempt(*, intent, provider_name, idempotency_key):
    provider = get_provider(provider_name)
    provider_name = provider.name.strip().lower()
    key = (idempotency_key or "").strip()
    if not key:
        raise ValidationError("Payment attempt idempotency key is required.")

    with transaction.atomic():
        locked_intent = PaymentIntent.objects.select_for_update().get(id=intent.id)
        if _expire_locked_intent_if_due(locked_intent):
            raise ValidationError("This payment intent has expired.")
        if locked_intent.status == PaymentIntent.STATUS.CONFIRMED:
            raise ValidationError("This payment intent is already confirmed.")
        if locked_intent.status in {
            PaymentIntent.STATUS.CANCELLED,
            PaymentIntent.STATUS.EXPIRED,
        }:
            raise ValidationError(
                f"Cannot start an attempt for a {locked_intent.status} payment intent."
            )
        attempt = (
            PaymentAttempt.objects.select_for_update()
            .filter(provider=provider_name, idempotency_key=key)
            .first()
        )
        if attempt:
            if attempt.intent_id != locked_intent.id:
                raise ValidationError(
                    "Payment attempt idempotency key belongs to another intent."
                )
            if attempt.provider_reference:
                return attempt, False
        else:
            attempt = PaymentAttempt.objects.create(
                intent=locked_intent,
                provider=provider_name,
                idempotency_key=key,
                amount=locked_intent.amount,
                currency=locked_intent.currency,
                status=PaymentAttempt.STATUS.CREATED,
            )
        if locked_intent.status == PaymentIntent.STATUS.CREATED:
            locked_intent.status = PaymentIntent.STATUS.PROCESSING
            locked_intent.save(update_fields=["status", "updated_at"])

    request = ProviderAttemptRequest(
        intent_reference=locked_intent.reference,
        attempt_reference=attempt.reference,
        amount=attempt.amount,
        currency=attempt.currency,
        description=locked_intent.description,
        metadata=dict(locked_intent.metadata or {}),
        idempotency_key=key,
        expires_at=locked_intent.expires_at,
    )
    try:
        result = provider.create_attempt(request)
    except Exception as exc:
        with transaction.atomic():
            locked_attempt = PaymentAttempt.objects.select_for_update().get(id=attempt.id)
            if not locked_attempt.provider_reference:
                locked_attempt.status = PaymentAttempt.STATUS.FAILED
                locked_attempt.failure_code = "provider_create_failed"
                locked_attempt.failure_message = str(exc)
                locked_attempt.completed_at = timezone.now()
                locked_attempt.save(
                    update_fields=[
                        "status",
                        "failure_code",
                        "failure_message",
                        "completed_at",
                        "updated_at",
                    ]
                )
        raise

    with transaction.atomic():
        locked_attempt = PaymentAttempt.objects.select_for_update().get(id=attempt.id)
        if locked_attempt.provider_reference:
            return locked_attempt, False
        provider_reference = (result.provider_reference or "").strip()
        result_status = (result.status or "pending").strip().lower()
        if result_status == "failed":
            locked_attempt.status = PaymentAttempt.STATUS.FAILED
            locked_attempt.completed_at = timezone.now()
        else:
            if not provider_reference:
                raise ValidationError(
                    "Payment provider did not return a transaction reference."
                )
            locked_attempt.status = PaymentAttempt.STATUS.PENDING
        locked_attempt.provider_reference = provider_reference
        locked_attempt.checkout_url = result.checkout_url or ""
        locked_attempt.provider_metadata = _normalize_payload(result.metadata or {})
        locked_attempt.save(
            update_fields=[
                "provider_reference",
                "checkout_url",
                "provider_metadata",
                "status",
                "completed_at",
                "updated_at",
            ]
        )
        return locked_attempt, True


def record_verified_provider_event(
    *,
    provider,
    event_key,
    event_type,
    payload,
    verification_metadata=None,
):
    provider = (provider or "").strip().lower()
    event_key = (event_key or "").strip()
    if not provider or not event_key:
        raise ValidationError("Verified provider events require provider and event key.")
    normalized, digest = _payload_digest(payload)
    verification = _normalize_payload(verification_metadata or {})
    try:
        with transaction.atomic():
            existing = (
                PaymentProviderEvent.objects.select_for_update()
                .filter(provider=provider, event_key=event_key)
                .first()
            )
            if existing:
                if existing.payload_digest != digest:
                    raise ValidationError(
                        "Provider event key was reused with a different payload."
                    )
                if existing.event_type != (event_type or ""):
                    raise ValidationError(
                        "Provider event key was reused with a different event type."
                    )
                return existing, False
            event = PaymentProviderEvent.objects.create(
                provider=provider,
                event_key=event_key,
                event_type=event_type or "",
                payload=normalized,
                payload_digest=digest,
                is_verified=True,
                verification_metadata=verification,
            )
            return event, True
    except IntegrityError:
        existing = PaymentProviderEvent.objects.get(provider=provider, event_key=event_key)
        if existing.payload_digest != digest:
            raise ValidationError(
                "Provider event key was reused with a different payload."
            )
        return existing, False


def _receipt_matches_verified(receipt, verified):
    return (
        receipt.provider_transaction_reference == verified.transaction_reference
        and receipt.amount == money(verified.amount)
        and receipt.currency == verified.currency.upper()
    )


def _confirmed_for_same_purpose_before(intent):
    total = (
        ConfirmedReceipt.objects.filter(
            intent__purpose_type=intent.purpose_type,
            intent__purpose_id=intent.purpose_id,
        )
        .exclude(intent_id=intent.id)
        .aggregate(total=Sum("amount"))["total"]
        or ZERO
    )
    return money(total)


def _effective_prior_paid(intent):
    central_confirmed = _confirmed_for_same_purpose_before(intent)
    return max(money(intent.accounting_prior_paid), central_confirmed)


def _ensure_finance_posted(receipt, intent, *, actor=None):
    account = receipt.finance_account
    if not account:
        account = resolve_receipt_finance_account(
            branch_id=intent.branch_id,
            currency=intent.currency,
        )
    journal, _ = post_external_receipt_journal(
        source_type="central_payment_receipt",
        source_id=receipt.reference,
        source_event="confirmed",
        finance_account=account,
        amount=receipt.amount,
        total_due=intent.accounting_total_due,
        total_tax=intent.accounting_total_tax,
        prior_paid=_effective_prior_paid(intent),
        entry_date=timezone.localtime(receipt.paid_at).date(),
        reference=receipt.provider_transaction_reference,
        memo=f"Central payment receipt {receipt.reference} for {intent.reference}",
        branch=account.branch or intent.branch,
        created_by=actor or intent.created_by,
        revenue_account_code=intent.revenue_account_code,
    )
    if (
        receipt.finance_account_id != account.id
        or receipt.finance_journal_id != journal.id
        or receipt.finance_posted_at is None
    ):
        receipt.finance_account = account
        receipt.finance_journal = journal
        receipt.finance_posted_at = receipt.finance_posted_at or timezone.now()
        receipt.save(
            update_fields=[
                "finance_account",
                "finance_journal",
                "finance_posted_at",
                "updated_at",
            ]
        )
    return receipt


def confirm_verified_attempt(
    *,
    attempt,
    event,
    verified: VerifiedProviderPayment,
    confirmed_by=None,
):
    if timezone.is_naive(verified.paid_at):
        raise ValidationError("Verified provider paid_at must be timezone-aware.")
    with transaction.atomic():
        locked_event = PaymentProviderEvent.objects.select_for_update().get(id=event.id)
        locked_attempt = (
            PaymentAttempt.objects.select_for_update()
            .select_related("intent")
            .get(id=attempt.id)
        )
        intent = PaymentIntent.objects.select_for_update().get(id=locked_attempt.intent_id)
        if not locked_event.is_verified:
            raise ValidationError("Unverified provider events cannot confirm payments.")
        if locked_event.provider != locked_attempt.provider:
            raise ValidationError("Provider event does not match the payment attempt.")
        if verified.provider_reference != locked_attempt.provider_reference:
            raise ValidationError(
                "Verified transaction reference does not match the attempt."
            )
        if verified.intent_reference and verified.intent_reference != intent.reference:
            raise ValidationError("Verified payment does not match the payment intent.")
        if money(verified.amount) != intent.amount:
            raise ValidationError("Verified provider amount does not match the payment intent.")
        if verified.currency.upper() != intent.currency:
            raise ValidationError("Verified provider currency does not match the payment intent.")
        effective_prior_paid = _effective_prior_paid(intent)
        if intent.amount > money(intent.accounting_total_due - effective_prior_paid):
            raise ValidationError(
                "Verified payment would exceed the remaining balance for this purpose."
            )

        existing = ConfirmedReceipt.objects.filter(intent=intent).first()
        if existing:
            if not _receipt_matches_verified(existing, verified):
                raise ValidationError(
                    "Payment intent is already confirmed by a different transaction."
                )
            receipt = _ensure_finance_posted(existing, intent, actor=confirmed_by)
        else:
            duplicate_reference = ConfirmedReceipt.objects.filter(
                provider=locked_attempt.provider,
                provider_transaction_reference=verified.transaction_reference,
            ).first()
            if duplicate_reference:
                if duplicate_reference.intent_id != intent.id:
                    raise ValidationError(
                        "Provider transaction reference already confirmed another intent."
                    )
                receipt = _ensure_finance_posted(
                    duplicate_reference,
                    intent,
                    actor=confirmed_by,
                )
            else:
                account = resolve_receipt_finance_account(
                    branch_id=intent.branch_id,
                    currency=intent.currency,
                )
                receipt = ConfirmedReceipt.objects.create(
                    intent=intent,
                    attempt=locked_attempt,
                    provider=locked_attempt.provider,
                    provider_transaction_reference=verified.transaction_reference,
                    amount=intent.amount,
                    currency=intent.currency,
                    paid_at=verified.paid_at,
                    payment_method=verified.payment_method or "",
                    metadata=_normalize_payload(verified.metadata or {}),
                    finance_account=account,
                )
                receipt = _ensure_finance_posted(receipt, intent, actor=confirmed_by)

        now = timezone.now()
        if locked_attempt.status != PaymentAttempt.STATUS.SUCCEEDED:
            locked_attempt.status = PaymentAttempt.STATUS.SUCCEEDED
            locked_attempt.completed_at = now
            locked_attempt.failure_code = ""
            locked_attempt.failure_message = ""
            locked_attempt.save(
                update_fields=[
                    "status",
                    "completed_at",
                    "failure_code",
                    "failure_message",
                    "updated_at",
                ]
            )
        if intent.status != PaymentIntent.STATUS.CONFIRMED:
            intent.status = PaymentIntent.STATUS.CONFIRMED
            intent.confirmed_at = now
            intent.save(update_fields=["status", "confirmed_at", "updated_at"])
        if (
            locked_event.status != PaymentProviderEvent.STATUS.PROCESSED
            or locked_event.receipt_id != receipt.id
            or locked_event.intent_id != intent.id
            or locked_event.attempt_id != locked_attempt.id
        ):
            locked_event.intent = intent
            locked_event.attempt = locked_attempt
            locked_event.receipt = receipt
            locked_event.status = PaymentProviderEvent.STATUS.PROCESSED
            locked_event.processed_at = now
            locked_event.error = ""
            locked_event.save(
                update_fields=[
                    "intent",
                    "attempt",
                    "receipt",
                    "status",
                    "processed_at",
                    "error",
                    "updated_at",
                ]
            )
        return receipt


def verify_and_apply_provider_event(
    *,
    provider_name,
    payload,
    headers,
    raw_body=None,
    confirmed_by=None,
):
    provider = get_provider(provider_name)
    verified = provider.verify_event(payload=payload, headers=headers, raw_body=raw_body)
    event, _ = record_verified_provider_event(
        provider=provider.name,
        event_key=verified.event_key,
        event_type=verified.event_type,
        payload=payload,
        verification_metadata={"adapter": provider.name, "verified": True},
    )
    if event.status == PaymentProviderEvent.STATUS.PROCESSED and event.receipt_id:
        return ConfirmedReceipt.objects.get(id=event.receipt_id)
    attempt = (
        PaymentAttempt.objects.select_related("intent")
        .filter(
            provider=provider.name.strip().lower(),
            provider_reference=verified.provider_reference,
        )
        .first()
    )
    if not attempt:
        event.status = PaymentProviderEvent.STATUS.FAILED
        event.error = "No payment attempt matches this provider transaction."
        event.processed_at = timezone.now()
        event.save(update_fields=["status", "error", "processed_at", "updated_at"])
        raise ValidationError(event.error)
    event.intent = attempt.intent
    event.attempt = attempt
    event.save(update_fields=["intent", "attempt", "updated_at"])
    try:
        return confirm_verified_attempt(
            attempt=attempt,
            event=event,
            verified=verified,
            confirmed_by=confirmed_by,
        )
    except Exception as exc:
        event.refresh_from_db()
        if event.status != PaymentProviderEvent.STATUS.PROCESSED:
            event.status = PaymentProviderEvent.STATUS.FAILED
            event.error = str(exc)
            event.processed_at = timezone.now()
            event.save(update_fields=["status", "error", "processed_at", "updated_at"])
        raise


def mark_receipt_applied(*, receipt, application_reference):
    reference = (application_reference or "").strip()
    if not reference:
        raise ValidationError("Application reference is required.")
    with transaction.atomic():
        locked = ConfirmedReceipt.objects.select_for_update().get(id=receipt.id)
        if locked.applied_at:
            if locked.application_reference != reference:
                raise ValidationError(
                    "Receipt was already applied with a different application reference."
                )
            return locked, False
        locked.application_reference = reference
        locked.applied_at = timezone.now()
        locked.save(update_fields=["application_reference", "applied_at", "updated_at"])
        return locked, True


def expire_payment_intent(*, intent, at=None):
    with transaction.atomic():
        locked = PaymentIntent.objects.select_for_update().get(id=intent.id)
        changed = _expire_locked_intent_if_due(locked, at=at)
        return locked, changed


def expire_due_payment_intents(*, at=None, limit=200):
    now = at or timezone.now()
    ids = list(
        PaymentIntent.objects.filter(
            status__in=[PaymentIntent.STATUS.CREATED, PaymentIntent.STATUS.PROCESSING],
            expires_at__isnull=False,
            expires_at__lte=now,
        )
        .order_by("expires_at")
        .values_list("id", flat=True)[:limit]
    )
    expired = 0
    for intent_id in ids:
        _, changed = expire_payment_intent(intent=PaymentIntent(id=intent_id), at=now)
        expired += int(changed)
    return expired
