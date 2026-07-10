"""Testes para o dashboard HTML."""


class TestDashboard:
    def test_returns_200(self, client):
        response = client.get("/dashboard")
        assert response.status_code == 200

    def test_contains_title(self, client):
        response = client.get("/dashboard")
        assert "PulsoDaLive" in response.text

    def test_contains_new_sections(self, client):
        response = client.get("/dashboard")
        html = response.text
        assert "emojis-chart" in html
        assert "top-authors-list" in html
        assert "export-json" in html
        assert "term-timeline-chart" in html
        assert "questions-list" in html
        assert "modality-chart" in html
        assert "emotion-chart" in html
        assert "framing-chart" in html
        assert "sarcasm-chart" in html
        assert "aspects-chart" in html
        assert "export-pdf" in html
        assert "pdf-progress" in html
        assert "live-link-btn" in html
        assert "live-status" in html
        assert "questions-search" in html
        assert "filter-bar" in html
        assert "term-tags-container" in html

    def test_contains_new_js_functions(self, client):
        response = client.get("/dashboard")
        html = response.text
        assert "loadEmojis" in html
        assert "loadTopAuthors" in html
        assert "loadTermTimeline" in html
        assert "exportData" in html
        assert "requestPdfReport" in html
        assert "loadQuestions" in html
        assert "loadModalityTimeline" in html
        assert "loadEmotionTimeline" in html
        assert "loadFraming" in html
        assert "loadSarcasm" in html
        assert "loadAspects" in html

    def test_contains_ux_improvements(self, client):
        response = client.get("/dashboard")
        html = response.text
        assert "badge-live" in html
        assert "badge-ended" in html
        assert "empty-state" in html
        assert "showEmpty" in html
        assert "applyFilters" in html
        assert "addTermTag" in html
        assert "removeTermTag" in html
        assert "renderTermTags" in html
        assert "renderQuestions" in html
        assert "filter-sentiment" in html
        assert "filter-time-start" in html
        assert "filter-time-end" in html
        assert "filter-apply-btn" in html
        assert "sentiment-stats" in html
        assert "loadSentimentSummary" in html
        assert "renderSentimentStats" in html
        assert "significant_change" in html

    def test_contains_get_headers_function(self, client):
        """getHeaders precisa estar declarada no escopo global antes de ser usada."""
        response = client.get("/dashboard")
        html = response.text
        assert "function getHeaders" in html
