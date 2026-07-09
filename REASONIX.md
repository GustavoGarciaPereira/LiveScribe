# REASONIX.md — Contexto do projeto para o Reasonix

## Identificacao

- **Nome do projeto:** PulsoDaLive / LiveScribe
- **Objetivo:** Coletar chat de lives de multiplas plataformas e analisar discurso (frequencia de palavras, sentimentos, topicos, picos de engajamento, emojis, ranking de espectadores)
- **Stack:** FastAPI + SQLAlchemy + SQLite + LeIA (lexico) + scikit-learn + regex + Extensao Chrome

## Arquitetura atual

```
app/
├── api/
│   ├── deps.py              -> get_db, get_chat_service (injeta LeiaSentimentAnalyzer + TfidfTopicExtractor + RegexEmojiExtractor), get_current_user, get_report_queue
│   └── routes/
│       ├── auth.py          -> register, login, login/google, callback/google, logout, /me
│       ├── chat.py          -> 16 endpoints de analise + export
│       ├── reports.py       -> 3 endpoints de relatorio PDF (create, status, download)
│       └── webhooks.py      -> CRUD de webhooks (create, list, delete)
├── core/
│   ├── config.py            -> Configuracoes do .env (pydantic-settings)
│   ├── limiter.py           -> Limiter compartilhado do slowapi (rate limiting)
│   ├── stopwords.py         -> ~220 stopwords em portugues (incluindo girias e abreviacoes de chat)
│   ├── emoji_sentiment.py   -> Mapeamento de 50 emojis para sentimento (Positivo/Negativo/Neutro)
│   ├── emotion_lexicon.py   -> Lexico de 6 emocoes (alegria, raiva, medo, surpresa, tristeza, nojo)
│   ├── modality_lexicon.py  -> Lexico de modalizacao (certeza, duvida, enfase)
│   └── timezone.py          -> Utilitarios de fuso horario (BRT, America/Sao_Paulo)
├── infrastructure/
│   └── database.py          -> SQLAlchemy engine + SessionLocal (SQLite)
├── models/
│   ├── message.py           -> Message ORM (id, live_id, author, message, platform, user_id, created_at)
│   ├── user.py              -> User ORM (email, name, google_id, password_hash/bcrypt, provider, is_active)
│   └── webhook.py           -> Webhook ORM (url, event, user_id, is_active)
├── repositories/
│   └── messages.py          -> create_message, list_messages_by_live, list_lives, list_top_authors
├── schemas/
│   ├── auth.py              -> LoginRequest, RegisterRequest, TokenResponse, UserInfo
│   ├── chat.py              -> ChatMessage, MessageResponse, WordFrequency*, Sentiment*, SentimentStatistics, LiveSummary, TimelineBucket, EngagementPeak, TopicItem, TopicBucket, EmojiItem, AuthorItem + Responses
│   └── webhook.py           -> WebhookCreate, WebhookResponse
├── services/
│   ├── auth.py              -> create_access_token, verify_token (JWT, jose)
│   ├── chat.py              -> ChatService (recebe SentimentAnalyzer + TopicExtractor + EmojiExtractor + ModalityAnalyzer + EmotionAnalyzer por DI)
│   ├── emojis.py            -> EmojiExtractor (ABC) + RegexEmojiExtractor (regex Extended_Pictographic)
│   ├── emotion.py           -> EmotionAnalyzer (ABC) + LexiconEmotionAnalyzer (6 categorias)
│   ├── export.py            -> ExportService (JSON, CSV, XLSX)
│   ├── modality.py          -> ModalityAnalyzer (ABC) + LexiconModalityAnalyzer (certeza/duvida/enfase)
│   ├── questions.py         -> detect_questions (agrupa perguntas similares por distancia de Levenshtein)
│   ├── report.py            -> ReportService: gera PDF com graficos, tabelas e analises
│   ├── report_queue.py      -> ReportQueue: fila assincrona para geracao de PDF em background
│   ├── sentiment.py         -> SentimentAnalyzer (ABC) + LeiaSentimentAnalyzer (LeIA)
│   ├── topics.py            -> TopicExtractor (ABC) + TfidfTopicExtractor (sklearn) com _filter_tokens
│   ├── transcript.py        -> TranscriptService: obtem transcricao via YouTube Transcript API
│   └── webhook.py           -> trigger_webhooks (POST para URLs cadastradas)
├── templates/
│   ├── dashboard.html       -> Dashboard interativo com Chart.js
│   ├── favicon.svg          -> Favicon SVG do PulsoDaLive
│   ├── landing.html         -> Landing page de vendas com secoes de features, precos, FAQ
│   └── report_html.py       -> Template Jinja2 para o relatorio PDF
└── main.py                  -> App factory, lifespan, CORS, healthcheck, /dashboard, /landing, /favicon.ico, migracoes legadas

frontend/
├── content.js               -> Extensao Chrome (v4): MutationObserver no #chatframe do YouTube + token JWT
├── popup.html               -> Popup de login dark mode
├── popup.js                 -> Login/logout via API, armazena token no chrome.storage.local
└── manifest.json            -> Manifest V3, permissões youtube + localhost

tests/
├── conftest.py              -> Fixtures: db_session, mock_analyzer, mock_topic_extractor, client, auth_client
├── test_auth.py
├── test_dashboard.py
├── test_deps.py
├── test_emojis.py           -> 4 testes de extracao de emoji
├── test_emotion.py          -> Testes do EmotionAnalyzer (6 categorias)
├── test_export.py
├── test_modality.py         -> Testes do ModalityAnalyzer
├── test_models.py
├── test_questions.py        -> Testes de deteccao de perguntas
├── test_repositories.py
├── test_report.py           -> Testes da fila de relatorios e geracao de PDF
├── test_routes.py           -> 44 testes (todas as rotas incluindo topic-timeline, top-authors)
├── test_schemas.py
├── test_services.py         -> testes (incluindo sentiment timeline, peaks, topics, emojis)
├── test_topics.py           -> Testes do _filter_tokens e TfidfTopicExtractor
├── test_topic_sentiment.py  -> Testes do endpoint topic-sentiment com transcript
├── test_transcript.py       -> Testes do TranscriptService e find_snippet_at
└── test_webhooks.py
```

