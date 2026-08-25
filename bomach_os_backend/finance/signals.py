from decimal import Decimal

from django.db.models import Sum
from django.db.models.signals import post_save, pre_save

from finance.models import (
    FinanceSettings,
    JournalEntry,
    PayrollRun,
    PettyCashAdvance,
    StatutoryObligation,
    VendorBill,
)
from finance.service.audit import record_finance_audit
from finance.transactions.expense import Expense
from finance.transactions.payment_submission import PaymentSubmission

STATUS_MODELS = (
    VendorBill,
    Expense,
    PettyCashAdvance,
    PaymentSubmission,
    PayrollRun,
    StatutoryObligation,
)

SETTINGS_FIELDS = (
    "financial_year_start_month",
    "closed_through_date",
    "journal_prefix",
    "draft_journal_warning_days",
    "large_manual_journal_review_threshold",
)


def _capture_previous_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._finance_previous_status = None
        return
    instance._finance_previous_status = (
        sender.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
    )


def _capture_journal_status(sender, instance, **kwargs):
    _capture_previous_status(sender, instance, **kwargs)


def _capture_settings(sender, instance, **kwargs):
    if not instance.pk:
        instance._finance_previous_settings = {}
        return
    previous = sender.objects.filter(pk=instance.pk).values(*SETTINGS_FIELDS).first()
    instance._finance_previous_settings = previous or {}


def _transition_actor(instance, field):
    if field == "_finance_audit_actor":
        return getattr(instance, field, None)
    return getattr(instance, field, None)


def _transition_reference(instance):
    for field in (
        "bill_number",
        "expense_number",
        "advance_number",
        "reference",
        "run_number",
        "obligation_number",
    ):
        value = getattr(instance, field, "")
        if value:
            return str(value)
    return ""


def _transition_amount(instance):
    for field in (
        "net_amount",
        "amount",
        "amount_requested",
        "net_pay",
    ):
        value = getattr(instance, field, None)
        if value is not None:
            return value
    return None


TRANSITIONS = {
    VendorBill: {
        VendorBill.STATUS.APPROVED: ("vendor_bills", "approved", "approved_by"),
        VendorBill.STATUS.REJECTED: ("vendor_bills", "rejected", "rejected_by"),
        VendorBill.STATUS.VOID: ("vendor_bills", "voided", "_finance_audit_actor"),
    },
    Expense: {
        Expense.STATUS.APPROVED: ("expenses", "approved", "approved_by"),
        Expense.STATUS.REJECTED: ("expenses", "rejected", "rejected_by"),
    },
    PettyCashAdvance: {
        PettyCashAdvance.STATUS.APPROVED: ("petty_cash", "approved", "approved_by"),
        PettyCashAdvance.STATUS.REJECTED: ("petty_cash", "rejected", "rejected_by"),
        PettyCashAdvance.STATUS.CANCELLED: (
            "petty_cash",
            "cancelled",
            "_finance_audit_actor",
        ),
    },
    PaymentSubmission: {
        PaymentSubmission.STATUS.REJECTED: ("payments", "rejected", "reviewed_by"),
    },
    PayrollRun: {
        PayrollRun.STATUS.AWAITING_APPROVAL: ("payroll", "submitted", "submitted_by"),
        PayrollRun.STATUS.APPROVED: ("payroll", "approved", "approved_by"),
        PayrollRun.STATUS.REJECTED: ("payroll", "rejected", "rejected_by"),
        PayrollRun.STATUS.CANCELLED: ("payroll", "cancelled", "cancelled_by"),
    },
    StatutoryObligation: {
        StatutoryObligation.STATUS.PENDING_APPROVAL: (
            "statutory",
            "submitted",
            "submitted_by",
        ),
        StatutoryObligation.STATUS.APPROVED: (
            "statutory",
            "approved",
            "approved_by",
        ),
        StatutoryObligation.STATUS.REJECTED: (
            "statutory",
            "rejected",
            "rejected_by",
        ),
        StatutoryObligation.STATUS.VOID: (
            "statutory",
            "voided",
            "_finance_audit_actor",
        ),
    },
}


def _audit_status_transition(sender, instance, created, **kwargs):
    if created:
        return
    previous = getattr(instance, "_finance_previous_status", None)
    current = getattr(instance, "status", None)
    if previous == current:
        return

    transition = TRANSITIONS.get(sender, {}).get(current)
    if not transition:
        return

    area, action, actor_field = transition
    actor = _transition_actor(instance, actor_field)
    details = {"from_status": previous, "to_status": current}

    for reason_field in (
        "rejection_reason",
        "cancellation_reason",
    ):
        value = getattr(instance, reason_field, "")
        if value:
            details["reason"] = value
            break

    record_finance_audit(
        area=area,
        action=action,
        actor=actor,
        entity=instance,
        reference=_transition_reference(instance),
        amount=_transition_amount(instance),
        details=details,
    )


