from ninja import Schema
from typing import Optional
from datetime import datetime


class NotificationOut(Schema):
    id: int
    title: str
    message: str
    notification_type: str
    is_read: bool
    link: str = ''
    metadata: dict = {}
    created_at: datetime


class NotificationStats(Schema):
    unread_count: int
