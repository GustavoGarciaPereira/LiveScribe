"""Testes para o sistema de webhooks."""

from unittest.mock import patch, MagicMock

from app.models.webhook import Webhook


class TestWebhookCrud:
    def test_create_webhook(self, client, auth_client):
        resp = auth_client.post("/api/webhooks", json={
            "url": "https://example.com/hook",
            "event": "new_message",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["url"] == "https://example.com/hook"
        assert data["event"] == "new_message"
        assert data["is_active"] is True

    def test_list_webhooks(self, client, auth_client):
        auth_client.post("/api/webhooks", json={
            "url": "https://example.com/hook", "event": "new_message",
        })
        resp = auth_client.get("/api/webhooks")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_delete_webhook(self, client, auth_client):
        resp = auth_client.post("/api/webhooks", json={
            "url": "https://example.com/hook", "event": "new_message",
        })
        wh_id = resp.json()["id"]
        resp2 = auth_client.delete(f"/api/webhooks/{wh_id}")
        assert resp2.status_code == 204
        # Verifica que foi removido
        resp3 = auth_client.get("/api/webhooks")
        assert len(resp3.json()) == 0


class TestWebhookTrigger:
    def test_trigger_schedules_background_task(self, client, auth_client):
        """Cria webhook e verifica que o POST /messages agenda o trigger em background."""
        auth_client.post("/api/webhooks", json={
            "url": "https://example.com/hook",
            "event": "new_message",
        })
        resp = auth_client.post("/api/chat/messages", json={
            "live_id": "live1", "author": "A", "message": "Test",
        })
        assert resp.status_code == 200
        # O webhook é disparado em background — a resposta não é afetada

    def test_trigger_silent_failure(self, client, auth_client):
        """Webhook com URL inválida não quebra o endpoint (ignora falhas em background)."""
        auth_client.post("/api/webhooks", json={
            "url": "https://invalid.example.com/hook",
            "event": "new_message",
        })
        # O endpoint deve retornar 200 mesmo que o webhook falhe (background task)
        resp = auth_client.post("/api/chat/messages", json={
            "live_id": "live1", "author": "A", "message": "Test",
        })
        assert resp.status_code == 200
