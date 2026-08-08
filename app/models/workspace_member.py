"""Workspace membership model.

The collaboration foundation: a workspace is owned by the user in
``Workspace.user_id`` and can additionally list members with a role. Phase 6
ships the membership data model and owner-only management API (add/update/
remove members); workspace owner actions remain owner-scoped, and a user who
is neither the owner nor a member cannot access the workspace at all.
Delegated read access for members is a follow-up phase.
"""

from datetime import UTC, datetime

from app.extensions import db

ROLE_OWNER = "owner"
ROLE_CONTRIBUTOR = "contributor"
ROLE_VIEWER = "viewer"
VALID_ROLES = (ROLE_OWNER, ROLE_CONTRIBUTOR, ROLE_VIEWER)


class WorkspaceMember(db.Model):
    """A user granted access to a workspace with a specific role."""

    __tablename__ = "workspace_members"
    __table_args__ = (
        db.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_members_ws_user"),
    )

    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(
        db.Integer,
        db.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role = db.Column(db.String(20), nullable=False, default=ROLE_VIEWER)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    workspace = db.relationship("Workspace", back_populates="members")
    user = db.relationship("User")

    def to_dict(self) -> dict:
        """Serialize the membership for JSON API responses."""
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            "role": self.role,
            "username": self.user.username if self.user else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<WorkspaceMember id={self.id} workspace_id={self.workspace_id} role={self.role!r}>"
