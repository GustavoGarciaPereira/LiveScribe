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

## Testes

```bash
pytest -v --cov=app
```

**Total:** 51 testes, 93% cobertura.

## Arquitetura

```
app/
├── api/
│   ├── deps.py           → get_db, get_chat_service (injeta LeiaSentimentAnalyzer + TfidfTopicExtractor)
│   └── routes/chat.py    → 8 endpoints
├── services/
│   ├── chat.py           → ChatService (recebe SentimentAnalyzer + TopicExtractor via DI)
│   ├── sentiment.py      → SentimentAnalyzer (ABC) + LeiaSentimentAnalyzer
│   └── topics.py         → TopicExtractor (ABC) + TfidfTopicExtractor (sklearn)
├── models/message.py     → Message ORM: id, live_id, author, message, platform, created_at
├── repositories/messages.py → create_message, list_messages_by_live, list_lives
├── schemas/chat.py       → 13 schemas Pydantic v2
├── core/config.py        → Settings via pydantic-settings
├── core/stopwords.py     → Stopwords em português
├── infrastructure/database.py → Engine + SessionLocal (SQLite)
├── main.py               → App factory, lifespan, CORS
└── templates/dashboard.html → Dashboard com Chart.js
frontend/
└── content.js            → Extensão Chrome (observa #chatframe, POST /api/chat/messages com platform)
tests/                    → 51 testes (pytest)
```

## Decisões de design

- **SentimentAnalyzer (ABC)**: interface desacoplada. LeiaSentimentAnalyzer é a implementação atual.
- **TopicExtractor (ABC)**: mesmo padrão. TfidfTopicExtractor usa sklearn.
- **Injeção em deps.py**: ambos são injetados opcionalmente no ChatService (default None).
- **Type hints**: Python 3.10+ (`list[X]`, `X | None`, `dict[K,V]`).
- **Pydantic v2**: model_validate, SettingsConfigDict, json_schema_extra.
- **FastAPI lifespan**: substituiu on_event.
- **Dashboard**: HTML direto sem Jinja2 (evita conflito de cache).
- **platform**: coluna com default "youtube", migração automática em bancos legados.

## Histórico

### Fase 2 (atual)
- Type hints modernos (Python 3.10+)
- 5 novos endpoints analíticos (lives, timeline, peaks, topics, dashboard)
- Coluna platform + desacoplamento de plataformas
- TopicExtractor + TfidfTopicExtractor (sklearn)
- 51 testes, 93% cobertura

### Fase 1
- Pydantic v2, FastAPI lifespan, datetime.utcnow fix
- Sentimento funcional com LeIA
- 28 testes, 90% cobertura
- Corrigida URL da extensão e escopo do liveId

## Environment

```
PROJECT_NAME=Chat Analytics API
VERSION=0.1.0
API_PREFIX=/api
```
