"""Invitation helpers shared across the workspaces and collaboration blueprints.

Covers secure token generation, overdue-invitation expiry, and cancelling a
user's pending invitations when their membership ends (leave/remove).
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from app.extensions import db
from app.models.activity_event import EVENT_INVITATION_CANCELLED
from app.models.invitation import (
    INVITE_STATUS_CANCELLED,
    INVITE_STATUS_EXPIRED,
    INVITE_STATUS_PENDING,
    WorkspaceInvitation,
    hash_invite_token,
)
from app.services.activity import record_activity


def generate_token() -> str:
    """Return a new 32-byte url-safe invitation token."""
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    """Return the stored digest for a raw invitation token."""
    return hash_invite_token(token)


def expire_overdue(workspace_id: int | None = None) -> None:
    """Flip pending invitations past their expiry to ``expired``.

    ``workspace_id`` scopes the sweep when given; otherwise all workspaces are
    swept (cheap, index-backed). Runs in the caller's transaction.
    """
    query = WorkspaceInvitation.query.filter(
        WorkspaceInvitation.status == INVITE_STATUS_PENDING,
        WorkspaceInvitation.expires_at <= datetime.now(UTC),
    )
    if workspace_id is not None:
        query = query.filter_by(workspace_id=workspace_id)
    for invitation in query:
        invitation.status = INVITE_STATUS_EXPIRED


def cancel_pending_for_user(workspace_id: int, user_id: int, actor) -> int:
    """Cancel pending invitations for ``user_id`` and return the count.

    Looks the invitations up through the user's email (a user can only be
    invited by email). Emits a ``invitation.cancelled`` activity event per
    cancelled invitation so the audit trail records the change.
    """
    from app.models import User

    user = db.session.get(User, user_id)
    if user is None:
        return 0
    pending = WorkspaceInvitation.query.filter_by(
        workspace_id=workspace_id, email=user.email, status=INVITE_STATUS_PENDING
    ).all()
    for invitation in pending:
        invitation.status = INVITE_STATUS_CANCELLED
        record_activity(
            workspace_id,
            EVENT_INVITATION_CANCELLED,
            actor=actor,
            target=invitation,
            metadata={"email": invitation.email},
        )
    return len(pending)


def effective_status(invitation: WorkspaceInvitation) -> str:
    """Return the invitation's status, resolving pending-but-overdue to expired."""
    if invitation.status == INVITE_STATUS_PENDING and invitation.is_expired():
        return INVITE_STATUS_EXPIRED
    return invitation.status
