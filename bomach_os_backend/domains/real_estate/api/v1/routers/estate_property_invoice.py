from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

import user
from domains.real_estate.api.v1.schemas.estate_property_invoice import (
    ApprovalDecisionSchema,
    EstateInvoiceChoicesSchema,
    InvoiceCreateSchema,
    InvoiceSchema,
    InvoiceUpdateSchema,
    RecordPaymentSchema,
)
from shared.api.schema.others import MessageSchema
from domains.real_estate.models.estate import Property
from domains.real_estate.models.estate_property_invoice import (
    EstatePropertyInvoice,
    EstatePropertyInvoiceItem,
    InvoiceApproval,
)
from user.models.user import User
from user.utils.perm import require_permission, scope_queryset
from user.utils.send_email import send_invoice_email

estate_invoice_api = Router(tags=["Estate Property Invoices"])


# ============== Choices ==============


@estate_invoice_api.get("/choices/fields", response=EstateInvoiceChoicesSchema)
def get_invoice_field_choices(request):
    """Get available choices for estate invoice fields."""
    return {
        "invoice_status": [
            {"value": c[0], "label": c[1]}
            for c in EstatePropertyInvoice.INVOICE_STATUS_CHOICES
        ],
        "invoice_type": [
            {"value": c[0], "label": c[1]}
            for c in EstatePropertyInvoice.INVOICE_TYPE_CHOICES
        ],
    }


# ============== Invoice CRUD ==============


