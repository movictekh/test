from datetime import timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from domains.real_estate.models.estate import Property
from domains.real_estate.models.property_purchase import PropertyPurchase
from domains.real_estate.payment_contract import PROPERTY_PURCHASE_PURPOSE_TYPE
from system.payments.models import ConfirmedReceipt, PaymentIntent
from system.payments.services import expire_payment_intent, money
from domains.real_estate.services.messaging import (
    enqueue_default_message,
    enqueue_payment_receipt_message,
    enqueue_reservation_message,
    enqueue_sale_completion_message,
)

ZERO = Decimal("0.00")


def _receipt_filter(purchase_id):
    return {
        "intent__purpose_type": PROPERTY_PURCHASE_PURPOSE_TYPE,
        "intent__purpose_id": str(purchase_id),
    }


def _intent_filter(purchase_id):
    return {
        "purpose_type": PROPERTY_PURCHASE_PURPOSE_TYPE,
        "purpose_id": str(purchase_id),
    }


def _lock_purchase(purchase_id):
    return (
        PropertyPurchase.objects.select_for_update()
        .select_related("property__estate", "client__user", "created_by")
        .get(id=purchase_id)
    )


def _holder(purchase):
    return purchase.client.user.get_full_name() or purchase.client.user.email


@transaction.atomic
def approve_property_purchase(*, purchase_id, approved_by=None):
    purchase = _lock_purchase(purchase_id)
    prop = Property.objects.select_for_update().get(id=purchase.property_id)
    if purchase.status == PropertyPurchase.STATUS_AWAITING_PAYMENT:
        return purchase
    if purchase.status != PropertyPurchase.STATUS_AWAITING_APPROVAL:
        raise ValidationError("Only purchases awaiting approval can be approved.")
    if prop.status != "available" or prop.owner_id is not None:
        raise ValidationError("Property must still be available and unowned.")
    if purchase.payment_window_hours < 1:
        raise ValidationError("Purchase payment-window snapshot is invalid.")
    now = timezone.now()
    deadline = now + timedelta(hours=purchase.payment_window_hours)
    purchase.status = PropertyPurchase.STATUS_AWAITING_PAYMENT
    purchase.approved_at = now
    purchase.payment_window_expires_at = deadline
    purchase.next_payment_due_at = deadline
    purchase.save(
        update_fields=[
            "status",
            "approved_at",
            "payment_window_expires_at",
            "next_payment_due_at",
            "updated_at",
        ]
    )
    return purchase


@transaction.atomic
def cancel_property_purchase(*, purchase_id, cancelled_by=None):
    purchase = _lock_purchase(purchase_id)
    Property.objects.select_for_update().get(id=purchase.property_id)
    if purchase.status == PropertyPurchase.STATUS_CANCELLED:
        return purchase
    if purchase.status not in {
        PropertyPurchase.STATUS_AWAITING_APPROVAL,
        PropertyPurchase.STATUS_AWAITING_PAYMENT,
    }:
        raise ValidationError("Only an unpaid purchase awaiting approval/payment can be cancelled.")
    if purchase.amount_paid > ZERO or ConfirmedReceipt.objects.filter(
        **_receipt_filter(purchase.id)
    ).exists():
        raise ValidationError(
            "Verified money exists. Complete refund/reconciliation before cancellation."
        )
    if (
        PaymentIntent.objects.filter(**_intent_filter(purchase.id))
        .exclude(status__in=[PaymentIntent.STATUS.EXPIRED, PaymentIntent.STATUS.CANCELLED])
        .exists()
    ):
        raise ValidationError(
            "A live/confirmed payment request exists. Let it expire or reconcile it first."
        )
    purchase.status = PropertyPurchase.STATUS_CANCELLED
    purchase.cancelled_at = timezone.now()
    purchase.next_payment_due_at = None
    purchase.save(
        update_fields=["status", "cancelled_at", "next_payment_due_at", "updated_at"]
    )
    return purchase


