"""Testes para o endpoint e servico de relatorio PDF."""

import pytest
from app.services.chat import ChatService
from app.services.report import ReportService


class TestReportEndpoint:
    def test_report_generates_pdf(self, auth_client):
        auth_client.post("/api/chat/messages", json={
            "live_id": "live-report-1",
            "author": "User",
            "message": "Que live incrivel!",
            "platform": "youtube",
        })
        resp = auth_client.get("/api/chat/live-report-1/report?format=pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content.startswith(b"%PDF-")

    def test_report_nonexistent_live_returns_404(self, auth_client):
        resp = auth_client.get("/api/chat/nonexistent-live-999/report?format=pdf")
        assert resp.status_code == 404

    def test_report_empty_live_returns_pdf_with_empty_summary(self, db_session, mock_analyzer):
        svc = ChatService(db_session, mock_analyzer)
        report_svc = ReportService(svc)
        pdf_bytes = report_svc.generate_pdf("empty-live", user_id=None)
        assert pdf_bytes is not None
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF-")
