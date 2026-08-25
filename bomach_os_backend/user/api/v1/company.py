from django.core.exceptions import ValidationError
from ninja import Router

from user.api.schemas.company import (
    CompanyBrandingSchema,
    CompanyBrandingUpdateSchema,
    CompanyChoicesSchema,
    CompanyPreferencesSchema,
    CompanyPreferencesUpdateSchema,
    CompanyProfileSchema,
    CompanyProfileUpdateSchema,
)
from user.api.schemas.others import MessageSchema
from user.models.company import (
    CURRENCY_CHOICES,
    LANGUAGE_CHOICES,
    CompanyBranding,
    CompanyPreferences,
    CompanyProfile,
)
from system.authorization import require_permission

company_api = Router(tags=["Company"])


def _apply_update(instance, payload):
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(instance, field, value)
    instance.save()
    return instance


# ── Profile ────────────────────────────────────────────────────────────


@company_api.get(
    "/company/profile", response={200: CompanyProfileSchema, 404: MessageSchema}
)
@require_permission("company_settings", "view")
def get_company_profile(request):
    return 200, CompanyProfile.get_settings()


@company_api.put(
    "/company/profile", response={200: CompanyProfileSchema, 400: MessageSchema}
)
@require_permission("company_settings", "update")
def update_company_profile(request, payload: CompanyProfileUpdateSchema):
    try:
        profile = CompanyProfile.get_settings()
        return 200, _apply_update(profile, payload)
    except ValidationError as e:
        return 400, {"detail": "; ".join(e.messages)}


# ── Branding ───────────────────────────────────────────────────────────


@company_api.get(
    "/company/branding", response={200: CompanyBrandingSchema, 404: MessageSchema}
)
@require_permission("company_settings", "view")
def get_company_branding(request):
    return 200, CompanyBranding.get_settings()


@company_api.put(
    "/company/branding", response={200: CompanyBrandingSchema, 400: MessageSchema}
)
@require_permission("company_settings", "update")
def update_company_branding(request, payload: CompanyBrandingUpdateSchema):
    try:
        branding = CompanyBranding.get_settings()
        return 200, _apply_update(branding, payload)
    except ValidationError as e:
        return 400, {"detail": "; ".join(e.messages)}


# ── Preferences ────────────────────────────────────────────────────────


@company_api.get(
    "/company/preferences", response={200: CompanyPreferencesSchema, 404: MessageSchema}
)
@require_permission("company_settings", "view")
def get_company_preferences(request):
    return 200, CompanyPreferences.get_settings()


@company_api.put(
    "/company/preferences", response={200: CompanyPreferencesSchema, 400: MessageSchema}
)
@require_permission("company_settings", "update")
def update_company_preferences(request, payload: CompanyPreferencesUpdateSchema):
    try:
        prefs = CompanyPreferences.get_settings()
        return 200, _apply_update(prefs, payload)
    except ValidationError as e:
        return 400, {"detail": "; ".join(e.messages)}


# ── Choices (for frontend dropdowns) ───────────────────────────────────


@company_api.get("/company/choices", response={200: CompanyChoicesSchema})
@require_permission("company_settings", "view")
def get_company_choices(request):
    return 200, {
        "currencies": [{"value": v, "label": l} for v, l in CURRENCY_CHOICES],
        "languages": [{"value": v, "label": l} for v, l in LANGUAGE_CHOICES],
    }
