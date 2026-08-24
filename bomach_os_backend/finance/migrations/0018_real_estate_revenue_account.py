from django.db import migrations


def seed_real_estate_revenue(apps, schema_editor):
    LedgerAccount = apps.get_model("finance", "LedgerAccount")
    try:
        parent = LedgerAccount.objects.get(code="4000")
    except LedgerAccount.DoesNotExist as exc:
        raise RuntimeError(
            "Canonical Revenue ledger 4000 must exist before Real Estate Revenue."
        ) from exc

    account, created = LedgerAccount.objects.get_or_create(
        code="4200",
        defaults={
            "name": "Real Estate Revenue",
            "account_type": "revenue",
            "normal_balance": "credit",
            "parent": parent,
            "is_postable": True,
            "description": "Revenue from Real Estate property sales.",
            "is_active": True,
        },
    )
    if not created and (
        account.account_type != "revenue"
        or account.normal_balance != "credit"
        or not account.is_postable
        or account.parent_id != parent.id
    ):
        raise RuntimeError(
            "Existing ledger code 4200 is incompatible with Real Estate Revenue."
        )


class Migration(migrations.Migration):
    dependencies = [("finance", "0017_finance_settings")]
    operations = [
        migrations.RunPython(seed_real_estate_revenue, migrations.RunPython.noop)
    ]
