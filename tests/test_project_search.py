"""Tests for project-wide search."""

from app.extensions import db
from app.models import Project, ProjectFile, User, Workspace
from app.models.project import SOURCE_ARCHIVE, STATUS_READY
from app.services.search import search_project


def _ready_project(files):
    user = User(username="searchuser", email="searchuser@example.com")
    user.set_password("supersecret123")
    db.session.add(user)
    db.session.commit()
    workspace = Workspace(user_id=user.id, name="Search workspace")
    db.session.add(workspace)
    db.session.commit()
    project = Project(
        workspace_id=workspace.id,
        user_id=user.id,
        name="Search project",
        source=SOURCE_ARCHIVE,
        status=STATUS_READY,
    )
    db.session.add(project)
    db.session.commit()

    for path, content, is_binary in files:
        db.session.add(
            ProjectFile(
                project_id=project.id,
                path=path,
                size=len(content or b""),
                is_binary=is_binary,
                content=None if is_binary else content,
            )
        )
    db.session.commit()
    return project


class TestPathSearch:
    def test_matches_file_name(self, app):
        project = _ready_project([("login_form.py", "x = 1", False), ("other.py", "y", False)])
        result = search_project(project.id, "login")
        assert result["total"] == 1
        assert result["results"][0]["path"] == "login_form.py"
        assert result["results"][0]["matched"] == "path"

    def test_empty_query_returns_nothing(self, app):
        project = _ready_project([("app.py", "x", False)])
        result = search_project(project.id, "   ")
        assert result["total"] == 0

    def test_path_match_sorted_before_content(self, app):
        project = _ready_project(
            [
                ("tools/search_helper.py", "a", False),
                ("helper.py", "def search_here(): pass", False),
            ]
        )
        result = search_project(project.id, "search")
        assert result["results"][0]["matched"] == "path"


class TestContentSearch:
    def test_matches_contents_with_snippet(self, app):
        content = "def main():\n    return 'unique_token_xyz'\n"
        project = _ready_project([("app.py", content, False)])
        result = search_project(project.id, "unique_token_xyz")
        assert result["total"] == 1
        hit = result["results"][0]
        assert hit["matched"] == "content"
        assert hit["snippet"] is not None
        assert "unique_token_xyz" in hit["snippet"]

    def test_binary_files_excluded_from_content_search(self, app):
        project = _ready_project(
            [("blob.dat", b"\x00secret_token\x00", True), ("text.py", "secret_token", False)]
        )
        result = search_project(project.id, "secret_token")
        paths = [r["path"] for r in result["results"]]
        assert "text.py" in paths
        assert "blob.dat" not in paths

    def test_case_sensitive_query(self, app):
        project = _ready_project([("a.py", "FooBar", False)])
        assert search_project(project.id, "foobar")["total"] == 1
        assert search_project(project.id, "FooBar", case_sensitive=True)["total"] == 1

    def test_limit_caps_results(self, app):
        project = _ready_project([(f"file_{i}.py", "needle", False) for i in range(20)])
        result = search_project(project.id, "needle", limit=5)
        assert result["total"] == 5

    def test_escape_like_wildcards(self, app):
        project = _ready_project([("app.py", "has 100% certainty", False)])
        result = search_project(project.id, "100%")
        assert result["total"] == 1