## Decisoes de design

- **Sentimento desacoplado:** Interface `SentimentAnalyzer` (ABC) permite trocar o analisador sem mexer no ChatService. Implementacao atual: LeiaSentimentAnalyzer (VADER adaptado para portugues).
- **Topicos desacoplados:** Interface `TopicExtractor` (ABC) + `TfidfTopicExtractor` (sklearn), mesmo padrao do SentimentAnalyzer.
- **Emojis desacoplados:** Interface `EmojiExtractor` (ABC) + `RegexEmojiExtractor` (regex Extended_Pictographic), injetado no ChatService.
- **Autenticacao JWT:** python-jose, tokens de 24h, providers local (bcrypt) e Google OAuth2. Token armazenado em **cookie HttpOnly** (`access_token`) — nao em localStorage. Rotas GET/POST protegidas com `get_current_user`. Logout via `POST /api/auth/logout` (deleta cookie).
- **Rate limiting:** slowapi com limites por endpoint (5/min auth, 120/min messages, 3/min reports, 10/min webhooks). Limiter compartilhado em `app/core/limiter.py`.
- **Seguranca:** CORS restrito a origens explicitas; XSS mitigado com `escapeHtml()` no dashboard; SSRF mitigado com validacao de URL de webhook (bloqueio de IPs internos); SECRET_KEY validado em todos os ambientes; parametros com bounds via `Query(ge=1, le=...)`; erros 500 retornam mensagem generica + log; webhooks e relatorios isolados por `user_id`.
- **Filtro por user_id:** Todas as queries de leitura e escrita filtram por `user_id`. Webhooks e reports verificam ownership do job/recurso.
- **Platform:** Coluna `platform VARCHAR(50) DEFAULT 'youtube'`. Extensao envia `"platform": "youtube"`. Migracao automatica no lifespan.
- **Banco:** SQLite em `data/app.db`. Tabelas: `messages` (id, live_id, author, message, platform, user_id, created_at), `users` (email, name, google_id, password_hash, provider, is_active), `webhooks` (url, event, user_id, is_active).
- **Extensao:** Observa o iframe `#chatframe` do YouTube via MutationObserver. Posta em `http://127.0.0.1:8000/api/chat/messages` com token JWT (cookie HttpOnly). Login via popup.
- **Type hints modernos:** Python 3.10+ sintaxe (`list[X]`, `X | None`, `dict[K,V]`).
- **Regex para emojis:** `\p{Extended_Pictographic}` no modulo `regex` — evita capturar digitos (0-9) que o `\p{Emoji}` incluiria.
- **Estatisticas de sentimento:** Media, desvio padrao e IC 95% calculados a partir dos compound scores do LeIA via `_compute_statistics`. Usa `1.96 * std/sqrt(n)` para o IC. Se `n < 2`, retorna `null` para `std_dev` e `ci_95`. Exposto via `analyze_with_compound()` no LeiaSentimentAnalyzer.

