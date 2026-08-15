"""Tests for the centralized role/permission model (#142).

Covers the capability matrix, fail-closed role resolution, the no-existence-
oracle 404 behavior of ``resolve_workspace``, and the AI content-access gate.
"""

import pytest

from app.extensions import db
from app.models import Project, User, Workspace, WorkspaceMember
from app.models.workspace_member import ROLE_CONTRIBUTOR, ROLE_OWNER, ROLE_VIEWER
from app.services import permissions
from app.services.permissions import (
    assert_content_access,
    can,
    capabilities_for_role,
    resolve_workspace,
    role_can,
    role_for,
)


def _create_user(username, email):
    user = User(username=username, email=email)
    user.set_password("supersecret123")
    db.session.add(user)
    db.session.commit()
    return user


class TestCapabilityMatrix:
    def test_owner_has_all_capabilities(self):
        for capability in permissions.CAPABILITIES:
            if capability == "leave_workspace":
                continue  # owners transfer ownership instead of leaving (#137)
            assert role_can(ROLE_OWNER, capability) is True

    def test_owner_cannot_leave(self):
        assert role_can(ROLE_OWNER, "leave_workspace") is False

    def test_contributor_admin_capabilities_denied(self):
        for capability in (
            "manage_members",
            "manage_invitations",
            "manage_settings",
            "transfer_ownership",
            "view_audit",
        ):
            assert role_can(ROLE_CONTRIBUTOR, capability) is False

    def test_viewer_read_only_capabilities(self):
        for capability in ("view_members", "comment", "view_activity", "heartbeat"):
            assert role_can(ROLE_VIEWER, capability) is True
        assert role_can(ROLE_VIEWER, "leave_workspace") is True

    def test_unknown_role_fails_closed(self):
        assert role_can("admin", "view_members") is False
        assert role_can(None, "view_members") is False
        assert role_can("OWNER", "manage_members") is False

    def test_unknown_capability_fails_closed(self):
        assert role_can(ROLE_OWNER, "delete_workspace") is False

    def test_capabilities_for_role(self):
        viewer_caps = set(capabilities_for_role(ROLE_VIEWER))
        owner_caps = set(capabilities_for_role(ROLE_OWNER))
        assert "manage_members" in owner_caps
        assert "manage_members" not in viewer_caps
        assert "leave_workspace" in viewer_caps
        assert "leave_workspace" not in owner_caps
        assert capabilities_for_role("admin") == []


class TestRoleResolution:
    def test_owner_role_from_workspace_user_id(self, make_user):
        owner = make_user()
        workspace = Workspace(user_id=owner.id, name="WS")
        db.session.add(workspace)
        db.session.commit()
        assert role_for(workspace.id, owner) == ROLE_OWNER

    def test_member_role_from_active_membership(self, make_user):
        owner = make_user()
        member = _create_user("member", "member@example.com")
        workspace = Workspace(user_id=owner.id, name="WS")
        db.session.add(workspace)
        db.session.commit()
        db.session.add(
            WorkspaceMember(workspace_id=workspace.id, user_id=member.id, role=ROLE_VIEWER)
        )
        db.session.commit()
        assert role_for(workspace.id, member) == ROLE_VIEWER

    def test_removed_member_fails_closed(self, make_user):
        owner = make_user()
        member = _create_user("member", "member@example.com")
        workspace = Workspace(user_id=owner.id, name="WS")
        db.session.add(workspace)
        db.session.commit()
        membership = WorkspaceMember(workspace_id=workspace.id, user_id=member.id, role=ROLE_VIEWER)
        db.session.add(membership)
        db.session.commit()
        membership.mark_removed()
        db.session.commit()
        assert role_for(workspace.id, member) is None

    def test_non_member_fails_closed(self, make_user):
        owner = make_user()
        outsider = _create_user("outsider", "outsider@example.com")
        workspace = Workspace(user_id=owner.id, name="WS")
        db.session.add(workspace)
        db.session.commit()
        assert role_for(workspace.id, outsider) is None
        assert role_for(workspace.id, None) is None

    def test_can_uses_active_membership(self, make_user):
        owner = make_user()
        member = _create_user("member", "member@example.com")
        workspace = Workspace(user_id=owner.id, name="WS")
        db.session.add(workspace)
        db.session.commit()
        db.session.add(
            WorkspaceMember(workspace_id=workspace.id, user_id=member.id, role=ROLE_CONTRIBUTOR)
        )
        db.session.commit()
        assert can("view_members", workspace.id, member) is True
        assert can("manage_members", workspace.id, member) is False


class TestResolveWorkspace:
    def test_member_resolves(self, make_user):
        owner = make_user()
        member = _create_user("member", "member@example.com")
        workspace = Workspace(user_id=owner.id, name="WS")
        db.session.add(workspace)
        db.session.commit()
        db.session.add(
            WorkspaceMember(workspace_id=workspace.id, user_id=member.id, role=ROLE_VIEWER)
        )
        db.session.commit()
        assert resolve_workspace(workspace.id, member).id == workspace.id

    def test_non_member_gets_404(self, app, make_user):
        owner = make_user()
        outsider = _create_user("outsider", "outsider@example.com")
        workspace = Workspace(user_id=owner.id, name="WS")
        db.session.add(workspace)
        db.session.commit()
        with app.test_request_context("/"), pytest.raises(Exception) as excinfo:
            resolve_workspace(workspace.id, outsider)
        assert excinfo.value.code == 404

    def test_missing_workspace_gets_404(self, app, make_user):
        user = make_user()
        with app.test_request_context("/"), pytest.raises(Exception) as excinfo:
            resolve_workspace(99999, user)
        assert excinfo.value.code == 404


class TestAssertContentAccess:
    def test_owner_allowed(self, app, make_user):
        owner = make_user()
        workspace = Workspace(user_id=owner.id, name="WS")
        db.session.add(workspace)
        db.session.commit()
        project = Project(workspace_id=workspace.id, user_id=owner.id, name="P", status="ready")
        db.session.add(project)
        db.session.commit()
        assert_content_access(project, owner)

    def test_member_denied_until_content_access(self, app, make_user):
        owner = make_user()
        member = _create_user("member", "member@example.com")
        workspace = Workspace(user_id=owner.id, name="WS")
        db.session.add(workspace)
        db.session.commit()
        project = Project(workspace_id=workspace.id, user_id=owner.id, name="P", status="ready")
        db.session.add(project)
        db.session.commit()
        db.session.add(
            WorkspaceMember(workspace_id=workspace.id, user_id=member.id, role=ROLE_VIEWER)
        )
        db.session.commit()
        with app.test_request_context("/"), pytest.raises(Exception) as excinfo:
            assert_content_access(project, member)
        assert excinfo.value.code == 403

    def test_anonymous_denied(self, app, make_user):
        owner = make_user()
        workspace = Workspace(user_id=owner.id, name="WS")
        db.session.add(workspace)
        db.session.commit()
        project = Project(workspace_id=workspace.id, user_id=owner.id, name="P", status="ready")
        db.session.add(project)
        db.session.commit()
        with app.test_request_context("/"), pytest.raises(Exception) as excinfo:
            assert_content_access(project, None)
        assert excinfo.value.code == 403
