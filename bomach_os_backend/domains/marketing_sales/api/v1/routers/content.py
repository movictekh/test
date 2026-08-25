import csv
from datetime import date
from io import StringIO
from typing import List

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from domains.marketing_sales.api.v1.schemas.content import (
    ContentCalendarBriefIn,
    ContentCalendarBriefUpdate,
    ContentCalendarPublishIn,
    ContentIn,
    ContentOut,
    ContentUpdate,
    MediaLibraryAssetIn,
    MediaLibraryAssetUpdate,
)
from domains.marketing_sales.constants import CONTENT_TYPE_BY_FORMAT
from domains.marketing_sales.models.content import (
    Content,
    ContentCalendarItem,
    MediaLibraryAsset,
)
from domains.marketing_sales.presenters import (
    _content_calendar_response as _calendar_response,
)
from domains.marketing_sales.presenters import (
    _content_media_metadata as _media_metadata,
)
from domains.marketing_sales.presenters import (
    _content_serialize_calendar_item as _serialize_calendar_item,
)
from domains.marketing_sales.presenters import (
    _content_serialize_media_asset as _serialize_media_asset,
)
from domains.marketing_sales.presenters import (
    _content_validation_detail as _validation_detail,
)
from domains.marketing_sales.selectors.marketing import (
    _content_apply_calendar_relations as _apply_calendar_relations,
)
from domains.marketing_sales.selectors.marketing import (
    _content_calendar_queryset as _calendar_queryset,
)
from domains.marketing_sales.selectors.marketing import (
    _content_content_only_rows as _content_only_rows,
)
from domains.marketing_sales.selectors.marketing import (
    _content_filter_calendar_items as _filter_calendar_items,
)
from domains.marketing_sales.selectors.marketing import (
    _content_filter_media_assets as _filter_media_assets,
)
from domains.marketing_sales.selectors.marketing import (
    _content_media_queryset as _media_queryset,
)
from domains.marketing_sales.selectors.marketing import (
    _content_media_summary as _media_summary,
)
from domains.marketing_sales.selectors.marketing import (
    _content_resolve_media_relations as _resolve_media_relations,
)
from domains.marketing_sales.selectors.marketing import (
    _content_week_bounds as _week_bounds,
)
from domains.marketing_sales.services.marketing import (
    _content_sync_campaign_asset as _sync_campaign_asset,
)
from domains.marketing_sales.services.marketing import (
    _content_sync_media_to_campaign_asset as _sync_media_to_campaign_asset,
)
from shared.api.schema.others import MessageSchema
from system.authorization import require_permission

content_router = Router(tags=["Content"])


@content_router.get("/calendar")
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


@content_router.get("/calendar/export")
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


