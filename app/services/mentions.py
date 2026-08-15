"""Mention extraction for project comments.

Parses ``@username`` tokens bounded by whitespace/punctuation and resolves them
against *active workspace members only* — never external users. Unknown
usernames are silently ignored and deduplicated. This keeps mentions from
exposing private users or private workspace information: only names already
visible to the workspace appear in notifications.
"""

from __future__ import annotations

import re

from app.models import User, WorkspaceMember
from app.models.workspace_member import STATUS_ACTIVE

_MENTION_RE = re.compile(r"(?<![\w.])@([A-Za-z0-9_\-]{1,80})")

_MENTION_HINTS = (
    "Tip: mention a teammate with @username (only active workspace members " "can be mentioned)."
)


def extract_mentions(content: str, workspace_id: int) -> list[User]:
    """Return the unique active workspace members mentioned in ``content``.

    Usernames are matched case-insensitively against active members of the
    workspace. Unknown usernames and members who have been removed are ignored.
    """
    if not content:
        return []
    names = {match.group(1).lower() for match in _MENTION_RE.finditer(content)}
    if not names:
        return []
    rows = (
        User.query.join(WorkspaceMember, WorkspaceMember.user_id == User.id)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.status == STATUS_ACTIVE,
            User.username.in_(names),
        )
        .all()
    )
    return rows
