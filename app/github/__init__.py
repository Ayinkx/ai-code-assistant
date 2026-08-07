"""GitHub integration blueprint: OAuth connection and repository browser.

Phase 4 brings GitHub into the assistant: users connect their GitHub account
via OAuth, browse repositories and commits, inspect issues and pull requests,
and ask the AI to analyze them. All GitHub API calls are made on the user's
behalf with their own (encrypted) token, so GitHub's permission model decides
what is visible.
"""

from flask import Blueprint

bp = Blueprint("github", __name__, url_prefix="/github")

from app.github import routes  # noqa: E402,F401  (register routes on import)
