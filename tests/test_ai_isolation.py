"""Tests for AI context isolation and team-context framing (#152/#153).

Verifies that (a) source-content access fails closed for non-owners at the
service and route layers, and (b) every prompt header carries escaped
workspace/team context so analyses are grounded and bounded.
"""

import contextlib

from flask_login import login_user

from app.extensions import db
from app.models import Project, ProjectFile, User, Workspace, WorkspaceMember
from app.services import project_analysis
from app.services.project_analysis import (
    _context_header,
    _member_roster,
    build_context,
    build_messages,
    team_context,
)


def _create_user(username, email):
    user = User(username=username, email=email)
    user.set_password("supersecret123")
    db.session.add(user)
    db.session.commit()
    return user


def _setup(owner, member=None, member_role="viewer"):
    workspace = Workspace(user_id=owner.id, name="Isolation workspace")
    db.session.add(workspace)
    db.session.commit()
    project = Project(
        workspace_id=workspace.id,
        user_id=owner.id,
        name="Secret project",
        source="archive",
        status="ready",
        file_count=1,
        total_size_bytes=20,
    )
    db.session.add(project)
    db.session.commit()
    db.session.add(
        ProjectFile(
            project_id=project.id,
            path="src/secret.py",
            size=20,
            is_binary=False,
            language="python",
            content="TOKEN_SECRET = 'only-for-owner'",
        )
    )
    if member is not None:
        db.session.add(
            WorkspaceMember(workspace_id=workspace.id, user_id=member.id, role=member_role)
        )
        db.session.commit()
    return workspace, project


@contextlib.contextmanager
def _authorized_context(app, user):
    with app.test_request_context("/"):
        login_user(user)
        yield


class TestFailClosedContentAccess:
    def test_member_cannot_build_context_for_owners_project(self, app, make_user):
        owner = make_user(username="owner", email="owner@example.com")
        member = _create_user("member", "member@example.com")
        _, project = _setup(owner, member)
        with _authorized_context(app, member):
            try:
                build_context(project, "what is the secret")
                raised = False
            except Exception:
                raised = True
        assert raised

    def test_member_cannot_chat_with_owners_project(self, app, make_user):
        owner = make_user(username="owner", email="owner@example.com")
        member = _create_user("member", "member@example.com")
        _, project = _setup(owner, member)
        with _authorized_context(app, member):
            try:
                project_analysis.chat_with_project(project, "hello")
                raised = False
            except Exception:
                raised = True
        assert raised

    def test_member_content_routes_404(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        member = _create_user("member", "member@example.com")
        _, project = _setup(owner, member)
        login(email="member@example.com")
        for path, kwargs in [
            (f"/workspaces/api/projects/{project.id}/tree", {"query_string": {"path": ""}}),
            (
                f"/workspaces/api/projects/{project.id}/file",
                {"query_string": {"path": "src/secret.py"}},
            ),
            (f"/workspaces/api/projects/{project.id}/stats", {}),
        ]:
            assert client.get(path, **kwargs).status_code == 404, path

    def test_owner_content_routes_work(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        member = _create_user("member", "member@example.com")
        _, project = _setup(owner, member)
        login(email="owner@example.com")
        assert (
            client.get(
                f"/workspaces/api/projects/{project.id}/file",
                query_string={"path": "src/secret.py"},
            ).status_code
            == 200
        )


class TestTeamContext:
    def test_header_includes_workspace_and_owner_first(self, app, make_user):
        owner = make_user(username="owner", email="owner@example.com")
        member = _create_user("member", "member@example.com")
        _, project = _setup(owner, member)
        with _authorized_context(app, owner):
            roster = _member_roster(project.workspace_id, max_members=20)
            assert roster[0] == (owner.username, "owner")
            header = _context_header(project)
            assert "Project: Secret project" in header
            assert "Workspace: Isolation workspace" in header
            assert "owner (owner)" in header
            assert "member (viewer)" in header

    def test_member_roster_capped_and_escaped(self, app, make_user):
        owner = make_user(username="owner", email="owner@example.com")
        for i in range(5):
            _create_user(f"m{i}", f"m{i}@example.com")
        workspace, project = _setup(owner)
        for i in range(5):
            user = User.query.filter_by(username=f"m{i}").first()
            db.session.add(
                WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="viewer")
            )
        db.session.commit()
        workspace.name = "Backtick ` workspace"
        db.session.commit()
        with _authorized_context(app, owner):
            roster = _member_roster(project.workspace_id, max_members=3)
            assert len(roster) == 3
            context = team_context(project, max_members=3)
            assert "`" not in context
            assert "…" in context
            assert "(you are the only member)" not in context

    def test_only_member_hint(self, app, make_user):
        owner = make_user(username="owner", email="owner@example.com")
        _, project = _setup(owner)
        with _authorized_context(app, owner):
            context = team_context(project, max_members=20)
            assert "(you are the only member)" in context

    def test_prompt_contains_team_context(self, app, make_user):
        owner = make_user(username="owner", email="owner@example.com")
        member = _create_user("member", "member@example.com")
        _, project = _setup(owner, member)
        with _authorized_context(app, owner):
            messages = build_messages(project, "Review the helper", [])
            user_prompt = messages[-1]["content"]
            assert "Project: Secret project" in user_prompt
            assert "Workspace: Isolation workspace" in user_prompt
            assert "owner (owner)" in user_prompt
            assert "Mention teammates with @username" in user_prompt

    def test_system_prompt_bounds_context(self, app, make_user):
        owner = make_user(username="owner", email="owner@example.com")
        _, project = _setup(owner)
        with _authorized_context(app, owner):
            messages = build_messages(project, "Anything", [])
            system = messages[0]["content"]
            assert "out of scope" in system
            assert "current project" in system
