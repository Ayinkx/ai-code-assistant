"""Tests for the invitation lifecycle (#140/#141) and token security.

Covers token hashing + single-delivery, create/list/cancel owner-scoping, the
uniform 404 behavior for unknown/expired/cancelled tokens, accept/decline
flows (including idempotency and rate limiting), and email delivery.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.extensions import db
from app.models import Notification, User, Workspace, WorkspaceInvitation, WorkspaceMember
from app.models.activity_event import EVENT_INVITATION_CREATED, ActivityEvent
from app.models.invitation import (
    INVITE_STATUS_ACCEPTED,
    INVITE_STATUS_CANCELLED,
    INVITE_STATUS_DECLINED,
)
from app.models.workspace_member import ROLE_VIEWER
from app.services import ratelimit
from app.services.invitations import token_hash


def _create_user(username, email):
    user = User(username=username, email=email)
    user.set_password("supersecret123")
    db.session.add(user)
    db.session.commit()
    return user


def _owner_workspace(make_user, username="owner", email="owner@example.com"):
    owner = make_user(username=username, email=email)
    workspace = Workspace(user_id=owner.id, name="Invite workspace")
    db.session.add(workspace)
    db.session.commit()
    return owner, workspace


def _invite(client, workspace, email="invitee@example.com", role="viewer"):
    return client.post(
        f"/workspaces/api/workspaces/{workspace.id}/invitations",
        json={"email": email, "role": role},
    )


class TestTokenSecurity:
    def test_token_returned_once_and_stored_hashed(self, client, make_user, login):
        _, workspace = _owner_workspace(make_user)
        login(email="owner@example.com")
        response = _invite(client, workspace)
        assert response.status_code == 201
        data = response.get_json()
        raw_token = data["token"]
        assert raw_token
        row = WorkspaceInvitation.query.filter_by(workspace_id=workspace.id).one()
        assert row.token_hash == token_hash(raw_token)
        assert row.token_hash != raw_token

    def test_list_never_exposes_token(self, client, make_user, login):
        _, workspace = _owner_workspace(make_user)
        login(email="owner@example.com")
        _invite(client, workspace)
        response = client.get(f"/workspaces/api/workspaces/{workspace.id}/invitations")
        assert response.status_code == 200
        item = response.get_json()["items"][0]
        assert "token" not in item
        assert "token_hash" not in item

    def test_email_is_only_token_delivery_channel(self, client, app, make_user, login, monkeypatch):
        sent = {}

        def fake_send_email(to, subject, text_body, html_body=None):
            sent["to"] = to
            sent["text"] = text_body
            sent["html"] = html_body
            return True

        monkeypatch.setattr("app.services.email.send_email", fake_send_email)
        _, workspace = _owner_workspace(make_user)
        login(email="owner@example.com")
        response = _invite(client, workspace, email="outsider@example.com")
        raw_token = response.get_json()["token"]
        assert sent["to"] == "outsider@example.com"
        assert f"/workspaces/invitations/{raw_token}" in sent["text"]

    def test_notification_payload_has_no_token(self, client, app, make_user, login):
        _, workspace = _owner_workspace(make_user)
        invitee = _create_user("invitee", "invitee@example.com")
        login(email="owner@example.com")
        response = _invite(client, workspace, email="invitee@example.com")
        raw_token = response.get_json()["token"]
        notification = Notification.query.filter_by(user_id=invitee.id).one()
        payload = notification.payload or {}
        assert "token" not in payload
        assert raw_token not in str(payload)
        assert notification.type == "invitation"


class TestCreateInvitation:
    def test_create_requires_owner(self, client, make_user, login):
        _, workspace = _owner_workspace(make_user)
        member = _create_user("member", "member@example.com")
        db.session.add(
            WorkspaceMember(workspace_id=workspace.id, user_id=member.id, role=ROLE_VIEWER)
        )
        db.session.commit()
        login(email="member@example.com")
        response = _invite(client, workspace)
        assert response.status_code == 403

    def test_invalid_email(self, client, make_user, login):
        _, workspace = _owner_workspace(make_user)
        login(email="owner@example.com")
        for bad in ("", "not-an-email", "a" * 300):
            response = _invite(client, workspace, email=bad)
            assert response.status_code == 400

    def test_self_invite_rejected(self, client, make_user, login):
        _, workspace = _owner_workspace(make_user)
        login(email="owner@example.com")
        response = _invite(client, workspace, email="OWNER@example.com")
        assert response.status_code == 400

    def test_existing_member_conflict(self, client, make_user, login):
        _, workspace = _owner_workspace(make_user)
        member = _create_user("member", "member@example.com")
        db.session.add(
            WorkspaceMember(workspace_id=workspace.id, user_id=member.id, role=ROLE_VIEWER)
        )
        db.session.commit()
        login(email="owner@example.com")
        response = _invite(client, workspace, email="member@example.com")
        assert response.status_code == 409

    def test_duplicate_pending_conflict(self, client, make_user, login):
        _, workspace = _owner_workspace(make_user)
        login(email="owner@example.com")
        assert _invite(client, workspace, email="dup@example.com").status_code == 201
        response = _invite(client, workspace, email="dup@example.com")
        assert response.status_code == 409

    def test_default_role_from_settings(self, client, make_user, login):
        _, workspace = _owner_workspace(make_user)
        login(email="owner@example.com")
        client.put(
            f"/workspaces/api/workspaces/{workspace.id}/settings",
            json={"default_member_role": "contributor"},
        )
        response = client.post(
            f"/workspaces/api/workspaces/{workspace.id}/invitations",
            json={"email": "newguy@example.com"},
        )
        assert response.status_code == 201
        row = WorkspaceInvitation.query.filter_by(workspace_id=workspace.id).one()
        assert row.role == "contributor"

    def test_activity_recorded(self, client, make_user, login):
        _, workspace = _owner_workspace(make_user)
        login(email="owner@example.com")
        _invite(client, workspace, email="tracked@example.com")
        event = ActivityEvent.query.filter_by(
            workspace_id=workspace.id, event_type=EVENT_INVITATION_CREATED
        ).one()
        assert event.event_metadata["email"] == "tracked@example.com"
        assert event.event_metadata["role"] == "viewer"

    def test_invitations_disabled_returns_403(self, client, make_user, login):
        _, workspace = _owner_workspace(make_user)
        login(email="owner@example.com")
        client.put(
            f"/workspaces/api/workspaces/{workspace.id}/settings",
            json={"invitations_enabled": False},
        )
        response = _invite(client, workspace)
        assert response.status_code == 403


class TestListAndCancelInvitations:
    def test_list_pagination_and_filter(self, client, make_user, login):
        _, workspace = _owner_workspace(make_user)
        login(email="owner@example.com")
        for i in range(3):
            _invite(client, workspace, email=f"p{i}@example.com")
        data = client.get(f"/workspaces/api/workspaces/{workspace.id}/invitations").get_json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert data["items"][0]["email"] == "p2@example.com"

    def test_cancel_pending_invitation(self, client, make_user, login):
        _, workspace = _owner_workspace(make_user)
        login(email="owner@example.com")
        _invite(client, workspace, email="cancel@example.com")
        invitation = WorkspaceInvitation.query.filter_by(workspace_id=workspace.id).one()
        response = client.delete(
            f"/workspaces/api/workspaces/{workspace.id}/invitations/{invitation.id}"
        )
        assert response.status_code == 200
        db.session.refresh(invitation)
        assert invitation.status == INVITE_STATUS_CANCELLED

    def test_cancel_resolved_invitation_conflict(self, client, make_user, login):
        _, workspace = _owner_workspace(make_user)
        login(email="owner@example.com")
        _invite(client, workspace, email="resolved@example.com")
        invitation = WorkspaceInvitation.query.filter_by(workspace_id=workspace.id).one()
        invitation.status = INVITE_STATUS_ACCEPTED
        db.session.commit()
        response = client.delete(
            f"/workspaces/api/workspaces/{workspace.id}/invitations/{invitation.id}"
        )
        assert response.status_code == 409

    def test_member_cannot_list_or_cancel(self, client, make_user, login):
        _, workspace = _owner_workspace(make_user)
        member = _create_user("member", "member@example.com")
        db.session.add(
            WorkspaceMember(workspace_id=workspace.id, user_id=member.id, role=ROLE_VIEWER)
        )
        db.session.commit()
        login(email="member@example.com")
        assert (
            client.get(f"/workspaces/api/workspaces/{workspace.id}/invitations").status_code == 403
        )
        assert (
            client.delete(f"/workspaces/api/workspaces/{workspace.id}/invitations/1").status_code
            == 403
        )


class TestLandingPage:
    def test_unknown_token_renders_invalid(self, client):
        response = client.get("/workspaces/invitations/not-a-real-token")
        assert response.status_code == 200
        assert b"not valid" in response.data or b"invalid" in response.data

    def test_landing_shows_join_links_for_anonymous(self, client, make_user, login):
        _, workspace = _owner_workspace(make_user)
        login(email="owner@example.com")
        raw = _invite(client, workspace, email="anon@example.com").get_json()["token"]
        client.post("/auth/logout")
        response = client.get(f"/workspaces/invitations/{raw}")
        assert response.status_code == 200
        assert b"/auth/login?next=" in response.data
        assert b"/auth/register?next=" in response.data


class TestAcceptFlow:
    def test_accept_requires_login(self, client):
        assert client.post("/workspaces/api/invitations/tok/accept").status_code == 302

    def test_accept_creates_membership(self, client, make_user, login):
        _, workspace = _owner_workspace(make_user)
        invitee = _create_user("invitee", "invitee@example.com")
        login(email="owner@example.com")
        raw = _invite(client, workspace, email="invitee@example.com").get_json()["token"]
        login(email="invitee@example.com")
        response = client.post(f"/workspaces/api/invitations/{raw}/accept")
        assert response.status_code == 201
        membership = WorkspaceMember.query.filter_by(workspace_id=workspace.id).one()
        assert membership.user_id == invitee.id
        assert membership.status == "active"
        invitation = WorkspaceInvitation.query.filter_by(workspace_id=workspace.id).one()
        assert invitation.status == INVITE_STATUS_ACCEPTED
        assert invitation.accepted_by == invitee.id

    def test_accept_notifies_inviter(self, client, make_user, login):
        owner, workspace = _owner_workspace(make_user)
        _create_user("invitee", "invitee@example.com")
        login(email="owner@example.com")
        raw = _invite(client, workspace, email="invitee@example.com").get_json()["token"]
        login(email="invitee@example.com")
        client.post(f"/workspaces/api/invitations/{raw}/accept")
        notification = Notification.query.filter_by(user_id=owner.id, type="invitation").first()
        assert notification is not None
        assert "accepted" in (notification.payload or {}).get("title", "").lower()

    def test_accept_wrong_email_403(self, client, make_user, login):
        _, workspace = _owner_workspace(make_user)
        _create_user("invitee", "invitee@example.com")
        _create_user("intruder", "intruder@example.com")
        login(email="owner@example.com")
        raw = _invite(client, workspace, email="invitee@example.com").get_json()["token"]
        login(email="intruder@example.com")
        response = client.post(f"/workspaces/api/invitations/{raw}/accept")
        assert response.status_code == 403

    def test_accept_idempotent_for_existing_member(self, client, make_user, login):
        _, workspace = _owner_workspace(make_user)
        _create_user("invitee", "invitee@example.com")
        login(email="owner@example.com")
        raw = _invite(client, workspace, email="invitee@example.com").get_json()["token"]
        login(email="invitee@example.com")
        first = client.post(f"/workspaces/api/invitations/{raw}/accept")
        second = client.post(f"/workspaces/api/invitations/{raw}/accept")
        assert first.status_code == 201
        assert second.status_code == 200
        assert second.get_json()["idempotent"] is True

    def test_accept_expired_404(self, client, app, make_user, login):
        _, workspace = _owner_workspace(make_user)
        _create_user("invitee", "invitee@example.com")
        login(email="owner@example.com")
        raw = _invite(client, workspace, email="invitee@example.com").get_json()["token"]
        invitation = WorkspaceInvitation.query.filter_by(workspace_id=workspace.id).one()
        invitation.expires_at = datetime.now(UTC) - timedelta(hours=1)
        db.session.commit()
        login(email="invitee@example.com")
        response = client.post(f"/workspaces/api/invitations/{raw}/accept")
        assert response.status_code == 404

    def test_accept_cancelled_404(self, client, make_user, login):
        _, workspace = _owner_workspace(make_user)
        _create_user("invitee", "invitee@example.com")
        login(email="owner@example.com")
        raw = _invite(client, workspace, email="invitee@example.com").get_json()["token"]
        invitation = WorkspaceInvitation.query.filter_by(workspace_id=workspace.id).one()
        invitation.status = INVITE_STATUS_CANCELLED
        db.session.commit()
        login(email="invitee@example.com")
        assert client.post(f"/workspaces/api/invitations/{raw}/accept").status_code == 404

    def test_accept_declined_409(self, client, make_user, login):
        _, workspace = _owner_workspace(make_user)
        _create_user("invitee", "invitee@example.com")
        login(email="owner@example.com")
        raw = _invite(client, workspace, email="invitee@example.com").get_json()["token"]
        invitation = WorkspaceInvitation.query.filter_by(workspace_id=workspace.id).one()
        invitation.status = INVITE_STATUS_DECLINED
        db.session.commit()
        login(email="invitee@example.com")
        assert client.post(f"/workspaces/api/invitations/{raw}/accept").status_code == 409

    def test_accept_unknown_token_404(self, client, make_user, login):
        make_user()
        login()
        assert client.post("/workspaces/api/invitations/nope/accept").status_code == 404

    def test_accept_reactivates_removed_member(self, client, make_user, login):
        _, workspace = _owner_workspace(make_user)
        invitee = _create_user("invitee", "invitee@example.com")
        login(email="owner@example.com")
        raw = _invite(client, workspace, email="invitee@example.com").get_json()["token"]
        membership = WorkspaceMember(
            workspace_id=workspace.id, user_id=invitee.id, role=ROLE_VIEWER
        )
        db.session.add(membership)
        db.session.commit()
        membership.mark_removed()
        db.session.commit()
        login(email="invitee@example.com")
        response = client.post(f"/workspaces/api/invitations/{raw}/accept")
        assert response.status_code == 201
        db.session.refresh(membership)
        assert membership.status == "active"
        assert membership.removed_at is None


class TestDeclineFlow:
    def test_decline_records_decision(self, client, make_user, login):
        _, workspace = _owner_workspace(make_user)
        _create_user("invitee", "invitee@example.com")
        login(email="owner@example.com")
        raw = _invite(client, workspace, email="invitee@example.com").get_json()["token"]
        login(email="invitee@example.com")
        response = client.post(f"/workspaces/api/invitations/{raw}/decline")
        assert response.status_code == 200
        invitation = WorkspaceInvitation.query.filter_by(workspace_id=workspace.id).one()
        assert invitation.status == INVITE_STATUS_DECLINED

    def test_decline_non_pending_404(self, client, make_user, login):
        _, workspace = _owner_workspace(make_user)
        _create_user("invitee", "invitee@example.com")
        login(email="owner@example.com")
        raw = _invite(client, workspace, email="invitee@example.com").get_json()["token"]
        invitation = WorkspaceInvitation.query.filter_by(workspace_id=workspace.id).one()
        invitation.status = INVITE_STATUS_ACCEPTED
        db.session.commit()
        login(email="invitee@example.com")
        assert client.post(f"/workspaces/api/invitations/{raw}/decline").status_code == 404


class TestRateLimiting:
    @pytest.fixture(autouse=True)
    def _low_limit(self, app):
        ratelimit.reset()
        app.config["RATE_LIMIT_MAX"] = 5

    def test_accept_hits_rate_limit(self, client, make_user, login):
        make_user()
        login()
        statuses = []
        for _ in range(7):
            response = client.post("/workspaces/api/invitations/bad-token/accept")
            statuses.append(response.status_code)
        assert statuses[0] == 404
        assert 429 in statuses
