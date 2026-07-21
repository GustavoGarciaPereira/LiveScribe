# REASONIX.md — Contexto do projeto para o Reasonix

## Identificacao

- **Nome do projeto:** PulsoDaLive / LiveScribe
- **Objetivo:** Coletar chat de lives de multiplas plataformas e analisar discurso (frequencia de palavras, sentimentos, topicos, picos de engajamento, emojis, ranking de espectadores, enquadramentos, sarcasmo)
- **Stack:** FastAPI + SQLAlchemy + SQLite + LeIA (lexico) + scikit-learn + regex + Extensao Chrome + Chart.js + WeasyPrint + google-api-python-client

## Arquitetura atual

```
app/
├── api/
│   ├── deps.py              -> get_db, get_chat_service (injeta LeiaSentimentAnalyzer + TfidfTopicExtractor + RegexEmojiExtractor + LexiconModalityAnalyzer + LexiconEmotionAnalyzer + LexiconFramingAnalyzer + LexiconSarcasmAnalyzer + LexiconAspectAnalyzer), get_current_user, get_report_queue
│   └── routes/
│       ├── auth.py          -> register, login, login/google, callback/google, logout, /me
│       ├── chat.py          -> 19 endpoints de analise + export
│       ├── reports.py       -> 3 endpoints de relatorio PDF (create, status, download)
│       ├── webhooks.py      -> CRUD de webhooks (create, list, delete)
│       └── youtube_comments.py -> Coleta de comentarios via YouTube Data API v3 (fetch, list, export CSV)
├── core/
│   ├── config.py            -> Configuracoes do .env (pydantic-settings)
│   ├── limiter.py           -> Limiter compartilhado do slowapi (rate limiting)
│   ├── stopwords.py         -> ~330 stopwords em portugues (incluindo girias, abreviacoes de chat e verbos de baixo valor)
│   ├── emoji_sentiment.py   -> Mapeamento de 50 emojis para sentimento (Positivo/Negativo/Neutro)
│   ├── emotion_lexicon.py   -> Lexico de 6 emocoes (alegria, raiva, medo, surpresa, tristeza, nojo)
│   ├── modality_lexicon.py  -> Lexico de modalizacao (certeza, duvida, enfase)
│   ├── framing_lexicon.py   -> Lexico de enquadramentos (ataque, defesa, ironia, elogio, pergunta) — 150+ entradas
│   ├── sarcasm_lexicon.py   -> Lexico de sarcasmo/ironia — ~60 expressoes
│   ├── aspects_lexicon.py   -> Lexico de entidades/aspectos para sentimento por aspecto
│   └── timezone.py          -> Utilitarios de fuso horario (BRT, America/Sao_Paulo)
├── infrastructure/
│   └── database.py          -> SQLAlchemy engine + SessionLocal (SQLite)
├── models/
│   ├── message.py           -> Message ORM (id, live_id, author, message, platform, user_id, created_at)
│   ├── user.py              -> User ORM (email, name, google_id, password_hash/bcrypt, provider, is_active)
│   ├── webhook.py           -> Webhook ORM (url, event, user_id, is_active)
│   └── youtube_comment.py   -> YouTubeComment ORM (video_id, author, comment, reply_count, reply_level, is_reply, parent_id, published_at, user_id)
├── repositories/
│   └── messages.py          -> create_message, list_messages_by_live, list_lives, list_top_authors
├── schemas/
│   ├── auth.py              -> LoginRequest, RegisterRequest, TokenResponse, UserInfo
│   ├── chat.py              -> ChatMessage, MessageResponse, WordFrequency*, Sentiment*, SentimentStatistics, LiveSummary, TimelineBucket, EngagementPeak, TopicItem, TopicBucket, EmojiItem, AuthorItem, QuestionItem, ModalityBucket, EmotionBucket, TopicSentimentItem, FramingResponse, SarcasmResponse, AspectSentimentItem, AspectSentimentResponse + Responses
│   └── webhook.py           -> WebhookCreate, WebhookResponse
├── services/
│   ├── auth.py              -> create_access_token, verify_token (JWT, jose)
│   ├── chat.py              -> ChatService (recebe 8 analisadores por DI: SentimentAnalyzer + TopicExtractor + EmojiExtractor + ModalityAnalyzer + EmotionAnalyzer + FramingAnalyzer + SarcasmAnalyzer + AspectAnalyzer)
│   ├── aspects.py           -> AspectAnalyzer (ABC) + LexiconAspectAnalyzer (sentimento por entidade)
│   ├── emojis.py            -> EmojiExtractor (ABC) + RegexEmojiExtractor (regex Extended_Pictographic)
│   ├── emotion.py           -> EmotionAnalyzer (ABC) + LexiconEmotionAnalyzer (6 categorias)
│   ├── export.py            -> ExportService (JSON, CSV, XLSX)
│   ├── framing.py           -> FramingAnalyzer (ABC) + LexiconFramingAnalyzer (6 categorias: ataque, defesa, ironia, elogio, pergunta, neutro)
│   ├── modality.py          -> ModalityAnalyzer (ABC) + LexiconModalityAnalyzer (certeza/duvida/enfase)
│   ├── questions.py         -> detect_questions (agrupa perguntas similares por distancia de Levenshtein)
│   ├── report.py            -> ReportService: gera PDF com graficos, tabelas e analises
│   ├── report_queue.py      -> ReportQueue: fila assincrona para geracao de PDF em background
│   ├── sarcasm.py           -> SarcasmAnalyzer (ABC) + LexiconSarcasmAnalyzer (sarcastic / non_sarcastic)
│   ├── sentiment.py         -> SentimentAnalyzer (ABC) + LeiaSentimentAnalyzer (LeIA)
│   ├── topics.py            -> TopicExtractor (ABC) + TfidfTopicExtractor (sklearn) com _filter_tokens
│   ├── transcript.py        -> TranscriptService: obtem transcricao via YouTube Transcript API
│   ├── webhook.py           -> trigger_webhooks (POST para URLs cadastradas)
│   └── youtube_comments.py  -> YouTubeCommentService: coleta de comentarios via YouTube Data API v3, com suporte a profundidade configurável de respostas (max_depth) e conversão de fuso horário (UTC→BRT)
├── templates/
│   ├── dashboard.html       -> Dashboard interativo com Chart.js (inclui graficos de enquadramentos e sarcasmo)
│   ├── favicon.svg          -> Favicon SVG do PulsoDaLive
│   ├── landing.html         -> Landing page de vendas com secoes de features, precos, FAQ
│   ├── login.html           -> Pagina de login segura com email/senha, cadastro e Google OAuth
│   └── report_html.py       -> Template Jinja2 para o relatorio PDF (inclui secoes de enquadramentos e sarcasmo)
└── main.py                  -> App factory, lifespan, CORS, healthcheck, /dashboard, /landing, /login, /favicon.ico, /youtube-comments, migracoes legadas

static/
├── css/
│   ├── dashboard.css        -> Estilos do dashboard (design tokens, grid, cards)
│   └── nav.css              -> Estilos da barra de navegacao (fixa, responsiva, dark mode)
└── js/
    ├── dashboard.js         -> Logica do dashboard SPA (Chart.js, auth, filtros)
    └── nav.js               -> Menu de navegacao dinamico com estado de autenticacao

frontend/
├── content.js               -> Extensao Chrome (v4): MutationObserver no #chatframe do YouTube + token JWT
├── popup.html               -> Popup de login dark mode
├── popup.js                 -> Login/logout via API, armazena token no chrome.storage.local
└── manifest.json            -> Manifest V3, permissoes youtube + localhost

tests/
├── conftest.py              -> Fixtures: db_session, mock_analyzer, mock_topic_extractor, client (com LexiconFramingAnalyzer + LexiconSarcasmAnalyzer + LexiconAspectAnalyzer), auth_client
├── test_aspects.py          -> Testes do AspectAnalyzer (sentimento por entidade)
├── test_auth.py             -> Testes de autenticacao JWT e OAuth
├── test_dashboard.py        -> Testes de elementos HTML do dashboard
├── test_deps.py             -> Testes de injecao de dependencia
├── test_emojis.py           -> 4 testes de extracao de emoji
├── test_emotion.py          -> Testes do EmotionAnalyzer (6 categorias)
├── test_export.py           -> Testes de exportacao JSON/CSV/XLSX
├── test_framing.py          -> 15 testes do FramingAnalyzer, servico e rota
├── test_modality.py         -> Testes do ModalityAnalyzer
├── test_models.py           -> Testes dos modelos ORM
├── test_questions.py        -> Testes de deteccao de perguntas
├── test_repositories.py     -> Testes do repositorio de mensagens
├── test_report.py           -> Testes da fila de relatorios, geracao de PDF e template (inclui framing e sarcasmo)
├── test_routes.py           -> 44 testes (todas as rotas incluindo topic-timeline, top-authors, aspect-sentiment)
├── test_sarcasm.py          -> 10 testes do SarcasmAnalyzer, servico e rota
├── test_schemas.py          -> Testes dos schemas Pydantic
├── test_services.py         -> Testes do ChatService (sentiment timeline, peaks, topics, emojis)
├── test_topics.py           -> Testes do _filter_tokens, TfidfTopicExtractor e expansao de stopwords
├── test_topic_sentiment.py  -> Testes do endpoint topic-sentiment com transcript
├── test_transcript.py       -> Testes do TranscriptService e find_snippet_at
└── test_webhooks.py         -> Testes de CRUD e trigger de webhooks
```

