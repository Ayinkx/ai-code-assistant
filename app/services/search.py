"""Project-wide search service.

Searches an indexed project by file path and (for plain-text files with stored
content) by file contents. Results are bounded so a single query never returns
an unbounded number of matches, and binary or oversized files are skipped for
content matches.
"""

from __future__ import annotations

from flask import current_app
from sqlalchemy import func

from app.extensions import db
from app.models import ProjectFile

_SNIPPET_RADIUS = 80


def _escape_like(value: str) -> str:
    """Escape LIKE wildcards so user input is matched literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _snippet(text: str, needle: str) -> str | None:
    """Return a short snippet surrounding the first match of ``needle``."""
    lower_text = text.lower()
    index = lower_text.find(needle)
    if index < 0:
        return None
    start = max(0, index - _SNIPPET_RADIUS)
    end = min(len(text), index + len(needle) + _SNIPPET_RADIUS)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    snippet = text[start:end].replace("\n", " ").replace("\r", "")
    return f"{prefix}{snippet}{suffix}"


def search_project(
    project_id: int,
    query: str,
    *,
    case_sensitive: bool = False,
    limit: int | None = None,
) -> dict:
    """Search ``project_id`` for ``query`` and return bounded results.

    Returns ``{"query", "total", "results"}`` where each result is a file with
    ``path``, ``size``, ``language``, ``matched`` (``path`` or ``content``), and
    an optional ``snippet``.
    """
    query = (query or "").strip()
    if not query:
        return {"query": "", "total": 0, "results": []}
    if limit is None:
        limit = current_app.config["PROJECT_SEARCH_MAX_RESULTS"]
    limit = max(1, min(int(limit), current_app.config["PROJECT_SEARCH_MAX_RESULTS"]))
    if len(query) > 200:
        query = query[:200]

    needle = query if case_sensitive else query.lower()
    pattern = f"%{_escape_like(needle)}%"
    path_col = ProjectFile.path if case_sensitive else func.lower(ProjectFile.path)
    content_col = ProjectFile.content if case_sensitive else func.lower(ProjectFile.content)

    def rows_for(*criteria):
        return (
            db.session.query(ProjectFile)
            .filter(*criteria)
            .order_by(ProjectFile.path.asc())
            .limit(limit)
            .all()
        )

    path_rows = rows_for(
        ProjectFile.project_id == project_id,
        path_col.like(pattern, escape="\\"),
    )
    content_rows = rows_for(
        ProjectFile.project_id == project_id,
        ProjectFile.is_binary.is_(False),
        ProjectFile.content.isnot(None),
        content_col.like(pattern, escape="\\"),
    )

    results: list[dict] = []
    seen: set[int] = set()
    combined = [
        *((f, "path") for f in path_rows),
        *((f, "content") for f in content_rows),
    ]
    for file, matched in combined:
        if len(results) >= limit:
            break
        if file.id in seen:
            continue
        seen.add(file.id)
        result = {
            "path": file.path,
            "size": file.size,
            "language": file.language,
            "matched": matched,
        }
        if matched == "content" and file.content:
            result["snippet"] = _snippet(file.content, needle)
        results.append(result)

    return {"query": query, "total": len(results), "results": results}
