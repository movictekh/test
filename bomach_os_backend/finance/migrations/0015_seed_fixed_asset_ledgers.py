from django.db import migrations

ACCOUNTS = [
    ("1610", "Fixed Asset Cost", "asset", "debit", "1600", None),
    ("1690", "Accumulated Depreciation", "asset", "credit", "1600", None),
    ("4200", "Asset Disposal Gain", "revenue", "credit", "4000", "asset_disposal_gain"),
    ("6300", "Depreciation Expense", "expense", "debit", "6000", None),
    ("6400", "Asset Disposal Loss", "expense", "debit", "6000", "asset_disposal_loss"),
]


def seed(apps, schema_editor):
    L = apps.get_model("finance", "LedgerAccount")
    for code, name, atype, normal, parent_code, role in ACCOUNTS:
        parent = L.objects.get(code=parent_code)
        obj = L.objects.filter(code=code).first()
        if obj:
            expected = {
                "account_type": atype,
                "normal_balance": normal,
                "parent_id": parent.id,
                "is_postable": True,
            }
            for f, v in expected.items():
                if getattr(obj, f) != v:
                    raise RuntimeError(f"Ledger {code} has incompatible {f}")
            if role and obj.system_role not in {None, role}:
                raise RuntimeError(f"Ledger {code} has incompatible system_role")
            if role and obj.system_role != role:
                obj.system_role = role
                obj.save(update_fields=["system_role"])
        else:
            L.objects.create(
                code=code,
                name=name,
                account_type=atype,
                normal_balance=normal,
                parent=parent,
                is_postable=True,
                system_role=role,
                description="Canonical fixed-asset accounting ledger.",
                is_active=True,
            )


class Migration(migrations.Migration):
    dependencies = [("finance", "0014_reconciliation_fixed_assets")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
