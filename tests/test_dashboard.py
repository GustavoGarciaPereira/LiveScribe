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
        """Os nomes das funcoes JS devem estar no arquivo dashboard.js carregado."""
        response = client.get("/dashboard")
        html = response.text
        # Verifica que o JS externo eh carregado
        assert "src=\"/static/js/dashboard.js\"" in html
        assert "defer" in html
        # Os nomes das funcoes estao no .js, nao no HTML — verificamos o arquivo
        import os
        js_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'static', 'js', 'dashboard.js')
        with open(js_path) as f:
            js = f.read()
        assert "loadEmojis" in js
        assert "loadTopAuthors" in js
        assert "loadTermTimeline" in js
        assert "exportData" in js
        assert "requestPdfReport" in js
        assert "loadQuestions" in js
        assert "loadModalityTimeline" in js
        assert "loadEmotionTimeline" in js
        assert "loadFraming" in js
        assert "loadSarcasm" in js
        assert "loadAspects" in js

    def test_contains_ux_improvements(self, client):
        """Elementos de UX devem estar presentes no HTML (classes CSS e IDs)."""
        response = client.get("/dashboard")
        html = response.text
        import os
        css_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'static', 'css', 'dashboard.css')
        with open(css_path) as f:
            css = f.read()
        assert "badge-live" in css
        assert "badge-ended" in css
        assert "empty-state" in html
        assert "filter-sentiment" in html
        assert "filter-time-start" in html
        assert "filter-time-end" in html
        assert "filter-apply-btn" in html
        assert "sentiment-stats" in html
        # Verifica que as funcoes JS estao no arquivo externo
        js_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'static', 'js', 'dashboard.js')
        with open(js_path) as f:
            js = f.read()
        assert "significant_change" in js
        assert "showEmpty" in js
        assert "applyFilters" in js
        assert "addTermTag" in js
        assert "removeTermTag" in js
        assert "renderTermTags" in js
        assert "renderQuestions" in js
        assert "loadSentimentSummary" in js
        assert "renderSentimentStats" in js

    def test_contains_get_headers_function(self, client):
        """getHeaders precisa estar declarada no escopo global no dashboard.js."""
        response = client.get("/dashboard")
        html = response.text
        assert "src=\"/static/js/dashboard.js\"" in html
        import os
        js_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'static', 'js', 'dashboard.js')
        with open(js_path) as f:
            js = f.read()
        assert "function getHeaders" in js
