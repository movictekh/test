from datetime import timedelta
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from finance.models import FinanceSettings, FixedAsset, JournalEntry, VendorBill
from finance.service.fixed_assets import depreciation_schedule

ZERO = Decimal("0.00")
CENT = Decimal("0.01")

OPEN_PAYABLE_STATUSES = {
    VendorBill.STATUS.AWAITING_APPROVAL,
    VendorBill.STATUS.APPROVED,
    VendorBill.STATUS.SCHEDULED,
}

SEVERITY_ORDER = {
    "critical": 0,
    "warning": 1,
    "info": 2,
}


def money(value):
    return (value or ZERO).quantize(CENT)


def _branch_scope(qs, *, branch_ids=None, branch_id=None, field="branch_id"):
    if branch_ids is not None:
        qs = qs.filter(**{f"{field}__in": branch_ids})
    if branch_id is not None:
        qs = qs.filter(**{field: branch_id})
    return qs


def _payable_scope(qs, *, branch_ids=None, branch_id=None):
    if branch_ids is not None:
        qs = qs.filter(
            Q(branch_id__in=branch_ids)
            | Q(service_order__branch_id__in=branch_ids)
            | Q(finance_account__branch_id__in=branch_ids)
        )
    if branch_id is not None:
        qs = qs.filter(
            Q(branch_id=branch_id)
            | Q(service_order__branch_id=branch_id)
            | Q(finance_account__branch_id=branch_id)
        )
    return qs


def _bill_branch(bill):
    return (
        bill.branch
        or (bill.service_order.branch if bill.service_order_id else None)
        or (bill.finance_account.branch if bill.finance_account_id else None)
    )


def _journal_exceptions(settings, *, branch_ids=None, branch_id=None):
    now = timezone.now()
    drafts = JournalEntry.objects.select_related("branch").filter(
        entry_type=JournalEntry.ENTRY_TYPE.MANUAL,
        status=JournalEntry.STATUS.DRAFT,
    )
    drafts = _branch_scope(
        drafts,
        branch_ids=branch_ids,
        branch_id=branch_id,
    ).annotate(review_amount=Sum("lines__debit"))

    results = []
    ageing_cutoff = now - timedelta(days=settings.draft_journal_warning_days)
    for entry in drafts.filter(created_at__lt=ageing_cutoff):
        age_days = max(0, (now.date() - entry.created_at.date()).days)
        results.append(
            {
                "key": f"journal-draft-age:{entry.id}",
                "severity": "warning",
                "category": "journal_draft_ageing",
                "title": "Manual journal has remained draft",
                "detail": (
                    f"{entry.journal_number} has remained draft for {age_days} days; "
                    f"the configured warning threshold is {settings.draft_journal_warning_days} days."
                ),
                "entity_type": "JournalEntry",
                "entity_id": entry.id,
                "reference": entry.journal_number,
                "branch_id": entry.branch_id,
                "branch_name": entry.branch.branch_name if entry.branch else "",
                "relevant_date": entry.entry_date,
                "amount": money(entry.review_amount),
                "action_path": f"/api/v1/finance/journals/{entry.id}",
            }
        )

    threshold = settings.large_manual_journal_review_threshold
    if threshold is not None:
        for entry in drafts.filter(review_amount__gte=threshold):
            results.append(
                {
                    "key": f"journal-large-review:{entry.id}",
                    "severity": "info",
                    "category": "manual_journal_review",
                    "title": "Large draft manual journal requires review",
                    "detail": (
                        f"{entry.journal_number} has total debits of {money(entry.review_amount)}; "
                        f"the configured review threshold is {money(threshold)}."
                    ),
                    "entity_type": "JournalEntry",
                    "entity_id": entry.id,
                    "reference": entry.journal_number,
                    "branch_id": entry.branch_id,
                    "branch_name": entry.branch.branch_name if entry.branch else "",
                    "relevant_date": entry.entry_date,
                    "amount": money(entry.review_amount),
                    "action_path": f"/api/v1/finance/journals/{entry.id}",
                }
            )

    return results