@transaction.atomic
def expire_property_purchase(*, purchase_id, at=None):
    purchase = _lock_purchase(purchase_id)
    Property.objects.select_for_update().get(id=purchase.property_id)
    now = at or timezone.now()
    if purchase.status == PropertyPurchase.STATUS_EXPIRED:
        return purchase
    if purchase.status != PropertyPurchase.STATUS_AWAITING_PAYMENT:
        raise ValidationError("Only an unpaid purchase awaiting payment can expire.")
    if purchase.payment_window_expires_at is None or now < purchase.payment_window_expires_at:
        raise ValidationError("This purchase payment window has not expired.")
    if purchase.amount_paid > ZERO or ConfirmedReceipt.objects.filter(
        **_receipt_filter(purchase.id)
    ).exists():
        raise ValidationError("Confirmed money must be reconciled before expiry.")
    for intent in PaymentIntent.objects.filter(
        **_intent_filter(purchase.id),
        status__in=[PaymentIntent.STATUS.CREATED, PaymentIntent.STATUS.PROCESSING],
    ):
        if intent.expires_at is None or intent.expires_at > now:
            raise ValidationError("A payment request is still live beyond purchase expiry.")
        expire_payment_intent(intent=intent, at=now)
    # Re-check after waiting on any open intent locks; a concurrent provider
    # confirmation may have committed a receipt while expiry was in progress.
    if ConfirmedReceipt.objects.filter(**_receipt_filter(purchase.id)).exists():
        raise ValidationError("Confirmed money must be reconciled before expiry.")

    purchase.status = PropertyPurchase.STATUS_EXPIRED
    purchase.next_payment_due_at = None
    purchase.save(update_fields=["status", "next_payment_due_at", "updated_at"])
    return purchase


@transaction.atomic
def default_property_purchase(*, purchase_id, at=None):
    purchase = _lock_purchase(purchase_id)
    prop = Property.objects.select_for_update().get(id=purchase.property_id)
    now = at or timezone.now()
    if purchase.status == PropertyPurchase.STATUS_DEFAULTED:
        return purchase
    if purchase.status != PropertyPurchase.STATUS_INSTALLMENT_ACTIVE:
        raise ValidationError("Only an active installment purchase can be defaulted.")
    if purchase.next_payment_due_at is None:
        raise ValidationError("This installment purchase has no next due date.")
    deadline = purchase.next_payment_due_at + timedelta(hours=purchase.payment_window_hours)
    if now <= deadline:
        raise ValidationError("The next installment is still within its payment window.")
    if ConfirmedReceipt.objects.filter(
        **_receipt_filter(purchase.id), applied_at__isnull=True
    ).exists():
        raise ValidationError("A confirmed receipt is waiting to be applied.")

    for intent in PaymentIntent.objects.filter(
        **_intent_filter(purchase.id),
        status__in=[PaymentIntent.STATUS.CREATED, PaymentIntent.STATUS.PROCESSING],
    ):
        if intent.expires_at is None or intent.expires_at > now:
            raise ValidationError("A payment request is still live beyond installment default.")
        expire_payment_intent(intent=intent, at=now)

    # Re-check after serializing against any provider confirmation that held
    # the intent row while this default transaction was waiting.
    if ConfirmedReceipt.objects.filter(
        **_receipt_filter(purchase.id), applied_at__isnull=True
    ).exists():
        raise ValidationError("A confirmed receipt is waiting to be applied.")

    purchase.status = PropertyPurchase.STATUS_DEFAULTED
    purchase.save(update_fields=["status", "updated_at"])
    enqueue_default_message(purchase=purchase)
    # Keep next_payment_due_at as the reconciliation deadline snapshot.
    # Money may already exist, so default never releases inventory for resale.
    prop.status = "hold"
    prop.owner = None
    prop.full_clean()
    prop.save(update_fields=["status", "owner", "updated_at"])
    return purchase


