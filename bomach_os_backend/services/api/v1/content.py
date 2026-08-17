import csv
from datetime import date, timedelta
from io import StringIO
from typing import List

from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from services.api.schema.content_schemas import (
    ContentCalendarBriefIn,
    ContentCalendarBriefUpdate,
    ContentCalendarPublishIn,
    ContentIn,
    ContentOut,
    ContentUpdate,
    MediaLibraryAssetIn,
    MediaLibraryAssetUpdate,
)
from services.api.schema.others import MessageSchema
from services.models.content import Content, ContentCalendarItem, MediaLibraryAsset
from services.models.marketing_campaign import CampaignAsset, MarketingCampaign
from user.models.branch import Branch
from user.models.employee import Employee
from user.utils.perm import require_permission, scope_queryset

router = Router(tags=["Content"])


TERMINAL_CALENDAR_STATUSES = {"published", "archived"}
CONTENT_TYPE_BY_FORMAT = {
    "video": "video",
    "graphic": "social_media",
    "carousel": "social_media",
    "text_image": "social_media",
    "email": "newsletter",
    "whatsapp_template": "newsletter",
    "blog_article": "article",
    "radio_script": "article",
    "billboard_artwork": "infographic",
}
CAMPAIGN_ASSET_TYPE_BY_FORMAT = {
    "video": "video",
    "graphic": "graphic",
    "carousel": "carousel",
    "email": "email",
    "whatsapp_template": "whatsapp_template",
    "radio_script": "radio_script",
    "billboard_artwork": "billboard_artwork",
    "blog_article": "other",
    "text_image": "graphic",
}
CAMPAIGN_ASSET_STATUS_BY_CALENDAR_STATUS = {
    "briefed": "briefed",
    "in_progress": "in_progress",
    "in_review": "review",
    "approved": "approved",
    "scheduled": "live",
    "published": "live",
    "overdue": "in_progress",
    "archived": "live",
}
MEDIA_ICONS = {
    "image": "ti-photo",
    "video": "ti-video",
    "document": "ti-file-text",
    "audio": "ti-volume",
    "design_source": "ti-palette",
    "other": "ti-file",
}
DIVISION_COLORS = {
    "real_estate": "#1F3D7A",
    "engineering": "#CC0000",
    "surveying": "#059669",
    "benji": "#7C3AED",
    "ict": "#B87D00",
    "agriculture": "#DC2626",
}


def _validation_detail(exc):
    if hasattr(exc, "message_dict"):
        return "; ".join(
            f"{field}: {', '.join(messages)}"
            for field, messages in exc.message_dict.items()
        )
    return exc.messages[0] if getattr(exc, "messages", None) else str(exc)


def _week_bounds(week_start=None, date_from=None, date_to=None):
    today = timezone.localdate()
    if date_from or date_to:
        start = date_from or date_to
        end = date_to or date_from
        if start > end:
            start, end = end, start
        return start, end
    start = week_start or (today - timedelta(days=today.weekday()))
    return start, start + timedelta(days=6)


def _calendar_queryset(request):
    return scope_queryset(
        request,
        ContentCalendarItem.objects.select_related(
            "branch",
            "owner",
            "owner__user",
            "campaign",
            "campaign_asset",
            "content",
            "created_by",
        ),
        branch_field="branch_id",
    )


def _owner_name(employee):
    if not employee:
        return ""
    full_name = employee.user.get_full_name()
    return full_name or employee.user.email or employee.user.username


def _format_bytes(size):
    size = int(size or 0)
    if size <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    unit = units[0]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            break
        value /= 1024
    if unit == "B":
        return f"{int(value)} {unit}"
    return f"{value:.1f} {unit}"


def _media_queryset(request):
    return scope_queryset(
        request,
        MediaLibraryAsset.objects.select_related(
            "branch",
            "owner",
            "owner__user",
            "campaign",
            "campaign_asset",
            "calendar_item",
            "content",
            "uploaded_by",
        ),
        branch_field="branch_id",
    )


