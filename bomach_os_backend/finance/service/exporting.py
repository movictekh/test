import csv
from io import StringIO

from finance.service.audit import finance_audit_queryset
from finance.service.intelligence import finance_exceptions
from finance.service.reporting import (
    balance_sheet,
    expense_report,
    payables_ageing,
    profit_and_loss,
    revenue_report,
)

SUPPORTED_REPORT_EXPORTS = {
    "profit_and_loss",
    "balance_sheet",
    "revenue",
    "expenses",
    "payables_ageing",
}


def _csv_content(headers, rows):
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return stream.getvalue()


def _activity_rows(report, section_key, section_name):
    return [
        {
            "section": section_name,
            "account_code": row["ledger_account_code"],
            "account_name": row["ledger_account_name"],
            "amount": row["amount"],
            "currency": report["currency"],
            "date_from": report.get("date_from", ""),
            "date_to": report.get("date_to", ""),
            "as_of": report.get("as_of", ""),
        }
        for row in report[section_key]
    ]


def export_financial_report_csv(
    report_key,
    *,
    branch_ids=None,
    branch_id=None,
    date_from=None,
    date_to=None,
    as_of=None,
    currency=None,
    vendor_id=None,
    search=None,
):
    if report_key not in SUPPORTED_REPORT_EXPORTS:
        supported = ", ".join(sorted(SUPPORTED_REPORT_EXPORTS))
        raise ValueError(
            f"Unsupported CSV report '{report_key}'. Supported: {supported}."
        )

    if report_key == "profit_and_loss":
        report = profit_and_loss(
            date_from=date_from,
            date_to=date_to,
            currency=currency,
            branch_ids=branch_ids,
            branch_id=branch_id,
        )
        rows = _activity_rows(report, "revenue", "Revenue")
        rows.extend(_activity_rows(report, "expenses", "Expenses"))
        rows.extend(
            [
                {
                    "section": "Summary",
                    "account_name": "Total Revenue",
                    "amount": report["total_revenue"],
                    "currency": report["currency"],
                    "date_from": report["date_from"],
                    "date_to": report["date_to"],
                },
                {
                    "section": "Summary",
                    "account_name": "Total Expenses",
                    "amount": report["total_expenses"],
                    "currency": report["currency"],
                    "date_from": report["date_from"],
                    "date_to": report["date_to"],
                },
                {
                    "section": "Summary",
                    "account_name": "Net Profit",
                    "amount": report["net_profit"],
                    "currency": report["currency"],
                    "date_from": report["date_from"],
                    "date_to": report["date_to"],
                },
            ]
        )
        headers = [
            "section",
            "account_code",
            "account_name",
            "amount",
            "currency",
            "date_from",
            "date_to",
            "as_of",
        ]
        filename = f"profit-and-loss-{report['date_from']}-to-{report['date_to']}.csv"
        return filename, _csv_content(headers, rows)

    if report_key == "balance_sheet":
        report = balance_sheet(
            as_of=as_of,
            currency=currency,
            branch_ids=branch_ids,
            branch_id=branch_id,
        )
        rows = _activity_rows(report, "assets", "Assets")
        rows.extend(_activity_rows(report, "liabilities", "Liabilities"))
        rows.extend(_activity_rows(report, "equity", "Posted Equity"))
        rows.extend(
            [
                {
                    "section": "Equity",
                    "account_name": "Cumulative Earnings",
                    "amount": report["cumulative_earnings"],
                    "currency": report["currency"],
                    "as_of": report["as_of"],
                },
                {
                    "section": "Summary",
                    "account_name": "Total Assets",
                    "amount": report["total_assets"],
                    "currency": report["currency"],
                    "as_of": report["as_of"],
                },
                {
                    "section": "Summary",
                    "account_name": "Total Liabilities",
                    "amount": report["total_liabilities"],
                    "currency": report["currency"],
                    "as_of": report["as_of"],
                },
                {
                    "section": "Summary",
                    "account_name": "Total Equity",
                    "amount": report["total_equity"],
                    "currency": report["currency"],
                    "as_of": report["as_of"],
                },
                {
                    "section": "Summary",
                    "account_name": "Accounting Equation Difference",
                    "amount": report["equation_difference"],
                    "currency": report["currency"],
                    "as_of": report["as_of"],
                },
            ]
        )
        headers = [
            "section",
            "account_code",
            "account_name",
            "amount",
            "currency",
            "date_from",
            "date_to",
            "as_of",
        ]
        filename = f"balance-sheet-{report['as_of']}.csv"
        return filename, _csv_content(headers, rows)

    if report_key in {"revenue", "expenses"}:
        report = (
            revenue_report(
                date_from=date_from,
                date_to=date_to,
                currency=currency,
                branch_ids=branch_ids,
                branch_id=branch_id,
            )
            if report_key == "revenue"
            else expense_report(
                date_from=date_from,
                date_to=date_to,
                currency=currency,
                branch_ids=branch_ids,
                branch_id=branch_id,
            )
        )
        rows = [
            {
                "account_code": row["ledger_account_code"],
                "account_name": row["ledger_account_name"],
                "amount": row["amount"],
                "currency": report["currency"],
                "date_from": report["date_from"],
                "date_to": report["date_to"],
            }
            for row in report["rows"]
        ]
        rows.append(
            {
                "account_name": "Total",
                "amount": report["total"],
                "currency": report["currency"],
                "date_from": report["date_from"],
                "date_to": report["date_to"],
            }
        )
        headers = [
            "account_code",
            "account_name",
            "amount",
            "currency",
            "date_from",
            "date_to",
        ]
        filename = f"{report_key}-{report['date_from']}-to-{report['date_to']}.csv"
        return filename, _csv_content(headers, rows)

    report = payables_ageing(
        branch_ids=branch_ids,
        branch_id=branch_id,
        vendor_id=vendor_id,
        search=search,
    )
    rows = [
        {
            "bill_number": row["bill_number"],
            "vendor_name": row["vendor_name"],
            "service_order_number": row["service_order_number"],
            "branch_name": row["branch_name"],
            "bill_date": row["bill_date"],
            "due_date": row["due_date"],
            "age_days": row["age_days"],
            "ageing_bucket": row["ageing_bucket"],
            "status": row["status"],
            "net_amount": row["net_amount"],
            "currency": report["currency"],
        }
        for row in report["rows"]
    ]
    headers = [
        "bill_number",
        "vendor_name",
        "service_order_number",
        "branch_name",
        "bill_date",
        "due_date",
        "age_days",
        "ageing_bucket",
        "status",
        "net_amount",
        "currency",
    ]
    filename = f"payables-ageing-{report['as_of']}.csv"
    return filename, _csv_content(headers, rows)


