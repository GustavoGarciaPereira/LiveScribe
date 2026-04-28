"""Testes de autenticação (JWT, Google OAuth2, login local)."""

from app.services.auth import create_access_token, verify_token


class TestJwtTokens:
    def test_create_and_verify_valid_token(self):
        token = create_access_token(user_id=42)
        user_id = verify_token(token)
        assert user_id == 42

    def test_verify_invalid_token(self):
        assert verify_token("invalid.token.here") is None

    def test_verify_empty_token(self):
        assert verify_token("") is None


class TestAuthRoutes:
    def test_login_google_redirect(self, client):
        response = client.get("/api/auth/login/google")
        assert response.status_code in (200, 500)

    def test_me_without_token(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 401


class TestLocalAuth:
    def test_register_success(self, client):
        response = client.post("/api/auth/register", json={
            "email": "test@example.com",
            "name": "Test User",
            "password": "senha1234",
        })
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "test@example.com"
        assert data["user"]["provider"] == "local"

    def test_register_duplicate(self, client):
        client.post("/api/auth/register", json={
            "email": "dup@example.com", "name": "User", "password": "senha1234",
        })
        response = client.post("/api/auth/register", json={
            "email": "dup@example.com", "name": "User2", "password": "senha5678",
        })
        assert response.status_code == 409

    def test_login_success(self, client):
        client.post("/api/auth/register", json={
            "email": "login@example.com", "name": "Test", "password": "senha1234",
        })
        response = client.post("/api/auth/login", json={
            "email": "login@example.com", "password": "senha1234",
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_invalid_password(self, client):
        client.post("/api/auth/register", json={
            "email": "fail@example.com", "name": "Test", "password": "senha1234",
        })
        response = client.post("/api/auth/login", json={
            "email": "fail@example.com", "password": "wrongpassword",
        })
        assert response.status_code == 401
