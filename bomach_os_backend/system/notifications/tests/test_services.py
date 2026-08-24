from django.http import Http404
from django.test import TestCase

from system.notifications.models import Notification
from system.notifications.selectors import (
    get_unread_notification_count,
    get_user_notification,
    list_user_notifications,
)
from system.notifications.services import (
    mark_all_user_notifications_read,
    mark_user_notification_read,
    notify_user,
    notify_users,
)
from user.models.user import User


class NotificationBoundaryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="boundary-one@test.com",
            username="boundary-one",
            password="password123",
        )
        self.other_user = User.objects.create_user(
            email="boundary-two@test.com",
            username="boundary-two",
            password="password123",
        )

    def test_notify_user_creates_notification(self):
        notification = notify_user(
            user_id=self.user.id,
            title="Approval Required",
            message="Expense #42 needs approval",
            notification_type="approval",
            link="/expenses/42",
            metadata={"expense_id": 42},
        )

        self.assertEqual(notification.user_id, self.user.id)
        self.assertEqual(notification.title, "Approval Required")
        self.assertEqual(notification.message, "Expense #42 needs approval")
        self.assertEqual(notification.notification_type, "approval")
        self.assertEqual(notification.link, "/expenses/42")
        self.assertEqual(notification.metadata, {"expense_id": 42})
        self.assertFalse(notification.is_read)

    def test_notify_users_creates_one_row_per_user(self):
        created = notify_users(
            user_ids=[self.user.id, self.other_user.id],
            title="System Update",
            message="Maintenance tonight",
            notification_type="system",
            metadata={"source": "workflow"},
        )

        self.assertEqual(len(created), 2)
        self.assertEqual(
            [item.user_id for item in created],
            [self.user.id, self.other_user.id],
        )
        self.assertEqual(
            [item.metadata for item in created],
            [{"source": "workflow"}, {"source": "workflow"}],
        )
        self.assertEqual(Notification.objects.count(), 2)

    def test_list_user_notifications_is_user_scoped_and_filterable(self):
        own_unread = notify_user(
            user_id=self.user.id,
            title="Own unread",
            message="Unread",
        )
        own_read = notify_user(
            user_id=self.user.id,
            title="Own read",
            message="Read",
        )
        own_read.is_read = True
        own_read.save(update_fields=["is_read", "updated_at"])
        notify_user(
            user_id=self.other_user.id,
            title="Other",
            message="Other user's notification",
        )

        all_ids = set(
            list_user_notifications(user=self.user).values_list("id", flat=True)
        )
        unread_ids = set(
            list_user_notifications(
                user=self.user,
                is_read=False,
            ).values_list("id", flat=True)
        )
        read_ids = set(
            list_user_notifications(
                user=self.user,
                is_read=True,
            ).values_list("id", flat=True)
        )

        self.assertEqual(all_ids, {own_unread.id, own_read.id})
        self.assertEqual(unread_ids, {own_unread.id})
        self.assertEqual(read_ids, {own_read.id})

    def test_get_user_notification_is_user_scoped(self):
        notification = notify_user(
            user_id=self.user.id,
            title="Private",
            message="Only the owner can fetch this",
        )

        found = get_user_notification(
            user=self.user,
            notification_id=notification.id,
        )
        self.assertEqual(found.id, notification.id)

        with self.assertRaises(Http404):
            get_user_notification(
                user=self.other_user,
                notification_id=notification.id,
            )

    def test_get_unread_notification_count(self):
        unread = notify_user(
            user_id=self.user.id,
            title="Unread",
            message="Unread",
        )
        read = notify_user(
            user_id=self.user.id,
            title="Read",
            message="Read",
        )
        read.is_read = True
        read.save(update_fields=["is_read", "updated_at"])
        notify_user(
            user_id=self.other_user.id,
            title="Other unread",
            message="Other",
        )

        self.assertFalse(unread.is_read)
        self.assertEqual(
            get_unread_notification_count(user=self.user),
            1,
        )

    def test_mark_user_notification_read(self):
        notification = notify_user(
            user_id=self.user.id,
            title="Read me",
            message="Read me",
        )

        result = mark_user_notification_read(
            user=self.user,
            notification_id=notification.id,
        )

        self.assertEqual(result.id, notification.id)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_mark_user_notification_read_cannot_cross_users(self):
        notification = notify_user(
            user_id=self.user.id,
            title="Private",
            message="Private",
        )

        with self.assertRaises(Http404):
            mark_user_notification_read(
                user=self.other_user,
                notification_id=notification.id,
            )

        notification.refresh_from_db()
        self.assertFalse(notification.is_read)

    def test_mark_all_user_notifications_read_is_user_scoped(self):
        notify_user(
            user_id=self.user.id,
            title="One",
            message="One",
        )
        notify_user(
            user_id=self.user.id,
            title="Two",
            message="Two",
        )
        other = notify_user(
            user_id=self.other_user.id,
            title="Other",
            message="Other",
        )

        updated = mark_all_user_notifications_read(user=self.user)

        self.assertEqual(updated, 2)
        self.assertEqual(
            Notification.objects.filter(
                user=self.user,
                is_read=False,
            ).count(),
            0,
        )
        other.refresh_from_db()
        self.assertFalse(other.is_read)