def _serialize_media_asset(asset, detail=False):
    row = {
        "id": asset.id,
        "title": asset.title,
        "asset_type": asset.asset_type,
        "file_url": asset.file_url,
        "thumbnail_url": asset.thumbnail_url,
        "mime_type": asset.mime_type,
        "file_size_bytes": asset.file_size_bytes,
        "display_size": _format_bytes(asset.file_size_bytes),
        "division": asset.division,
        "branch_id": asset.branch_id,
        "branch_name": asset.branch.branch_name if asset.branch else "",
        "owner_id": asset.owner_id,
        "owner_name": asset.owner_name or _owner_name(asset.owner),
        "campaign_id": asset.campaign_id,
        "campaign_name": asset.campaign.name if asset.campaign else "",
        "campaign_asset_id": asset.campaign_asset_id,
        "campaign_asset_name": (
            asset.campaign_asset.name if asset.campaign_asset else ""
        ),
        "calendar_item_id": asset.calendar_item_id,
        "calendar_item_title": asset.calendar_item.title if asset.calendar_item else "",
        "content_id": asset.content_id,
        "content_title": asset.content.title if asset.content else "",
        "tags": asset.tags,
        "description": asset.description,
        "status": asset.status,
        "icon": MEDIA_ICONS.get(asset.asset_type, MEDIA_ICONS["other"]),
        "color": DIVISION_COLORS.get(asset.division, "#6B7280"),
        "uploaded_by_id": asset.uploaded_by_id,
        "uploaded_by_name": (
            asset.uploaded_by.get_full_name() if asset.uploaded_by else ""
        ),
        "created_at": asset.created_at,
        "updated_at": asset.updated_at,
    }
    if detail:
        row["links"] = {
            "campaign": (
                {"id": asset.campaign_id, "name": row["campaign_name"]}
                if asset.campaign
                else None
            ),
            "campaign_asset": (
                {"id": asset.campaign_asset_id, "name": row["campaign_asset_name"]}
                if asset.campaign_asset
                else None
            ),
            "calendar_item": (
                {"id": asset.calendar_item_id, "title": row["calendar_item_title"]}
                if asset.calendar_item
                else None
            ),
            "content": (
                {"id": asset.content_id, "title": row["content_title"]}
                if asset.content
                else None
            ),
        }
    return row


def _filter_media_assets(
    assets,
    asset_type=None,
    division=None,
    campaign_id=None,
    content_id=None,
    calendar_item_id=None,
    branch_id=None,
    owner_id=None,
    status=None,
    search=None,
):
    if asset_type:
        assets = assets.filter(asset_type=asset_type)
    if division:
        assets = assets.filter(division=division)
    if campaign_id:
        assets = assets.filter(campaign_id=campaign_id)
    if content_id:
        assets = assets.filter(content_id=content_id)
    if calendar_item_id:
        assets = assets.filter(calendar_item_id=calendar_item_id)
    if branch_id:
        assets = assets.filter(branch_id=branch_id)
    if owner_id:
        assets = assets.filter(owner_id=owner_id)
    if status:
        assets = assets.filter(status=status)
    if search:
        assets = assets.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(tags__icontains=search)
            | Q(file_url__icontains=search)
            | Q(owner_name__icontains=search)
            | Q(campaign__name__icontains=search)
            | Q(content__title__icontains=search)
        )
    return assets.distinct()


def _media_summary(assets):
    total_size = assets.aggregate(total=Sum("file_size_bytes"))["total"] or 0
    type_counts = [
        {
            "asset_type": value,
            "label": label,
            "count": assets.filter(asset_type=value).count(),
        }
        for value, label in MediaLibraryAsset.ASSET_TYPE_CHOICES
    ]
    return {
        "total_assets": assets.count(),
        "active_assets": assets.filter(status="active").count(),
        "archived_assets": assets.filter(status="archived").count(),
        "total_size_bytes": total_size,
        "total_size_display": _format_bytes(total_size),
        "type_counts": type_counts,
    }


def _media_metadata():
    return {
        "asset_types": [
            {"value": value, "label": label}
            for value, label in MediaLibraryAsset.ASSET_TYPE_CHOICES
        ],
        "statuses": [
            {"value": value, "label": label}
            for value, label in MediaLibraryAsset.STATUS_CHOICES
        ],
        "divisions": [
            {"value": value, "label": label}
            for value, label in MediaLibraryAsset.DIVISION_CHOICES
        ],
    }