## Endpoints

| Metodo | Rota | Auth | Descricao |
|--------|------|------|-----------|
| GET | / | — | Healthcheck |
| GET | /dashboard | — | Dashboard HTML (Chart.js) |
| GET | /landing | — | Landing page de vendas |
| GET | /favicon.ico | — | Favicon SVG |
| **Auth** |
| POST | /api/auth/register | — | Registrar conta local → cookie HttpOnly |
| POST | /api/auth/login | — | Login email/senha → cookie HttpOnly |
| POST | /api/auth/logout | — | Deleta cookie de autenticacao |
| GET | /api/auth/login/google | — | Redirect Google OAuth2 |
| GET | /api/auth/callback/google | — | Callback Google → cookie HttpOnly |
| GET | /api/auth/me | 🔒 | Perfil do usuario |
| **Chat** |
| POST | /api/chat/messages | 🔒 | Salvar mensagem do chat |
| GET | /api/chat/lives | 🔒 | Lista lives do usuario |
| GET | /api/chat/{live_id}/word-frequency | 🔒 | Top-N palavras (com filtro de URLs e digitos) |
| GET | /api/chat/{live_id}/sentiment | 🔒 | Analise de sentimentos com media e IC 95% |
| GET | /api/chat/{live_id}/sentiment-timeline | 🔒 | Timeline de sentimentos por bucket |
| GET | /api/chat/{live_id}/engagement-peaks | 🔒 | Picos de engajamento |
| GET | /api/chat/{live_id}/topics | 🔒 | Topicos via TF-IDF (com filtro de tokens) |
| GET | /api/chat/{live_id}/topic-timeline | 🔒 | Evolucao de frequencia de um termo |
| GET | /api/chat/{live_id}/emojis | 🔒 | Ranking de emojis com sentimento |
| GET | /api/chat/{live_id}/top-authors | 🔒 | Ranking de espectadores por mensagens |
| GET | /api/chat/{live_id}/export | 🔒 | Exportar JSON/CSV/XLSX |
| GET | /api/chat/{live_id}/topic-sentiment | 🔒 | Sentimento por topico com transcricao |
| GET | /api/chat/{live_id}/modality-timeline | 🔒 | Modalidade (certeza/duvida/enfase) |
| GET | /api/chat/{live_id}/emotion-timeline | 🔒 | Emocoes (6 categorias) |
| GET | /api/chat/{live_id}/questions | 🔒 | Perguntas frequentes detectadas |
| **Relatorios** |
| POST | /api/reports | 🔒 | Criar job de relatorio PDF |
| GET | /api/reports/{job_id} | 🔒 | Status do job de relatorio |
| GET | /api/reports/{job_id}/download | 🔒 | Download do PDF gerado |
| **Webhooks** |
| POST | /api/webhooks | 🔒 | Criar webhook |
| GET | /api/webhooks | 🔒 | Listar webhooks |
| DELETE | /api/webhooks/{id} | 🔒 | Deletar webhook |

