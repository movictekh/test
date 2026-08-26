from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("user", "0100_real_estate_four_corner_boundaries")]

    operations = [
        migrations.AddField(
            model_name="estate",
            name="reservation_allowed",
            field=models.BooleanField(
                default=False,
                help_text="Whether properties in this estate may be reserved before full payment.",
                verbose_name="Reservation Allowed",
            ),
        ),
        migrations.AddField(
            model_name="estate",
            name="reservation_threshold_percent",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text=(
                    "Percentage of the final purchase total that must be verified "
                    "before a property becomes reserved."
                ),
                max_digits=5,
                null=True,
                validators=[
                    MinValueValidator(Decimal("0.01")),
                    MaxValueValidator(Decimal("100.00")),
                ],
                verbose_name="Reservation Down Payment (%)",
            ),
        ),
        migrations.AddField(
            model_name="estate",
            name="installment_allowed",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Whether buyers may continue paying an outstanding property "
                    "balance in installments."
                ),
                verbose_name="Installment Payment Allowed",
            ),
        ),
        migrations.AddField(
            model_name="estate",
            name="max_installment_months",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Optional maximum installment duration for purchases in this estate.",
                null=True,
                validators=[MinValueValidator(1)],
                verbose_name="Maximum Installment Months",
            ),
        ),
        migrations.AddField(
            model_name="estate",
            name="reservation_payment_window_hours",
            field=models.PositiveIntegerField(
                default=72,
                help_text=(
                    "How long an approved reservation payment request may remain "
                    "open before expiry rules are evaluated."
                ),
                validators=[MinValueValidator(1)],
                verbose_name="Reservation Payment Window (Hours)",
            ),
        ),
    ]
