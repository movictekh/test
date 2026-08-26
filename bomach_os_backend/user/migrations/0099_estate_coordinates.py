from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0098_estate_media_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="estate",
            name="latitude",
            field=models.DecimalField(
                blank=True,
                decimal_places=7,
                help_text="Optional map pin latitude for the estate location.",
                max_digits=10,
                null=True,
                verbose_name="Latitude",
            ),
        ),
        migrations.AddField(
            model_name="estate",
            name="longitude",
            field=models.DecimalField(
                blank=True,
                decimal_places=7,
                help_text="Optional map pin longitude for the estate location.",
                max_digits=10,
                null=True,
                verbose_name="Longitude",
            ),
        ),
    ]