def _payable_exceptions(*, branch_ids=None, branch_id=None):
    today = timezone.localdate()
    bills = VendorBill.objects.select_related(
        "vendor",
        "branch",
        "service_order",
        "service_order__branch",
        "finance_account",
        "finance_account__branch",
    ).filter(
        status__in=OPEN_PAYABLE_STATUSES,
        due_date__lt=today,
    )
    bills = _payable_scope(
        bills,
        branch_ids=branch_ids,
        branch_id=branch_id,
    )

    results = []
    for bill in bills.distinct().order_by("due_date", "bill_number"):
        overdue_days = (today - bill.due_date).days
        branch = _bill_branch(bill)
        results.append(
            {
                "key": f"vendor-bill-overdue:{bill.id}",
                "severity": "warning",
                "category": "payables",
                "title": "Vendor bill is overdue",
                "detail": (
                    f"{bill.bill_number} for {bill.vendor.name} is {overdue_days} days overdue "
                    f"with an unpaid amount of {money(bill.net_amount)}."
                ),
                "entity_type": "VendorBill",
                "entity_id": bill.id,
                "reference": bill.bill_number,
                "branch_id": branch.id if branch else None,
                "branch_name": branch.branch_name if branch else "",
                "relevant_date": bill.due_date,
                "amount": money(bill.net_amount),
                "action_path": f"/api/v1/finance/vendor-bills/{bill.id}",
            }
        )
    return results


def _fixed_asset_exceptions(*, branch_ids=None, branch_id=None):
    today = timezone.localdate()
    assets = FixedAsset.objects.select_related("branch").filter(
        status=FixedAsset.STATUS.ACTIVE,
        capitalization_date__isnull=False,
    )
    assets = _branch_scope(
        assets,
        branch_ids=branch_ids,
        branch_id=branch_id,
    )

    results = []
    for asset in assets.order_by("asset_number"):
        next_required = next(
            (row for row in depreciation_schedule(asset) if not row["posted"]),
            None,
        )
        if not next_required or next_required["period_end"] >= today:
            continue

        overdue_days = (today - next_required["period_end"]).days
        results.append(
            {
                "key": f"fixed-asset-depreciation:{asset.id}:{next_required['period_end']:%Y-%m}",
                "severity": "warning",
                "category": "fixed_assets",
                "title": "Fixed asset depreciation is overdue",
                "detail": (
                    f"{asset.asset_number} requires depreciation for "
                    f"{next_required['period_end']:%Y-%m-%d}; it is {overdue_days} days overdue."
                ),
                "entity_type": "FixedAsset",
                "entity_id": asset.id,
                "reference": asset.asset_number,
                "branch_id": asset.branch_id,
                "branch_name": asset.branch.branch_name if asset.branch else "",
                "relevant_date": next_required["period_end"],
                "amount": money(next_required["depreciation_amount"]),
                "action_path": f"/api/v1/finance/fixed-assets/{asset.id}",
            }
        )
    return results


def finance_exceptions(
    *,
    branch_ids=None,
    branch_id=None,
    severity=None,
    category=None,
):
    settings = FinanceSettings.get_settings()
    results = []
    results.extend(
        _journal_exceptions(
            settings,
            branch_ids=branch_ids,
            branch_id=branch_id,
        )
    )
    results.extend(
        _payable_exceptions(
            branch_ids=branch_ids,
            branch_id=branch_id,
        )
    )
    results.extend(
        _fixed_asset_exceptions(
            branch_ids=branch_ids,
            branch_id=branch_id,
        )
    )

    if severity:
        results = [row for row in results if row["severity"] == severity]
    if category:
        results = [row for row in results if row["category"] == category]

    return sorted(
        results,
        key=lambda row: (
            SEVERITY_ORDER.get(row["severity"], 99),
            row["relevant_date"],
            row["key"],
        ),
    )


def finance_exception_summary(**filters):
    rows = finance_exceptions(**filters)
    category_counts = {}
    severity_counts = {"critical": 0, "warning": 0, "info": 0}
    for row in rows:
        category_counts[row["category"]] = category_counts.get(row["category"], 0) + 1
        severity_counts[row["severity"]] = severity_counts.get(row["severity"], 0) + 1

    return {
        "generated_at": timezone.now(),
        "total_count": len(rows),
        "critical_count": severity_counts["critical"],
        "warning_count": severity_counts["warning"],
        "info_count": severity_counts["info"],
        "category_counts": category_counts,
    }
