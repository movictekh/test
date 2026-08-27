from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [("user", "0104_property_purchase_payment_lifecycle")]

    operations = [
        migrations.CreateModel(
            name="MessageOutbox",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, help_text="When this record was created")),
                ("updated_at", models.DateTimeField(auto_now=True, help_text="When this record was last updated")),
                ("event_key", models.CharField(max_length=255, unique=True)),
                ("event_type", models.CharField(db_index=True, max_length=100)),
                ("channel", models.CharField(choices=[("in_app", "In app"), ("email", "Email")], max_length=20)),
                ("recipient_address", models.CharField(blank=True, default="", max_length=320)),
                ("subject", models.CharField(max_length=255)),
                ("body", models.TextField()),
                ("link", models.CharField(blank=True, default="", max_length=500)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("processing", "Processing"), ("sent", "Sent"), ("failed", "Failed")], db_index=True, default="pending", max_length=20)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("max_attempts", models.PositiveSmallIntegerField(default=5)),
                ("available_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("claimed_at", models.DateTimeField(blank=True, null=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True, default="")),
                ("recipient_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="message_outbox_entries", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "user_message_outbox", "ordering": ["available_at", "created_at"]},
        ),
        migrations.AddIndex(
            model_name="messageoutbox",
            index=models.Index(fields=["status", "available_at"], name="user_msgout_status_avail_idx"),
        ),
    ]
