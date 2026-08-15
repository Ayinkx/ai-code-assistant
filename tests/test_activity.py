"""Tests for the member activity feed and the owner-only audit log (#145/#151).

Covers role scoping (members never see the audit-sensitive subset), cursor
pagination, filters, and the uniform no-existence-oracle behavior.
"""

from datetime import UTC, datetime, timedelta

from app.extensions import db
from app.models import User, Workspace, WorkspaceMember
from app.models.activity_event import (
    AUDIT_EVENT_TYPES,
    EVENT_AI_ANALYSIS_RUN,
    EVENT_COMMENT_ADDED,
    EVENT_MEMBER_ADDED,
    EVENT_MEMBER_REMOVED,
    ActivityEvent,
)


def _create_user(username, email):
    user = User(username=username, email=email)
    user.set_password("supersecret123")
    db.session.add(user)
    db.session.commit()
    return user


def _setup(owner, member):
    workspace = Workspace(user_id=owner.id, name="Activity workspace")
    db.session.add(workspace)
    db.session.commit()
    db.session.add(WorkspaceMember(workspace_id=workspace.id, user_id=member.id, role="viewer"))
    db.session.commit()
    return workspace


def _add_event(workspace_id, actor_id, event_type, metadata=None, minutes_ago=0):
    event = ActivityEvent(
        workspace_id=workspace_id,
        actor_id=actor_id,
        event_type=event_type,
        event_metadata=metadata,
        created_at=datetime.now(UTC) - timedelta(minutes=minutes_ago),
    )
    db.session.add(event)
    db.session.commit()
    return event


class TestActivityFeed:
    def test_member_never_sees_audit_subset(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        member = _create_user("member", "member@example.com")
        workspace = _setup(owner, member)
        _add_event(workspace.id, owner.id, EVENT_MEMBER_ADDED)
        _add_event(workspace.id, owner.id, EVENT_COMMENT_ADDED)
        login(email="member@example.com")
        data = client.get(f"/workspaces/api/workspaces/{workspace.id}/activity").get_json()
        assert len(data["items"]) == 1
        assert data["items"][0]["event_type"] == EVENT_COMMENT_ADDED

    def test_owner_sees_all(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        member = _create_user("member", "member@example.com")
        workspace = _setup(owner, member)
        _add_event(workspace.id, owner.id, EVENT_MEMBER_ADDED)
        _add_event(workspace.id, owner.id, EVENT_COMMENT_ADDED)
        login(email="owner@example.com")
        data = client.get(f"/workspaces/api/workspaces/{workspace.id}/activity").get_json()
        assert len(data["items"]) == 2

    def test_member_feed_never_includes_metadata(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        member = _create_user("member", "member@example.com")
        workspace = _setup(owner, member)
        _add_event(workspace.id, owner.id, EVENT_AI_ANALYSIS_RUN, metadata={"kind": "bugs"})
        login(email="member@example.com")
        data = client.get(f"/workspaces/api/workspaces/{workspace.id}/activity").get_json()
        assert len(data["items"]) == 1
        assert "metadata" not in data["items"][0]

    def test_event_type_filter(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        member = _create_user("member", "member@example.com")
        workspace = _setup(owner, member)
        _add_event(workspace.id, owner.id, EVENT_COMMENT_ADDED)
        _add_event(workspace.id, owner.id, EVENT_AI_ANALYSIS_RUN)
        login(email="member@example.com")
        data = client.get(
            f"/workspaces/api/workspaces/{workspace.id}/activity",
            query_string={"event_type": EVENT_COMMENT_ADDED},
        ).get_json()
        assert len(data["items"]) == 1
        assert data["items"][0]["event_type"] == EVENT_COMMENT_ADDED

    def test_cursor_pagination(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        member = _create_user("member", "member@example.com")
        workspace = _setup(owner, member)
        for i in range(3):
            _add_event(workspace.id, owner.id, EVENT_COMMENT_ADDED, minutes_ago=i)
        login(email="member@example.com")
        first = client.get(
            f"/workspaces/api/workspaces/{workspace.id}/activity", query_string={"per_page": 2}
        ).get_json()
        assert len(first["items"]) == 2
        assert first["next_cursor"] is not None
        second = client.get(
            f"/workspaces/api/workspaces/{workspace.id}/activity",
            query_string={"per_page": 2, "before": first["next_cursor"]},
        ).get_json()
        assert len(second["items"]) == 1
        assert second["next_cursor"] is None

    def test_actor_filter(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        member = _create_user("member", "member@example.com")
        workspace = _setup(owner, member)
        _add_event(workspace.id, owner.id, EVENT_COMMENT_ADDED)
        _add_event(workspace.id, member.id, EVENT_COMMENT_ADDED)
        login(email="member@example.com")
        data = client.get(
            f"/workspaces/api/workspaces/{workspace.id}/activity",
            query_string={"actor": "owner"},
        ).get_json()
        assert len(data["items"]) == 1

    def test_non_member_gets_404(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        outsider = _create_user("outsider", "outsider@example.com")
        workspace = _setup(owner, outsider)
        make_user(username="stranger", email="stranger@example.com")
        login(email="stranger@example.com")
        assert client.get(f"/workspaces/api/workspaces/{workspace.id}/activity").status_code == 404


class TestAuditLog:
    def test_audit_is_owner_only(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        member = _create_user("member", "member@example.com")
        workspace = _setup(owner, member)
        _add_event(workspace.id, owner.id, EVENT_MEMBER_ADDED)
        login(email="member@example.com")
        assert client.get(f"/workspaces/api/workspaces/{workspace.id}/audit").status_code == 403
        login(email="owner@example.com")
        assert client.get(f"/workspaces/api/workspaces/{workspace.id}/audit").status_code == 200

    def test_audit_only_contains_audit_subset(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        workspace = _setup(owner, _create_user("member", "member@example.com"))
        _add_event(workspace.id, owner.id, EVENT_MEMBER_ADDED)
        _add_event(workspace.id, owner.id, EVENT_COMMENT_ADDED)
        _add_event(workspace.id, owner.id, EVENT_MEMBER_REMOVED)
        login(email="owner@example.com")
        data = client.get(f"/workspaces/api/workspaces/{workspace.id}/audit").get_json()
        types = {item["event_type"] for item in data["items"]}
        assert types == {EVENT_MEMBER_ADDED, EVENT_MEMBER_REMOVED}
        assert types.issubset(set(AUDIT_EVENT_TYPES))

    def test_audit_includes_metadata_for_owner(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        workspace = _setup(owner, _create_user("member", "member@example.com"))
        _add_event(workspace.id, owner.id, EVENT_MEMBER_ADDED, metadata={"role": "viewer"})
        login(email="owner@example.com")
        data = client.get(f"/workspaces/api/workspaces/{workspace.id}/audit").get_json()
        assert data["items"][0]["metadata"]["role"] == "viewer"

    def test_audit_pagination_and_filter(self, client, make_user, login):
        owner = make_user(username="owner", email="owner@example.com")
        workspace = _setup(owner, _create_user("member", "member@example.com"))
        for i in range(5):
            _add_event(workspace.id, owner.id, EVENT_MEMBER_ADDED, minutes_ago=i)
        login(email="owner@example.com")
        data = client.get(
            f"/workspaces/api/workspaces/{workspace.id}/audit",
            query_string={"per_page": 2, "page": 2},
        ).get_json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