def _resolve_media_relations(data):
    missing = object()
    branch_id = data.pop("branch_id", missing)
    owner_id = data.pop("owner_id", missing)
    campaign_id = data.pop("campaign_id", missing)
    campaign_asset_id = data.pop("campaign_asset_id", missing)
    calendar_item_id = data.pop("calendar_item_id", missing)
    content_id = data.pop("content_id", missing)
    relations = {}

    if branch_id is not missing:
        relations["branch"] = (
            Branch.objects.filter(id=branch_id).first() if branch_id else None
        )
    if owner_id is not missing:
        relations["owner"] = (
            Employee.objects.filter(id=owner_id).first() if owner_id else None
        )
    if campaign_id is not missing:
        relations["campaign"] = (
            MarketingCampaign.objects.filter(id=campaign_id).first()
            if campaign_id
            else None
        )
    if campaign_asset_id is not missing:
        relations["campaign_asset"] = (
            CampaignAsset.objects.select_related("campaign", "content")
            .filter(id=campaign_asset_id)
            .first()
            if campaign_asset_id
            else None
        )
    if calendar_item_id is not missing:
        relations["calendar_item"] = (
            ContentCalendarItem.objects.select_related(
                "campaign", "campaign_asset", "content"
            )
            .filter(id=calendar_item_id)
            .first()
            if calendar_item_id
            else None
        )
    if content_id is not missing:
        relations["content"] = (
            Content.objects.filter(id=content_id).first() if content_id else None
        )

    campaign_asset = relations.get("campaign_asset")
    calendar_item = relations.get("calendar_item")
    if calendar_item:
        if not relations.get("campaign"):
            relations["campaign"] = calendar_item.campaign
        if not relations.get("campaign_asset"):
            relations["campaign_asset"] = calendar_item.campaign_asset
        if not relations.get("content"):
            relations["content"] = calendar_item.content
    campaign_asset = relations.get("campaign_asset")
    if campaign_asset:
        campaign = relations.get("campaign")
        if campaign and campaign.id != campaign_asset.campaign_id:
            raise ValidationError(
                {
                    "campaign_asset_id": "Campaign asset does not belong to the selected campaign."
                }
            )
        relations["campaign"] = campaign_asset.campaign
        if not relations.get("content"):
            relations["content"] = campaign_asset.content
    return data, relations


def _sync_media_to_campaign_asset(asset):
    if not asset.campaign_asset:
        return
    campaign_asset = asset.campaign_asset
    if asset.content_id:
        campaign_asset.content_id = asset.content_id
    if asset.description and not campaign_asset.description:
        campaign_asset.description = asset.description
    if asset.thumbnail_url and not campaign_asset.specifications:
        campaign_asset.specifications = asset.thumbnail_url
    campaign_asset.full_clean()
    campaign_asset.save()


def _effective_status(item, today=None):
    today = today or timezone.localdate()
    if (
        item.status not in TERMINAL_CALENDAR_STATUSES
        and item.due_date
        and item.due_date < today
    ):
        return "overdue"
    return item.status


def _item_display_date(item):
    if item.published_at:
        return item.published_at.date()
    if item.scheduled_at:
        return item.scheduled_at.date()
    return item.due_date


