"""Workspaces blueprint: user workspaces, project import, and project
intelligence (explorer, search, AI chat, analysis, and health stats).
"""

from flask import Blueprint

bp = Blueprint("workspaces", __name__, url_prefix="/workspaces")

from app.workspaces import routes  # noqa: E402,F401
