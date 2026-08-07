"""Tests for the prompts blueprint: CRUD, favorites, categories, search."""

from app.models import Prompt


def _register(client, username="tester", email="tester@example.com"):
    client.post(
        "/auth/register",
        data={
            "username": username,
            "email": email,
            "password": "supersecret123",
            "password_confirm": "supersecret123",
        },
    )


def _create_prompt(client, title="Explain code", content="Explain this code:", category="Explain"):
    return client.post(
        "/prompts/api/prompts",
        json={"title": title, "content": content, "category": category},
        headers={"X-CSRFToken": "ignored"},
    )


class TestPromptsPage:
    def test_prompts_page_requires_login(self, client):
        response = client.get("/prompts/")
        assert response.status_code == 302

    def test_prompts_page_renders(self, client):
        _register(client)
        response = client.get("/prompts/")
        assert response.status_code == 200
        assert b"Prompt Library" in response.data


class TestPromptCrud:
    def test_create_prompt(self, client, db):
        _register(client)
        response = _create_prompt(client)
        assert response.status_code == 201
        assert response.get_json()["category"] == "Explain"
        assert Prompt.query.count() == 1

    def test_create_requires_title_and_content(self, client, db):
        _register(client)
        response = client.post(
            "/prompts/api/prompts",
            json={"title": "", "content": ""},
            headers={"X-CSRFToken": "ignored"},
        )
        assert response.status_code == 400

    def test_update_prompt(self, client, db):
        _register(client)
        created = _create_prompt(client).get_json()
        response = client.patch(
            f"/prompts/api/prompts/{created['id']}",
            json={"title": "Renamed prompt"},
            headers={"X-CSRFToken": "ignored"},
        )
        assert response.get_json()["title"] == "Renamed prompt"

    def test_delete_prompt(self, client, db):
        _register(client)
        created = _create_prompt(client).get_json()
        response = client.delete(
            f"/prompts/api/prompts/{created['id']}",
            headers={"X-CSRFToken": "ignored"},
        )
        assert response.status_code == 200
        assert Prompt.query.count() == 0

    def test_other_users_prompt_is_404(self, client, db):
        _register(client, username="owner", email="owner@example.com")
        created = _create_prompt(client).get_json()
        client.post("/auth/logout")
        _register(client, username="intruder", email="intruder@example.com")
        response = client.get(f"/prompts/api/prompts/{created['id']}")
        assert response.status_code == 404


class TestPromptFilters:
    def test_favorite_filter(self, client, db):
        _register(client)
        created = _create_prompt(client).get_json()
        client.post(
            f"/prompts/api/prompts/{created['id']}/favorite",
            headers={"X-CSRFToken": "ignored"},
        )
        response = client.get("/prompts/api/prompts?favorites=1")
        assert [p["id"] for p in response.get_json()] == [created["id"]]

    def test_toggle_favorite_flips_flag(self, client, db):
        _register(client)
        created = _create_prompt(client).get_json()
        response = client.post(
            f"/prompts/api/prompts/{created['id']}/favorite",
            headers={"X-CSRFToken": "ignored"},
        )
        assert response.get_json()["is_favorite"] is True
        response = client.post(
            f"/prompts/api/prompts/{created['id']}/favorite",
            headers={"X-CSRFToken": "ignored"},
        )
        assert response.get_json()["is_favorite"] is False

    def test_category_filter(self, client, db):
        _register(client)
        _create_prompt(client, title="Explainer", category="Explain")
        _create_prompt(client, title="Generator", category="Generate")
        response = client.get("/prompts/api/prompts?category=Generate")
        assert [p["title"] for p in response.get_json()] == ["Generator"]

    def test_search_matches_title_content_category(self, client, db):
        _register(client)
        _create_prompt(client, title="Refactor helper", content="Refactor this snippet")
        _create_prompt(client, title="Unrelated", content="Nothing to see")
        response = client.get("/prompts/api/prompts?q=refactor")
        assert len(response.get_json()) == 1
        assert response.get_json()[0]["title"] == "Refactor helper"

    def test_categories_endpoint(self, client, db):
        _register(client)
        _create_prompt(client, category="Explain")
        _create_prompt(client, category="Generate")
        _create_prompt(client, category="Explain")
        response = client.get("/prompts/api/categories")
        categories = response.get_json()
        assert set(categories) == {"Explain", "Generate"}
