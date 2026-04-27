"""Testes para o dashboard HTML."""


class TestDashboard:
    def test_returns_200(self, client):
        response = client.get("/dashboard")
        assert response.status_code == 200

    def test_contains_title(self, client):
        response = client.get("/dashboard")
        assert "PulsoDaLive" in response.text