## Decisoes de design

- **Analisadores desacoplados:** Interfaces ABC para SentimentAnalyzer, TopicExtractor, EmojiExtractor, ModalityAnalyzer, EmotionAnalyzer, FramingAnalyzer, SarcasmAnalyzer, AspectAnalyzer — todos injetados por DI no ChatService via `app/api/deps.py`.
- **Lexico de enquadramentos:** `FRAMING_LEXICON` mapeia palavras para listas de categorias (ataque, defesa, ironia, elogio, pergunta). O `LexiconFramingAnalyzer` inverte o mapeamento, compila regex por categoria, e usa `\b` para palavras simples e substring para expressoes. Mensagens sem match viram "neutro".
- **Lexico de sarcasmo:** `SARCASM_LEXICON` com ~60 expressoes ironicas. `LexiconSarcasmAnalyzer` verifica presenca via regex case-insensitive e retorna `{"sarcastic": N, "non_sarcastic": M}`.
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
- **Significancia estatistica na timeline:** Teste T de Welch entre buckets consecutivos de sentimento — destacando momentos de virada real (p < 0.05). Campos `significant_change`, `p_value`, `change_direction`, `change_magnitude` adicionados ao schema `TimelineBucket`.
- **Sentimento por aspectos:** `LexiconAspectAnalyzer` detecta entidades (pessoas, marcas, termos do léxico `ASPECTS_LEXICON`) e calcula sentimento agregado (LeIA) para cada entidade encontrada.
- **Visualizacao no dashboard:** Grafico de barras horizontal para enquadramentos; grafico de rosca (doughnut) para sarcasmo. Ambos com tooltip mostrando contagem e percentual.
- **Relatorio PDF:** Ambos enriquecimento via `report_queue.py` — necessario adicionar cada novo analisador ao `ChatService` criado na thread background (mesmo problema recorrente com framing e sarcasmo).
- **Test coverage:** 93%, com testes unitarios, de servico e de rota para cada novo analisador. Total: **243 testes**.

