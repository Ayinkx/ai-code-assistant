"""Tests for the AI tools blueprint: code generation, code actions, file analysis."""

from io import BytesIO

import pytest


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


class TestGenerate:
    def test_generate_requires_login(self, client):
        response = client.post("/tools/generate", json={})
        assert response.status_code == 302

    def test_generate_requires_description(self, client):
        _register(client)
        response = client.post("/tools/generate", json={}, headers={"X-CSRFToken": "ignored"})
        assert response.status_code == 400

    def test_generate_returns_mock_result(self, client):
        _register(client)
        response = client.post(
            "/tools/generate",
            json={"description": "Build a REST API in Flask", "language": "python"},
            headers={"X-CSRFToken": "ignored"},
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["language"] == "python"
        assert "mock assistant response" in payload["result"].lower()


class TestCodeActions:
    @pytest.mark.parametrize(
        "action",
        ["explain", "refactor", "bugs", "optimize", "comments", "docs", "commit"],
    )
    def test_all_actions_work(self, client, action):
        _register(client)
        response = client.post(
            "/tools/code",
            json={"action": action, "code": "def foo():\n    return 1"},
            headers={"X-CSRFToken": "ignored"},
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["action"] == action
        assert "mock assistant response" in payload["result"].lower()

    def test_unsupported_action(self, client):
        _register(client)
        response = client.post(
            "/tools/code",
            json={"action": "nonsense", "code": "x = 1"},
            headers={"X-CSRFToken": "ignored"},
        )
        assert response.status_code == 400

    def test_code_required(self, client):
        _register(client)
        response = client.post(
            "/tools/code",
            json={"action": "explain", "code": ""},
            headers={"X-CSRFToken": "ignored"},
        )
        assert response.status_code == 400


class TestAnalyzeFile:
    def test_analyze_python_file(self, client):
        _register(client)
        data = {
            "file": (BytesIO(b"def add(a, b):\n    return a + b"), "calc.py"),
        }
        response = client.post("/tools/analyze", data=data, content_type="multipart/form-data")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["filename"] == "calc.py"
        assert payload["action"] == "explain"
        assert "mock assistant response" in payload["result"].lower()

    def test_analyze_rejects_unsupported_type(self, client):
        _register(client)
        data = {"file": (BytesIO(b"binary\x00data"), "notes.exe")}
        response = client.post("/tools/analyze", data=data, content_type="multipart/form-data")
        assert response.status_code == 400

    def test_analyze_rejects_non_utf8(self, client):
        _register(client)
        data = {"file": (BytesIO(b"\xff\xfe\x00garbage"), "bad.txt")}
        response = client.post("/tools/analyze", data=data, content_type="multipart/form-data")
        assert response.status_code == 400

    def test_analyze_accepts_custom_action(self, client):
        _register(client)
        data = {
            "file": (BytesIO(b"print('hi')"), "main.py"),
            "action": "bugs",
        }
        response = client.post("/tools/analyze", data=data, content_type="multipart/form-data")
        assert response.status_code == 200
        assert response.get_json()["action"] == "bugs"


class TestSendToChat:
    def test_send_to_chat_creates_conversation(self, client, db):
        _register(client)
        response = client.post(
            "/tools/send-to-chat",
            json={"content": "Generated code here"},
            headers={"X-CSRFToken": "ignored"},
        )
        assert response.status_code == 201
        assert "conversation_id" in response.get_json()

    def test_send_to_chat_requires_content(self, client):
        _register(client)
        response = client.post(
            "/tools/send-to-chat",
            json={"content": ""},
            headers={"X-CSRFToken": "ignored"},
        )
        assert response.status_code == 400
