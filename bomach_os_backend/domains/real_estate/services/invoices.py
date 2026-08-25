import hashlib
import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from finance.service import post_external_receipt_journal, resolve_receipt_finance_account
from domains.real_estate.models.estate import Property
from domains.real_estate.models.estate_property_invoice import (
    EstatePropertyInvoice,
    EstatePropertyInvoiceItem,
    InvoiceApproval,
)
from domains.people.models.employee import Employee
from user.models.user import User

ZERO = Decimal("0.00")


def _branch_id_for_user(user):
    try:
        return user.employee_profile.branch_id
    except Employee.DoesNotExist:
        return None


def _reservation_holder(user):
    full_name = (user.get_full_name() or "").strip()
    return full_name or user.email or str(user)


def create_estate_invoice(*, created_by, payload):
    if not payload.items:
        raise ValidationError({"items": "At least one property is required."})
    property_ids = [item.property_id for item in payload.items]
    if len(property_ids) != len(set(property_ids)):
        raise ValidationError(
            {"items": "The same property cannot appear twice on one invoice."}
        )

    with transaction.atomic():
        try:
            client = User.objects.get(id=payload.client_id)
        except User.DoesNotExist as exc:
            raise ValidationError({"client_id": "Client not found."}) from exc

        locked = list(
            Property.objects.select_for_update()
            .select_related("estate")
            .filter(id__in=property_ids)
        )
        by_id = {prop.id: prop for prop in locked}
        if len(by_id) != len(property_ids):
            missing = sorted(set(property_ids) - set(by_id))
            raise ValidationError({"items": f"Property not found: {missing[0]}."})

        validated = []
        for item in payload.items:
            prop = by_id[item.property_id]
            if prop.status != "available":
                raise ValidationError(
                    {"items": f"Property '{prop.property_name}' is not available for sale."}
                )
            quantity = item.quantity or 1
            if quantity != 1:
                raise ValidationError(
                    {"items": "Each estate invoice item must have quantity 1."}
                )
            unit_price = item.unit_price if item.unit_price is not None else prop.price
            if unit_price <= ZERO:
                raise ValidationError(
                    {"items": f"Unit price for '{prop.property_name}' must be greater than zero."}
                )
            validated.append((item, prop, unit_price))

        data = payload.dict(exclude={"client_id", "items", "approvers"})
        data = {key: value for key, value in data.items() if value is not None}
        invoice = EstatePropertyInvoice.objects.create(
            **data,
            client=client,
            created_by=created_by,
            status="draft",
        )
        for item, prop, unit_price in validated:
            EstatePropertyInvoiceItem.objects.create(
                invoice=invoice,
                property=prop,
                description=item.description or "",
                unit_price=unit_price,
                quantity=1,
            )
        invoice.recalculate_subtotal()
        invoice.refresh_from_db()
        invoice.full_clean()
        return invoice


def update_estate_invoice(invoice, payload):
    with transaction.atomic():
        invoice = EstatePropertyInvoice.objects.select_for_update().get(id=invoice.id)
        if invoice.status != "draft":
            raise ValidationError("You can only update a draft invoice.")
        if invoice.approvals.exists():
            raise ValidationError(
                "A submitted invoice cannot be edited while approval is in progress."
            )
        data = payload.dict(exclude_unset=True)
        if {"status", "payment_completed_date"}.intersection(data):
            raise ValidationError(
                "Invoice status/payment state can only change through the workflow."
            )
        for field, value in data.items():
            if value is not None:
                setattr(invoice, field, value)
        invoice.full_clean()
        invoice.save()
        invoice.refresh_from_db()
        return invoice


def delete_estate_invoice(invoice):
    with transaction.atomic():
        invoice = EstatePropertyInvoice.objects.select_for_update().get(id=invoice.id)
        if invoice.status != "draft":
            raise ValidationError("You can only delete a draft invoice.")
        if invoice.approvals.exists():
            raise ValidationError(
                "A submitted invoice cannot be deleted while approval is in progress."
            )
        invoice.delete()


