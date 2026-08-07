"""Tests for authentication routes and the user model."""

from app.models import User


def _register(client, username="tester", email="tester@example.com", password="supersecret123"):
    return client.post(
        "/auth/register",
        data={
            "username": username,
            "email": email,
            "password": password,
            "password_confirm": password,
        },
        follow_redirects=True,
    )


def _login(client, email="tester@example.com", password="supersecret123"):
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def _logout(client):
    return client.post("/auth/logout", follow_redirects=True)


class TestRegistration:
    def test_register_success(self, client):
        response = _register(client)
        assert response.status_code == 200
        assert b"account was created successfully" in response.data

        user = User.query.filter_by(email="tester@example.com").first()
        assert user is not None
        assert user.check_password("supersecret123")

    def test_register_requires_all_fields(self, client):
        response = client.post("/auth/register", data={"username": "", "email": "", "password": ""})
        assert b"All fields are required" in response.data

    def test_register_rejects_short_password(self, client):
        response = _register(client, password="short")
        assert b"at least 8 characters" in response.data

    def test_register_rejects_mismatched_passwords(self, client):
        response = client.post(
            "/auth/register",
            data={
                "username": "tester",
                "email": "tester@example.com",
                "password": "supersecret123",
                "password_confirm": "different123",
            },
        )
        assert b"Passwords do not match" in response.data

    def test_register_rejects_duplicate_username(self, client):
        _register(client)
        _logout(client)
        response = _register(client, email="other@example.com")
        assert b"already taken" in response.data

    def test_register_rejects_duplicate_email(self, client):
        _register(client)
        _logout(client)
        response = _register(client, username="another")
        assert b"already exists" in response.data

    def test_password_is_never_stored_in_plain_text(self, client):
        _register(client)
        user = User.query.filter_by(email="tester@example.com").first()
        assert user is not None
        assert "supersecret123" not in user.password_hash


class TestLogin:
    def test_login_success_updates_last_login(self, client, db):
        _register(client)
        _logout(client)
        user = User.query.filter_by(email="tester@example.com").first()
        assert user.last_login_at is None

        response = _login(client)
        assert response.status_code == 200
        assert b"Welcome back" in response.data

        db.session.refresh(user)
        assert user.last_login_at is not None

    def test_login_rejects_wrong_password(self, client):
        _register(client)
        _logout(client)
        response = _login(client, password="wrongpassword")
        assert b"Invalid email or password" in response.data

    def test_login_rejects_unknown_email(self, client):
        response = _login(client, email="nobody@example.com")
        assert b"Invalid email or password" in response.data

    def test_login_redirects_authenticated_user(self, client):
        _register(client)
        response = client.get("/auth/login")
        assert response.status_code == 302


class TestLogout:
    def test_logout_requires_auth(self, client):
        response = client.post("/auth/logout")
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]

    def test_logout_ends_session(self, client):
        _register(client)
        response = client.post("/auth/logout", follow_redirects=True)
        assert b"You have been logged out" in response.data

        # Authenticated account page should now redirect to login.
        response = client.get("/auth/me", follow_redirects=True)
        assert b"Please log in" in response.data


class TestAuthScaffolding:
    def test_account_page_requires_login(self, client):
        response = client.get("/auth/me")
        assert response.status_code == 302

    def test_account_page_shows_user_details(self, client):
        _register(client)
        response = client.get("/auth/me")
        assert b"tester" in response.data
        assert b"tester@example.com" in response.data
