from datetime import timedelta

from django.utils import timezone

from domains.real_estate.models.property_purchase import PropertyPurchase
from system.notifications.outbox import enqueue_user_message


def _user(purchase):
    return purchase.client.user


def _property_name(purchase):
    return purchase.property.property_name


def enqueue_payment_request_message(*, purchase, intent, attempt):
    return enqueue_user_message(
        event_key=f"real-estate:purchase:{purchase.id}:intent:{intent.reference}:payment-request",
        event_type="real_estate.payment_request",
        user=_user(purchase),
        subject=f"Payment request for {_property_name(purchase)}",
        body=(
            f"A payment request of {attempt.amount:,.2f} {attempt.currency} is ready for "
            f"{_property_name(purchase)}. Payment reference: "
            f"{attempt.provider_reference or attempt.reference}."
        ),
        link=attempt.checkout_url or "",
        metadata={
            "purchase_id": purchase.id,
            "property_id": purchase.property_id,
            "intent_reference": intent.reference,
            "attempt_reference": attempt.reference,
            "amount": str(attempt.amount),
            "currency": attempt.currency,
            "checkout_url": attempt.checkout_url,
            "expires_at": intent.expires_at.isoformat() if intent.expires_at else None,
            "notification_type": "info",
        },
    )


def enqueue_payment_receipt_message(*, purchase, receipt):
    return enqueue_user_message(
        event_key=f"real-estate:purchase:{purchase.id}:receipt:{receipt.reference}:received",
        event_type="real_estate.payment_received",
        user=_user(purchase),
        subject=f"Payment received for {_property_name(purchase)}",
        body=(
            f"We received {receipt.amount:,.2f} {receipt.currency} for "
            f"{_property_name(purchase)}. Receipt reference: {receipt.reference}."
        ),
        metadata={
            "purchase_id": purchase.id,
            "receipt_reference": receipt.reference,
            "provider": receipt.provider,
            "provider_transaction_reference": receipt.provider_transaction_reference,
            "amount": str(receipt.amount),
            "currency": receipt.currency,
            "paid_at": receipt.paid_at.isoformat(),
            "notification_type": "success",
        },
    )


def enqueue_reservation_message(*, purchase, receipt):
    return enqueue_user_message(
        event_key=f"real-estate:purchase:{purchase.id}:reservation-confirmed",
        event_type="real_estate.reservation_confirmed",
        user=_user(purchase),
        subject=f"Reservation confirmed for {_property_name(purchase)}",
        body=(
            f"Your reservation for {_property_name(purchase)} is confirmed. "
            f"Total verified payments: {purchase.amount_paid:,.2f} NGN."
        ),
        metadata={
            "purchase_id": purchase.id,
            "receipt_reference": receipt.reference,
            "amount_paid": str(purchase.amount_paid),
            "notification_type": "success",
        },
    )


def enqueue_sale_completion_message(*, purchase, receipt):
    return enqueue_user_message(
        event_key=f"real-estate:purchase:{purchase.id}:sale-completed",
        event_type="real_estate.sale_completed",
        user=_user(purchase),
        subject=f"Purchase completed for {_property_name(purchase)}",
        body=(
            f"Your purchase of {_property_name(purchase)} is fully paid and completed. "
            f"Total paid: {purchase.amount_paid:,.2f} NGN."
        ),
        metadata={
            "purchase_id": purchase.id,
            "receipt_reference": receipt.reference,
            "amount_paid": str(purchase.amount_paid),
            "notification_type": "success",
        },
    )


def enqueue_default_message(*, purchase):
    return enqueue_user_message(
        event_key=f"real-estate:purchase:{purchase.id}:defaulted",
        event_type="real_estate.installment_defaulted",
        user=_user(purchase),
        subject=f"Installment payment overdue for {_property_name(purchase)}",
        body=(
            f"Your installment purchase for {_property_name(purchase)} is overdue "
            "and requires reconciliation."
        ),
        metadata={
            "purchase_id": purchase.id,
            "next_payment_due_at": (
                purchase.next_payment_due_at.isoformat()
                if purchase.next_payment_due_at else None
            ),
            "notification_type": "warning",
        },
    )


def enqueue_due_installment_reminders(*, at=None, lookahead_hours=24):
    now = at or timezone.now()
    until = now + timedelta(hours=int(lookahead_hours))
    queued = 0
    purchases = (
        PropertyPurchase.objects.filter(
            status=PropertyPurchase.STATUS_INSTALLMENT_ACTIVE,
            next_payment_due_at__isnull=False,
            next_payment_due_at__gte=now,
            next_payment_due_at__lte=until,
        )
        .select_related("client__user", "property")
        .order_by("next_payment_due_at")
    )
    for purchase in purchases:
        due_key = purchase.next_payment_due_at.isoformat()
        rows = enqueue_user_message(
            event_key=f"real-estate:purchase:{purchase.id}:installment-reminder:{due_key}",
            event_type="real_estate.installment_reminder",
            user=_user(purchase),
            subject=f"Upcoming installment for {_property_name(purchase)}",
            body=(
                f"Your next installment for {_property_name(purchase)} is due "
                f"{purchase.next_payment_due_at:%Y-%m-%d %H:%M %Z}."
            ),
            metadata={
                "purchase_id": purchase.id,
                "next_payment_due_at": due_key,
                "notification_type": "info",
            },
        )
        queued += len(rows)
    return queued