def _journal_business_event(entry):
    if entry.entry_type == JournalEntry.ENTRY_TYPE.MANUAL:
        return "journals", "posted", entry.journal_number
    if entry.entry_type == JournalEntry.ENTRY_TYPE.REVERSAL:
        return "journals", "reversed", entry.journal_number
    if entry.entry_type == JournalEntry.ENTRY_TYPE.OPENING:
        return "journals", "opening_posted", entry.journal_number

    source_type = entry.source_type
    source_event = entry.source_event

    if source_type == "payment" and source_event == "confirmed":
        return "payments", "confirmed", entry.reference or entry.journal_number
    if source_type == "expense" and source_event == "paid":
        return "expenses", "paid", entry.reference or entry.journal_number
    if source_type == "vendor_bill" and source_event == "paid":
        return "vendor_bills", "paid", entry.reference or entry.journal_number
    if source_type == "petty_cash_advance" and source_event == "issued":
        return "petty_cash", "issued", entry.reference or entry.journal_number
    if source_type == "petty_cash_retirement_line":
        return "petty_cash", source_event, entry.reference or entry.journal_number
    if source_type == "payroll_run" and source_event == "paid":
        return "payroll", "paid", entry.reference or entry.journal_number
    if source_type == "statutory_obligation" and source_event == "paid":
        return "statutory", "paid", entry.reference or entry.journal_number
    if source_type == "fixed_asset":
        if source_event == "capitalization":
            return (
                "fixed_assets",
                "capitalized",
                entry.reference or entry.journal_number,
            )
        if source_event.startswith("depreciation:"):
            return (
                "fixed_assets",
                "depreciated",
                entry.reference or entry.journal_number,
            )
        if source_event == "disposal":
            return "fixed_assets", "disposed", entry.reference or entry.journal_number

    return "journals", "automatic_posted", entry.journal_number


def _audit_posted_journal(sender, instance, created, **kwargs):
    if created:
        return
    previous = getattr(instance, "_finance_previous_status", None)
    if previous == JournalEntry.STATUS.POSTED:
        return
    if instance.status != JournalEntry.STATUS.POSTED:
        return

    area, action, reference = _journal_business_event(instance)
    amount = (
        instance.lines.aggregate(total=Sum("debit"))["total"] or Decimal("0.00")
    ).quantize(Decimal("0.01"))

    record_finance_audit(
        area=area,
        action=action,
        actor=instance.posted_by or instance.created_by,
        entity=instance,
        reference=reference,
        branch=instance.branch,
        amount=amount,
        details={
            "journal_number": instance.journal_number,
            "entry_type": instance.entry_type,
            "source_type": instance.source_type,
            "source_id": instance.source_id,
            "source_event": instance.source_event,
        },
    )


def _audit_settings_update(sender, instance, created, **kwargs):
    if created or not instance.updated_by_id:
        return

    previous = getattr(instance, "_finance_previous_settings", {})
    changes = {}
    for field in SETTINGS_FIELDS:
        before = previous.get(field)
        after = getattr(instance, field)
        if before != after:
            changes[field] = {"from": before, "to": after}

    if not changes:
        return

    record_finance_audit(
        area="finance_settings",
        action="updated",
        actor=instance.updated_by,
        entity=instance,
        reference="Finance Settings",
        details={"changes": changes},
    )


for model in STATUS_MODELS:
    pre_save.connect(
        _capture_previous_status,
        sender=model,
        dispatch_uid=f"finance_audit_capture_{model._meta.label_lower}",
    )
    post_save.connect(
        _audit_status_transition,
        sender=model,
        dispatch_uid=f"finance_audit_transition_{model._meta.label_lower}",
    )

pre_save.connect(
    _capture_journal_status,
    sender=JournalEntry,
    dispatch_uid="finance_audit_capture_journal_status",
)
post_save.connect(
    _audit_posted_journal,
    sender=JournalEntry,
    dispatch_uid="finance_audit_posted_journal",
)

pre_save.connect(
    _capture_settings,
    sender=FinanceSettings,
    dispatch_uid="finance_audit_capture_settings",
)
post_save.connect(
    _audit_settings_update,
    sender=FinanceSettings,
    dispatch_uid="finance_audit_settings_update",
)
