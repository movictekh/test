from django.db import migrations, models


def backfill_status(apps, schema_editor):
    """All pre-existing work locations are grandfathered to APPROVED so that
    active clock-in flows continue to work without admin intervention."""
    WorkLocation = apps.get_model("user", "WorkLocation")
    WorkLocation.objects.all().update(status="approved")


def reverse_backfill(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0078_user_face_embedding"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="worklocation",
            name="user_worklo_locatio_78cf9d_idx",
        ),
        migrations.AddField(
            model_name="worklocation",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending Approval"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                ],
                default="pending",
                help_text="Approval status — set by admin via approve/reject endpoints",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="worklocation",
            name="rejection_reason",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Reason provided by admin when rejecting a proposal",
            ),
        ),
        migrations.RunPython(backfill_status, reverse_backfill),
        migrations.RemoveField(
            model_name="worklocation",
            name="is_verified",
        ),
        migrations.AlterField(
            model_name="worklocation",
            name="allowed_radius_meters",
            field=models.PositiveIntegerField(
                default=100,
                help_text="Allowed radius in meters. Admin-only field.",
            ),
        ),
        migrations.AlterField(
            model_name="worklocation",
            name="verified_by",
            field=models.ForeignKey(
                blank=True,
                help_text="Admin who approved or rejected this location",
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="verified_locations",
                to="user.employee",
            ),
        ),
        migrations.AlterField(
            model_name="worklocation",
            name="verified_at",
            field=models.DateTimeField(
                blank=True,
                help_text="When the approval decision was made",
                null=True,
            ),
        ),
        migrations.AddIndex(
            model_name="worklocation",
            index=models.Index(
                fields=["location_type", "status"],
                name="user_worklo_locatio_c2aca8_idx",
            ),
        ),
    ]
