from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from domains.real_estate.models.property_purchase import PropertyPurchase
from system.payments.services import create_payment_intent
from user.models.employee import Employee

PURPOSE_TYPE = "real_estate_property_purchase"
REAL_ESTATE_REVENUE_ACCOUNT_CODE = "4200"


def _purchase_branch(purchase):
    try:
        return purchase.created_by.employee_profile.branch
    except Employee.DoesNotExist:
        return None


def create_property_purchase_payment_intent(
    purchase,
    *,
    amount,
    idempotency_key,
    expires_at=None,
    created_by=None,
):
    """Create a Central Payment intent without changing Real Estate state."""
    with transaction.atomic():
        purchase = (
            PropertyPurchase.objects.select_for_update()
            .select_related("property__estate", "client__user", "created_by")
            .get(id=purchase.id)
        )
        if purchase.status not in {
            PropertyPurchase.STATUS_AWAITING_PAYMENT,
            PropertyPurchase.STATUS_RESERVED,
            PropertyPurchase.STATUS_INSTALLMENT_ACTIVE,
        }:
            raise ValidationError(
                "Payment intents require an awaiting-payment, reserved or active-installment purchase."
            )
        amount = Decimal(str(amount))
        outstanding = purchase.agreed_price - purchase.amount_paid
        if amount <= Decimal("0.00"):
            raise ValidationError("Payment intent amount must be greater than zero.")
        if amount > outstanding:
            raise ValidationError("Payment intent amount exceeds the purchase balance.")
        expiry = expires_at or purchase.payment_window_expires_at
        return create_payment_intent(
            idempotency_key=idempotency_key,
            purpose_type=PURPOSE_TYPE,
            purpose_id=purchase.id,
            amount=amount,
            currency="NGN",
            description=f"Payment for {purchase.property.property_name}",
            metadata={
                "property_purchase_id": purchase.id,
                "property_id": purchase.property_id,
                "client_id": purchase.client_id,
                "mode": purchase.mode,
                "customer_email": purchase.client.user.email,
                "customer_name": purchase.client.user.get_full_name() or purchase.client.user.email,
            },
            expires_at=expiry,
            branch=_purchase_branch(purchase),
            created_by=created_by or purchase.created_by,
            accounting_total_due=purchase.agreed_price,
            accounting_total_tax=Decimal("0.00"),
            accounting_prior_paid=purchase.amount_paid,
            revenue_account_code=REAL_ESTATE_REVENUE_ACCOUNT_CODE,
        )
