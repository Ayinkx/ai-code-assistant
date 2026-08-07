"""Tests for workspace API routes: CRUD, ownership isolation, and auth."""

from app.extensions import db
from app.models import Workspace


def _create_workspace(user_id, name="Alice workspace"):
    workspace = Workspace(user_id=user_id, name=name, description="desc")
    db.session.add(workspace)
    db.session.commit()
    return workspace


class TestWorkspaceAuth:
    def test_list_requires_login(self, client):
        response = client.get("/workspaces/")
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]

    def test_api_list_requires_login(self, client):
        response = client.get("/workspaces/api/workspaces")
        assert response.status_code == 302


class TestWorkspaceCRUD:
    def test_create_workspace(self, client, make_user, login):
        make_user()
        login()
        response = client.post(
            "/workspaces/api/workspaces",
            json={"name": "My Workspace", "description": "A description"},
        )
        assert response.status_code == 201
        payload = response.get_json()
        assert payload["name"] == "My Workspace"
        assert payload["description"] == "A description"
        assert payload["project_count"] == 0

    def test_create_requires_name(self, client, make_user, login):
        make_user()
        login()
        response = client.post("/workspaces/api/workspaces", json={"name": "  "})
        assert response.status_code == 400
        assert "name" in response.get_json()["error"].lower()

    def test_list_own_workspaces(self, client, make_user, login):
        user = make_user()
        login()
        _create_workspace(user.id, "First")
        _create_workspace(user.id, "Second")
        response = client.get("/workspaces/api/workspaces")
        assert response.status_code == 200
        names = [w["name"] for w in response.get_json()]
        assert names == ["Second", "First"]

    def test_rename_workspace(self, client, make_user, login):
        user = make_user()
        login()
        workspace = _create_workspace(user.id)
        response = client.patch(
            f"/workspaces/api/workspaces/{workspace.id}",
            json={"name": "Renamed"},
        )
        assert response.status_code == 200
        assert response.get_json()["name"] == "Renamed"

    def test_delete_workspace(self, client, make_user, login):
        user = make_user()
        login()
        workspace = _create_workspace(user.id)
        response = client.delete(f"/workspaces/api/workspaces/{workspace.id}")
        assert response.status_code == 200
        assert Workspace.query.count() == 0

    def test_pages_render(self, client, make_user, login):
        user = make_user()
        login()
        workspace = _create_workspace(user.id)
        assert client.get("/workspaces/").status_code == 200
        assert client.get(f"/workspaces/{workspace.id}").status_code == 200


class TestOwnershipIsolation:
    def test_other_users_workspace_is_404(self, client, make_user, login):
        alice = make_user(username="alice", email="alice@example.com")
        make_user(username="bob", email="bob@example.com")
        login(email="bob@example.com")

        workspace = _create_workspace(alice.id)

        assert client.get(f"/workspaces/{workspace.id}").status_code == 404
        assert (
            client.patch(
                f"/workspaces/api/workspaces/{workspace.id}", json={"name": "nope"}
            ).status_code
            == 404
        )
        assert client.delete(f"/workspaces/api/workspaces/{workspace.id}").status_code == 404
        assert client.get(f"/workspaces/api/workspaces/{workspace.id}/projects").status_code == 404

    def test_list_only_shows_own(self, client, make_user, login):
        alice = make_user(username="alice", email="alice@example.com")
        _create_workspace(alice.id, "Alice only")
        make_user(username="bob", email="bob@example.com")
        login(email="bob@example.com")
        response = client.get("/workspaces/api/workspaces")
        assert response.get_json() == []
