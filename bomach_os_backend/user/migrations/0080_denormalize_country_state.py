from django.db import migrations, models


def copy_location_to_strings(apps, schema_editor):
    """Copy FK country/state values into the new CharFields before the FKs are
    dropped."""
    Branch = apps.get_model("user", "Branch")
    Estate = apps.get_model("user", "Estate")

    for b in Branch.objects.select_related("country", "state").all():
        b.country_str = b.country.name if b.country_id else ""
        b.country_code = (b.country.code or "") if b.country_id else ""
        b.state_str = b.state.name if b.state_id else ""
        b.state_code = (b.state.code or "") if b.state_id else ""
        b.save(update_fields=["country_str", "country_code", "state_str", "state_code"])

    for e in Estate.objects.select_related("country").all():
        e.country_str = e.country.name if e.country_id else ""
        e.country_code = (e.country.code or "") if e.country_id else ""
        e.save(update_fields=["country_str", "country_code"])


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0079_worklocation_approval_status"),
    ]

    operations = [
        # ── 1. Drop the old composite index that spans the FK columns ──
        migrations.RemoveIndex(
            model_name="branch",
            name="user_branch_country_841746_idx",
        ),
        migrations.RemoveIndex(
            model_name="estate",
            name="user_estate_country_6d8d65_idx",
        ),

        # ── 2. Add the new string columns alongside the existing FKs ──
        migrations.AddField(
            model_name="branch",
            name="country_str",
            field=models.CharField(default="", help_text="Country name", max_length=100, verbose_name="Country"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="branch",
            name="country_code",
            field=models.CharField(blank=True, default="", help_text="ISO 3166-1 alpha-3 code (e.g., USA, GBR, NGA)", max_length=3, verbose_name="Country Code"),
        ),
        migrations.AddField(
            model_name="branch",
            name="state_str",
            field=models.CharField(default="", help_text="State or province name", max_length=100, verbose_name="State"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="branch",
            name="state_code",
            field=models.CharField(blank=True, default="", help_text="State / province code", max_length=10, verbose_name="State Code"),
        ),
        migrations.AddField(
            model_name="branch",
            name="city",
            field=models.CharField(blank=True, default="", max_length=100, verbose_name="City"),
        ),
        migrations.AddField(
            model_name="estate",
            name="country_str",
            field=models.CharField(default="", help_text="Country name", max_length=100, verbose_name="Country"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="estate",
            name="country_code",
            field=models.CharField(blank=True, default="", help_text="ISO 3166-1 alpha-3 code", max_length=3, verbose_name="Country Code"),
        ),

        # ── 3. Backfill the new columns from the FKs ──
        migrations.RunPython(copy_location_to_strings, reverse_noop),

        # ── 4. Drop the FK fields (cascades the FK-column auto-indexes) ──
        migrations.RemoveField(model_name="branch", name="country"),
        migrations.RemoveField(model_name="branch", name="state"),
        migrations.RemoveField(model_name="estate", name="country"),

        # ── 5. Rename the string columns into their final names ──
        migrations.RenameField(model_name="branch", old_name="country_str", new_name="country"),
        migrations.RenameField(model_name="branch", old_name="state_str", new_name="state"),
        migrations.RenameField(model_name="estate", old_name="country_str", new_name="country"),

        # ── 6. Drop the Country and State models ──
        migrations.DeleteModel(name="State"),
        migrations.DeleteModel(name="Country"),

        # ── 7. Re-add single-column indexes on the new text columns ──
        migrations.AddIndex(
            model_name="branch",
            index=models.Index(fields=["country"], name="user_branch_country_a6e042_idx"),
        ),
        migrations.AddIndex(
            model_name="branch",
            index=models.Index(fields=["state"], name="user_branch_state_d3d598_idx"),
        ),
    ]