def _serialize_calendar_item(item):
    return {
        "id": item.id,
        "source": "calendar_item",
        "title": item.title,
        "format": item.format,
        "platform": item.platform,
        "division": item.division,
        "branch_id": item.branch_id,
        "branch_name": item.branch.branch_name if item.branch else "",
        "owner_id": item.owner_id,
        "owner_name": item.owner_name or _owner_name(item.owner),
        "status": item.status,
        "effective_status": _effective_status(item),
        "due_date": item.due_date,
        "scheduled_at": item.scheduled_at,
        "published_at": item.published_at,
        "calendar_date": _item_display_date(item),
        "campaign_id": item.campaign_id,
        "campaign_name": item.campaign.name if item.campaign else "",
        "campaign_asset_id": item.campaign_asset_id,
        "content_id": item.content_id,
        "funnel_stage": item.funnel_stage,
        "description": item.description,
        "call_to_action": item.call_to_action,
        "specifications": item.specifications,
        "approval_notes": item.approval_notes,
        "sort_order": item.sort_order,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _serialize_content_only(content):
    calendar_date = None
    if content.published_date:
        calendar_date = content.published_date.date()
    elif content.scheduled_date:
        calendar_date = content.scheduled_date.date()
    return {
        "id": None,
        "source": "content",
        "title": content.title,
        "format": content.content_type,
        "platform": content.platform,
        "division": "",
        "branch_id": None,
        "branch_name": "",
        "owner_id": None,
        "owner_name": content.author.get_full_name() if content.author else "",
        "status": content.status,
        "effective_status": content.status,
        "due_date": None,
        "scheduled_at": content.scheduled_date,
        "published_at": content.published_date,
        "calendar_date": calendar_date,
        "campaign_id": None,
        "campaign_name": "",
        "campaign_asset_id": None,
        "content_id": content.id,
        "funnel_stage": "",
        "description": content.excerpt,
        "call_to_action": "",
        "specifications": content.external_url,
        "approval_notes": "",
        "sort_order": 0,
        "created_at": content.created_at,
        "updated_at": content.updated_at,
    }


def _filter_calendar_items(
    items,
    start,
    end,
    status=None,
    platform=None,
    division=None,
    owner_id=None,
    campaign_id=None,
    branch_id=None,
    search=None,
):
    items = items.filter(
        Q(due_date__gte=start, due_date__lte=end)
        | Q(scheduled_at__date__gte=start, scheduled_at__date__lte=end)
        | Q(published_at__date__gte=start, published_at__date__lte=end)
    )
    if status:
        if status == "overdue":
            items = items.exclude(status__in=TERMINAL_CALENDAR_STATUSES).filter(
                due_date__lt=timezone.localdate()
            )
        else:
            items = items.filter(status=status)
    if platform:
        items = items.filter(platform=platform)
    if division:
        items = items.filter(division=division)
    if owner_id:
        items = items.filter(owner_id=owner_id)
    if campaign_id:
        items = items.filter(campaign_id=campaign_id)
    if branch_id:
        items = items.filter(branch_id=branch_id)
    if search:
        items = items.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(specifications__icontains=search)
            | Q(owner_name__icontains=search)
            | Q(campaign__name__icontains=search)
        )
    return items.distinct()


def _content_only_rows(start, end, status=None, platform=None, search=None):
    contents = (
        Content.objects.select_related("author")
        .filter(calendar_items__isnull=True)
        .filter(
            Q(scheduled_date__date__gte=start, scheduled_date__date__lte=end)
            | Q(published_date__date__gte=start, published_date__date__lte=end)
        )
    )
    if status:
        if status == "overdue":
            return []
        contents = contents.filter(status=status)
    if platform:
        contents = contents.filter(platform=platform)
    if search:
        contents = contents.filter(
            Q(title__icontains=search)
            | Q(body__icontains=search)
            | Q(excerpt__icontains=search)
            | Q(tags__icontains=search)
        )
    return [_serialize_content_only(content) for content in contents.distinct()]


def _calendar_response(rows, start, end, filters):
    rows = sorted(
        rows,
        key=lambda row: (
            str(row["calendar_date"] or ""),
            row["sort_order"],
            row["title"],
        ),
    )
    week_days = []
    current = start
    while current <= end:
        day_rows = [row for row in rows if row["calendar_date"] == current]
        week_days.append(
            {
                "date": current,
                "weekday": current.strftime("%a"),
                "is_today": current == timezone.localdate(),
                "items": day_rows,
            }
        )
        current += timedelta(days=1)

    total = len(rows)
    published = len([row for row in rows if row["effective_status"] == "published"])
    overdue = len([row for row in rows if row["effective_status"] == "overdue"])
    scheduled = len([row for row in rows if row["effective_status"] == "scheduled"])
    in_progress = len(
        [
            row
            for row in rows
            if row["effective_status"]
            in {"briefed", "in_progress", "in_review", "approved"}
        ]
    )

    return {
        "period": {"start": start, "end": end},
        "label": f"Week of {start.strftime('%b %-d')} - {end.strftime('%b %-d, %Y')}",
        "filters": filters,
        "kpis": {
            "total": total,
            "published": published,
            "scheduled": scheduled,
            "in_progress": in_progress,
            "overdue": overdue,
            "published_label": f"{published} / {total} published",
        },
        "days": week_days,
        "rows": rows,
        "metadata": {
            "statuses": [
                {"value": value, "label": label}
                for value, label in ContentCalendarItem.STATUS_CHOICES
            ],
            "formats": [
                {"value": value, "label": label}
                for value, label in ContentCalendarItem.FORMAT_CHOICES
            ],
            "platforms": [
                {"value": value, "label": label}
                for value, label in ContentCalendarItem.PLATFORM_CHOICES
            ],
            "divisions": [
                {"value": value, "label": label}
                for value, label in ContentCalendarItem.DIVISION_CHOICES
            ],
            "funnel_stages": [
                {"value": value, "label": label}
                for value, label in ContentCalendarItem.FUNNEL_STAGE_CHOICES
            ],
        },
    }


