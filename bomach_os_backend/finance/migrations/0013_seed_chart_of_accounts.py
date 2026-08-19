from django.db import migrations


CANONICAL_ACCOUNTS = [
    # code, name, type, normal, parent, postable, system_role
    ("1000", "Assets", "asset", "debit", None, False, None),
    ("1100", "Cash & Bank", "asset", "debit", "1000", False, None),
    ("1200", "Accounts Receivable", "asset", "debit", "1000", True, "accounts_receivable"),
    ("1300", "Employee Receivables", "asset", "debit", "1000", True, "employee_receivables"),
    ("1400", "Petty Cash Advances", "asset", "debit", "1000", True, "petty_cash_advance"),
    ("1500", "Capital Expenditure Clearing", "asset", "debit", "1000", True, "capital_expenditure_clearing"),
    ("1600", "Fixed Assets", "asset", "debit", "1000", False, None),
    ("2000", "Liabilities", "liability", "credit", None, False, None),
    ("2100", "Accounts Payable", "liability", "credit", "2000", True, "accounts_payable"),
    ("2200", "Payroll Deductions Payable", "liability", "credit", "2000", True, "payroll_deductions_payable"),
    ("2300", "Statutory Payable", "liability", "credit", "2000", True, "statutory_payable"),
    ("3000", "Equity", "equity", "credit", None, False, None),
    ("3100", "Opening Balance Equity", "equity", "credit", "3000", True, "opening_balance_equity"),
    ("4000", "Revenue", "revenue", "credit", None, False, None),
    ("4100", "Service Revenue", "revenue", "credit", "4000", True, "service_revenue"),
    ("5000", "Direct Costs", "expense", "debit", None, False, None),
    ("5100", "Service Cost Expense", "expense", "debit", "5000", True, "service_cost_expense"),
    ("6000", "Operating Expenses", "expense", "debit", None, False, None),
    ("6100", "Operating Expense", "expense", "debit", "6000", True, "operating_expense"),
    ("6200", "Payroll Expense", "expense", "debit", "6000", True, "payroll_expense"),
]


def seed_chart_and_map_finance_accounts(apps, schema_editor):
    LedgerAccount = apps.get_model("finance", "LedgerAccount")
    FinanceAccount = apps.get_model("finance", "FinanceAccount")
    by_code = {}
    for code, name, account_type, normal_balance, parent_code, is_postable, system_role in CANONICAL_ACCOUNTS:
        parent = by_code.get(parent_code)
        account, _ = LedgerAccount.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "account_type": account_type,
                "normal_balance": normal_balance,
                "parent": parent,
                "is_postable": is_postable,
                "system_role": system_role,
                "description": "Canonical Bomach accounting account.",
                "is_active": True,
            },
        )
        by_code[code] = account

    cash_parent = by_code["1100"]
    for finance_account in FinanceAccount.objects.filter(ledger_account__isnull=True).order_by("id"):
        prefix = "1110" if finance_account.account_type == "bank" else "1120"
        code = f"{prefix}-{finance_account.pk:06d}"
        ledger, _ = LedgerAccount.objects.get_or_create(
            code=code,
            defaults={
                "name": finance_account.display_name,
                "account_type": "asset",
                "normal_balance": "debit",
                "parent": cash_parent,
                "is_postable": True,
                "description": f"Dedicated ledger account for FinanceAccount #{finance_account.pk}.",
                "is_active": True,
            },
        )
        FinanceAccount.objects.filter(pk=finance_account.pk).update(ledger_account_id=ledger.pk)


class Migration(migrations.Migration):
    dependencies = [("finance", "0012_accounting_gl")]
    operations = [migrations.RunPython(seed_chart_and_map_finance_accounts, migrations.RunPython.noop)]
