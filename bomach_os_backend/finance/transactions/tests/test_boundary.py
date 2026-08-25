import importlib

from django.apps import apps
from django.test import SimpleTestCase

from domains.service_operations.models import Invoice
from finance.models import FinanceBudget
from finance.transactions.expense import Expense
from finance.transactions.payment import Payment
from finance.transactions.payment_submission import PaymentSubmission


class FinanceTransactionOwnershipTests(SimpleTestCase):
    def test_models_keep_historical_django_identity(self):
        self.assertEqual(Payment._meta.label, "services.Payment")
        self.assertEqual(Expense._meta.label, "services.Expense")
        self.assertEqual(PaymentSubmission._meta.label, "user.PaymentSubmission")

    def test_services_transaction_modules_are_true_aliases(self):
        self.assertIs(
            importlib.import_module("services.models.payment"),
            importlib.import_module("finance.transactions.payment"),
        )
        self.assertIs(
            importlib.import_module("services.models.expenses"),
            importlib.import_module("finance.transactions.expense"),
        )

    def test_mixed_user_module_exports_canonical_payment_submission(self):
        legacy = importlib.import_module("user.models.client_service")
        self.assertIs(legacy.PaymentSubmission, PaymentSubmission)

    def test_transaction_relations_resolve_to_canonical_models(self):
        self.assertIs(Payment._meta.get_field("invoice").remote_field.model, Invoice)
        self.assertIs(
            PaymentSubmission._meta.get_field("invoice").remote_field.model,
            Invoice,
        )
        self.assertIs(
            PaymentSubmission._meta.get_field("confirmed_payment").remote_field.model,
            Payment,
        )

    def test_legacy_budget_is_not_resurrected(self):
        with self.assertRaises(LookupError):
            apps.get_model("services", "Budget")
        self.assertEqual(FinanceBudget._meta.label, "finance.FinanceBudget")

    def test_cashbook_uses_canonical_transaction_classes(self):
        from finance.api.v1 import cashbook

        self.assertIs(cashbook.Payment, Payment)
        self.assertIs(cashbook.Expense, Expense)