## Endpoints

| Metodo | Rota | Auth | Descricao |
|--------|------|------|-----------|
| GET | / | — | Healthcheck |
| GET | /dashboard | 🔒 | Dashboard HTML (Chart.js) |
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
| GET | /api/chat/{live_id}/framing | 🔒 | Enquadramentos (ataque/defesa/ironia/elogio/pergunta/neutro) |
| GET | /api/chat/{live_id}/sarcasm | 🔒 | Sarcasmo/ironia (sarcastic/non_sarcastic) |
| GET | /api/chat/{live_id}/aspect-sentiment | 🔒 | Sentimento por aspectos/entidades |
| **Relatorios** |
| POST | /api/reports | 🔒 | Criar job de relatorio PDF |
| GET | /api/reports/{job_id} | 🔒 | Status do job de relatorio |
| GET | /api/reports/{job_id}/download | 🔒 | Download do PDF gerado |
| **Webhooks** |
| POST | /api/webhooks | 🔒 | Criar webhook |
| GET | /api/webhooks | 🔒 | Listar webhooks |
| DELETE | /api/webhooks/{id} | 🔒 | Deletar webhook |
| **YouTube Comments** |
| POST | /api/youtube/comments/fetch | 🔒 | Coletar comentarios de um video via YouTube Data API (com max_depth opcional) |
| GET | /api/youtube/comments | 🔒 | Listar videos coletados |
| GET | /api/youtube/comments/{video_id} | 🔒 | Listar comentarios de um video |
| GET | /api/youtube/comments/{video_id}/export | 🔒 | Exportar comentarios para CSV |
| **Paginas** |
| GET | /login | — | Pagina de login (email/senha, cadastro, Google OAuth) |
| GET | /youtube-comments | 🔒 | Pagina de gerenciamento de comentarios do YouTube |

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

