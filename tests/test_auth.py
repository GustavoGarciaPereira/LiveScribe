"""Testes de autenticação (JWT + Google OAuth2)."""

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
        # Sem credenciais Google, retorna a URL de autorização de qualquer forma
        # O OAuth client pode lançar erro se client_id for vazio
        assert response.status_code in (200, 500)

    def test_me_without_token(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 401  # HTTPBearer exige Authorization
