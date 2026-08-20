from django.db import migrations, models
from django.db.models import Count, Q


def validate_no_duplicate_bank_accounts(apps, schema_editor):
    FinanceAccount = apps.get_model("finance", "FinanceAccount")
    duplicates = list(
        FinanceAccount.objects.filter(account_type="bank")
        .values("bank_name", "account_number")
        .annotate(row_count=Count("id"))
        .filter(row_count__gt=1)
        .order_by("bank_name", "account_number")
    )
    if duplicates:
        details = "; ".join(
            f"{row['bank_name']} / {row['account_number']} ({row['row_count']} rows)"
            for row in duplicates
        )
        raise RuntimeError(
            "Cannot add the Finance bank-account uniqueness rule because "
            f"duplicate physical bank accounts already exist: {details}. "
            "Resolve those records from business evidence before retrying."
        )


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0010_tax_statutory"),
    ]

    operations = [
        migrations.RunPython(
            validate_no_duplicate_bank_accounts,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="financeaccount",
            constraint=models.UniqueConstraint(
                fields=("bank_name", "account_number"),
                condition=Q(account_type="bank"),
                name="uniq_finance_bank_account_identity",
            ),
        ),
    ]