def _resolve_invoice_approvers(submitted_by):
    try:
        creator = (
            Employee.objects.select_related(
                "branch", "role", "reporting_to", "reporting_to__user", "reporting_to__role"
            )
            .get(user=submitted_by)
        )
    except Employee.DoesNotExist as exc:
        raise ValidationError(
            "The invoice creator must have an active employee profile."
        ) from exc
    if creator.employment_status != "active":
        raise ValidationError("The invoice creator's employee profile is not active.")

    manager_employee = creator.reporting_to
    if (
        manager_employee
        and manager_employee.user_id != submitted_by.id
        and manager_employee.employment_status == "active"
        and manager_employee.role_id
    ):
        manager = manager_employee.user
    else:
        qs = (
            Employee.objects.select_related("user", "role")
            .filter(employment_status="active", role__isnull=False)
            .exclude(user_id=submitted_by.id)
        )
        qs = (
            qs.filter(branch_id=creator.branch_id)
            if creator.branch_id
            else qs.filter(branch__isnull=True)
        )
        manager_employee = qs.order_by("id").first()
        manager = manager_employee.user if manager_employee else None
    if not manager:
        raise ValidationError("No active manager is available to approve this invoice.")

    final_employee = (
        Employee.objects.select_related("user", "role")
        .filter(
            employment_status="active",
            role__isnull=False,
            role__branches__isnull=True,
        )
        .exclude(user_id__in=[submitted_by.id, manager.id])
        .distinct()
        .order_by("id")
        .first()
    )
    final_approver = final_employee.user if final_employee else None
    if not final_approver:
        raise ValidationError(
            "No company-wide final approver is available for this invoice."
        )
    return manager, final_approver, creator.branch_id


def _lock_invoice_properties(invoice):
    property_ids = list(invoice.estate_invoice_items.values_list("property_id", flat=True))
    return list(
        Property.objects.select_for_update().filter(id__in=property_ids).order_by("id")
    )


def _reserve_invoice_properties(invoice):
    properties = _lock_invoice_properties(invoice)
    if not properties:
        raise ValidationError("Cannot submit an invoice with no properties.")
    holder = _reservation_holder(invoice.client)
    for prop in properties:
        if prop.status != "available" or prop.owner_id:
            raise ValidationError(
                f"Property '{prop.property_name}' is no longer available for this invoice."
            )
    for prop in properties:
        prop.status = "reserved"
        prop.client_name = holder
        prop.save(update_fields=["status", "client_name", "updated_at"])
    return properties


def _release_invoice_reservations(invoice):
    holder = _reservation_holder(invoice.client)
    for prop in _lock_invoice_properties(invoice):
        if prop.status == "reserved" and prop.owner_id is None and prop.client_name == holder:
            prop.status = "available"
            prop.client_name = ""
            prop.save(update_fields=["status", "client_name", "updated_at"])


def _payment_account_for_invoice(invoice, finance_account_id=None):
    return resolve_receipt_finance_account(
        finance_account_id,
        branch_id=_branch_id_for_user(invoice.created_by),
        currency="NGN",
    )


def submit_estate_invoice(invoice, *, submitted_by):
    with transaction.atomic():
        invoice = (
            EstatePropertyInvoice.objects.select_for_update()
            .select_related("client", "created_by")
            .get(id=invoice.id)
        )
        if invoice.status != "draft":
            raise ValidationError("Only draft invoices can be submitted for approval.")
        if invoice.approvals.exists():
            raise ValidationError("Invoice has already been submitted for approval.")
        if not invoice.estate_invoice_items.exists():
            raise ValidationError("Cannot submit an invoice with no items.")

        manager, final_approver, branch_id = _resolve_invoice_approvers(submitted_by)
        account = resolve_receipt_finance_account(branch_id=branch_id, currency="NGN")
        _reserve_invoice_properties(invoice)
        InvoiceApproval.objects.create(
            invoice=invoice, step=1, step_name="Manager Approval", assigned_to=manager
        )
        InvoiceApproval.objects.create(
            invoice=invoice, step=2, step_name="Final Approval", assigned_to=final_approver
        )
        invoice.generate_payment_details(account)
        invoice.refresh_from_db()
        return invoice


