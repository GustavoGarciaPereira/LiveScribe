"""Testes para o dashboard HTML."""

import json
import os
import shutil
import subprocess

import pytest

JS_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "static", "js", "dashboard.js")
HARNESS_PATH = os.path.join(os.path.dirname(__file__), "_dashboard_auth_harness.js")


class TestDashboard:
    def test_redirects_to_login_when_not_authenticated(self, client):
        """Sem auth, /dashboard redireciona para /login."""
        response = client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 303
        assert "/login" in response.headers.get("location", "")

    def test_returns_200_when_authenticated(self, auth_client):
        response = auth_client.get("/dashboard")
        assert response.status_code == 200

    def test_contains_title_when_authenticated(self, auth_client):
        response = auth_client.get("/dashboard")
        assert "PulsoDaLive" in response.text

    def test_contains_new_sections(self, auth_client):
        response = auth_client.get("/dashboard")
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

    def test_contains_new_js_functions(self, auth_client):
        """Os nomes das funcoes JS devem estar no arquivo dashboard.js carregado."""
        response = auth_client.get("/dashboard")
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

    def test_contains_ux_improvements(self, auth_client):
        """Elementos de UX devem estar presentes no HTML (classes CSS e IDs)."""
        response = auth_client.get("/dashboard")
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

    def test_contains_get_headers_function(self, auth_client):
        """getHeaders precisa estar declarada no escopo global no dashboard.js."""
        response = auth_client.get("/dashboard")
        html = response.text
        assert "src=\"/static/js/dashboard.js\"" in html
        import os
        js_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'static', 'js', 'dashboard.js')
        with open(js_path) as f:
            js = f.read()
        assert "function getHeaders" in js


class TestDashboardSessionHandling:
    """Cobre a perda de sessao no F5 e o tratamento de 401 no dashboard.js.

    Contexto do bug: fetch() para /api/chat/lives e /api/auth/me nao
    enviava `credentials`, e loadLives() nao checava o status da resposta
    antes de repassar o corpo para renderLiveOptions(), que chamava
    .forEach() em algo que nao era array quando a API respondia 401 —
    lancando TypeError e deixando a UI (login + dashboard) dessincronizada.
    """

    def test_authenticated_fetches_send_credentials(self):
        with open(JS_PATH) as f:
            js = f.read()
        assert "credentials: 'same-origin'" in js
        assert "async function apiFetch(" in js

    def test_single_source_of_truth_for_auth_ui(self):
        with open(JS_PATH) as f:
            js = f.read()
        assert "function setAuthUI(" in js
        # checkAuthState (resultado de /api/auth/me) e o handler de 401
        # de qualquer fetch autenticado devem convergir para setAuthUI().
        assert "setAuthUI(true" in js
        assert "setAuthUI(false)" in js

    def test_stray_unconditional_loadLives_call_was_removed(self):
        """loadLives() so pode ser chamada depois de checkAuthState() confirmar
        a sessao — a chamada solta no topo do script (antes de qualquer
        checagem de auth) era a causa raiz do 401 nao tratado."""
        with open(JS_PATH) as f:
            js = f.read()
        assert "renderTermTags();\nloadLives();" not in js

    @pytest.mark.skipif(shutil.which("node") is None, reason="Node.js nao disponivel neste ambiente")
    def test_dashboard_handles_401_without_throwing(self):
        """Executa o dashboard.js real (via Node) com /api/auth/me e
        /api/chat/lives mockados para responder 401, e confirma que:
        - checkAuthState() e loadLives() nao lancam excecao;
        - a UI converge para o estado 'nao autenticado' (login visivel,
          user-info e dashboard escondidos) de forma consistente, mesmo
          depois de loadLives() rodar.
        """
        result = subprocess.run(
            ["node", HARNESS_PATH, JS_PATH],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, f"harness falhou: {result.stderr}"
        data = json.loads(result.stdout.strip().splitlines()[-1])

        assert data["checkAuthStateThrew"] is False, data.get("checkAuthStateError")
        assert data["loadLivesThrew"] is False, data.get("loadLivesError")

        # Estado apos checkAuthState(): apenas o formulario de login visivel.
        assert data["loginFormVisible"] is True
        assert data["userInfoHidden"] is True
        assert data["dataSectionHidden"] is True

        # Estado permanece consistente apos loadLives() (que tambem recebeu
        # 401) rodar — nunca "Logado como X" e login form ao mesmo tempo.
        assert data["loginFormVisibleAfterLoadLives"] is True
        assert data["dataSectionHiddenAfterLoadLives"] is True

        # setAuthUI(false) (chamado no logout) precisa limpar estado
        # residual: #stats-footer fica fora de #data-section (nao eh
        # escondido so por isso) e os campos de login mantinham o valor
        # digitado anteriormente por nao haver reload de pagina na SPA.
        assert data["footerHiddenAfterLogout"] is True
        assert data["loginEmailClearedAfterLogout"] is True
        assert data["loginPasswordClearedAfterLogout"] is True
