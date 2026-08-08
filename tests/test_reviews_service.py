"""Tests for the AI review service: parsing, bounds, and structured findings."""

import json

from app.extensions import db
from app.models import Project, ProjectFile, User, Workspace
from app.models.project import SOURCE_ARCHIVE, STATUS_READY
from app.services import reviews


def _ready_project(files):
    user = User(username="revsvcuser", email="revsvcuser@example.com")
    user.set_password("supersecret123")
    db.session.add(user)
    db.session.commit()
    workspace = Workspace(user_id=user.id, name="Svc workspace")
    db.session.add(workspace)
    db.session.commit()
    project = Project(
        workspace_id=workspace.id,
        user_id=user.id,
        name="Svc project",
        source=SOURCE_ARCHIVE,
        status=STATUS_READY,
    )
    db.session.add(project)
    db.session.commit()
    for path, content in files:
        db.session.add(
            ProjectFile(
                project_id=project.id,
                path=path,
                size=len(content),
                is_binary=False,
                content=content,
            )
        )
    db.session.commit()
    return project


class FakeProvider:
    def __init__(self, text):
        self.text = text

    def complete(self, messages, *, stream=False):
        return self.text


JSON_REPLY = json.dumps(
    {
        "summary": {
            "overall_assessment": "Solid overall.",
            "important_findings": ["One high risk found."],
            "suggested_improvements": ["Add tests."],
            "testing_recommendations": ["Cover edge cases."],
            "security_concerns": ["None observed."],
            "performance_concerns": ["Fine."],
            "files_affected": ["app/main.py"],
        },
        "findings": [
            {
                "file": "app/main.py",
                "line": 4,
                "severity": "critical",
                "category": "bug",
                "explanation": "Null dereference when data is missing.",
                "recommendation": "Guard against None.",
                "confidence": "confirmed",
            },
            {
                "file": "app/main.py",
                "line": 9,
                "severity": "informational",
                "category": "other",
                "explanation": "Style note only.",
                "recommendation": "",
                "confidence": "suggestion",
            },
        ],
    }
)


class TestParseReviewResponse:
    def test_parses_json_findings(self, app):
        result = reviews.parse_review_response(JSON_REPLY, kind="pr")
        assert result["error"] is None
        assert result["summary"]["overall_assessment"] == "Solid overall."
        assert len(result["findings"]) == 2
        finding = result["findings"][0]
        assert finding["severity"] == "critical"
        assert finding["file"] == "app/main.py"
        assert finding["line"] == 4
        assert finding["confidence"] == "confirmed"

    def test_threshold_drops_low_severity(self, app):
        result = reviews.parse_review_response(JSON_REPLY, kind="pr", threshold="high")
        severities = [f["severity"] for f in result["findings"]]
        assert severities == ["critical"]

    def test_markdown_fenced_json(self, app):
        fenced = "```json\n" + JSON_REPLY + "\n```"
        result = reviews.parse_review_response(fenced, kind="pr")
        assert len(result["findings"]) == 2

    def test_unstructured_text_falls_back(self, app):
        result = reviews.parse_review_response("No JSON here, just prose.", kind="pr")
        assert result["findings"] == []
        assert "raw" in result["summary"]

    def test_invalid_finding_entries_skipped(self, app):
        payload = {
            "summary": {"overall_assessment": "x"},
            "findings": [
                "not-a-dict",
                {"severity": "high"},
                {"explanation": "   "},
                {"file": "a.py", "line": "nope", "explanation": "ok", "category": "bogus"},
            ],
        }
        result = reviews.parse_review_response(json.dumps(payload), kind="pr")
        assert len(result["findings"]) == 1
        finding = result["findings"][0]
        assert finding["file"] == "a.py"
        assert finding["line"] is None
        assert finding["category"] == "other"
        assert finding["severity"] == "medium"

    def test_categories_scoped_by_kind(self, app):
        payload = {
            "findings": [{"explanation": "x", "category": "missing-tests"}],
        }
        pr_result = reviews.parse_review_response(json.dumps(payload), kind="pr")
        tests_result = reviews.parse_review_response(json.dumps(payload), kind="tests")
        assert pr_result["findings"][0]["category"] == "other"
        assert tests_result["findings"][0]["category"] == "missing-tests"


