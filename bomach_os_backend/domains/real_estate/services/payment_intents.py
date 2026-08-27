from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from domains.real_estate.models.property_purchase import PropertyPurchase
from domains.real_estate.payment_contract import (
    PROPERTY_PURCHASE_PURPOSE_TYPE,
    REAL_ESTATE_REVENUE_ACCOUNT_CODE,
)
from system.payments.models import ConfirmedReceipt, PaymentIntent
from system.payments.services import (
    create_payment_intent,
    expire_payment_intent,
    money,
    start_payment_attempt,
)
from user.models.employee import Employee

CENT = Decimal("0.01")
ZERO = Decimal("0.00")

# Backward-compatible Phase 4/5 public adapter constant.
PURPOSE_TYPE = PROPERTY_PURCHASE_PURPOSE_TYPE


def _purchase_branch(purchase):
    try:
        return purchase.created_by.employee_profile.branch
    except Employee.DoesNotExist:
        return None


def _intent_filter(purchase_id):
    return {
        "purpose_type": PROPERTY_PURCHASE_PURPOSE_TYPE,
        "purpose_id": str(purchase_id),
    }


def _receipt_filter(purchase_id):
    return {
        "intent__purpose_type": PROPERTY_PURCHASE_PURPOSE_TYPE,
        "intent__purpose_id": str(purchase_id),
    }


def _lock_purchase(purchase_id):
    return (
        PropertyPurchase.objects.select_for_update()
        .select_related("property__estate", "client__user", "created_by")
        .get(id=purchase_id)
    )


def _assert_payable(purchase):
    if purchase.status not in {
        PropertyPurchase.STATUS_AWAITING_PAYMENT,
        PropertyPurchase.STATUS_RESERVED,
        PropertyPurchase.STATUS_INSTALLMENT_ACTIVE,
    }:
        raise ValidationError(
            "Payment requests require an approved/reserved/active-installment purchase."
        )
    if purchase.amount_paid >= purchase.agreed_price:
        raise ValidationError("This purchase is already fully paid.")
    if (
        purchase.status == PropertyPurchase.STATUS_AWAITING_PAYMENT
        and purchase.payment_window_expires_at
        and purchase.payment_window_expires_at <= timezone.now()
    ):
        raise ValidationError("The initial purchase payment window has expired.")


def installment_schedule(purchase):
    if purchase.mode != PropertyPurchase.MODE_INSTALLMENT:
        return []
    months = int(purchase.installment_months or 0)
    if months < 1:
        raise ValidationError("Installment duration snapshot is missing.")
    agreed = money(purchase.agreed_price)
    if months == 1:
        return [agreed]
    equal = (agreed / Decimal(months)).quantize(CENT, rounding=ROUND_HALF_UP)
    first = max(equal, money(purchase.reservation_amount or ZERO))
    first = min(first, agreed)
    if first == agreed:
        return [agreed]
    remaining = agreed - first
    count = months - 1
    regular = (remaining / Decimal(count)).quantize(CENT, rounding=ROUND_HALF_UP)
    schedule = [first]
    allocated = first
    for index in range(count):
        amount = agreed - allocated if index == count - 1 else regular
        amount = money(amount)
        if amount > ZERO:
            schedule.append(amount)
            allocated += amount
    if sum(schedule, ZERO) != agreed:
        schedule[-1] = money(schedule[-1] + agreed - sum(schedule, ZERO))
    return schedule


def expected_next_payment_amount(purchase):
    outstanding = money(purchase.agreed_price - purchase.amount_paid)
    if outstanding <= ZERO:
        raise ValidationError("This purchase has no outstanding balance.")
    if purchase.mode == PropertyPurchase.MODE_FULL_PAYMENT:
        return outstanding
    if purchase.mode == PropertyPurchase.MODE_RESERVATION:
        if purchase.reservation_amount is None:
            raise ValidationError("Reservation threshold snapshot is missing.")
        threshold = money(purchase.reservation_amount)
        return (
            money(threshold - purchase.amount_paid)
            if purchase.amount_paid < threshold
            else outstanding
        )
    if purchase.mode == PropertyPurchase.MODE_INSTALLMENT:
        cumulative = ZERO
        current = money(purchase.amount_paid)
        for amount in installment_schedule(purchase):
            cumulative = money(cumulative + amount)
            if current < cumulative:
                return money(min(cumulative - current, outstanding))
        return outstanding
    raise ValidationError("Unsupported purchase mode.")


def _assert_no_unapplied_receipt(purchase):
    if ConfirmedReceipt.objects.filter(
        **_receipt_filter(purchase.id), applied_at__isnull=True
    ).exists():
        raise ValidationError(
            "A confirmed payment is waiting for Real Estate settlement."
        )


