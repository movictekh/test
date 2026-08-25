from django.core.exceptions import ValidationError
from ninja import Router
from ninja.errors import HttpError

from finance.api.schemas.settings import FinanceSettingsOut, FinanceSettingsUpdate
from finance.models import FinanceSettings
from shared.api.schema import MessageSchema
from user.models.company import CompanyPreferences
from system.authorization import require_permission

router = Router(tags=["Finance Settings"])


def _require_company_scope(request):
    if getattr(request, "_perm_scope", "branches") != "company":
        raise HttpError(
            403,
            "Finance Settings are company-wide and require company-scope access.",
        )


def _settings_out(settings):
    return {
        "default_currency": CompanyPreferences.get_settings().default_currency.upper(),
        "financial_year_start_month": settings.financial_year_start_month,
        "closed_through_date": settings.closed_through_date,
        "journal_prefix": settings.journal_prefix,
        "draft_journal_warning_days": settings.draft_journal_warning_days,
        "large_manual_journal_review_threshold": (
            settings.large_manual_journal_review_threshold
        ),
        "updated_by_id": settings.updated_by_id,
        "created_at": settings.created_at,
        "updated_at": settings.updated_at,
    }


@router.get("/settings", response=FinanceSettingsOut)
@require_permission("finance_settings", "view")
def get_finance_settings(request):
    _require_company_scope(request)
    return _settings_out(FinanceSettings.get_settings())


@router.patch(
    "/settings",
    response={200: FinanceSettingsOut, 400: MessageSchema},
)
@require_permission("finance_settings", "update")
def update_finance_settings(request, payload: FinanceSettingsUpdate):
    _require_company_scope(request)

    try:
        settings = FinanceSettings.get_settings()
        for field, value in payload.dict(exclude_unset=True).items():
            setattr(settings, field, value)
        settings.updated_by = request.user
        settings.save()
        return 200, _settings_out(settings)
    except ValidationError as exc:
        return 400, {"detail": str(exc)}
