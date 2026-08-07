"""Prompt management blueprint: saved prompt templates."""

from flask import Blueprint

bp = Blueprint("prompts", __name__, url_prefix="/prompts")

from app.prompts import routes  # noqa: E402, F401  (import routes to register them)
