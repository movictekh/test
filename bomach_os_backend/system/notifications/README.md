# System Notifications

`system.notifications` is the canonical Python source owner for Bomach OS
in-app notifications.

## Stable identity and public contract

The extraction continues to preserve:

- Django identity: `user.Notification`
- database table: `user_notification`
- historical migration ownership under `user/migrations`
- notification permission resource/actions
- `/api/v1/notifications...` public HTTP contract
- legacy `user.models.notification`, `user.api.schemas.notification`, and
  `user.api.v1.notification` compatibility imports

`system.notifications` is intentionally not added to `INSTALLED_APPS`. The
existing `user` Django app remains the model identity owner.

## Phase 1 — source ownership

Phase 1 moved the canonical model, API schema/router, and tests into
`system.notifications` without changing behavior.

## Phase 2 — internal service boundary

Phase 2 makes Notifications an actual system capability instead of only a
better-owned model.

Reads go through `system.notifications.selectors`:

- `list_user_notifications()`
- `get_user_notification()`
- `get_unread_notification_count()`

Mutations and production go through `system.notifications.services`:

- `mark_user_notification_read()`
- `mark_all_user_notifications_read()`
- `notify_user()`
- `notify_users()`

Application/workflow code should not directly create `Notification` rows.
The workflow engine now uses the producer service. `notify_users()` deliberately
keeps the previous one-row-at-a-time create behavior in this phase rather than
introducing `bulk_create`.

Email and Announcement remain separate capabilities and are not folded into
the Notification model.
