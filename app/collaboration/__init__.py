"""Collaboration blueprint: invitations, notifications, comments, activity,
audit, settings, presence, and the members/audit pages.

All Phase 7 member-facing and owner-facing endpoints that are not direct
extensions of the Phase 6 workspace/project CRUD live here, and every one of
them routes its authorization through ``app/services/permissions.py``.
"""

from flask import Blueprint

bp = Blueprint("collaboration", __name__, url_prefix="/workspaces")

from app.collaboration import routes  # noqa: E402,F401
