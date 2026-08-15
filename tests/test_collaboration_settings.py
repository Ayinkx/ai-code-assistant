"""Tests for workspace collaboration settings (#158)."""

from app.extensions import db
from app.models import User, Workspace, WorkspaceMember


def _create_user(username, email):
    user = User(username=username, email=email)
    user.set_password("supersecret123")
    db.session.add(user)
    db.session.commit()
    return user


def _setup(owner, member=None):
    workspace = Workspace(user_id=owner.id, name="Settings workspace")
    db.session.add(workspace)
    db.session.commit()
    if member is not None:
        db.session.add(WorkspaceMember(workspace_id=workspace.id, user_id=member.id, role="viewer"))
        db.session.commit()
    return workspace


class TestSettings:
    def test_defaults(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        workspace = _setup(owner)
        login(email="owner@example.com")
        data = client.get(f"/workspaces/api/workspaces/{workspace.id}/settings").get_json()
        assert data["invitations_enabled"] is True
        assert data["default_member_role"] == "viewer"

    def test_member_can_read_settings(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        member = _create_user("member", "member@example.com")
        workspace = _setup(owner, member)
        login(email="member@example.com")
        assert client.get(f"/workspaces/api/workspaces/{workspace.id}/settings").status_code == 200

    def test_member_cannot_update_settings(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        member = _create_user("member", "member@example.com")
        workspace = _setup(owner, member)
        login(email="member@example.com")
        response = client.put(
            f"/workspaces/api/workspaces/{workspace.id}/settings",
            json={"invitations_enabled": False},
        )
        assert response.status_code == 403

    def test_owner_can_update_settings(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        workspace = _setup(owner)
        login(email="owner@example.com")
        response = client.put(
            f"/workspaces/api/workspaces/{workspace.id}/settings",
            json={"invitations_enabled": False, "default_member_role": "contributor"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["invitations_enabled"] is False
        assert data["default_member_role"] == "contributor"

    def test_invalid_default_role_rejected(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        workspace = _setup(owner)
        login(email="owner@example.com")
        response = client.put(
            f"/workspaces/api/workspaces/{workspace.id}/settings",
            json={"default_member_role": "admin"},
        )
        assert response.status_code == 400

    def test_settings_change_records_activity(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        workspace = _setup(owner)
        login(email="owner@example.com")
        client.put(
            f"/workspaces/api/workspaces/{workspace.id}/settings",
            json={"invitations_enabled": False},
        )
        from app.models.activity_event import EVENT_SETTINGS_CHANGED, ActivityEvent

        event = ActivityEvent.query.filter_by(
            workspace_id=workspace.id, event_type=EVENT_SETTINGS_CHANGED
        ).one()
        assert event.event_metadata["invitations_enabled"] is False

    def test_settings_are_per_workspace(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        first = _setup(owner)
        second = Workspace(user_id=owner.id, name="Second")
        db.session.add(second)
        db.session.commit()
        login(email="owner@example.com")
        client.put(
            f"/workspaces/api/workspaces/{first.id}/settings",
            json={"invitations_enabled": False},
        )
        data = client.get(f"/workspaces/api/workspaces/{second.id}/settings").get_json()
        assert data["invitations_enabled"] is True

    def test_non_member_cannot_read_settings(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        workspace = _setup(owner)
        make_user(username="stranger", email="stranger@example.com")
        login(email="stranger@example.com")
        assert client.get(f"/workspaces/api/workspaces/{workspace.id}/settings").status_code == 404
