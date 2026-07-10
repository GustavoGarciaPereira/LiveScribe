# CLAUDE.md

Guia para Claude Code ao trabalhar neste repositório.

## Running the API

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the development server (tabelas criadas automaticamente no startup)
uvicorn app.main:app --reload
```

Docs: `http://localhost:8000/docs`

## Database

SQLite em `data/app.db`. Tabelas criadas automaticamente via `Base.metadata.create_all` no lifespan.
Migração automática: coluna `platform` é adicionada via ALTER TABLE se não existir.

Para recriar do zero:
```bash
rm data/app.db
uvicorn app.main:app --reload
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Healthcheck |
| `GET` | `/dashboard` | Dashboard HTML (Chart.js) |
| `POST` | `/api/chat/messages` | Salva mensagem |
| `GET` | `/api/chat/lives` | Lista lives capturadas |
| `GET` | `/api/chat/{live_id}/word-frequency` | Top palavras |
| `GET` | `/api/chat/{live_id}/sentiment` | Análise de sentimento |
| `GET` | `/api/chat/{live_id}/sentiment-timeline` | Sentimento por buckets |
| `GET` | `/api/chat/{live_id}/engagement-peaks` | Picos de engajamento |
| `GET` | `/api/chat/{live_id}/topics` | Tópicos via TF-IDF |
| `GET` | `/api/chat/{live_id}/topic-timeline` | Evolução de termo |
| `GET` | `/api/chat/{live_id}/emojis` | Ranking de emojis |
| `GET` | `/api/chat/{live_id}/top-authors` | Top espectadores |
| `GET` | `/api/chat/{live_id}/export` | Exportar JSON/CSV/XLSX |
| `GET` | `/api/chat/{live_id}/topic-sentiment` | Sentimento por tópico |
| `GET` | `/api/chat/{live_id}/modality-timeline` | Modalidade (certeza/duvida/enfase) |
| `GET` | `/api/chat/{live_id}/emotion-timeline` | Emoções (6 categorias) |
| `GET` | `/api/chat/{live_id}/questions` | Perguntas frequentes |
| `GET` | `/api/chat/{live_id}/framing` | Enquadramentos (ataque/defesa/ironia/elogio/pergunta/neutro) |
| `GET` | `/api/chat/{live_id}/sarcasm` | Sarcasmo (sarcastic/non_sarcastic) |

## Testes

```bash
pytest -v --cov=app
```

**Total:** 182 testes, 92% cobertura.

## Arquitetura

```
app/
├── api/
│   ├── deps.py              → get_db, get_chat_service (injeta 7 analisadores), get_current_user, get_report_queue
│   └── routes/
│       ├── auth.py          → register, login, Google OAuth, /me
│       ├── chat.py          → 18 endpoints analíticos + export
│       ├── reports.py       → CRUD de relatórios PDF
│       └── webhooks.py      → CRUD de webhooks
├── core/
│   ├── config.py, limiter.py, stopwords.py, timezone.py
│   ├── emoji_sentiment.py, emotion_lexicon.py, modality_lexicon.py
│   ├── framing_lexicon.py   → 150+ entradas de enquadramento
│   └── sarcasm_lexicon.py   → ~60 expressões de sarcasmo
├── models/                  → Message, User, Webhook ORM
├── repositories/messages.py → Acesso a dados
├── schemas/                 → Pydantic v2 (chat.py: 18 schemas)
├── services/
│   ├── chat.py              → ChatService (7 analyzers injetados via DI)
│   ├── sentiment.py, topics.py, emojis.py, emotion.py, modality.py
│   ├── framing.py           → FramingAnalyzer (ABC) + LexiconFramingAnalyzer
│   ├── sarcasm.py           → SarcasmAnalyzer (ABC) + LexiconSarcasmAnalyzer
│   ├── questions.py, transcript.py, export.py
│   ├── report.py            → Geração de PDF (WeasyPrint)
│   └── report_queue.py      → Fila assíncrona para PDF em background
├── templates/               → dashboard.html, landing.html, report_html.py
└── main.py                  → App factory, lifespan, CORS
frontend/                    → Extensão Chrome (Manifest V3)
tests/                       → 182 testes (pytest + coverage)
```

## Decisões de design

- **Analisadores desacoplados via ABC**: SentimentAnalyzer, TopicExtractor, EmojiExtractor, ModalityAnalyzer, EmotionAnalyzer, FramingAnalyzer, SarcasmAnalyzer — todos injetados via DI em `ChatService`.
- **report_queue.py**: Ao adicionar novo analisador, é necessário incluí-lo também na criação do `ChatService` dentro da thread background, senão o PDF mostra zeros.
- **Type hints**: Python 3.10+ (`list[X]`, `X | None`, `dict[K,V]`).
- **Pydantic v2**: model_validate, SettingsConfigDict, json_schema_extra.
- **FastAPI lifespan**: substituiu on_event.
- **Dashboard**: HTML direto sem Jinja2 (evita conflito de cache).
- **Dashboard charts**: barras horizontais para framing; doughnut para sarcasmo.
- **Regex para emojis**: `\p{Extended_Pictographic}` no módulo `regex`.
- **JWT em cookie HttpOnly**: sem localStorage, sem XSS via token.

## Histórico

### Fase 8 (atual)
- Analisador de sarcasmo (`LexiconSarcasmAnalyzer`) com léxico de ~60 expressões
- Endpoint `GET /api/chat/{live_id}/sarcasm`
- Dashboard: gráfico doughnut no card "😏 Sarcasmo/ironia"
- Relatório PDF: tabela Sarcastico/Não sarcastico com percentuais
- 10 testes de sarcasmo

### Fase 7
- Analisador de enquadramentos (`LexiconFramingAnalyzer`) com léxico de 150+ entradas
- 6 categorias: ataque, defesa, ironia, elogio, pergunta, neutro
- Endpoint `GET /api/chat/{live_id}/framing`
- Dashboard: gráfico de barras horizontal no card "🗣️ Enquadramentos"
- Relatório PDF: tabela com categorias e percentuais
- 15 testes de framing

### Fase 6
- Revisão completa de segurança (CORS, XSS, SSRF, JWT HttpOnly, rate limiting)
- 154 testes, 91% cobertura

### Fase 5
- Landing page, topic-sentiment, modality, emotion, questions, relatório PDF
- 147 testes, 89% cobertura

### Fase 4
- topic-timeline, emojis, top-authors, export JSON/CSV/XLSX
- 80 testes, 90% cobertura

### Fase 3
- Autenticação JWT, Google OAuth2, proteção de rotas, webhooks
- 60 testes, 86% cobertura

### Fase 2
- 5 novos endpoints (lives, timeline, peaks, topics, dashboard)
- Coluna platform, TopicExtractor desacoplado
- 51 testes, 93% cobertura

### Fase 1
- Pydantic v2, FastAPI lifespan, datetime.utcnow fix
- Sentimento funcional com LeIA
- 28 testes, 90% cobertura

## Environment

```
PROJECT_NAME=Chat Analytics API
VERSION=0.1.0
API_PREFIX=/api
```
