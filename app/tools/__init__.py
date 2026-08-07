"""AI tools blueprint: code generation, code actions, and file analysis."""

from flask import Blueprint

bp = Blueprint("tools", __name__, url_prefix="/tools")

from app.tools import routes  # noqa: E402, F401  (import routes to register them)
