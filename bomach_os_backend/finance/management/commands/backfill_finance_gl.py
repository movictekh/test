from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from finance.models import (
    FinanceAccount,
    PettyCashAdvance,
    PettyCashRetirementLine,
    PayrollRun,
    StatutoryObligation,
    VendorBill,
)
from finance.service.accounting import (
    ensure_finance_account_ledger_account,
    post_client_payment_journal,
    post_expense_payment_journal,
    post_opening_balance_journal,
    post_payroll_payment_journal,
    post_petty_cash_issue_journal,
    post_petty_cash_retirement_line_journal,
    post_statutory_payment_journal,
    post_vendor_bill_payment_journal,
)
from services.models.expenses import Expense
from services.models.payment import Payment


class Command(BaseCommand):
    help = "Idempotently backfill General Ledger journals from existing settled Finance events."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate/build all missing journals and roll them back.",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Fail if a non-zero FinanceAccount opening balance has no opening_balance_date.",
        )

    def handle(self, *args, **options):
        dry_run, strict = options["dry_run"], options["strict"]
        created = existing = 0
        warnings = []

        def record(result):
            nonlocal created, existing
            if not result:
                return
            _entry, was_created = result
            created += int(was_created)
            existing += int(not was_created)

        with transaction.atomic():
            for account in FinanceAccount.objects.select_related(
                "branch", "ledger_account"
            ).order_by("id"):
                ensure_finance_account_ledger_account(account)
                if account.opening_balance:
                    if not account.opening_balance_date:
                        warnings.append(
                            f"FinanceAccount #{account.id} ({account.display_name}) has a non-zero opening balance but no opening_balance_date."
                        )
                    else:
                        record(post_opening_balance_journal(account))

            for payment in (
                Payment.objects.filter(finance_account__isnull=False)
                .select_related(
                    "finance_account",
                    "invoice",
                    "invoice__service_request__branch",
                    "invoice__order__branch",
                    "created_by",
                )
                .order_by("id")
            ):
                record(post_client_payment_journal(payment, payment.created_by))

            for expense in (
                Expense.objects.filter(
                    status=Expense.STATUS.PAID, finance_account__isnull=False
                )
                .select_related(
                    "finance_account", "branch", "service_order__branch", "paid_by"
                )
                .order_by("id")
            ):
                record(post_expense_payment_journal(expense, expense.paid_by))

            for bill in (
                VendorBill.objects.filter(
                    status=VendorBill.STATUS.PAID, finance_account__isnull=False
                )
                .select_related(
                    "finance_account", "branch", "service_order__branch", "paid_by"
                )
                .order_by("id")
            ):
                record(post_vendor_bill_payment_journal(bill, bill.paid_by))

            for advance in (
                PettyCashAdvance.objects.filter(
                    status__in=[
                        PettyCashAdvance.STATUS.ISSUED,
                        PettyCashAdvance.STATUS.PARTIALLY_RETIRED,
                        PettyCashAdvance.STATUS.RETIRED,
                    ],
                    amount_issued__gt=0,
                )
                .select_related(
                    "finance_account", "branch", "service_order__branch", "issued_by"
                )
                .order_by("id")
            ):
                record(post_petty_cash_issue_journal(advance, advance.issued_by))

            for line in (
                PettyCashRetirementLine.objects.filter(amount_spent__gt=0)
                .select_related(
                    "advance__finance_account",
                    "advance__branch",
                    "advance__service_order__branch",
                    "service_order__branch",
                    "created_by",
                )
                .order_by("id")
            ):
                record(post_petty_cash_retirement_line_journal(line, line.created_by))
            for line in (
                PettyCashRetirementLine.objects.filter(amount_returned__gt=0)
                .select_related(
                    "advance__finance_account",
                    "advance__branch",
                    "advance__service_order__branch",
                    "service_order__branch",
                    "created_by",
                )
                .order_by("id")
            ):
                record(post_petty_cash_retirement_line_journal(line, line.created_by))

            for payroll in (
                PayrollRun.objects.filter(
                    status=PayrollRun.STATUS.PAID,
                    finance_account__isnull=False,
                    paid_at__isnull=False,
                )
                .select_related("finance_account", "branch", "paid_by")
                .order_by("id")
            ):
                record(post_payroll_payment_journal(payroll, payroll.paid_by))

            for obligation in (
                StatutoryObligation.objects.filter(
                    status=StatutoryObligation.STATUS.PAID,
                    finance_account__isnull=False,
                    paid_at__isnull=False,
                )
                .select_related("finance_account", "branch", "paid_by")
                .order_by("id")
            ):
                record(post_statutory_payment_journal(obligation, obligation.paid_by))

            for warning in warnings:
                self.stdout.write(self.style.WARNING(warning))
            if strict and warnings:
                raise CommandError(
                    "Strict backfill stopped because opening-balance dates are missing."
                )
            if dry_run:
                transaction.set_rollback(True)

        mode = "DRY RUN (rolled back)" if dry_run else "COMMITTED"
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode}: {created} journal(s) created; {existing} already existed; {len(warnings)} warning(s)."
            )
        )
