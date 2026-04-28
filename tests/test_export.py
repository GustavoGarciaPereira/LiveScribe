"""Testes de exportação (JSON, CSV, XLSX)."""

import json


class TestExportJson:
    def test_export_json(self, client, auth_client):
        auth_client.post("/api/chat/messages", json={
            "live_id": "live1", "author": "A", "message": "Teste",
        })
        resp = auth_client.get("/api/chat/live1/export?format=json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["live_id"] == "live1"
        assert len(data["messages"]) == 1

    def test_export_json_with_analysis(self, client, auth_client):
        auth_client.post("/api/chat/messages", json={
            "live_id": "live1", "author": "A", "message": "Que incrível!",
        })
        resp = auth_client.get("/api/chat/live1/export?format=json&include_analysis=true")
        assert resp.status_code == 200
        data = resp.json()
        assert "sentiment" in data
        assert "topics" in data


class TestExportCsv:
    def test_export_csv(self, client, auth_client):
        auth_client.post("/api/chat/messages", json={
            "live_id": "live1", "author": "A", "message": "Teste",
        })
        resp = auth_client.get("/api/chat/live1/export?format=csv")
        assert resp.status_code == 200
        assert "author" in resp.text
        assert "Teste" in resp.text


class TestExportEdgeCases:
    def test_empty_live(self, client, auth_client):
        resp = auth_client.get("/api/chat/vazia/export?format=json")
        assert resp.status_code == 404

    def test_xlsx_not_available(self, client, auth_client):
        """Se openpyxl não instalado, deve retornar 501."""
        auth_client.post("/api/chat/messages", json={
            "live_id": "live1", "author": "A", "message": "Teste",
        })
        resp = auth_client.get("/api/chat/live1/export?format=xlsx")
        # 200 se openpyxl instalado, 501 se não
        assert resp.status_code in (200, 501)
