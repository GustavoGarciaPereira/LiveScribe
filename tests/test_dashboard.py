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

    def test_contains_new_js_functions(self, client):
        response = client.get("/dashboard")
        html = response.text
        assert "loadEmojis" in html
        assert "loadTopAuthors" in html
        assert "loadTermTimeline" in html
        assert "exportData" in html
        assert "loadQuestions" in html
        assert "loadModalityTimeline" in html
        assert "loadEmotionTimeline" in html
