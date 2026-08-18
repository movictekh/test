from ninja import Schema
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


class ContentIn(Schema):
    title: str
    content_type: str = "blog_post"
    status: str = "draft"
    platform: str
    body: str = ""
    excerpt: str = ""
    featured_image: Optional[str] = None
    views: int = 0
    likes: int = 0
    shares: int = 0
    comments: int = 0
    author_id: Optional[int] = None
    published_date: Optional[datetime] = None
    scheduled_date: Optional[datetime] = None
    slug: str = ""
    external_url: str = ""
    meta_description: str = ""
    keywords: str = ""
    tags: str = ""
    category: str = ""
    is_featured: bool = False
    allow_comments: bool = True


class ContentUpdate(Schema):
    title: Optional[str] = None
    content_type: Optional[str] = None
    status: Optional[str] = None
    platform: Optional[str] = None
    body: Optional[str] = None
    excerpt: Optional[str] = None
    featured_image: Optional[str] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    shares: Optional[int] = None
    comments: Optional[int] = None
    author_id: Optional[int] = None
    published_date: Optional[datetime] = None
    scheduled_date: Optional[datetime] = None
    slug: Optional[str] = None
    external_url: Optional[str] = None
    meta_description: Optional[str] = None
    keywords: Optional[str] = None
    tags: Optional[str] = None
    category: Optional[str] = None
    is_featured: Optional[bool] = None
    allow_comments: Optional[bool] = None


class ContentOut(Schema):
    id: int
    title: str
    content_type: str
    status: str
    platform: str
    body: str
    excerpt: str
    featured_image: Optional[str]
    views: int
    likes: int
    shares: int
    comments: int
    author_id: Optional[int]
    published_date: Optional[datetime]
    scheduled_date: Optional[datetime]
    slug: str
    external_url: str
    meta_description: str
    keywords: str
    tags: str
    category: str
    is_featured: bool
    allow_comments: bool
    engagement_rate: float
    total_engagement: int
    is_published: bool
    created_at: datetime
    updated_at: datetime


class ContentListOut(Schema):
    count: int
    results: List[ContentOut]


class ContentCalendarBriefIn(Schema):
    title: str
    format: str = "other"
    platform: str = "multiple"
    division: Optional[str] = ""
    branch_id: Optional[int] = None
    owner_id: Optional[int] = None
    owner_name: Optional[str] = ""
    status: str = "briefed"
    due_date: Optional[date] = None
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    campaign_id: Optional[int] = None
    content_id: Optional[int] = None
    funnel_stage: Optional[str] = ""
    description: Optional[str] = ""
    call_to_action: Optional[str] = ""
    specifications: Optional[str] = ""
    approval_notes: Optional[str] = ""
    sort_order: int = 0


class ContentCalendarBriefUpdate(Schema):
    title: Optional[str] = None
    format: Optional[str] = None
    platform: Optional[str] = None
    division: Optional[str] = None
    branch_id: Optional[int] = None
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[date] = None
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    campaign_id: Optional[int] = None
    content_id: Optional[int] = None
    funnel_stage: Optional[str] = None
    description: Optional[str] = None
    call_to_action: Optional[str] = None
    specifications: Optional[str] = None
    approval_notes: Optional[str] = None
    sort_order: Optional[int] = None


class ContentCalendarPublishIn(Schema):
    content_id: Optional[int] = None
    body: Optional[str] = ""
    excerpt: Optional[str] = ""
    featured_image: Optional[str] = None
    external_url: Optional[str] = ""
    meta_description: Optional[str] = ""
    keywords: Optional[str] = ""
    tags: Optional[str] = ""
    category: Optional[str] = ""
    published_at: Optional[datetime] = None


class MediaLibraryAssetIn(Schema):
    title: str
    asset_type: str = "other"
    file_url: str
    thumbnail_url: Optional[str] = ""
    mime_type: Optional[str] = ""
    file_size_bytes: int = 0
    division: Optional[str] = ""
    branch_id: Optional[int] = None
    owner_id: Optional[int] = None
    owner_name: Optional[str] = ""
    campaign_id: Optional[int] = None
    campaign_asset_id: Optional[int] = None
    calendar_item_id: Optional[int] = None
    content_id: Optional[int] = None
    tags: Optional[str] = ""
    description: Optional[str] = ""
    status: str = "active"


class MediaLibraryAssetUpdate(Schema):
    title: Optional[str] = None
    asset_type: Optional[str] = None
    file_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    mime_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    division: Optional[str] = None
    branch_id: Optional[int] = None
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    campaign_id: Optional[int] = None
    campaign_asset_id: Optional[int] = None
    calendar_item_id: Optional[int] = None
    content_id: Optional[int] = None
    tags: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