@transaction.atomic
def apply_property_purchase_receipt(receipt):
    seed = ConfirmedReceipt.objects.select_related("intent").get(id=receipt.id)
    if seed.intent.purpose_type != PROPERTY_PURCHASE_PURPOSE_TYPE:
        raise ValidationError("Receipt is not for a Real Estate property purchase.")
    try:
        purchase_id = int(seed.intent.purpose_id)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Receipt purpose has an invalid purchase id.") from exc

    # Purchase row is the settlement serialization lock for all receipts.
    purchase = _lock_purchase(purchase_id)
    prop = Property.objects.select_for_update().get(id=purchase.property_id)
    receipt = (
        ConfirmedReceipt.objects.select_for_update()
        .select_related("intent")
        .get(id=receipt.id)
    )
    if receipt.applied_at is not None:
        return purchase
    if receipt.finance_posted_at is None:
        raise ValidationError("Finance posting must complete before Real Estate settlement.")
    if receipt.intent.status != PaymentIntent.STATUS.CONFIRMED:
        raise ValidationError("Only confirmed payment intents can settle purchases.")
    if receipt.amount <= ZERO:
        raise ValidationError("Settlement receipt amount must be positive.")

    if purchase.status == PropertyPurchase.STATUS_EXPIRED:
        if (
            purchase.payment_window_expires_at is None
            or receipt.paid_at > purchase.payment_window_expires_at
        ):
            raise ValidationError("Late payment after expiry requires reconciliation.")
        # Provider webhook may arrive after local expiry even when paid on time.
        purchase.status = PropertyPurchase.STATUS_AWAITING_PAYMENT

    if purchase.status == PropertyPurchase.STATUS_CANCELLED:
        raise ValidationError("Cancelled purchase money requires reconciliation.")

    if purchase.status == PropertyPurchase.STATUS_DEFAULTED:
        if (
            purchase.next_payment_due_at is None
            or receipt.paid_at
            > purchase.next_payment_due_at
            + timedelta(hours=purchase.payment_window_hours)
        ):
            raise ValidationError("Payment after installment default requires reconciliation.")
        # Provider notification was delayed, but the customer paid inside the
        # due+grace window. Resume settlement from the active installment state.
        purchase.status = PropertyPurchase.STATUS_INSTALLMENT_ACTIVE
    if purchase.status == PropertyPurchase.STATUS_AWAITING_APPROVAL:
        raise ValidationError("Unapproved purchase cannot receive settlement.")
    if purchase.status == PropertyPurchase.STATUS_FULLY_PAID:
        raise ValidationError("Purchase is already fully paid.")

    new_total = money(purchase.amount_paid + receipt.amount)
    agreed = money(purchase.agreed_price)
    if new_total > agreed:
        raise ValidationError("Receipt would overpay the agreed purchase price.")

    previous_status = purchase.status
    purchase.amount_paid = new_total
    display_name = _holder(purchase)

    if new_total == agreed:
        if prop.status not in {"available", "reserved"}:
            raise ValidationError("Property state conflicts with final settlement.")
        if prop.owner_id not in {None, purchase.client.user_id}:
            raise ValidationError("Property already belongs to another owner.")
        purchase.status = PropertyPurchase.STATUS_FULLY_PAID
        purchase.completed_at = receipt.paid_at
        purchase.next_payment_due_at = None
        prop.status = "sold"
        prop.owner = purchase.client.user
        prop.client_name = display_name
    elif purchase.mode == PropertyPurchase.MODE_RESERVATION:
        if purchase.reservation_amount is None:
            raise ValidationError("Reservation threshold snapshot is missing.")
        if new_total >= money(purchase.reservation_amount):
            purchase.status = PropertyPurchase.STATUS_RESERVED
            purchase.reserved_at = purchase.reserved_at or receipt.paid_at
            purchase.next_payment_due_at = None
            prop.status = "reserved"
            prop.owner = None
            prop.client_name = display_name
        else:
            purchase.status = PropertyPurchase.STATUS_AWAITING_PAYMENT
    elif purchase.mode == PropertyPurchase.MODE_INSTALLMENT:
        threshold_ok = (
            purchase.reservation_amount is None
            or new_total >= money(purchase.reservation_amount)
        )
        if threshold_ok:
            purchase.status = PropertyPurchase.STATUS_INSTALLMENT_ACTIVE
            purchase.reserved_at = purchase.reserved_at or receipt.paid_at
            applied_after = (
                ConfirmedReceipt.objects.filter(
                    **_receipt_filter(purchase.id), applied_at__isnull=False
                ).count()
                + 1
            )
            purchase.next_payment_due_at = purchase.reserved_at + relativedelta(
                months=applied_after
            )
            prop.status = "reserved"
            prop.owner = None
            prop.client_name = display_name
        else:
            purchase.status = PropertyPurchase.STATUS_AWAITING_PAYMENT
    else:
        purchase.status = PropertyPurchase.STATUS_AWAITING_PAYMENT

    purchase.full_clean()
    purchase.save(
        update_fields=[
            "amount_paid",
            "status",
            "reserved_at",
            "completed_at",
            "next_payment_due_at",
            "updated_at",
        ]
    )
    prop.full_clean()
    prop.save(update_fields=["status", "owner", "client_name", "updated_at"])

    receipt.application_reference = (
        f"real-estate:property-purchase:{purchase.id}:receipt:{receipt.reference}"
    )
    receipt.applied_at = timezone.now()
    receipt.save(
        update_fields=["application_reference", "applied_at", "updated_at"]
    )
    enqueue_payment_receipt_message(purchase=purchase, receipt=receipt)
    if (
        purchase.status in {
            PropertyPurchase.STATUS_RESERVED,
            PropertyPurchase.STATUS_INSTALLMENT_ACTIVE,
        }
        and previous_status not in {
            PropertyPurchase.STATUS_RESERVED,
            PropertyPurchase.STATUS_INSTALLMENT_ACTIVE,
        }
    ):
        enqueue_reservation_message(purchase=purchase, receipt=receipt)
    if purchase.status == PropertyPurchase.STATUS_FULLY_PAID:
        enqueue_sale_completion_message(purchase=purchase, receipt=receipt)
    return purchase
