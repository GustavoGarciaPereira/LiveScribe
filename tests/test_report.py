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


def test_report_template_has_statistics_columns():
    """O template do relatorio contem colunas Media e IC 95%."""
    from app.templates.report_html import report_html
    source = report_html.render({
        "live_id": "test", "total_messages": 1, "unique_authors": 1,
        "first_msg": "", "last_msg": "", "duration": "",
        "sentiment_summary": {}, "word_freq": [], "topics": [],
        "topic_sentiment": [{
            "topic": "teste", "message_count": 1,
            "sentiment": {"Positivo": 1, "Negativo": 0, "Neutro": 0},
            "statistics": {"mean": 0.5, "std_dev": 0.1, "ci_95": [0.3, 0.7]},
            "dominant_emotion": "alegria", "peak_minute": "00:01",
        }],
        "authors": [], "questions": [], "emojis": [],
        "charts": {}, "generated_at": "",
    })
    assert "Media" in source
    assert "IC 95%" in source
    assert "0.50" in source  # mean formatado
    assert "0.30" in source  # ci_95 lower
    assert "0.70" in source  # ci_95 upper


def test_report_template_has_significance_section():
    """O template do relatorio contem seção Momentos de Virada Significativa."""
    from app.templates.report_html import report_html
    source = report_html.render({
        "live_id": "test", "total_messages": 10, "unique_authors": 3,
        "first_msg": "", "last_msg": "", "duration": "00:30:00",
        "sentiment_summary": {}, "word_freq": [], "topics": [],
        "topic_sentiment": [], "authors": [], "questions": [], "emojis": [],
        "sentiment_timeline": [
            {"start_time": "2024-01-01T18:00", "significant_change": False, "p_value": None, "change_direction": "none", "change_magnitude": None},
            {"start_time": "2024-01-01T18:05", "significant_change": True, "p_value": 0.003, "change_direction": "drop", "change_magnitude": -0.5},
            {"start_time": "2024-01-01T18:10", "significant_change": True, "p_value": 0.012, "change_direction": "rise", "change_magnitude": 0.35},
        ],
        "total_intervals": 3,
        "charts": {}, "generated_at": "",
    })
    assert "Momentos de Virada Significativa" in source
    assert "mudancas estatisticamente significativas" in source
    assert "Dos 3 intervalos analisados" in source
    assert "0.003" in source
    assert "0.012" in source


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
