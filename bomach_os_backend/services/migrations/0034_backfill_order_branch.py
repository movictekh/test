from django.db import migrations


def forwards(apps, schema_editor):
    ServiceOrder = apps.get_model('services', 'ServiceOrder')
    ServiceRequest = apps.get_model('services', 'ServiceRequest')
    # Backfill branch from service_request for existing orders
    orders = ServiceOrder.objects.filter(
        branch__isnull=True,
        service_request__isnull=False,
    ).select_related('service_request')
    for order in orders:
        if order.service_request and order.service_request_id:
            sr = ServiceRequest.objects.filter(id=order.service_request_id).first()
            if sr and sr.branch_id:
                ServiceOrder.objects.filter(id=order.id).update(branch_id=sr.branch_id)


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0033_serviceorder_branch'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