def export_exceptions_csv(
    *,
    branch_ids=None,
    branch_id=None,
    severity=None,
    category=None,
):
    rows = finance_exceptions(
        branch_ids=branch_ids,
        branch_id=branch_id,
        severity=severity,
        category=category,
    )
    export_rows = [
        {
            "severity": row["severity"],
            "category": row["category"],
            "title": row["title"],
            "reference": row["reference"],
            "branch_name": row["branch_name"],
            "relevant_date": row["relevant_date"],
            "amount": row["amount"],
            "detail": row["detail"],
            "action_path": row["action_path"],
        }
        for row in rows
    ]
    headers = [
        "severity",
        "category",
        "title",
        "reference",
        "branch_name",
        "relevant_date",
        "amount",
        "detail",
        "action_path",
    ]
    return "finance-exceptions.csv", _csv_content(headers, export_rows)


def export_audit_csv(**filters):
    logs = finance_audit_queryset(**filters)
    rows = []
    for log in logs:
        metadata = log.metadata or {}
        user = log.user
        rows.append(
            {
                "created_at": log.created_at.isoformat(),
                "user_name": (
                    user.get_full_name() or user.email or user.username if user else ""
                ),
                "user_email": user.email if user else "",
                "area": metadata.get("area", ""),
                "action": metadata.get("action", ""),
                "entity_type": metadata.get("entity_type", ""),
                "entity_id": metadata.get("entity_id", ""),
                "reference": metadata.get("reference", ""),
                "branch_name": metadata.get("branch_name", ""),
                "amount": metadata.get("amount", ""),
                "activity": log.activity,
            }
        )

    headers = [
        "created_at",
        "user_name",
        "user_email",
        "area",
        "action",
        "entity_type",
        "entity_id",
        "reference",
        "branch_name",
        "amount",
        "activity",
    ]
    return "finance-audit.csv", _csv_content(headers, rows)
