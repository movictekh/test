from django.db import migrations, models


CORNERS = ("nw", "ne", "se", "sw")


def _to_boundary(value):
    if not value:
        return {}
    if isinstance(value, dict):
        return {
            key: point
            for key, point in value.items()
            if key in CORNERS and point not in (None, {})
        }
    if isinstance(value, list):
        if len(value) > 4:
            raise RuntimeError(
                "Existing real-estate boundary has more than four points; refusing to truncate geographic data."
            )
        return {
            corner: point
            for corner, point in zip(CORNERS, value)
            if point not in (None, {})
        }
    return {}


def forwards(apps, schema_editor):
    for name in ("Estate", "Property", "BrokerageListing"):
        model = apps.get_model("user", name)
        for obj in model.objects.all().only("id", "boundary").iterator():
            normalized = _to_boundary(obj.boundary)
            if normalized != obj.boundary:
                model.objects.filter(pk=obj.pk).update(boundary=normalized)


def backwards(apps, schema_editor):
    for name in ("Estate", "Property", "BrokerageListing"):
        model = apps.get_model("user", name)
        for obj in model.objects.all().only("id", "boundary").iterator():
            if isinstance(obj.boundary, dict):
                model.objects.filter(pk=obj.pk).update(
                    boundary=[obj.boundary[key] for key in CORNERS if key in obj.boundary]
                )


class Migration(migrations.Migration):
    dependencies = [("user", "0099_estate_coordinates")]

    operations = [
        migrations.RunPython(forwards, backwards),
        migrations.RemoveField(model_name="estate", name="latitude"),
        migrations.RemoveField(model_name="estate", name="longitude"),
        migrations.AlterField(
            model_name="estate",
            name="boundary",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Optional named corners: nw, ne, se, sw. Any subset from zero to four corners is valid.",
                verbose_name="Boundary Coordinates",
            ),
        ),
        migrations.AlterField(
            model_name="property",
            name="boundary",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Optional named corners: nw, ne, se, sw. Empty linked properties default to their estate boundary.",
                verbose_name="Boundary Coordinates",
            ),
        ),
        migrations.AddField(
            model_name="brokeragelisting",
            name="boundary",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Optional named corners: nw, ne, se, sw. Any subset from zero to four corners is valid.",
                verbose_name="Boundary Coordinates",
            ),
        ),
    ]
