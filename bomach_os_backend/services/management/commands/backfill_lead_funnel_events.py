from django.core.management.base import BaseCommand

from services.funnel_events import backfill_lead_funnel_events
from services.models.crm import Lead


class Command(BaseCommand):
    help = "Backfill best-effort lead funnel events from existing leads and lead activities."

    def add_arguments(self, parser):
        parser.add_argument("--branch-id", type=int, default=None)
        parser.add_argument("--limit", type=int, default=None)

    def handle(self, *args, **options):
        leads = Lead.objects.all().order_by("id")
        if options["branch_id"]:
            leads = leads.filter(branch_id=options["branch_id"])
        if options["limit"]:
            leads = leads[: options["limit"]]

        result = backfill_lead_funnel_events(leads)
        self.stdout.write(
            self.style.SUCCESS(
                f"Lead funnel event backfill complete: {result['created']} created, {result['skipped']} skipped."
            )
        )