## Tarefas concluidas

### Fase 1 — Migracao e testes
1. Rota da extensao alinhada com API
2. Sentimento funcional com LeIA
3. Chamada dupla do word_frequency removida
4. Migracao para Pydantic v2
5. Substituicao de on_event por lifespan handler
6. Corrigido DeprecationWarning do datetime.utcnow
7. Type hints modernos (list, dict, X | None)
8. Tratamento de erro 500 no endpoint de sentimento
9. 28+ testes, 97% de cobertura

### Fase 2 — Analises temporais, topicos, dashboard e plataformas
1. Coluna platform adicionada (default youtube)
2. Migracao automatica ALTER TABLE no startup
3. Endpoint GET /api/chat/lives (GROUP BY)
4. Endpoint GET /{live_id}/sentiment-timeline (buckets)
5. Endpoint GET /{live_id}/engagement-peaks (janelas)
6. Endpoint GET /{live_id}/topics (TF-IDF)
7. TopicExtractor ABC + TfidfTopicExtractor
8. Dashboard HTML interativo (Chart.js)
9. 51+ testes, 93% de cobertura

### Fase 3 — Autenticacao e protecao de rotas
1. Model User (email, google_id, password_hash, provider)
2. Rotas de auth: register, login, Google OAuth2, /me
3. Protecao JWT em todas as rotas GET de chat
4. Filtro por user_id no repositorio e servico
5. get_current_user_optional para POST /messages
6. Popup de login na extensao Chrome
7. content.js envia token JWT no header Authorization
8. Webhooks CRUD + trigger em new_message e peak_engagement
9. 60+ testes, 86% de cobertura

### Fase 4 — Novas analises (topic-timeline, emojis, top-authors)
1. Endpoint GET /{live_id}/topic-timeline — evolucao de termo ao longo da live
2. Endpoint GET /{live_id}/emojis — ranking de emojis com sentimento (50 emojis mapeados)
3. EmojiExtractor ABC + RegexEmojiExtractor (regex Extended_Pictographic)
4. Endpoint GET /{live_id}/top-authors — ranking de espectadores por mensagens + sentimento medio
5. Repository: list_top_authors com SQL GROUP BY
6. Export endpoint: JSON, CSV, XLSX
7. 80 testes, 90% de cobertura

### Fase 5 — Landing page, analises expandidas, correcoes de qualidade
1. Landing page de vendas (GET /landing) — design responsivo, secoes de features, precos, FAQ, CTA WhatsApp
2. Endpoint /topic-sentiment — cruza topicos com sentimento, emocao e transcricao (YouTube Transcript API)
3. Endpoint /modality-timeline — timeline de certeza/duvida/enfase
4. Endpoint /emotion-timeline — timeline de 6 emocoes
5. Endpoint /questions — deteccao de perguntas frequentes com agrupamento por similaridade
6. ReportService + ReportQueue — geracao de PDF com graficos, tabelas e analises em background
7. Refinamento da landing page — tom autentico, SVGs, novas secoes "Como funciona", "Quem fez isso"
8. Favicon SVG e rota GET /favicon.ico
9. **Expansao de stopwords** — adicionadas ~80 girias e abreviacoes de chat em `app/core/stopwords.py`
10. **Filtro de tokens no TF-IDF** — `_filter_tokens` remove @mencoes, URLs, digitos, repeticoes (kkkk, rsrsrs), tokens < 3 caracteres
11. **Correcao peak_timestamp** — `topic_sentiment` agora calcula `peak_timestamp` e `peak_minute` corretamente (elapsed seconds desde primeira mensagem)
12. **Snippet de transcricao varia por topico** — cada topico recebe o snippet do seu proprio minuto de pico
13. **Relatorio PDF enriquecido** — `video_id=live_id` passado ao topic_sentiment; `word_frequency` filtra URLs, digitos e tokens < 2 caracteres
14. **Dashboard — Top Perguntas** — limitado a 10 itens com botao expansivel "Ver mais"
15. **Estatisticas de sentimento** — `analyze_with_compound` no LeIA; `_compute_statistics` com mean, std_dev, IC 95% adicionado a `/sentiment`, `/sentiment-timeline` e `/topic-sentiment`
16. **Indicadores no dashboard** — Media e IC 95% exibidos abaixo do grafico de sentimentos
17. **Colunas no relatorio PDF** — Media e IC 95% adicionados a tabela de Sentimento por Topico
18. **147+ testes, 89% de cobertura**

