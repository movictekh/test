from datetime import timedelta
from typing import Any

from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from system.notifications.models import MessageOutbox
from system.notifications.services import notify_user


def enqueue_message(
    *,
    event_key: str,
    event_type: str,
    channel: str,
    subject: str,
    body: str,
    recipient_user_id: int | None = None,
    recipient_address: str = "",
    link: str = "",
    metadata: dict[str, Any] | None = None,
    max_attempts: int = 5,
):
    """Persist an idempotent outbox row; never perform delivery here."""
    if not event_key.strip():
        raise ValueError("event_key is required")
    if channel not in {MessageOutbox.CHANNEL_IN_APP, MessageOutbox.CHANNEL_EMAIL}:
        raise ValueError(f"Unsupported message channel: {channel}")
    if channel == MessageOutbox.CHANNEL_IN_APP and recipient_user_id is None:
        raise ValueError("in_app delivery requires recipient_user_id")
    if channel == MessageOutbox.CHANNEL_EMAIL and not recipient_address.strip():
        raise ValueError("email delivery requires recipient_address")

    defaults = {
        "event_type": event_type,
        "channel": channel,
        "recipient_user_id": recipient_user_id,
        "recipient_address": recipient_address.strip(),
        "subject": subject,
        "body": body,
        "link": link,
        "metadata": dict(metadata or {}),
        "max_attempts": max_attempts,
    }
    row, created = MessageOutbox.objects.get_or_create(
        event_key=event_key, defaults=defaults
    )
    if not created:
        for field in (
            "event_type", "channel", "recipient_user_id", "recipient_address",
            "subject", "body", "link",
        ):
            if getattr(row, field) != defaults[field]:
                raise ValueError(
                    f"Outbox idempotency key {event_key!r} reused with different {field}."
                )
    return row, created


def enqueue_user_message(
    *, event_key, event_type, user, subject, body, link="", metadata=None,
    include_email=True,
):
    rows = []
    row, _ = enqueue_message(
        event_key=f"{event_key}:in-app",
        event_type=event_type,
        channel=MessageOutbox.CHANNEL_IN_APP,
        recipient_user_id=user.id,
        subject=subject,
        body=body,
        link=link,
        metadata=metadata,
    )
    rows.append(row)
    email = (getattr(user, "email", "") or "").strip()
    if include_email and email:
        row, _ = enqueue_message(
            event_key=f"{event_key}:email",
            event_type=event_type,
            channel=MessageOutbox.CHANNEL_EMAIL,
            recipient_user_id=user.id,
            recipient_address=email,
            subject=subject,
            body=body,
            link=link,
            metadata=metadata,
        )
        rows.append(row)
    return rows


def _claim_one(*, at=None):
    now = at or timezone.now()
    with transaction.atomic():
        row = (
            MessageOutbox.objects.select_for_update(skip_locked=True)
            .filter(
                status__in=[MessageOutbox.STATUS_PENDING, MessageOutbox.STATUS_FAILED],
                available_at__lte=now,
                attempts__lt=F("max_attempts"),
            )
            .order_by("available_at", "created_at")
            .first()
        )
        if row is None:
            return None
        row.status = MessageOutbox.STATUS_PROCESSING
        row.claimed_at = now
        row.attempts += 1
        row.save(update_fields=["status", "claimed_at", "attempts", "updated_at"])
        return row.id


def _deliver(row):
    if transaction.get_connection().in_atomic_block:
        raise RuntimeError("Message delivery must run outside a database transaction.")
    if row.channel == MessageOutbox.CHANNEL_IN_APP:
        if row.recipient_user_id is None:
            raise ValueError("In-app row has no recipient user.")
        notify_user(
            user_id=row.recipient_user_id,
            title=row.subject,
            message=row.body,
            notification_type=row.metadata.get("notification_type", "info"),
            link=row.link,
            metadata={**dict(row.metadata or {}), "outbox_event_key": row.event_key},
        )
        return
    if row.channel == MessageOutbox.CHANNEL_EMAIL:
        send_mail(
            subject=row.subject,
            message=row.body,
            from_email=None,
            recipient_list=[row.recipient_address],
            fail_silently=False,
        )
        return
    raise ValueError(f"Unsupported outbox channel: {row.channel}")


def process_outbox(*, limit=50, at=None):
    result = {"processed": 0, "sent": 0, "failed": 0}
    for _ in range(max(0, int(limit))):
        row_id = _claim_one(at=at)
        if row_id is None:
            break
        row = MessageOutbox.objects.get(id=row_id)
        try:
            _deliver(row)
        except Exception as exc:
            result["failed"] += 1
            with transaction.atomic():
                row = MessageOutbox.objects.select_for_update().get(id=row_id)
                row.status = MessageOutbox.STATUS_FAILED
                row.last_error = str(exc)[:4000]
                row.available_at = timezone.now() + timedelta(
                    minutes=min(2 ** max(row.attempts - 1, 0), 60)
                )
                row.save(
                    update_fields=["status", "last_error", "available_at", "updated_at"]
                )
        else:
            result["sent"] += 1
            with transaction.atomic():
                row = MessageOutbox.objects.select_for_update().get(id=row_id)
                row.status = MessageOutbox.STATUS_SENT
                row.sent_at = timezone.now()
                row.last_error = ""
                row.save(update_fields=["status", "sent_at", "last_error", "updated_at"])
        result["processed"] += 1
    return result
