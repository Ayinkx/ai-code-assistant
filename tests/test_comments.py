"""Tests for project discussion comments and @mention notifications (#146)."""

from app.extensions import db
from app.models import Notification, Project, User, Workspace, WorkspaceMember
from app.models.project_comment import COMMENT_MAX_LENGTH
from app.services.mentions import extract_mentions


def _create_user(username, email):
    user = User(username=username, email=email)
    user.set_password("supersecret123")
    db.session.add(user)
    db.session.commit()
    return user


def _setup(owner, member=None):
    workspace = Workspace(user_id=owner.id, name="Comments workspace")
    db.session.add(workspace)
    db.session.commit()
    project = Project(
        workspace_id=workspace.id,
        user_id=owner.id,
        name="Commented project",
        source="archive",
        status="ready",
    )
    db.session.add(project)
    db.session.commit()
    if member is not None:
        db.session.add(WorkspaceMember(workspace_id=workspace.id, user_id=member.id, role="viewer"))
        db.session.commit()
    return workspace, project


class TestCommentCrud:
    def test_member_can_comment(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        member = _create_user("member", "member@example.com")
        _, project = _setup(owner, member)
        login(email="member@example.com")
        response = client.post(
            f"/workspaces/api/projects/{project.id}/comments",
            json={"content": "What does this module do?"},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["author_username"] == "member"
        assert data["content"] == "What does this module do?"

    def test_list_comments(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        _, project = _setup(owner)
        login(email="owner@example.com")
        client.post(
            f"/workspaces/api/projects/{project.id}/comments",
            json={"content": "First"},
        )
        client.post(
            f"/workspaces/api/projects/{project.id}/comments",
            json={"content": "Second"},
        )
        data = client.get(f"/workspaces/api/projects/{project.id}/comments").get_json()
        assert data["total"] == 2
        assert [c["content"] for c in data["items"]] == ["First", "Second"]

    def test_reply_to_parent(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        _, project = _setup(owner)
        login(email="owner@example.com")
        parent = client.post(
            f"/workspaces/api/projects/{project.id}/comments",
            json={"content": "Parent"},
        ).get_json()
        response = client.post(
            f"/workspaces/api/projects/{project.id}/comments",
            json={"content": "Reply", "parent_id": parent["id"]},
        )
        assert response.status_code == 201
        assert response.get_json()["parent_id"] == parent["id"]

    def test_empty_content_rejected(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        _, project = _setup(owner)
        login(email="owner@example.com")
        assert (
            client.post(
                f"/workspaces/api/projects/{project.id}/comments", json={"content": "   "}
            ).status_code
            == 400
        )

    def test_overlong_content_rejected(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        _, project = _setup(owner)
        login(email="owner@example.com")
        response = client.post(
            f"/workspaces/api/projects/{project.id}/comments",
            json={"content": "x" * (COMMENT_MAX_LENGTH + 1)},
        )
        assert response.status_code == 400

    def test_author_can_delete_own_comment(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        member = _create_user("member", "member@example.com")
        _, project = _setup(owner, member)
        login(email="member@example.com")
        comment = client.post(
            f"/workspaces/api/projects/{project.id}/comments",
            json={"content": "Delete me"},
        ).get_json()
        response = client.delete(f"/workspaces/api/projects/{project.id}/comments/{comment['id']}")
        assert response.status_code == 200

    def test_other_member_cannot_delete(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        member = _create_user("member", "member@example.com")
        _, project = _setup(owner, member)
        login(email="member@example.com")
        comment = client.post(
            f"/workspaces/api/projects/{project.id}/comments",
            json={"content": "Keep me"},
        ).get_json()
        other = _create_user("other", "other@example.com")
        db.session.add(
            WorkspaceMember(workspace_id=project.workspace_id, user_id=other.id, role="viewer")
        )
        db.session.commit()
        login(email="other@example.com")
        response = client.delete(f"/workspaces/api/projects/{project.id}/comments/{comment['id']}")
        assert response.status_code == 403

    def test_owner_can_delete_any_comment(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        member = _create_user("member", "member@example.com")
        _, project = _setup(owner, member)
        login(email="member@example.com")
        comment = client.post(
            f"/workspaces/api/projects/{project.id}/comments",
            json={"content": "Delete me by owner"},
        ).get_json()
        login(email="owner@example.com")
        response = client.delete(f"/workspaces/api/projects/{project.id}/comments/{comment['id']}")
        assert response.status_code == 200

    def test_non_member_cannot_comment(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        _, project = _setup(owner)
        make_user(username="outsider", email="outsider@example.com")
        login(email="outsider@example.com")
        assert (
            client.post(
                f"/workspaces/api/projects/{project.id}/comments",
                json={"content": "Intrusion"},
            ).status_code
            == 404
        )
        assert client.get(f"/workspaces/api/projects/{project.id}/comments").status_code == 404


class TestMentions:
    def test_extract_mentions_resolves_active_members_only(self, make_user):
        owner = make_user(username="owner", email="owner@example.com")
        member = _create_user("member", "member@example.com")
        workspace = Workspace(user_id=owner.id, name="Mention workspace")
        db.session.add(workspace)
        db.session.commit()
        db.session.add(WorkspaceMember(workspace_id=workspace.id, user_id=member.id, role="viewer"))
        removed = _create_user("removed", "removed@example.com")
        membership = WorkspaceMember(workspace_id=workspace.id, user_id=removed.id, role="viewer")
        db.session.add(membership)
        db.session.commit()
        membership.mark_removed()
        db.session.commit()
        mentioned = extract_mentions("Hey @Member and @Outsider and @removed!", workspace.id)
        assert [u.username for u in mentioned] == ["member"]

    def test_extract_mentions_dedupes_and_ignores_unknown(self, make_user):
        owner = make_user(username="owner", email="owner@example.com")
        member = _create_user("member", "member@example.com")
        workspace = Workspace(user_id=owner.id, name="Mention workspace")
        db.session.add(workspace)
        db.session.commit()
        db.session.add(WorkspaceMember(workspace_id=workspace.id, user_id=member.id, role="viewer"))
        db.session.commit()
        mentioned = extract_mentions("@member @member @nobody", workspace.id)
        assert len(mentioned) == 1
        assert extract_mentions("no mentions", workspace.id) == []

    def test_mention_creates_notification_excluding_author(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        member = _create_user("member", "member@example.com")
        _, project = _setup(owner, member)
        login(email="owner@example.com")
        client.post(
            f"/workspaces/api/projects/{project.id}/comments",
            json={"content": "@member please review"},
        )
        member_notif = Notification.query.filter_by(user_id=member.id, type="mention").all()
        assert len(member_notif) == 1
        owner_notif = Notification.query.filter_by(user_id=owner.id, type="mention").all()
        assert owner_notif == []

    def test_mention_unknown_user_no_notification(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        member = _create_user("member", "member@example.com")
        _, project = _setup(owner, member)
        login(email="member@example.com")
        client.post(
            f"/workspaces/api/projects/{project.id}/comments",
            json={"content": "@ghosthello are you there?"},
        )
        assert Notification.query.filter_by(type="mention").all() == []
