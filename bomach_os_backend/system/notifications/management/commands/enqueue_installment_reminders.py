from django.core.management.base import BaseCommand
from domains.real_estate.services.messaging import enqueue_due_installment_reminders


class Command(BaseCommand):
    help = "Enqueue idempotent reminders for installments due soon."

    def add_arguments(self, parser):
        parser.add_argument("--lookahead-hours", type=int, default=24)

    def handle(self, *args, **options):
        queued = enqueue_due_installment_reminders(
            lookahead_hours=options["lookahead_hours"]
        )
        self.stdout.write(self.style.SUCCESS(f"queued={queued}"))