def _apply_calendar_relations(data):
    missing = object()
    branch_id = data.pop("branch_id", missing)
    owner_id = data.pop("owner_id", missing)
    campaign_id = data.pop("campaign_id", missing)
    content_id = data.pop("content_id", missing)
    relations = {}
    if branch_id is not missing:
        relations["branch"] = (
            Branch.objects.filter(id=branch_id).first() if branch_id else None
        )
    if owner_id is not missing:
        relations["owner"] = (
            Employee.objects.filter(id=owner_id).first() if owner_id else None
        )
    if campaign_id is not missing:
        relations["campaign"] = (
            MarketingCampaign.objects.filter(id=campaign_id).first()
            if campaign_id
            else None
        )
    if content_id is not missing:
        relations["content"] = (
            Content.objects.filter(id=content_id).first() if content_id else None
        )
    return data, relations


def _sync_campaign_asset(item, actor=None):
    if not item.campaign:
        if item.campaign_asset_id:
            item.campaign_asset = None
            item.save(update_fields=["campaign_asset", "updated_at"])
        return None
    defaults = {
        "name": item.title,
        "asset_type": CAMPAIGN_ASSET_TYPE_BY_FORMAT.get(item.format, "other"),
        "owner": item.owner,
        "owner_name": item.owner_name,
        "due_date": item.due_date,
        "status": CAMPAIGN_ASSET_STATUS_BY_CALENDAR_STATUS.get(
            _effective_status(item), "briefed"
        ),
        "description": item.description,
        "specifications": item.specifications,
        "approval_notes": item.approval_notes,
        "content": item.content,
        "created_by": actor or item.created_by,
    }
    if item.campaign_asset_id:
        asset = item.campaign_asset
        for attr, value in defaults.items():
            setattr(asset, attr, value)
        asset.full_clean()
        asset.save()
        return asset
    asset = CampaignAsset.objects.create(campaign=item.campaign, **defaults)
    item.campaign_asset = asset
    item.save(update_fields=["campaign_asset", "updated_at"])
    return asset


@router.get("/calendar")
@require_permission("content", "list")
def get_content_calendar(
    request,
    week_start: date = None,
    date_from: date = None,
    date_to: date = None,
    status: str = None,
    platform: str = None,
    division: str = None,
    owner_id: int = None,
    campaign_id: int = None,
    branch_id: int = None,
    search: str = None,
):
    start, end = _week_bounds(week_start, date_from, date_to)
    items = _filter_calendar_items(
        _calendar_queryset(request),
        start,
        end,
        status=status,
        platform=platform,
        division=division,
        owner_id=owner_id,
        campaign_id=campaign_id,
        branch_id=branch_id,
        search=search,
    )
    rows = [_serialize_calendar_item(item) for item in items]
    if (
        not any([division, owner_id, campaign_id, branch_id])
        and getattr(request, "_perm_scope", "company") == "company"
    ):
        rows.extend(
            _content_only_rows(
                start, end, status=status, platform=platform, search=search
            )
        )
    return _calendar_response(
        rows,
        start,
        end,
        {
            "week_start": week_start,
            "date_from": date_from,
            "date_to": date_to,
            "status": status,
            "platform": platform,
            "division": division,
            "owner_id": owner_id,
            "campaign_id": campaign_id,
            "branch_id": branch_id,
            "search": search,
        },
    )