def _payment_expiry(purchase):
    now = timezone.now()
    if purchase.status == PropertyPurchase.STATUS_AWAITING_PAYMENT:
        expiry = purchase.payment_window_expires_at
        if expiry is None or expiry <= now:
            raise ValidationError("The initial payment window has expired.")
        return expiry
    if (
        purchase.mode == PropertyPurchase.MODE_INSTALLMENT
        and purchase.status == PropertyPurchase.STATUS_INSTALLMENT_ACTIVE
        and purchase.next_payment_due_at is not None
    ):
        expiry = purchase.next_payment_due_at + timedelta(
            hours=purchase.payment_window_hours
        )
        if expiry <= now:
            raise ValidationError(
                "Installment is beyond its grace window; default/reconcile it first."
            )
        return expiry
    return now + timedelta(hours=purchase.payment_window_hours)


def _intent_values(purchase, amount, expires_at, created_by):
    return {
        "purpose_type": PROPERTY_PURCHASE_PURPOSE_TYPE,
        "purpose_id": purchase.id,
        "amount": amount,
        "currency": "NGN",
        "description": f"Payment for {purchase.property.property_name}",
        "metadata": {
            "property_purchase_id": purchase.id,
            "property_id": purchase.property_id,
            "client_id": purchase.client_id,
            "mode": purchase.mode,
            "customer_email": purchase.client.user.email,
            "customer_name": (
                purchase.client.user.get_full_name() or purchase.client.user.email
            ),
        },
        "expires_at": expires_at,
        "branch": _purchase_branch(purchase),
        "created_by": created_by or purchase.created_by,
        "accounting_total_due": purchase.agreed_price,
        "accounting_total_tax": ZERO,
        "accounting_prior_paid": purchase.amount_paid,
        "revenue_account_code": REAL_ESTATE_REVENUE_ACCOUNT_CODE,
    }


def create_property_purchase_payment_intent(
    purchase,
    *,
    amount,
    idempotency_key,
    expires_at=None,
    created_by=None,
):
    with transaction.atomic():
        purchase = _lock_purchase(purchase.id)
        _assert_payable(purchase)
        _assert_no_unapplied_receipt(purchase)
        expected = expected_next_payment_amount(purchase)
        requested = money(amount)
        if requested != expected:
            raise ValidationError(f"The next exact payment amount is {expected:.2f} NGN.")
        other_open = (
            PaymentIntent.objects.filter(
                **_intent_filter(purchase.id),
                status__in=[
                    PaymentIntent.STATUS.CREATED,
                    PaymentIntent.STATUS.PROCESSING,
                ],
            )
            .exclude(idempotency_key=idempotency_key)
            .first()
        )
        if other_open and (
            other_open.expires_at is None or other_open.expires_at > timezone.now()
        ):
            raise ValidationError("This purchase already has a live payment request.")
        return create_payment_intent(
            idempotency_key=idempotency_key,
            **_intent_values(
                purchase,
                requested,
                expires_at or _payment_expiry(purchase),
                created_by,
            ),
        )


def start_next_property_purchase_payment(*, purchase_id, provider_name, created_by=None):
    now = timezone.now()
    with transaction.atomic():
        purchase = _lock_purchase(purchase_id)
        _assert_payable(purchase)
        _assert_no_unapplied_receipt(purchase)
        expected = expected_next_payment_amount(purchase)
        expiry = _payment_expiry(purchase)
        selected = None
        for intent in (
            PaymentIntent.objects.select_for_update()
            .filter(
                **_intent_filter(purchase.id),
                status__in=[
                    PaymentIntent.STATUS.CREATED,
                    PaymentIntent.STATUS.PROCESSING,
                ],
            )
            .order_by("-created_at")
        ):
            if intent.expires_at is not None and intent.expires_at <= now:
                expire_payment_intent(intent=intent, at=now)
                continue
            if selected is not None:
                raise ValidationError(
                    "Multiple live payment intents require reconciliation."
                )
            if money(intent.amount) != expected:
                raise ValidationError(
                    "Live payment intent does not match the exact next amount."
                )
            selected = intent
        if selected is None:
            cycle = PaymentIntent.objects.filter(**_intent_filter(purchase.id)).count() + 1
            key = (
                f"real-estate-purchase:{purchase.id}:cycle:{cycle}:"
                f"amount:{expected:.2f}"
            )
            selected, _ = create_payment_intent(
                idempotency_key=key,
                **_intent_values(purchase, expected, expiry, created_by),
            )
    attempt, created = start_payment_attempt(
        intent=selected,
        provider_name=provider_name,
        idempotency_key=f"{selected.reference}:{provider_name.strip().lower()}",
    )
    return selected, attempt, created