### Fase 7 — Analise de enquadramentos (Framing)
1. **`app/core/framing_lexicon.py`** — 150+ entradas mapeando palavras/expressoes a categorias (ataque, defesa, ironia, elogio, pergunta)
2. **`app/services/framing.py`** — `FramingAnalyzer` (ABC) + `LexiconFramingAnalyzer` com regex pre-compilados (\b para palavras, substring para expressoes)
3. **Schema `FramingResponse`** — `live_id`, `total_messages`, `framing` (dict com as 6 categorias)
4. **Endpoint `GET /api/chat/{live_id}/framing`** — autenticado, retorna contagens por categoria
5. **Dashboard** — card "🗣️ Enquadramentos" com grafico de barras horizontal (Chart.js), cores por categoria, tooltip com percentual
6. **Relatorio PDF** — tabela com categorias, contagens e percentuais no template Jinja2
7. **15 testes** — unitarios do analisador, servico e rota

### Fase 8 — Deteccao de sarcasmo (Sarcasm)
1. **`app/core/sarcasm_lexicon.py`** — ~60 expressoes ironicas (ironia explicita, riso ironico, falso elogio, questionamento ironico, deboche)
2. **`app/services/sarcasm.py`** — `SarcasmAnalyzer` (ABC) + `LexiconSarcasmAnalyzer` com pattern matching case-insensitive
3. **Schema `SarcasmResponse`** — `live_id`, `total_messages`, `sarcasm` (`sarcastic`/`non_sarcastic`)
4. **Endpoint `GET /api/chat/{live_id}/sarcasm`** — autenticado
5. **Dashboard** — card "😏 Sarcasmo/ironia" com grafico de rosca (doughnut), cores laranja/cinza
6. **Relatorio PDF** — tabela com Sarcastico/Nao sarcastico, contagens e percentuais
7. **10 testes** — unitarios do analisador, servico e rota

### Fase 9 — Correcoes pos-implementacao
1. **report_queue.py** — Adicionados `LexiconFramingAnalyzer` e `LexiconSarcasmAnalyzer` ao `ChatService` da thread background (bug recorrente: PDFs mostravam zeros)
2. **conftest.py** — Adicionados `LexiconFramingAnalyzer` e `LexiconSarcasmAnalyzer` ao `client` fixture
3. **report.py** — Fallback explicito de zeros para `framing` e `sarcasm` no contexto do template
4. **report_html.py** — Templates refatorados para usar iteracao com `items()` em vez de keys hardcoded
5. **Total: 182 testes, 92% de cobertura**

