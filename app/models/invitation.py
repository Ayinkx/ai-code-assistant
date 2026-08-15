"""Workspace invitation model.

An invitation is the consent-based onboarding path for a teammate: an owner
creates an invite for an email (registered or not), and the invitee accepts or
declines through the secure token flow. The lifecycle states are:

* ``pending`` — outstanding, usable until ``expires_at``.
* ``accepted`` — the invitee activated the membership.
* ``declined`` — the invitee (or token holder) turned it down.
* ``cancelled`` — the owner retracted it.
* ``expired`` — past ``expires_at`` and still pending.

Security: the raw token is a capability. Only a SHA-256 hash of the token is
stored, the raw value is returned exactly once (at creation) and only ever
delivered through the invite email link (see the invitation security issue).
``to_dict()`` therefore never includes the token.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.extensions import db

INVITE_STATUS_PENDING = "pending"
INVITE_STATUS_ACCEPTED = "accepted"
INVITE_STATUS_DECLINED = "declined"
INVITE_STATUS_CANCELLED = "cancelled"
INVITE_STATUS_EXPIRED = "expired"
INVITE_STATUSES = (
    INVITE_STATUS_PENDING,
    INVITE_STATUS_ACCEPTED,
    INVITE_STATUS_DECLINED,
    INVITE_STATUS_CANCELLED,
    INVITE_STATUS_EXPIRED,
)


def _as_utc(value: datetime) -> datetime:
    """Compare helper: SQLite returns naive datetimes, ``datetime.now(UTC)`` aware.

    Normalize a database-retrieved value to UTC so expiry comparisons stay
    safe across backends (SQLite/PySQLite drops ``tzinfo`` on read).
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class WorkspaceInvitation(db.Model):
    """A pending (or resolved) invitation to join a workspace."""

    __tablename__ = "workspace_invitations"

    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(
        db.Integer,
        db.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invited_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    email = db.Column(db.String(255), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    status = db.Column(db.String(20), nullable=False, default=INVITE_STATUS_PENDING)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    accepted_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    accepted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        db.Index("ix_workspace_invitations_workspace_status", "workspace_id", "status"),
    )

    workspace = db.relationship("Workspace", back_populates="invitations")
    inviter = db.relationship("User", foreign_keys=[invited_by])
    acceptor = db.relationship("User", foreign_keys=[accepted_by])

    def is_valid(self) -> bool:
        """Return ``True`` when the invitation can still be used."""
        return self.status == INVITE_STATUS_PENDING and _as_utc(self.expires_at) > datetime.now(UTC)

    def is_expired(self) -> bool:
        """Return ``True`` when a pending invite is past its expiry."""
        return self.status == INVITE_STATUS_PENDING and _as_utc(self.expires_at) <= datetime.now(
            UTC
        )

    def mark(self, status: str, *, accepted_by: int | None = None) -> None:
        """Transition to ``status``, recording acceptance details when given."""
        self.status = status
        if status == INVITE_STATUS_ACCEPTED:
            self.accepted_by = accepted_by
            self.accepted_at = datetime.now(UTC)

    def to_dict(self) -> dict:
        """Serialize the invitation.

        The raw token is intentionally excluded; it is only returned once in
        the create response.
        """
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "invited_by": self.invited_by,
            "inviter_username": self.inviter.username if self.inviter else None,
            "email": self.email,
            "role": self.role,
            "status": self.status,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "accepted_by": self.accepted_by,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<WorkspaceInvitation id={self.id} status={self.status!r}>"


def hash_invite_token(token: str) -> str:
    """Return the SHA-256 hex digest of an invitation token."""
    import hashlib

    return hashlib.sha256(token.encode("utf-8")).hexdigest()
