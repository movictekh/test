from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from system.notifications.models import MessageOutbox, Notification
from system.notifications.outbox import enqueue_message, enqueue_user_message, process_outbox


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class MessageOutboxTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="outbox",
            email="outbox@example.com",
            password="OutboxTestPass123!",
        )

    def test_enqueue_idempotent_and_reuse_guarded(self):
        first, created = enqueue_message(
            event_key="event:1:email", event_type="test.event",
            channel=MessageOutbox.CHANNEL_EMAIL,
            recipient_user_id=self.user.id, recipient_address=self.user.email,
            subject="Subject", body="Body",
        )
        self.assertTrue(created)
        second, created = enqueue_message(
            event_key="event:1:email", event_type="test.event",
            channel=MessageOutbox.CHANNEL_EMAIL,
            recipient_user_id=self.user.id, recipient_address=self.user.email,
            subject="Subject", body="Body",
        )
        self.assertFalse(created)
        self.assertEqual(first.id, second.id)
        with self.assertRaises(ValueError):
            enqueue_message(
                event_key="event:1:email", event_type="test.event",
                channel=MessageOutbox.CHANNEL_EMAIL,
                recipient_user_id=self.user.id, recipient_address=self.user.email,
                subject="Changed", body="Body",
            )

    def test_processes_in_app_and_email(self):
        enqueue_user_message(
            event_key="event:2", event_type="test.event", user=self.user,
            subject="Paid", body="We received your payment.",
        )
        result = process_outbox(limit=10)
        self.assertEqual(result, {"processed": 2, "sent": 2, "failed": 0})
        self.assertEqual(MessageOutbox.objects.filter(status="sent").count(), 2)
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_failure_is_retryable(self):
        enqueue_message(
            event_key="event:3:email", event_type="test.event",
            channel=MessageOutbox.CHANNEL_EMAIL,
            recipient_user_id=self.user.id, recipient_address=self.user.email,
            subject="Subject", body="Body",
        )
        with patch("system.notifications.outbox.send_mail", side_effect=RuntimeError("provider down")):
            result = process_outbox(limit=1)
        self.assertEqual(result["failed"], 1)
        row = MessageOutbox.objects.get(event_key="event:3:email")
        self.assertEqual(row.status, MessageOutbox.STATUS_FAILED)
        self.assertEqual(row.attempts, 1)
        self.assertIn("provider down", row.last_error)
        self.assertGreater(row.available_at, timezone.now())