@estate_invoice_api.get("/", response=List[InvoiceSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("estate_invoices", "list")
def list_invoices(
    request,
    status: Optional[str] = Query(None),
    invoice_type: Optional[str] = Query(None),
    client_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    """List all estate property invoices with filtering and search."""
    invoices = EstatePropertyInvoice.objects.select_related(
        "client", "created_by"
    ).all()

    if status:
        invoices = invoices.filter(status=status)
    if invoice_type:
        invoices = invoices.filter(invoice_type=invoice_type)
    if client_id:
        invoices = invoices.filter(client_id=client_id)
    if search:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search) | Q(notes__icontains=search)
        )

    invoices = scope_queryset(
        request,
        invoices,
        owner_field="created_by",
        branch_field="created_by__employee_profile__branch",
    )

    return invoices.order_by("-created_at")


@estate_invoice_api.get("/pending-approvals", response=List[InvoiceSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("estate_invoices", "list")
def list_pending_approvals(
    request,
    search: Optional[str] = Query(None),
):
    """List invoices pending the current user's approval.

    Returns invoices where the current user is either:
    - Specifically assigned to a pending approval step, OR
    - Has the required level for a pending approval step (when no specific user is assigned)
      and all previous steps are already approved.
    """
    user = request.user

    # Invoices where the user is specifically assigned to a pending step
    assigned_invoices = EstatePropertyInvoice.objects.filter(
        approvals__assigned_to=user,
        approvals__decision="pending",
    )

    invoices = assigned_invoices.distinct().select_related("client", "created_by")

    if search:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search) | Q(notes__icontains=search)
        )

    return invoices.order_by("-created_at")


@estate_invoice_api.get(
    "/{invoice_id}", response={200: InvoiceSchema, 404: MessageSchema}
)
@require_permission("estate_invoices", "view")
def get_invoice(request, invoice_id: int):
    """Get a specific estate property invoice by ID."""
    try:
        invoice = (
            EstatePropertyInvoice.objects.select_related("client", "created_by")
            .prefetch_related("estate_invoice_items__property__estate")
            .get(id=invoice_id)
        )
        return 200, invoice
    except EstatePropertyInvoice.DoesNotExist:
        return 404, {"detail": "Invoice not found"}


@estate_invoice_api.post("/", response={201: InvoiceSchema, 400: MessageSchema})
@require_permission("estate_invoices", "create")
def create_invoice(request, payload: InvoiceCreateSchema):
    """Create a new estate property invoice with optional items and approvers.

    If `approvers` is provided, the invoice is created as 'draft' and approval
    steps are automatically created for each specified approver. Each approver
    entry requires: user_id, step (order), and step_name.

    If no approvers are provided and invoice_type is 'full-payment', the invoice
    is sent directly to the client.
    """
    try:
        client = get_object_or_404(User, id=payload.client_id)
        props_list = []
        for item_data in payload.items:
            prop = get_object_or_404(Property, id=item_data.property_id)
            props_list.append(prop)

            if prop.status in {"sold", "reserved", "not-for-sale"}:
                return 400, {
                    "detail": f"Property '{prop.property_name}' is not available for sale."
                }

        data = payload.dict(exclude={"client_id", "items", "approvers"})
        data = {k: v for k, v in data.items() if v is not None}

        status = "sent" if payload.invoice_type == "full-payment" else "draft"

        invoice = EstatePropertyInvoice.objects.create(
            **data,
            client=client,
            created_by=request.user,
            status=status,
        )

        # Create invoice items (properties)
        for prop in props_list:
            EstatePropertyInvoiceItem.objects.create(
                invoice=invoice,
                property=prop,
                description=item_data.description or "",
                unit_price=item_data.unit_price or prop.price,
                quantity=item_data.quantity,
            )

        # Recalculate subtotal from items
        if payload.items:
            invoice.recalculate_subtotal()

        invoice.generate_payment_details()

        # Create approval steps
        creator_employee = request.user.employee_profile
        creator_branch = creator_employee.branch

        # Step 1: Find a manager in the same branch (by reporting structure)
        manager_qs = User.objects.filter(
            employee_profile__employment_status="active",
            employee_profile__role__isnull=False,
        )
        if creator_branch:
            manager_qs = manager_qs.filter(employee_profile__branch=creator_branch)
        # Prefer the creator's direct manager if available
        if creator_employee.reporting_to:
            approver_manager = creator_employee.reporting_to.user
        else:
            approver_manager = manager_qs.exclude(id=request.user.id).first()
        if not approver_manager:
            return 400, {
                "detail": "No active manager found in your branch to approve this invoice."
            }

        # Step 2: Find a company-wide approver (role with no branch restriction)
        from user.models.role import Role

        company_wide_roles = Role.objects.filter(branches__isnull=True).exclude(
            branches__isnull=False
        )
        approver_ceo = (
            User.objects.filter(
                employee_profile__role__in=company_wide_roles,
                employee_profile__employment_status="active",
            )
            .exclude(id=approver_manager.id)
            .first()
        )
        if not approver_ceo:
            return 400, {
                "detail": "No company-wide approver found to approve this invoice."
            }

        InvoiceApproval.objects.create(
            invoice=invoice,
            step=1,
            step_name="Manager Approval",
            assigned_to=approver_manager,
        )

        InvoiceApproval.objects.create(
            invoice=invoice,
            step=2,
            step_name="Final Approval",
            assigned_to=approver_ceo,
        )

        invoice.refresh_from_db()

        # Only send email if no approval needed and full-payment
        if payload.invoice_type == "full-payment":
            send_invoice_email(invoice.client.email, invoice.client.first_name, invoice)

        return 201, invoice

    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@estate_invoice_api.put(
    "/{invoice_id}",
    response={200: InvoiceSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("estate_invoices", "update")
def update_invoice(request, invoice_id: int, payload: InvoiceUpdateSchema):
    """Update an existing estate property invoice."""
    try:
        invoice = get_object_or_404(EstatePropertyInvoice, id=invoice_id)
        if invoice.status != "draft":
            return 400, {"detail": "You can only update a draft invoice."}

        update_data = payload.dict(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:
                setattr(invoice, field, value)

        invoice.save()
        invoice.refresh_from_db()
        return 200, invoice

    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@estate_invoice_api.delete(
    "/{invoice_id}", response={200: MessageSchema, 404: MessageSchema}
)
@require_permission("estate_invoices", "delete")
def delete_invoice(request, invoice_id: int):
    """Delete an estate property invoice."""
    try:
        invoice = get_object_or_404(EstatePropertyInvoice, id=invoice_id)

        if invoice.status != "draft":
            return 400, {"detail": "You can only delete a draft invoice."}

        invoice.delete()
        return 200, {"detail": "Invoice deleted successfully"}

    except Exception as e:
        return 400, {"detail": str(e)}


# ============== Approval Flow ==============
# Flow: creator submits → Step 1 (Manager approves) → Step 2 (CEO approves) → status = 'sent'


@estate_invoice_api.post(
    "/{invoice_id}/submit-for-approval",
    response={200: InvoiceSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("estate_invoices", "submit_for_approval")
def submit_for_approval(request, invoice_id: int):
    """Submit a draft invoice for approval. Creates the 2-step approval chain."""
    try:
        invoice = get_object_or_404(EstatePropertyInvoice, id=invoice_id)

        if invoice.status != "draft":
            return 400, {"detail": "Only draft invoices can be submitted for approval."}

        if invoice.estate_invoice_items.count() == 0:
            return 400, {"detail": "Cannot submit an invoice with no items."}

        # Prevent duplicate submissions
        if invoice.approvals.exists():
            return 400, {"detail": "Invoice has already been submitted for approval."}

        # Create the two approval steps
        InvoiceApproval.objects.create(
            invoice=invoice,
            step=1,
            step_name="Manager Approval",
        )
        InvoiceApproval.objects.create(
            invoice=invoice,
            step=2,
            step_name="Final Approval",
        )

        invoice.status = "draft"  # remains draft until fully approved
        invoice.save(update_fields=["status", "updated_at"])
        invoice.refresh_from_db()
        return 200, invoice

    except Exception as e:
        return 400, {"detail": str(e)}


@estate_invoice_api.post(
    "/{invoice_id}/approvals/{step}/decide",
    response={200: InvoiceSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("estate_invoices", "approve")
def decide_approval(
    request, invoice_id: int, step: int, payload: ApprovalDecisionSchema
):
    """Approve or reject an approval step. Manager handles step 1, CEO handles step 2."""
    try:

        invoice = get_object_or_404(EstatePropertyInvoice, id=invoice_id)

        if invoice.status == "cancelled":
            return 400, {"detail": "Cannot act on a cancelled invoice."}

        approval = get_object_or_404(InvoiceApproval, invoice=invoice, step=step)

        if approval.decision != "pending":
            return 400, {"detail": f"Step {step} has already been decided."}

        # Ensure previous steps are approved before this one
        if step > 1:
            previous = InvoiceApproval.objects.filter(
                invoice=invoice, step=step - 1
            ).first()
            if not previous or previous.decision != "approved":
                return 400, {"detail": "Previous approval step must be approved first."}

        # Check the user is authorized to decide this step
        if approval.assigned_to and approval.assigned_to != request.user:
            return 400, {
                "detail": f"This approval step is assigned to {approval.assigned_to.get_full_name() or approval.assigned_to}. Only they can decide it."
            }

        # Record the decision
        approval.decision = payload.decision
        approval.decided_by = request.user
        approval.decided_at = timezone.now()
        approval.comment = payload.comment or ""
        approval.save()

        # Handle rejection — mark invoice cancelled
        if payload.decision == "rejected":
            invoice.status = "cancelled"
            invoice.save(update_fields=["status", "updated_at"])
            invoice.refresh_from_db()
            return 200, invoice

        # If approved and this is the last step, mark invoice as 'sent' and email client
        all_approved = not invoice.approvals.filter(decision="pending").exists()
        if all_approved:
            invoice.status = "sent"
            invoice.save(update_fields=["status", "updated_at"])
            send_invoice_email(invoice.client.email, invoice.client.first_name, invoice)

        invoice.refresh_from_db()
        return 200, invoice

    except Exception as e:
        return 400, {"detail": str(e)}


# ============== Payment ==============


@estate_invoice_api.post(
    "/{invoice_id}/record-payment",
    response={200: InvoiceSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("estate_invoices", "record_payment")
def record_payment(request, invoice_id: int, payload: RecordPaymentSchema):
    """Record a client payment (partial or full). Updates amount_paid on the invoice."""
    try:
        invoice = get_object_or_404(EstatePropertyInvoice, id=invoice_id)

        if invoice.status not in ("sent", "partially_paid"):
            return 400, {
                "detail": f"Payments can only be recorded on sent or partially paid invoices. Current status: '{invoice.status}'."
            }

        if payload.amount <= 0:
            return 400, {"detail": "Payment amount must be greater than zero."}

        invoice.amount_paid += payload.amount

        if invoice.amount_paid >= invoice.total_amount:
            invoice.status = "paid"
            invoice.payment_completed_date = timezone.now().date()

            # the property should now be assigned to the client and marked as sold
            for item in invoice.estate_invoice_items.select_related("property").all():
                prop = item.property
                prop.owner = invoice.client
                prop.status = "sold"
                prop.save(update_fields=["owner", "status", "updated_at"])

        else:
            invoice.status = "partially_paid"

        invoice.save(
            update_fields=[
                "amount_paid",
                "status",
                "payment_completed_date",
                "updated_at",
            ]
        )
        invoice.refresh_from_db()
        return 200, invoice

    except Exception as e:
        return 400, {"detail": str(e)}
