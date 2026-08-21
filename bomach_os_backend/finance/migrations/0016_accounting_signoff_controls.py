from django.db import migrations, models
from django.db.models import Count

EXPECTED_FIXED_ASSET_LEDGERS = [
    ("1610", "Fixed Asset Cost", "asset", "debit", "1600", True, True, None),
    ("1690", "Accumulated Depreciation", "asset", "credit", "1600", True, True, None),
    (
        "4200",
        "Asset Disposal Gain",
        "revenue",
        "credit",
        "4000",
        True,
        True,
        "asset_disposal_gain",
    ),
    ("6300", "Depreciation Expense", "expense", "debit", "6000", True, True, None),
    (
        "6400",
        "Asset Disposal Loss",
        "expense",
        "debit",
        "6000",
        True,
        True,
        "asset_disposal_loss",
    ),
]


def validate_signoff_state(apps, schema_editor):
    LedgerAccount = apps.get_model("finance", "LedgerAccount")
    BankReconciliation = apps.get_model("finance", "BankReconciliation")

    duplicate_drafts = list(
        BankReconciliation.objects.filter(status="draft")
        .values("finance_account_id")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
    )
    if duplicate_drafts:
        details = ", ".join(
            f"FinanceAccount #{row['finance_account_id']} has {row['count']} drafts"
            for row in duplicate_drafts
        )
        raise RuntimeError(
            "Cannot add one-draft-per-bank reconciliation control: " + details
        )

    for (
        code,
        name,
        account_type,
        normal_balance,
        parent_code,
        postable,
        active,
        role,
    ) in EXPECTED_FIXED_ASSET_LEDGERS:
        account = LedgerAccount.objects.filter(code=code).first()
        if not account:
            raise RuntimeError(
                f"Expected canonical fixed-asset ledger {code} from migration 0015, but it is missing."
            )
        parent = (
            LedgerAccount.objects.filter(pk=account.parent_id).first()
            if account.parent_id
            else None
        )
        actual_parent_code = parent.code if parent else None
        expected = {
            "name": name,
            "account_type": account_type,
            "normal_balance": normal_balance,
            "parent_code": parent_code,
            "is_postable": postable,
            "is_active": active,
            "system_role": role,
        }
        actual = {
            "name": account.name,
            "account_type": account.account_type,
            "normal_balance": account.normal_balance,
            "parent_code": actual_parent_code,
            "is_postable": account.is_postable,
            "is_active": account.is_active,
            "system_role": account.system_role or None,
        }
        mismatches = [
            f"{field}: expected {expected[field]!r}, found {actual[field]!r}"
            for field in expected
            if actual[field] != expected[field]
        ]
        if mismatches:
            raise RuntimeError(
                f"Canonical fixed-asset ledger {code} conflicts with existing data: "
                + "; ".join(mismatches)
                + ". Resolve the ledger deliberately; this migration will not rename, reactivate, or repurpose it."
            )


class Migration(migrations.Migration):
    dependencies = [("finance", "0015_seed_fixed_asset_ledgers")]

    operations = [
        migrations.RunPython(validate_signoff_state, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="bankreconciliation",
            constraint=models.UniqueConstraint(
                fields=("finance_account",),
                condition=models.Q(status="draft"),
                name="uniq_fin_bank_reconciliation_draft_account",
            ),
        ),
    ]