@content_router.post("/calendar/briefs", response={201: dict, 400: MessageSchema})
@require_permission("content", "create")
def create_content_calendar_brief(request, payload: ContentCalendarBriefIn):
    try:
        data, relations = _apply_calendar_relations(payload.dict())
        item = ContentCalendarItem.objects.create(
            created_by=request.user, **relations, **data
        )
        _sync_campaign_asset(item, actor=request.user)
        item.refresh_from_db()
        return (201, _serialize_calendar_item(item))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@content_router.patch(
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
        return (200, _serialize_calendar_item(item))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@content_router.post(
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
        return (
            200,
            {"calendar_item": _serialize_calendar_item(item), "content_id": content.id},
        )
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@content_router.get("/media-library")
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


@content_router.get("/media-library/export")
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


@content_router.post("/media-library/assets", response={201: dict, 400: MessageSchema})
@require_permission("content", "create")
def create_media_library_asset(request, payload: MediaLibraryAssetIn):
    try:
        data, relations = _resolve_media_relations(payload.dict())
        asset = MediaLibraryAsset.objects.create(
            uploaded_by=request.user, **relations, **data
        )
        _sync_media_to_campaign_asset(asset)
        asset.refresh_from_db()
        return (201, _serialize_media_asset(asset, detail=True))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@content_router.get(
    "/media-library/assets/{asset_id}", response={200: dict, 404: MessageSchema}
)
@require_permission("content", "view")
def get_media_library_asset(request, asset_id: int):
    asset = get_object_or_404(_media_queryset(request), id=asset_id)
    return (200, _serialize_media_asset(asset, detail=True))


@content_router.patch(
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
        return (200, _serialize_media_asset(asset, detail=True))
    except ValidationError as e:
        return (400, {"detail": _validation_detail(e)})
    except Exception as e:
        return (400, {"detail": str(e)})


@content_router.get("", response=List[ContentOut])
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


@content_router.post("", response={201: ContentOut, 400: MessageSchema})
@require_permission("content", "create")
def create_content(request, payload: ContentIn):
    """Create new content."""
    try:
        content = Content.objects.create(**payload.dict())
        return (201, content)
    except ValidationError as e:
        return (400, {"detail": e.messages[0]})
    except Exception as e:
        return (400, {"detail": str(e)})


@content_router.get("/{content_id}", response=ContentOut)
@require_permission("content", "view")
def get_content(request, content_id: int):
    """Get a specific content by ID."""
    return get_object_or_404(Content, id=content_id)


@content_router.put(
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
        return (200, content)
    except ValidationError as e:
        return (400, {"detail": e.messages[0]})
    except Exception as e:
        return (400, {"detail": str(e)})


@content_router.delete(
    "/{content_id}",
    response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("content", "delete")
def delete_content(request, content_id: int):
    """Delete content."""
    try:
        content = get_object_or_404(Content, id=content_id)
        content.delete()
        return (200, {"detail": "Content deleted successfully"})
    except ValidationError as e:
        return (400, {"detail": e.messages[0]})
    except Exception as e:
        return (400, {"detail": str(e)})


@content_router.get("/slug/{slug}", response=ContentOut)
@require_permission("content", "view")
def get_content_by_slug(request, slug: str):
    """Get content by slug."""
    return get_object_or_404(Content, slug=slug)


@content_router.get("/author/{author_id}/content", response=List[ContentOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("content", "list")
def get_author_content(request, author_id: int):
    """Get all content by a specific author."""
    contents = Content.objects.filter(author_id=author_id)
    return contents


@content_router.get("/platform/{platform}/content", response=List[ContentOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("content", "list")
def get_platform_content(request, platform: str):
    """Get all content for a specific platform."""
    contents = Content.objects.filter(platform=platform)
    return contents


@content_router.post(
    "/{content_id}/increment-views",
    response={200: ContentOut, 400: MessageSchema, 404: MessageSchema},
)
def increment_views(request, content_id: int):
    """Increment view count for content."""
    try:
        content = get_object_or_404(Content, id=content_id)
        content.increment_views()
        return (200, content)
    except ValidationError as e:
        return (400, {"detail": e.messages[0]})
    except Exception as e:
        return (400, {"detail": str(e)})


@content_router.post(
    "/{content_id}/increment-likes",
    response={200: ContentOut, 400: MessageSchema, 404: MessageSchema},
)
def increment_likes(request, content_id: int):
    """Increment like count for content."""
    try:
        content = get_object_or_404(Content, id=content_id)
        content.increment_likes()
        return (200, content)
    except ValidationError as e:
        return (400, {"detail": e.messages[0]})
    except Exception as e:
        return (400, {"detail": str(e)})


@content_router.post(
    "/{content_id}/increment-shares",
    response={200: ContentOut, 400: MessageSchema, 404: MessageSchema},
)
def increment_shares(request, content_id: int):
    """Increment share count for content."""
    try:
        content = get_object_or_404(Content, id=content_id)
        content.increment_shares()
        return (200, content)
    except ValidationError as e:
        return (400, {"detail": e.messages[0]})
    except Exception as e:
        return (400, {"detail": str(e)})


@content_router.post(
    "/{content_id}/increment-comments",
    response={200: ContentOut, 400: MessageSchema, 404: MessageSchema},
)
def increment_comments(request, content_id: int):
    """Increment comment count for content."""
    try:
        content = get_object_or_404(Content, id=content_id)
        content.increment_comments()
        return (200, content)
    except ValidationError as e:
        return (400, {"detail": e.messages[0]})
    except Exception as e:
        return (400, {"detail": str(e)})


@content_router.get("/scheduled/upcoming", response=List[ContentOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("content", "list")
def get_upcoming_scheduled_content(request):
    """Get upcoming scheduled content."""
    from django.utils import timezone

    contents = Content.objects.filter(
        status="scheduled", scheduled_date__gte=timezone.now()
    ).order_by("scheduled_date")
    return contents
