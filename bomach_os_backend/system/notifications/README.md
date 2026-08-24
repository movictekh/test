# System Notifications

`system.notifications` is the canonical Python source owner for Bomach OS
in-app notifications.

## Phase 1

Phase 1 changes source ownership only. It preserves:

- Django identity: `user.Notification`
- database table and historical migration ownership
- migration history, including `user/0082_notification.py`
- notification permission resource/actions
- `/api/v1/notifications...` public HTTP contract
- legacy `user.models.notification`, `user.api.schemas.notification`, and
  `user.api.v1.notification` imports

`system.notifications` is intentionally not added to `INSTALLED_APPS`. The
existing `user` Django app remains the model identity owner.

## Deferred to Phase 2

Phase 2 will add selectors/services and a centralized notification producer
boundary. Existing producers, including the workflow engine, keep their legacy
imports during Phase 1 so compatibility is exercised.
