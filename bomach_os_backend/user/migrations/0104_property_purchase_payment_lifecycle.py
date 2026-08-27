from django.core.validators import MinValueValidator
from django.db import migrations, models


def backfill_purchase_lifecycle(apps, schema_editor):
    PropertyPurchase = apps.get_model("user", "PropertyPurchase")
    for purchase in PropertyPurchase.objects.all().iterator():
        hours = 72
        if purchase.created_at and purchase.payment_window_expires_at:
            seconds = (
                purchase.payment_window_expires_at - purchase.created_at
            ).total_seconds()
            if seconds > 0:
                hours = max(1, int(round(seconds / 3600)))
        purchase.payment_window_hours = hours
        if purchase.status != "awaiting_approval":
            purchase.approved_at = purchase.updated_at
        if purchase.status == "awaiting_payment":
            purchase.next_payment_due_at = purchase.payment_window_expires_at
        purchase.save(
            update_fields=[
                "payment_window_hours",
                "approved_at",
                "next_payment_due_at",
            ]
        )


class Migration(migrations.Migration):
    dependencies = [("user", "0103_central_payments")]

    operations = [
        migrations.AddField(
            model_name="propertypurchase",
            name="payment_window_hours",
            field=models.PositiveSmallIntegerField(
                default=72, validators=[MinValueValidator(1)]
            ),
        ),
        migrations.AddField(
            model_name="propertypurchase",
            name="approved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="propertypurchase",
            name="next_payment_due_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_purchase_lifecycle, migrations.RunPython.noop),
    ]