def decide_estate_invoice_approval(invoice, *, step, decision, comment, decided_by):
    if decision not in {"approved", "rejected"}:
        raise ValidationError("Decision must be 'approved' or 'rejected'.")
    with transaction.atomic():
        invoice = (
            EstatePropertyInvoice.objects.select_for_update()
            .select_related("client", "created_by")
            .get(id=invoice.id)
        )
        if invoice.status in {"cancelled", "paid"}:
            raise ValidationError(f"Cannot approve an invoice in '{invoice.status}' status.")
        try:
            approval = (
                InvoiceApproval.objects.select_for_update()
                .select_related("assigned_to")
                .get(invoice=invoice, step=step)
            )
        except InvoiceApproval.DoesNotExist as exc:
            raise ValidationError(f"Approval step {step} does not exist.") from exc
        if approval.decision != "pending":
            raise ValidationError(f"Step {step} has already been decided.")
        if step > 1:
            previous = InvoiceApproval.objects.filter(invoice=invoice, step=step - 1).first()
            if not previous or previous.decision != "approved":
                raise ValidationError("Previous approval step must be approved first.")
        if approval.assigned_to_id and approval.assigned_to_id != decided_by.id:
            label = approval.assigned_to.get_full_name() or str(approval.assigned_to)
            raise ValidationError(
                f"This approval step is assigned to {label}. Only they can decide it."
            )
        approval.decision = decision
        approval.decided_by = decided_by
        approval.decided_at = timezone.now()
        approval.comment = comment or ""
        approval.save(
            update_fields=["decision", "decided_by", "decided_at", "comment", "updated_at"]
        )
        if decision == "rejected":
            invoice.status = "cancelled"
            invoice.save(update_fields=["status", "updated_at"])
            _release_invoice_reservations(invoice)
            invoice.refresh_from_db()
            return invoice, False
        if invoice.approvals.filter(decision="pending").exists():
            invoice.refresh_from_db()
            return invoice, False
        account = _payment_account_for_invoice(invoice)
        invoice.generate_payment_details(account)
        invoice.status = "sent"
        invoice.save(update_fields=["status", "updated_at"])
        invoice.refresh_from_db()
        return invoice, True


def _receipt_identity(invoice, payment_reference):
    reference = (payment_reference or "").strip()
    if not reference:
        reference = f"RE-{invoice.invoice_number}-{uuid.uuid4().hex[:10].upper()}"
    digest = hashlib.sha256(f"{invoice.id}:{reference}".encode("utf-8")).hexdigest()[:48]
    return reference, digest


def record_estate_invoice_payment(
    invoice,
    *,
    amount,
    recorded_by,
    finance_account_id=None,
    payment_date=None,
    payment_reference="",
):
    with transaction.atomic():
        invoice = (
            EstatePropertyInvoice.objects.select_for_update()
            .select_related("client", "created_by")
            .get(id=invoice.id)
        )
        if invoice.status not in {"sent", "partially_paid", "paid"}:
            raise ValidationError(
                "Payments can only be recorded on sent or partially paid invoices. "
                f"Current status: '{invoice.status}'."
            )
        amount = Decimal(amount)
        if amount <= ZERO:
            raise ValidationError("Payment amount must be greater than zero.")

        properties = _lock_invoice_properties(invoice)
        holder = _reservation_holder(invoice.client)
        for prop in properties:
            if prop.owner_id and prop.owner_id != invoice.client_id:
                raise ValidationError(
                    f"Property '{prop.property_name}' is already owned by another client."
                )
            if prop.status in {"not-for-sale", "hold"}:
                raise ValidationError(
                    f"Property '{prop.property_name}' cannot receive payment in its current status."
                )
            if prop.status == "sold" and prop.owner_id != invoice.client_id:
                raise ValidationError(f"Property '{prop.property_name}' is already sold.")

        account = _payment_account_for_invoice(invoice, finance_account_id)
        reference, receipt_id = _receipt_identity(invoice, payment_reference)
        branch = account.branch
        try:
            branch = invoice.created_by.employee_profile.branch or account.branch
        except Employee.DoesNotExist:
            pass

        _, created = post_external_receipt_journal(
            source_type="real_estate_payment",
            source_id=receipt_id,
            source_event="confirmed",
            finance_account=account,
            amount=amount,
            total_due=invoice.total_amount,
            total_tax=invoice.tax_amount,
            prior_paid=invoice.amount_paid,
            entry_date=payment_date or timezone.localdate(),
            reference=reference,
            memo=f"Real Estate receipt for {invoice.invoice_number}",
            branch=branch,
            created_by=recorded_by,
            revenue_account_code="4200",
        )
        if not created:
            invoice.refresh_from_db()
            return invoice

        for prop in properties:
            if prop.status == "available":
                prop.status = "reserved"
                prop.client_name = holder
                prop.save(update_fields=["status", "client_name", "updated_at"])

        invoice.amount_paid += amount
        if invoice.amount_paid == invoice.total_amount:
            invoice.status = "paid"
            invoice.payment_completed_date = payment_date or timezone.localdate()
            for prop in properties:
                prop.owner = invoice.client
                prop.status = "sold"
                prop.client_name = holder
                prop.save(
                    update_fields=["owner", "status", "client_name", "updated_at"]
                )
        else:
            invoice.status = "partially_paid"
        invoice.save(
            update_fields=["amount_paid", "status", "payment_completed_date", "updated_at"]
        )
        invoice.refresh_from_db()
        return invoice