### Fase 6 — Seguranca (revisao completa)
1. **CORS restrito** — `allow_origins` com lista explicita (localhost:8000, 127.0.0.1:8000, localhost:5173), `allow_credentials=False`
2. **XSS mitigado** — funcao `escapeHtml()` em todos os renders `innerHTML` do dashboard (live_id, author, topic, transcript_snippet, questions, errors)
3. **SSRF mitigado** — `validate_webhook_url` bloqueia schemes nao-http e IPs privados/reservados (RFC 1918, loopback, link-local, CGNAT) com resolucao DNS
4. **SECRET_KEY seguro** — validador rejeita valor padrao em qualquer ambiente nao-dev; lido dinamicamente nas funcoes (nao em import-time)
5. **Google OAuth config** — `redirect_uri` movido para `settings.GOOGLE_REDIRECT_URI` (nao hardcoded)
6. **Rate limiting** — slowapi com `@limiter.limit` em todos os endpoints de escrita: auth (5/min), messages (120/min), reports (3/min), webhooks (10/min); `Limiter` compartilhado em `app/core/limiter.py`
7. **JWT em cookie HttpOnly** — token `access_token` setado como cookie (`httponly=True, samesite=lax, secure=production`); dashboard usa cookie automatico, sem localStorage; endpoint `POST /api/auth/logout` deleta cookie
8. **POST /messages requer auth** — `get_current_user` substitui `get_current_user_optional_v2`; todo usuario vinculado a `user_id`
9. **Webhooks isolados por user_id** — `trigger_webhooks` recebe `user_id` e filtra webhooks do dono do recurso
10. **Relatorios isolados por user_id** — `get_status`/`get_pdf` verificam `job.user_id == user.id`
11. **Header injection mitigado** — `urllib.parse.quote(live_id)` no `Content-Disposition` do export (previne CRLF injection)
12. **Erros internos genericos** — excecoes 500 retornam mensagem generica + `logger.error()` no servidor
13. **Parametros com bounds** — `top_n`, `interval_minutes`, `window_minutes`, `min_length` usam `Query(ge=1, le=...)`
14. **Cleanup de jobs** — `_cleanup_old_jobs()` remove reports concluidos/failed ha >1h (previne memory leak)
15. **OAuth Google vincula contas** — callback verifica email existente e vincula `google_id` em vez de falhar com duplicata
16. **Chart.js com SRI** — `integrity="sha384-..."` + `crossorigin="anonymous"` no CDN
17. **154 testes, 91% de cobertura**

## Comandos uteis

```bash
# Iniciar servidor
uvicorn app.main:app --reload

# Instalar dependencias
pip install -r requirements.txt

# Testar endpoints (com auth — substitua TOKEN por um JWT valido)
TOKEN="xxx"
curl -X POST http://127.0.0.1:8000/api/chat/messages -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d '{"author":"Test","message":"Boa noite","live_id":"test"}'
curl http://127.0.0.1:8000/api/chat/lives -H "Authorization: Bearer $TOKEN"
curl http://127.0.0.1:8000/api/chat/test/emojis?top_n=20
curl http://127.0.0.1:8000/api/chat/test/top-authors?top_n=10
curl http://127.0.0.1:8000/api/chat/test/topic-timeline?term=gato

# Rodar testes
pytest -v --cov=app --cov-report=term-missing
```