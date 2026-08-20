from decimal import Decimal
import uuid
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class FixedAssetCategory(models.Model):
    class DEPRECIATION_METHOD(models.TextChoices):
        STRAIGHT_LINE = "straight_line", "Straight line"

    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True, default="")
    asset_ledger_account = models.ForeignKey(
        "finance.LedgerAccount",
        on_delete=models.PROTECT,
        related_name="fixed_asset_cost_categories",
    )
    accumulated_depreciation_ledger_account = models.ForeignKey(
        "finance.LedgerAccount",
        on_delete=models.PROTECT,
        related_name="fixed_asset_accumulated_depreciation_categories",
    )
    depreciation_expense_ledger_account = models.ForeignKey(
        "finance.LedgerAccount",
        on_delete=models.PROTECT,
        related_name="fixed_asset_depreciation_expense_categories",
    )
    default_useful_life_months = models.PositiveIntegerField()
    default_residual_value_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    default_depreciation_method = models.CharField(
        max_length=30,
        choices=DEPRECIATION_METHOD.choices,
        default=DEPRECIATION_METHOD.STRAIGHT_LINE,
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_fixed_asset_categories",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        indexes = [models.Index(fields=["is_active", "name"])]

    @staticmethod
    def _under(account, code):
        seen = set()
        cur = account
        while cur:
            if cur.code == code:
                return True
            if cur.pk in seen:
                return False
            seen.add(cur.pk)
            cur = cur.parent
        return False

    def clean(self):
        super().clean()
        errors = {}
        if not self.default_useful_life_months:
            errors["default_useful_life_months"] = (
                "Useful life must be greater than zero."
            )
        if not (
            Decimal("0.00") <= self.default_residual_value_percent < Decimal("100.00")
        ):
            errors["default_residual_value_percent"] = (
                "Residual value percent must be at least 0 and less than 100."
            )
        if self.default_depreciation_method != self.DEPRECIATION_METHOD.STRAIGHT_LINE:
            errors["default_depreciation_method"] = (
                "Only straight-line depreciation is supported in this pass."
            )
        if self.asset_ledger_account_id:
            a = self.asset_ledger_account
            if not (
                a.is_active
                and a.is_postable
                and a.account_type == a.ACCOUNT_TYPE.ASSET
                and a.normal_balance == a.NORMAL_BALANCE.DEBIT
                and self._under(a, "1600")
            ):
                errors["asset_ledger_account"] = (
                    "Asset cost ledger must be active, postable, debit-normal Asset under 1600 Fixed Assets."
                )
        if self.accumulated_depreciation_ledger_account_id:
            a = self.accumulated_depreciation_ledger_account
            if not (
                a.is_active
                and a.is_postable
                and a.account_type == a.ACCOUNT_TYPE.ASSET
                and a.normal_balance == a.NORMAL_BALANCE.CREDIT
                and self._under(a, "1600")
            ):
                errors["accumulated_depreciation_ledger_account"] = (
                    "Accumulated depreciation ledger must be active, postable, credit-normal Asset under 1600 Fixed Assets."
                )
        if self.depreciation_expense_ledger_account_id:
            a = self.depreciation_expense_ledger_account
            if not (
                a.is_active
                and a.is_postable
                and a.account_type == a.ACCOUNT_TYPE.EXPENSE
                and a.normal_balance == a.NORMAL_BALANCE.DEBIT
            ):
                errors["depreciation_expense_ledger_account"] = (
                    "Depreciation expense ledger must be active, postable, debit-normal Expense."
                )
        if errors:
            raise ValidationError(errors)

    def save(self, *a, **kw):
        self.code = (self.code or "").strip().upper()
        self.full_clean()
        return super().save(*a, **kw)


class FixedAsset(models.Model):
    class STATUS(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        FULLY_DEPRECIATED = "fully_depreciated", "Fully depreciated"
        DISPOSED = "disposed", "Disposed"

    asset_number = models.CharField(max_length=50, unique=True, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    category = models.ForeignKey(
        FixedAssetCategory, on_delete=models.PROTECT, related_name="fixed_assets"
    )
    branch = models.ForeignKey(
        "user.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fixed_assets",
    )
    source_expense = models.ForeignKey(
        "services.Expense",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="fixed_assets",
    )
    acquisition_date = models.DateField()
    capitalization_date = models.DateField(null=True, blank=True)
    acquisition_cost = models.DecimalField(
        max_digits=18, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    residual_value = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    useful_life_months = models.PositiveIntegerField()
    depreciation_method = models.CharField(
        max_length=30,
        choices=FixedAssetCategory.DEPRECIATION_METHOD.choices,
        default=FixedAssetCategory.DEPRECIATION_METHOD.STRAIGHT_LINE,
    )
    asset_ledger_account = models.ForeignKey(
        "finance.LedgerAccount",
        on_delete=models.PROTECT,
        related_name="fixed_assets_at_cost",
    )
    accumulated_depreciation_ledger_account = models.ForeignKey(
        "finance.LedgerAccount",
        on_delete=models.PROTECT,
        related_name="fixed_assets_accumulated_depreciation",
    )
    depreciation_expense_ledger_account = models.ForeignKey(
        "finance.LedgerAccount",
        on_delete=models.PROTECT,
        related_name="fixed_assets_depreciation_expense",
    )
    status = models.CharField(
        max_length=30, choices=STATUS.choices, default=STATUS.DRAFT
    )
    disposed_at = models.DateField(null=True, blank=True)
    disposal_proceeds = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    disposal_finance_account = models.ForeignKey(
        "finance.FinanceAccount",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="fixed_asset_disposals",
    )
    disposal_reference = models.CharField(max_length=120, blank=True, default="")
    disposal_notes = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_fixed_assets",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["asset_number"]
        indexes = [
            models.Index(fields=["status", "branch"]),
            models.Index(fields=["category", "status"]),
            models.Index(fields=["source_expense"]),
        ]

    @property
    def currency(self):
        return (
            self.source_expense.finance_account.currency.upper()
            if self.source_expense_id and self.source_expense.finance_account_id
            else "NGN"
        )

    def clean(self):
        super().clean()
        errors = {}
        if not self.useful_life_months:
            errors["useful_life_months"] = "Useful life must be greater than zero."
        if (
            self.residual_value is not None
            and self.acquisition_cost is not None
            and self.residual_value >= self.acquisition_cost
        ):
            errors["residual_value"] = (
                "Residual value must be less than acquisition cost."
            )
        if (
            self.depreciation_method
            != FixedAssetCategory.DEPRECIATION_METHOD.STRAIGHT_LINE
        ):
            errors["depreciation_method"] = (
                "Only straight-line depreciation is supported."
            )
        if self.source_expense_id:
            e = self.source_expense
            if e.cost_type != "capital_expenditure":
                errors["source_expense"] = (
                    "Fixed assets require a capital-expenditure Expense."
                )
            elif e.status != "paid":
                errors["source_expense"] = (
                    "Fixed assets require a paid capital-expenditure Expense."
                )
            elif not e.finance_account_id:
                errors["source_expense"] = (
                    "Paid capital expenditure requires a Finance account."
                )
            source_branch = (
                e.branch_id
                or (e.service_order.branch_id if e.service_order_id else None)
                or (e.finance_account.branch_id if e.finance_account_id else None)
            )
            if self.branch_id and source_branch and self.branch_id != source_branch:
                errors["branch"] = (
                    "Fixed asset branch must match the source capital expenditure."
                )
        if (
            self.capitalization_date
            and self.acquisition_date
            and self.capitalization_date < self.acquisition_date
        ):
            errors["capitalization_date"] = (
                "Capitalization date cannot be before acquisition date."
            )
        if not self.pk and self.status != self.STATUS.DRAFT:
            errors["status"] = (
                "Create fixed assets as draft and capitalize through the fixed-asset workflow."
            )
        if self.pk:
            old = type(self).objects.filter(pk=self.pk).first()
            workflow = getattr(self, "_workflow_via_service", False)
            if old and old.status != self.status and not workflow:
                errors["status"] = (
                    "Fixed asset status can only change through the fixed-asset workflow."
                )
            if old and old.status != self.STATUS.DRAFT:
                for f in [
                    "category_id",
                    "branch_id",
                    "source_expense_id",
                    "acquisition_date",
                    "capitalization_date",
                    "acquisition_cost",
                    "residual_value",
                    "useful_life_months",
                    "depreciation_method",
                    "asset_ledger_account_id",
                    "accumulated_depreciation_ledger_account_id",
                    "depreciation_expense_ledger_account_id",
                ]:
                    if getattr(self, f) != getattr(old, f):
                        errors[f] = (
                            "Capitalized fixed-asset accounting terms are immutable."
                        )
            if old and old.status == self.STATUS.DISPOSED and not workflow:
                for f in ["name", "description"]:
                    if getattr(self, f) != getattr(old, f):
                        errors[f] = "Disposed fixed assets are immutable."
        if self.status == self.STATUS.DISPOSED and not self.disposed_at:
            errors["disposed_at"] = "Disposed fixed assets require a disposal date."
        if errors:
            raise ValidationError(errors)

    def save(self, *a, **kw):
        if not self.asset_number:
            self.asset_number = f"FA-{uuid.uuid4().hex[:12].upper()}"
        self.full_clean()
        return super().save(*a, **kw)

    def delete(self, *a, **kw):
        if self.status != self.STATUS.DRAFT:
            raise ValidationError(
                "Capitalized or disposed fixed assets cannot be deleted."
            )
        return super().delete(*a, **kw)
