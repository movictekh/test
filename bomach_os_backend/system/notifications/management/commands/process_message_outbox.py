from django.core.management.base import BaseCommand
from system.notifications.outbox import process_outbox


class Command(BaseCommand):
    help = "Process pending transactional message outbox rows."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50)

    def handle(self, *args, **options):
        result = process_outbox(limit=options["limit"])
        self.stdout.write(
            self.style.SUCCESS(
                "processed={processed} sent={sent} failed={failed}".format(**result)
            )
        )
