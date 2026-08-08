"""AI code review blueprint.

Phase 6 adds an AI review workflow on top of the GitHub pull requests and
imported projects: pull request reviews (structured findings with severities),
project quality/security/test reviews, per-project review configuration, and a
quality dashboard whose metrics are computed only from real review data.

Nothing here ever modifies a pull request, closes or approves it, or takes any
destructive GitHub action — reviews are strictly read-only on the GitHub side.
"""

from flask import Blueprint

bp = Blueprint("reviews", __name__, url_prefix="/reviews")

from app.reviews import routes  # noqa: E402,F401  (register routes on import)
