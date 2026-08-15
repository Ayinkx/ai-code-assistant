"""Workspace activity recording service.

A thin service that appends ``ActivityEvent`` rows alongside the actions that
produce them, so the activity feed (145), the owner audit view (151), and
notification triggers (149) all read one consistent history. Events are
append-only: nothing in the application updates or deletes them.

Only authorized actions call ``record_activity`` — the caller is responsible
for having already validated the actor can perform the action. ``metadata``
must contain only small, safe facts (role values, labels); never file contents,
tokens, or passwords.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.extensions import db
from app.models.activity_event import ActivityEvent

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.user import User


def record_activity(
    workspace_id: int,
    event_type: str,
    actor: User | None = None,
    target: object | None = None,
    metadata: dict | None = None,
) -> ActivityEvent:
    """Append an activity event in the current transaction.

    ``actor`` may be ``None`` for system-originated events. ``target`` is an
    ORM object; its ``__tablename__`` (minus any trailing ``s`` heuristics are
    avoided) and primary key become ``target_type``/``target_id``.
    """
    target_type = None
    target_id = None
    if target is not None:
        target_type = getattr(target, "__tablename__", None) or type(target).__name__
        target_id = getattr(target, "id", None)
    event = ActivityEvent(
        workspace_id=workspace_id,
        actor_id=actor.id if actor is not None else None,
        event_type=event_type,
        target_type=target_type,
        target_id=target_id,
        event_metadata=metadata or None,
    )
    db.session.add(event)
    return event
