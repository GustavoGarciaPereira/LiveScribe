"""Testes para o sistema de relatorios com fila e polling."""

import time
import pytest
from app.services.chat import ChatService
from app.services.report import ReportService
from app.services.report_queue import ReportQueue


class TestReportQueue:
    def test_submit_returns_job_id(self, report_queue):
        job_id = report_queue.submit("live-test-1", user_id=1)
        assert job_id is not None
        assert len(job_id) == 12

    def test_get_status_pending(self, report_queue):
        job_id = report_queue.submit("live-test-2", user_id=1)
        status = report_queue.get_status(job_id)
        assert status is not None
        assert status["status"] == "pending"
        assert status["live_id"] == "live-test-2"

    def test_get_status_nonexistent(self, report_queue):
        assert report_queue.get_status("nonexistent") is None

    def test_get_pdf_not_ready(self, report_queue):
        job_id = report_queue.submit("live-test-3", user_id=1)
        assert report_queue.get_pdf(job_id) is None  # ainda pending


class TestReportService:
    """Testes unitarios do ReportService (geracao de PDF)."""

    def test_empty_live_generates_pdf(self, db_session, mock_analyzer):
        svc = ChatService(db_session, mock_analyzer)
        report_svc = ReportService(svc)
        pdf_bytes = report_svc.generate_pdf("empty-live", user_id=None)
        assert pdf_bytes is not None
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF-")


class TestReportRoutes:
    def test_create_report_requires_auth(self, client):
        resp = client.post("/api/reports?live_id=test-live")
        assert resp.status_code in (401, 403)

    def test_create_report_returns_job_id(self, auth_client):
        auth_client.post("/api/chat/messages", json={
            "live_id": "live-report-new-1",
            "author": "User",
            "message": "Que live incrivel!",
            "platform": "youtube",
        })
        resp = auth_client.post("/api/reports?live_id=live-report-new-1")
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "pending"

    def test_get_report_status(self, auth_client):
        auth_client.post("/api/chat/messages", json={
            "live_id": "live-report-new-2",
            "author": "User",
            "message": "Teste de status",
            "platform": "youtube",
        })
        create_resp = auth_client.post("/api/reports?live_id=live-report-new-2")
        job_id = create_resp.json()["job_id"]

        status_resp = auth_client.get(f"/api/reports/{job_id}")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["job_id"] == job_id
        assert status_data["status"] in ("pending", "processing", "done")

    def test_get_report_status_nonexistent(self, auth_client):
        resp = auth_client.get("/api/reports/nonexistent-job-id")
        assert resp.status_code == 404

    def test_download_not_ready(self, auth_client):
        auth_client.post("/api/chat/messages", json={
            "live_id": "live-dl-not-ready",
            "author": "User",
            "message": "Teste",
            "platform": "youtube",
        })
        create_resp = auth_client.post("/api/reports?live_id=live-dl-not-ready")
        job_id = create_resp.json()["job_id"]

        resp = auth_client.get(f"/api/reports/{job_id}/download")
        # 409 Conflict: ainda nao pronto ou 200 se worker ja processou
        assert resp.status_code in (200, 409)

    def test_download_nonexistent_job(self, auth_client):
        resp = auth_client.get("/api/reports/nonexistent-job-id/download")
        assert resp.status_code == 404

    def test_full_flow_waits_for_completion(self, auth_client, report_queue):
        """Fluxo completo: cria job, espera conclusao, faz download."""
        auth_client.post("/api/chat/messages", json={
            "live_id": "live-full-flow",
            "author": "User",
            "message": "Live incrivel! Muito bom!",
            "platform": "youtube",
        })
        create_resp = auth_client.post("/api/reports?live_id=live-full-flow")
        assert create_resp.status_code == 200
        job_id = create_resp.json()["job_id"]

        # Espera o worker processar (polling)
        for _ in range(30):  # timeout 15s
            status_resp = auth_client.get(f"/api/reports/{job_id}")
            status_data = status_resp.json()
            if status_data["status"] in ("done", "failed"):
                break
            time.sleep(0.5)

        assert status_data["status"] == "done", f"Job falhou: {status_data.get('error')}"

        # Download
        dl_resp = auth_client.get(f"/api/reports/{job_id}/download")
        assert dl_resp.status_code == 200
        assert dl_resp.headers["content-type"] == "application/pdf"
        assert dl_resp.content.startswith(b"%PDF-")
