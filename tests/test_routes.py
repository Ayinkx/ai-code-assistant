"""Tests for public routes and the application factory."""

from app import create_app


class TestAppFactory:
    def test_create_app_with_testing_config(self):
        app = create_app("testing")
        assert app.config["TESTING"] is True

    def test_create_app_unknown_config_raises(self):
        try:
            create_app("does-not-exist")
        except KeyError:
            pass
        else:
            raise AssertionError("Expected KeyError for unknown config")


class TestPublicRoutes:
    def test_index_renders(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert b"AI Code Assistant" in response.data

    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["status"] == "ok"

    def test_404_page(self, client):
        response = client.get("/this-page-does-not-exist")
        assert response.status_code == 404
        assert b"404" in response.data

    def test_security_headers_present(self, client):
        response = client.get("/")
        assert "text/html" in response.headers["Content-Type"]