def _pr_file(name, patch="x", status="modified", additions=1, deletions=0):
    return {
        "filename": name,
        "patch": patch,
        "status": status,
        "additions": additions,
        "deletions": deletions,
    }


class TestBuildPrContext:
    def test_language_filter(self, app):
        config = {"languages": "py,ts", "max_files": 10, "max_context_chars": 20000}
        files = [
            _pr_file("app.py"),
            _pr_file("app.js"),
            _pr_file("README.md", status="added", additions=2),
        ]
        pr = {
            "number": 1,
            "title": "t",
            "state": "open",
            "merged": False,
            "author": "a",
            "base": "main",
            "head": "feat",
        }
        context = reviews.build_pr_context(pr, files, config)
        assert "app.py" in context["files_text"]
        assert "README.md" not in context["files_text"]

    def test_max_files_bounds_context(self, app):
        config = {"languages": None, "max_files": 2, "max_context_chars": 50000}
        files = [_pr_file(f"f{i}.py") for i in range(6)]
        context = reviews.build_pr_context({"number": 1}, files, config)
        assert context["selected_count"] == 2
        assert context["total_count"] == 6
        assert "only 2 of 6 changed files" in context["files_text"]

    def test_detects_test_files(self, app):
        config = {"languages": None, "max_files": 10, "max_context_chars": 50000}
        files = [_pr_file("tests/test_app.py", status="added"), _pr_file("app.py")]
        context = reviews.build_pr_context({"number": 1}, files, config)
        assert context["test_files"] == ["tests/test_app.py"]


class TestReviewRun:
    def test_review_project_structured(self, app, monkeypatch):
        project = _ready_project([("app/main.py", "def f():\n    pass\n")])
        monkeypatch.setattr(reviews, "get_provider", lambda: FakeProvider(JSON_REPLY))
        config = {
            "languages": None,
            "max_files": 40,
            "max_context_chars": 40000,
            "severity_threshold": "low",
            "testing_focus": True,
            "security_focus": True,
            "performance_focus": True,
        }
        result = reviews.review_project(project, "quality", config)
        assert result["error"] is None
        # The critical finding survives; the informational one is below the
        # "low" severity threshold and is correctly dropped.
        assert len(result["findings"]) == 1
        assert result["findings"][0]["severity"] == "critical"

    def test_review_project_unknown_kind_defaults_to_quality(self, app, monkeypatch):
        project = _ready_project([("app/main.py", "x")])
        monkeypatch.setattr(reviews, "get_provider", lambda: FakeProvider(JSON_REPLY))
        config = {
            "languages": None,
            "max_files": 40,
            "max_context_chars": 40000,
            "severity_threshold": "low",
        }
        result = reviews.review_project(project, "bogus", config)
        assert result["findings"]

    def test_review_pull_request(self, app, monkeypatch):
        monkeypatch.setattr(reviews, "get_provider", lambda: FakeProvider(JSON_REPLY))
        pr = {
            "number": 3,
            "title": "Add feature",
            "body": "Closes #2",
            "state": "open",
            "merged": False,
        }
        files = [_pr_file("app/main.py", patch="---\n+++\n+def f()")]
        config = {
            "languages": None,
            "max_files": 40,
            "max_context_chars": 40000,
            "severity_threshold": "low",
            "security_focus": True,
            "performance_focus": True,
        }
        result = reviews.review_pull_request(pr, files, config)
        assert result["findings"][0]["file"] == "app/main.py"

    def test_provider_error_reported(self, app, monkeypatch):
        from app.services.llm import LLMProviderError

        def boom(*args, **kwargs):
            raise LLMProviderError("no key")

        project = _ready_project([("app/main.py", "x")])
        monkeypatch.setattr(reviews, "get_provider", boom)
        config = {
            "languages": None,
            "max_files": 40,
            "max_context_chars": 40000,
            "severity_threshold": "low",
        }
        result = reviews.review_project(project, "quality", config)
        assert result["error"]
        assert result["findings"] == []

    def test_is_test_path(self):
        assert reviews.is_test_path("tests/test_a.py")
        assert reviews.is_test_path("src/test_a.py")
        assert reviews.is_test_path("pkg/tests/tests_b.py")
        assert not reviews.is_test_path("app/main.py")