@router.get("/calendar/export")
@require_permission("content", "list")
def export_content_calendar(
    request,
    week_start: date = None,
    date_from: date = None,
    date_to: date = None,
    status: str = None,
    platform: str = None,
    division: str = None,
    owner_id: int = None,
    campaign_id: int = None,
    branch_id: int = None,
    search: str = None,
):
    calendar = get_content_calendar(
        request,
        week_start=week_start,
        date_from=date_from,
        date_to=date_to,
        status=status,
        platform=platform,
        division=division,
        owner_id=owner_id,
        campaign_id=campaign_id,
        branch_id=branch_id,
        search=search,
    )
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "Title",
            "Format",
            "Platform",
            "Division",
            "Owner",
            "Status",
            "Due",
            "Scheduled",
            "Published",
            "Campaign",
        ]
    )
    for row in calendar["rows"]:
        writer.writerow(
            [
                row["title"],
                row["format"],
                row["platform"],
                row["division"],
                row["owner_name"],
                row["effective_status"],
                row["due_date"],
                row["scheduled_at"],
                row["published_at"],
                row["campaign_name"],
            ]
        )
    response = HttpResponse(buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="content-calendar.csv"'
    return response


@router.post("/calendar/briefs", response={201: dict, 400: MessageSchema})
@require_permission("content", "create")
def create_content_calendar_brief(request, payload: ContentCalendarBriefIn):
    try:
        data, relations = _apply_calendar_relations(payload.dict())
        item = ContentCalendarItem.objects.create(
            created_by=request.user, **relations, **data
        )
        _sync_campaign_asset(item, actor=request.user)
        item.refresh_from_db()
        return 201, _serialize_calendar_item(item)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/calendar/briefs/{item_id}",
    response={200: dict, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("content", "update")
def update_content_calendar_brief(
    request, item_id: int, payload: ContentCalendarBriefUpdate
):
    try:
        item = get_object_or_404(ContentCalendarItem, id=item_id)
        data, relations = _apply_calendar_relations(payload.dict(exclude_unset=True))
        for attr, value in {**relations, **data}.items():
            setattr(item, attr, value)
        item.full_clean()
        item.save()
        _sync_campaign_asset(item, actor=request.user)
        item.refresh_from_db()
        return 200, _serialize_calendar_item(item)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.post(
    "/calendar/briefs/{item_id}/publish",
    response={200: dict, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("content", "update")
def publish_content_calendar_brief(
    request, item_id: int, payload: ContentCalendarPublishIn
):
    try:
        item = get_object_or_404(ContentCalendarItem, id=item_id)
        data = payload.dict()
        content_id = data.pop("content_id", None) or item.content_id
        published_at = data.pop("published_at", None) or timezone.now()
        content_payload = {
            "title": item.title,
            "content_type": CONTENT_TYPE_BY_FORMAT.get(item.format, "social_media"),
            "status": "published",
            "platform": (
                item.platform
                if item.platform in dict(Content.PLATFORM_CHOICES)
                else "website"
            ),
            "body": data.get("body") or item.description,
            "excerpt": data.get("excerpt") or item.call_to_action,
            "featured_image": data.get("featured_image"),
            "external_url": data.get("external_url") or "",
            "meta_description": data.get("meta_description") or "",
            "keywords": data.get("keywords") or "",
            "tags": data.get("tags") or "",
            "category": data.get("category") or item.division,
            "published_date": published_at,
            "scheduled_date": item.scheduled_at,
            "author": request.user,
        }
        if content_id:
            content = get_object_or_404(Content, id=content_id)
            for attr, value in content_payload.items():
                if value is not None:
                    setattr(content, attr, value)
            content.full_clean()
            content.save()
        else:
            content = Content.objects.create(**content_payload)

        item.content = content
        item.status = "published"
        item.published_at = published_at
        item.save(update_fields=["content", "status", "published_at", "updated_at"])
        _sync_campaign_asset(item, actor=request.user)
        item.refresh_from_db()
        return 200, {
            "calendar_item": _serialize_calendar_item(item),
            "content_id": content.id,
        }
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get("/media-library")
@require_permission("content", "list")
def get_media_library(
    request,
    asset_type: str = None,
    division: str = None,
    campaign_id: int = None,
    content_id: int = None,
    calendar_item_id: int = None,
    branch_id: int = None,
    owner_id: int = None,
    status: str = None,
    search: str = None,
    limit: int = 48,
):
    assets = _filter_media_assets(
        _media_queryset(request),
        asset_type=asset_type,
        division=division,
        campaign_id=campaign_id,
        content_id=content_id,
        calendar_item_id=calendar_item_id,
        branch_id=branch_id,
        owner_id=owner_id,
        status=status,
        search=search,
    )
    limit = max(min(limit, 200), 1)
    return {
        "filters": {
            "asset_type": asset_type,
            "division": division,
            "campaign_id": campaign_id,
            "content_id": content_id,
            "calendar_item_id": calendar_item_id,
            "branch_id": branch_id,
            "owner_id": owner_id,
            "status": status,
            "search": search,
            "limit": limit,
        },
        "summary": _media_summary(assets),
        "assets": [_serialize_media_asset(asset) for asset in assets[:limit]],
        "metadata": _media_metadata(),
        "data_notes": [
            "Upload binaries through /api/v1/others/upload-file, then store the returned URL here.",
            "CampaignAsset is workflow state; MediaLibraryAsset is the reusable file record.",
        ],
    }


@router.get("/media-library/export")
@require_permission("content", "list")
def export_media_library(
    request,
    asset_type: str = None,
    division: str = None,
    campaign_id: int = None,
    content_id: int = None,
    calendar_item_id: int = None,
    branch_id: int = None,
    owner_id: int = None,
    status: str = None,
    search: str = None,
):
    assets = _filter_media_assets(
        _media_queryset(request),
        asset_type=asset_type,
        division=division,
        campaign_id=campaign_id,
        content_id=content_id,
        calendar_item_id=calendar_item_id,
        branch_id=branch_id,
        owner_id=owner_id,
        status=status,
        search=search,
    )
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "Title",
            "Asset Type",
            "Division",
            "Owner",
            "Size",
            "Status",
            "Campaign",
            "Content",
            "File URL",
        ]
    )
    for asset in assets[:500]:
        row = _serialize_media_asset(asset)
        writer.writerow(
            [
                row["title"],
                row["asset_type"],
                row["division"],
                row["owner_name"],
                row["display_size"],
                row["status"],
                row["campaign_name"],
                row["content_title"],
                row["file_url"],
            ]
        )
    response = HttpResponse(buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="media-library.csv"'
    return response


@router.post("/media-library/assets", response={201: dict, 400: MessageSchema})
@require_permission("content", "create")
def create_media_library_asset(request, payload: MediaLibraryAssetIn):
    try:
        data, relations = _resolve_media_relations(payload.dict())
        asset = MediaLibraryAsset.objects.create(
            uploaded_by=request.user, **relations, **data
        )
        _sync_media_to_campaign_asset(asset)
        asset.refresh_from_db()
        return 201, _serialize_media_asset(asset, detail=True)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/media-library/assets/{asset_id}", response={200: dict, 404: MessageSchema}
)
@require_permission("content", "view")
def get_media_library_asset(request, asset_id: int):
    asset = get_object_or_404(_media_queryset(request), id=asset_id)
    return 200, _serialize_media_asset(asset, detail=True)


@router.patch(
    "/media-library/assets/{asset_id}",
    response={200: dict, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("content", "update")
def update_media_library_asset(
    request, asset_id: int, payload: MediaLibraryAssetUpdate
):
    try:
        asset = get_object_or_404(_media_queryset(request), id=asset_id)
        data, relations = _resolve_media_relations(payload.dict(exclude_unset=True))
        for attr, value in {**relations, **data}.items():
            setattr(asset, attr, value)
        asset.full_clean()
        asset.save()
        _sync_media_to_campaign_asset(asset)
        asset.refresh_from_db()
        return 200, _serialize_media_asset(asset, detail=True)
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get("", response=List[ContentOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("content", "list")
def list_content(
    request,
    status: str = None,
    content_type: str = None,
    platform: str = None,
    author_id: int = None,
    is_featured: bool = None,
    search: str = None,
):
    """List all content with optional filtering."""
    contents = Content.objects.all()

    if status:
        contents = contents.filter(status=status)
    if content_type:
        contents = contents.filter(content_type=content_type)
    if platform:
        contents = contents.filter(platform=platform)
    if author_id:
        contents = contents.filter(author_id=author_id)
    if is_featured is not None:
        contents = contents.filter(is_featured=is_featured)
    if search:
        contents = contents.filter(
            Q(title__icontains=search)
            | Q(body__icontains=search)
            | Q(excerpt__icontains=search)
            | Q(tags__icontains=search)
        )

    return contents


@router.post("", response={201: ContentOut, 400: MessageSchema})
@require_permission("content", "create")
def create_content(request, payload: ContentIn):
    """Create new content."""
    try:
        content = Content.objects.create(**payload.dict())
        return 201, content
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get("/{content_id}", response=ContentOut)
@require_permission("content", "view")
def get_content(request, content_id: int):
    """Get a specific content by ID."""
    return get_object_or_404(Content, id=content_id)


@router.put(
    "/{content_id}", response={200: ContentOut, 400: MessageSchema, 404: MessageSchema}
)
@require_permission("content", "update")
def update_content(request, content_id: int, payload: ContentUpdate):
    """Update existing content."""
    try:
        content = get_object_or_404(Content, id=content_id)
        for attr, value in payload.dict(exclude_unset=True).items():
            setattr(content, attr, value)
        content.save()
        return 200, content
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.delete(
    "/{content_id}",
    response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("content", "delete")
def delete_content(request, content_id: int):
    """Delete content."""
    try:
        content = get_object_or_404(Content, id=content_id)
        content.delete()
        return 200, {"detail": "Content deleted successfully"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get("/slug/{slug}", response=ContentOut)
@require_permission("content", "view")
def get_content_by_slug(request, slug: str):
    """Get content by slug."""
    return get_object_or_404(Content, slug=slug)


@router.get("/author/{author_id}/content", response=List[ContentOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("content", "list")
def get_author_content(request, author_id: int):
    """Get all content by a specific author."""
    contents = Content.objects.filter(author_id=author_id)
    return contents


@router.get("/platform/{platform}/content", response=List[ContentOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("content", "list")
def get_platform_content(request, platform: str):
    """Get all content for a specific platform."""
    contents = Content.objects.filter(platform=platform)
    return contents


@router.post(
    "/{content_id}/increment-views",
    response={200: ContentOut, 400: MessageSchema, 404: MessageSchema},
)
def increment_views(request, content_id: int):
    """Increment view count for content."""
    try:
        content = get_object_or_404(Content, id=content_id)
        content.increment_views()
        return 200, content
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.post(
    "/{content_id}/increment-likes",
    response={200: ContentOut, 400: MessageSchema, 404: MessageSchema},
)
def increment_likes(request, content_id: int):
    """Increment like count for content."""
    try:
        content = get_object_or_404(Content, id=content_id)
        content.increment_likes()
        return 200, content
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.post(
    "/{content_id}/increment-shares",
    response={200: ContentOut, 400: MessageSchema, 404: MessageSchema},
)
def increment_shares(request, content_id: int):
    """Increment share count for content."""
    try:
        content = get_object_or_404(Content, id=content_id)
        content.increment_shares()
        return 200, content
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.post(
    "/{content_id}/increment-comments",
    response={200: ContentOut, 400: MessageSchema, 404: MessageSchema},
)
def increment_comments(request, content_id: int):
    """Increment comment count for content."""
    try:
        content = get_object_or_404(Content, id=content_id)
        content.increment_comments()
        return 200, content
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get("/scheduled/upcoming", response=List[ContentOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("content", "list")
def get_upcoming_scheduled_content(request):
    """Get upcoming scheduled content."""
    from django.utils import timezone

    contents = Content.objects.filter(
        status="scheduled", scheduled_date__gte=timezone.now()
    ).order_by("scheduled_date")
    return contents