### Fase 10 — Aspectos, significancia estatistica e expansao de stopwords
1. **`app/services/aspects.py`** — `AspectAnalyzer` (ABC) + `LexiconAspectAnalyzer`: detecta entidades no texto e calcula sentimento agregado (LeIA) para cada entidade
2. **`app/core/aspects_lexicon.py`** — Léxico de ~80 entidades/aspectos organizados por categoria (pessoas, marcas, termos técnicos)
3. **Endpoint `GET /api/chat/{live_id}/aspect-sentiment`** — autenticado, aceita `entities` opcional via query, retorna sentimento por entidade
4. **Significancia estatistica na timeline** — Teste T de Welch entre buckets consecutivos; campos `significant_change`, `p_value`, `change_direction`, `change_magnitude` no schema `TimelineBucket`; destaque visual no dashboard
5. **Filtro por user_id** — todas as queries de leitura e escrita filtram por `user_id`; webhooks e relatorios verificam ownership
6. **Landing page atualizada** — seção de funcionalidades expandida com framing, sarcasmo e aspectos
7. **Expansao de stopwords** — ~110 novas entradas incluindo verbos de primeira pessoa (acho, acredito, agradecemos), verbos genericos (ver, falar, quer, fazer, saber, dizer) e pronomes/advérbios (coisa, gente, ainda, super, tudo, nada, algo)
8. **Teste de validacao de lexicos** — `scripts/validate_lexicons.py` + `scripts/compute_lexicon_accuracy.py` para medir precisao real dos léxicos de sarcasmo e enquadramento
9. **Total: 201 testes, 93% de cobertura**

### Fase 11 — Modulo de comentarios de videos do YouTube
1. **`app/services/youtube_comments.py`** — `YouTubeCommentService` com coleta via YouTube Data API v3
2. **``app/models/youtube_comment.py`** — Modelo ORM `YouTubeComment` (video_id, author, comment, reply_count, is_reply, parent_id, published_at, user_id)
3. **Endpoints:** `POST /api/youtube/comments/fetch` (coleta), `GET /api/youtube/comments` (listar videos), `GET /api/youtube/comments/{video_id}` (listar comentarios), `GET /api/youtube/comments/{video_id}/export` (CSV)
4. **UI em `/youtube-comments`** — Pagina com dark mode, tabela de comentarios, exportacao CSV
5. **Profundidade configuravel de respostas** — `max_depth`: 0 (so principais), 1 (N1), 2 (N2), -1 (todas); recursao com `reply_level`
6. **Fuso horario BRT** — Armazenamento em UTC, exibicao em America/Sao_Paulo (-03:00)
7. **`google-api-python-client`** adicionado as dependencias
8. **36 testes** — fuso, max_depth, reply_count, reply_level, rotas
9. **Total: 222+ testes**

### Fase 12 — .env, python-dotenv e seguranca de credenciais
1. **`.env` criado** — `SECRET_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `YOUTUBE_API_KEY`
2. **`python-dotenv`** — `load_dotenv()` no startup (fallback para pydantic-settings)
3. **`YOUTUBE_API_KEY` removida do codigo-fonte** — existe apenas no `.env`
4. **`.env` adicionado ao `.gitignore`** — prevencao de vazamento de credenciais
5. **Correcao Chart.js integrity** — hash SHA-384 corrigido para v4.4.7
6. **Import opcional do dotenv** — `try/except ImportError` para nao crashar fora do venv

### Fase 13 — Tela de login segura e menu de navegacao
1. **`/login`** — Pagina de login dark mode com abas Entrar/Cadastrar, email/senha e Google OAuth; aceita `?next=` para redirect pos-login
2. **`get_current_user_optional`** — Dependency que retorna `None` em vez de 401, usada para proteger paginas HTML
3. **`/dashboard` e `/youtube-comments` protegidos** — Redirecionam para `/login?next=...` quando nao autenticados
4. **Google OAuth com `state`** — Callback aceita `state` e redireciona o navegador apos login
5. **`nav.css` + `nav.js`** — Barra de navegacao fixa no topo com links, auth state (avatar + nome + Sair), responsiva (hamburguer em mobile)
6. **243 testes, 100% passando**

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
curl http://127.0.0.1:8000/api/chat/test/framing -H "Authorization: Bearer $TOKEN"
curl http://127.0.0.1:8000/api/chat/test/sarcasm -H "Authorization: Bearer $TOKEN"

# Rodar testes
pytest -v --cov=app --cov-report=term-missing
```
