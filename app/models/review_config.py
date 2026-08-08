"""Review configuration model.

Per-project configuration that controls how AI reviews behave for that
project. Every field has a sensible default from the application config, so a
project can rely on defaults and only override what it needs. ``kinds`` and
``languages`` are stored as comma-separated strings.
"""

from datetime import UTC, datetime

from app.extensions import db

ROLE_UNSET = ""


class ReviewConfig(db.Model):
    """Per-user, per-project AI review configuration."""

    __tablename__ = "review_configs"
    __table_args__ = (
        db.UniqueConstraint("user_id", "project_id", name="uq_review_configs_user_project"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kinds = db.Column(db.String(200), nullable=True)
    severity_threshold = db.Column(db.String(20), nullable=True)
    languages = db.Column(db.String(500), nullable=True)
    testing_focus = db.Column(db.Boolean, nullable=False, default=True)
    security_focus = db.Column(db.Boolean, nullable=False, default=True)
    performance_focus = db.Column(db.Boolean, nullable=False, default=True)
    max_files = db.Column(db.Integer, nullable=True)
    max_context_chars = db.Column(db.Integer, nullable=True)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    project = db.relationship("Project", back_populates="review_config")

    def to_dict(self) -> dict:
        """Serialize the configuration for JSON API responses."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "kinds": self.kinds,
            "severity_threshold": self.severity_threshold,
            "languages": self.languages,
            "testing_focus": self.testing_focus,
            "security_focus": self.security_focus,
            "performance_focus": self.performance_focus,
            "max_files": self.max_files,
            "max_context_chars": self.max_context_chars,
            "enabled": self.enabled,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<ReviewConfig id={self.id} project_id={self.project_id}>"
