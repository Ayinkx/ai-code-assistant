"""Chat blueprint: conversation management and AI streaming."""

from flask import Blueprint

bp = Blueprint("chat", __name__, url_prefix="/chat")

from app.chat import routes  # noqa: E402, F401  (import routes to register them)
