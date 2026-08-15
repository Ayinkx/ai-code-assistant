"""Project discussion comment model.

Team members discuss a project inside a shared workspace. Comments are
project-scoped, support a single reply level via ``parent_id``, and may contain
``@username`` mentions which are resolved against workspace members only (see
``app/services/mentions.py``). Access is granted to the workspace owner and
active members; the author or the workspace owner may delete a comment.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.extensions import db

COMMENT_MAX_LENGTH = 4000


class ProjectComment(db.Model):
    """A discussion comment (or reply) on a project."""

    __tablename__ = "project_comments"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_id = db.Column(
        db.Integer, db.ForeignKey("project_comments.id", ondelete="CASCADE"), nullable=True
    )
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (db.Index("ix_project_comments_project_created", "project_id", "created_at"),)

    project = db.relationship("Project", back_populates="comments")
    author = db.relationship("User", foreign_keys=[author_id])
    replies = db.relationship(
        "ProjectComment",
        backref=db.backref("parent", remote_side=[id]),
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        """Serialize the comment for API responses."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "author_id": self.author_id,
            "author_username": self.author.username if self.author else None,
            "parent_id": self.parent_id,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<ProjectComment id={self.id} project_id={self.project_id}>"
