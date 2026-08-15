"""Notification service.

The single path every notification goes through: ``notify()`` creates a
persisted ``Notification`` for a user, honoring their notification preferences
(150). Payloads never contain secrets, invitation tokens, or another user's
data — at most small, safe facts plus a route link.

Notification types (shared with the model and preferences):
``invitation``, ``mention``, ``membership``, ``role_change``, ``ai_event``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.extensions import db
from app.models.notification import Notification

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.user import User


def _preferences(user_id: int):
    """Return the user's preference row (creating defaults), or None."""
    from app.models.notification_preference import NotificationPreference

    pref = NotificationPreference.query.filter_by(user_id=user_id).first()
    if pref is None:
        pref = NotificationPreference(user_id=user_id)
        db.session.add(pref)
        db.session.flush()
    return pref


def notify(
    user: User,
    notification_type: str,
    *,
    actor=None,
    workspace=None,
    project=None,
    payload: dict | None = None,
    link: str | None = None,
) -> Notification | None:
    """Create a notification for ``user`` unless they opted out of the type.

    Returns the created ``Notification`` or ``None`` when skipped. Runs in the
    caller's transaction. ``workspace``/``project`` may be ORM objects or ids.
    """
    if user is None:
        return None
    pref = _preferences(user.id)
    if not pref.allows(notification_type):
        return None

    notification = Notification(
        user_id=user.id,
        type=notification_type,
        actor_id=actor.id if actor is not None else None,
        workspace_id=_id_of(workspace),
        project_id=_id_of(project),
        payload=payload or {},
        link=link,
        is_read=False,
    )
    db.session.add(notification)
    return notification


def _id_of(obj) -> int | None:
    if obj is None:
        return None
    if isinstance(obj, int):
        return obj
    return getattr(obj, "id", None)
