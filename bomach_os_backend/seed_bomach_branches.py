from __future__ import annotations

from django.apps import apps
from django.db import transaction


SEED_BRANCHES = [
    {
        "branch_name": "Enugu",
        "branch_id": "ENU",
        "country": "Nigeria",
        "state": "Enugu",
        "city": "Enugu",
        "office_address": "Plot 12, Independence Layout, Enugu",
        "contact_email": "enugu@bomach.com",
        "contact_phone": "+2348010000001",
    },
    {
        "branch_name": "Port Harcourt",
        "branch_id": "PHC",
        "country": "Nigeria",
        "state": "Rivers",
        "city": "Port Harcourt",
        "office_address": "14 Aba Road, Port Harcourt",
        "contact_email": "portharcourt@bomach.com",
        "contact_phone": "+2348010000002",
    },
    {
        "branch_name": "Lagos",
        "branch_id": "LOS",
        "country": "Nigeria",
        "state": "Lagos",
        "city": "Lagos",
        "office_address": "22 Adeola Odeku Street, Victoria Island, Lagos",
        "contact_email": "lagos@bomach.com",
        "contact_phone": "+2348010000003",
    },
    {
        "branch_name": "Abuja",
        "branch_id": "ABV",
        "country": "Nigeria",
        "state": "Federal Capital Territory",
        "city": "Abuja",
        "office_address": "18 Ahmadu Bello Way, Wuse, Abuja",
        "contact_email": "abuja@bomach.com",
        "contact_phone": "+2348010000004",
    },
]


def find_branch_model():
    matches = [model for model in apps.get_models() if model.__name__.lower() == "branch"]

    if not matches:
        raise RuntimeError(
            "Could not find an installed Django model named 'Branch'. "
            "Run this from the actual Bomach backend environment after Django is configured."
        )

    if len(matches) > 1:
        print("Multiple Branch models found:")
        for model in matches:
            print(f"  - {model._meta.label}")
        raise RuntimeError(
            "More than one Branch model exists. Edit this script to select the intended model explicitly."
        )

    return matches[0]


def field_map(model):
    return {
        field.name: field
        for field in model._meta.get_fields()
        if getattr(field, "concrete", False) and not getattr(field, "auto_created", False)
    }


def operational_value(field):
    choices = list(getattr(field, "choices", ()) or ())
    if not choices:
        return "operational"

    normalized = {str(value).lower(): value for value, _label in choices}
    for candidate in ("operational", "active", "open"):
        if candidate in normalized:
            return normalized[candidate]

    print(
        f"WARNING: could not infer the operational choice for "
        f"{field.model._meta.label}.{field.name}. Available choices: {choices}"
    )
    return choices[0][0]


Branch = find_branch_model()
fields = field_map(Branch)

print(f"\nUsing Branch model: {Branch._meta.label}")
print("Concrete fields:")
for name in sorted(fields):
    print(f"  - {name}")

required_expected = {"branch_name", "branch_id"}
missing = required_expected - fields.keys()
if missing:
    raise RuntimeError(
        f"The discovered Branch model is missing expected fields: {sorted(missing)}. "
        "No database changes were made."
    )


print("\nBranches currently in THIS backend database:")
existing = Branch.objects.all().order_by("pk")

if not existing.exists():
    print("  (none)")
else:
    for branch in existing:
        values = []
        for attr in (
            "id",
            "branch_id",
            "branch_name",
            "country",
            "state",
            "city",
            "operational_status",
            "is_active",
            "is_operational",
        ):
            if hasattr(branch, attr):
                values.append(f"{attr}={getattr(branch, attr)!r}")
        print("  - " + ", ".join(values))


with transaction.atomic():
    print("\nSeeding/updating Bomach branches...")

    for seed in SEED_BRANCHES:
        lookup = {"branch_id": seed["branch_id"]}
        defaults = {}

        for key, value in seed.items():
            if key == "branch_id":
                continue
            if key in fields:
                defaults[key] = value

        if "operational_status" in fields:
            defaults["operational_status"] = operational_value(fields["operational_status"])

        if "is_active" in fields:
            defaults["is_active"] = True

        if "is_operational" in fields:
            defaults["is_operational"] = True

        branch, created = Branch.objects.update_or_create(
            **lookup,
            defaults=defaults,
        )

        print(
            f"  {'CREATED' if created else 'UPDATED'} "
            f"{getattr(branch, 'branch_name', branch)} "
            f"(pk={branch.pk}, branch_id={getattr(branch, 'branch_id', None)!r})"
        )


print("\nFinal branches in THIS backend database:")
for branch in Branch.objects.all().order_by("pk"):
    values = []
    for attr in (
        "id",
        "branch_id",
        "branch_name",
        "country",
        "state",
        "city",
        "operational_status",
        "is_active",
        "is_operational",
    ):
        if hasattr(branch, attr):
            values.append(f"{attr}={getattr(branch, attr)!r}")
    print("  - " + ", ".join(values))

print("\nBRANCH SEED COMPLETE")
