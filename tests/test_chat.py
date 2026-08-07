"""Tests for the chat blueprint: conversations, messages, streaming, export."""

from app.models import Conversation


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


def _logout(client):
    client.post("/auth/logout")


def _create_conversation(client, title=None):
    payload = {"title": title} if title is not None else {}
    response = client.post(
        "/chat/conversations",
        json=payload,
        headers={"X-CSRFToken": "ignored"},
    )
    assert response.status_code == 201
    return response.get_json()


class TestChatPage:
    def test_chat_page_requires_login(self, client):
        response = client.get("/chat/")
        assert response.status_code == 302

    def test_chat_page_renders(self, client):
        _register(client)
        response = client.get("/chat/")
        assert response.status_code == 200
        assert b"Conversations" in response.data
        assert b"chat-input" in response.data


class TestConversationApi:
    def test_create_conversation(self, client, db):
        _register(client)
        data = _create_conversation(client, title="First chat")
        assert data["title"] == "First chat"
        assert data["message_count"] == 0

    def test_list_conversations_scoped_to_user(self, client, db):
        _register(client)
        _create_conversation(client, title="Mine")
        _logout(client)
        _register(client, username="other", email="other@example.com")
        response = client.get("/chat/conversations")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_search_conversations(self, client, db):
        _register(client)
        _create_conversation(client, title="Refactor session")
        _create_conversation(client, title="Bug hunt")
        response = client.get("/chat/conversations?q=refactor")
        titles = [c["title"] for c in response.get_json()]
        assert titles == ["Refactor session"]

    def test_rename_conversation(self, client, db):
        _register(client)
        conversation = _create_conversation(client)
        response = client.patch(
            f"/chat/conversations/{conversation['id']}",
            json={"title": "Renamed"},
            headers={"X-CSRFToken": "ignored"},
        )
        assert response.get_json()["title"] == "Renamed"

    def test_pin_conversation(self, client, db):
        _register(client)
        conversation = _create_conversation(client)
        response = client.patch(
            f"/chat/conversations/{conversation['id']}",
            json={"is_pinned": True},
            headers={"X-CSRFToken": "ignored"},
        )
        assert response.get_json()["is_pinned"] is True

    def test_delete_conversation(self, client, db):
        _register(client)
        conversation = _create_conversation(client)
        response = client.delete(
            f"/chat/conversations/{conversation['id']}",
            headers={"X-CSRFToken": "ignored"},
        )
        assert response.status_code == 200
        assert Conversation.query.count() == 0

    def test_other_users_conversation_is_404(self, client, db):
        _register(client, username="owner", email="owner@example.com")
        conversation = _create_conversation(client)
        _logout(client)
        _register(client, username="intruder", email="intruder@example.com")
        response = client.get(f"/chat/conversations/{conversation['id']}")
        assert response.status_code == 404


class TestMessageApi:
    def test_send_message_returns_mock_reply(self, client, db):
        _register(client)
        conversation = _create_conversation(client)
        response = client.post(
            f"/chat/conversations/{conversation['id']}/messages",
            json={"content": "Explain the strategy pattern"},
            headers={"X-CSRFToken": "ignored"},
        )
        assert response.status_code == 201
        reply = response.get_json()["assistant_message"]
        assert reply["role"] == "assistant"
        assert "mock assistant response" in reply["content"].lower()

    def test_send_message_rejects_empty(self, client, db):
        _register(client)
        conversation = _create_conversation(client)
        response = client.post(
            f"/chat/conversations/{conversation['id']}/messages",
            json={"content": "   "},
            headers={"X-CSRFToken": "ignored"},
        )
        assert response.status_code == 400

    def test_first_message_sets_title(self, client, db):
        _register(client)
        conversation = _create_conversation(client)
        client.post(
            f"/chat/conversations/{conversation['id']}/messages",
            json={"content": "Help me build a CLI"},
            headers={"X-CSRFToken": "ignored"},
        )
        stored = db.session.get(Conversation, conversation["id"])
        assert stored.title == "Help me build a CLI"

    def test_history_is_returned(self, client, db):
        _register(client)
        conversation = _create_conversation(client)
        client.post(
            f"/chat/conversations/{conversation['id']}/messages",
            json={"content": "hi"},
            headers={"X-CSRFToken": "ignored"},
        )
        response = client.get(f"/chat/conversations/{conversation['id']}")
        messages = response.get_json()["messages"]
        assert [m["role"] for m in messages] == ["user", "assistant"]


class TestStreaming:
    def test_stream_returns_sse_tokens_and_done(self, client, db):
        _register(client)
        conversation = _create_conversation(client)
        response = client.post(
            f"/chat/conversations/{conversation['id']}/stream",
            json={"content": "Write a Fibonacci function"},
            headers={"X-CSRFToken": "ignored"},
        )
        assert response.status_code == 200
        assert response.mimetype == "text/event-stream"
        data = response.get_data(as_text=True)
        assert "data: " in data
        assert '"type": "token"' in data
        assert '"type": "done"' in data

    def test_stream_persists_messages(self, client, db):
        _register(client)
        conversation = _create_conversation(client)
        response = client.post(
            f"/chat/conversations/{conversation['id']}/stream",
            json={"content": "hello there"},
            headers={"X-CSRFToken": "ignored"},
        )
        # Consume the stream so the response generator runs and commits.
        response.get_data()
        stored = db.session.get(Conversation, conversation["id"])
        assert len(stored.messages) == 2

    def test_stream_rejects_empty(self, client, db):
        _register(client)
        conversation = _create_conversation(client)
        response = client.post(
            f"/chat/conversations/{conversation['id']}/stream",
            json={"content": ""},
            headers={"X-CSRFToken": "ignored"},
        )
        assert response.status_code == 400


class TestExport:
    def test_export_returns_json_document(self, client, db):
        _register(client)
        conversation = _create_conversation(client, title="Export me")
        client.post(
            f"/chat/conversations/{conversation['id']}/messages",
            json={"content": "hi"},
            headers={"X-CSRFToken": "ignored"},
        )
        response = client.get(f"/chat/conversations/{conversation['id']}/export")
        assert response.status_code == 200
        assert response.mimetype == "application/json"
        assert "attachment" in response.headers["Content-Disposition"]
        payload = response.get_json()
        assert payload["conversation"]["title"] == "Export me"
        assert len(payload["messages"]) == 2
