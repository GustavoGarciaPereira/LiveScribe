# REASONIX.md — Contexto do projeto para o Reasonix

## Identificação

- **Nome do projeto:** PulsoDaLive / LiveScribe
- **Objetivo:** Coletar chat de lives de multiplas plataformas e analisar discurso (frequencia de palavras, sentimentos, topicos, picos de engajamento)
- **Stack:** FastAPI + SQLAlchemy + SQLite + LeIA (lexico) + scikit-learn + Extensao Chrome

## Arquitetura atual

```
app/
├── api/deps.py              -> get_db, get_chat_service (injeta LeiaSentimentAnalyzer + TfidfTopicExtractor)
├── api/routes/chat.py       -> 8 endpoints
├── services/chat.py         -> ChatService (recebe SentimentAnalyzer + TopicExtractor por DI)
├── services/sentiment.py    -> SentimentAnalyzer (ABC) + LeiaSentimentAnalyzer
├── services/topics.py       -> TopicExtractor (ABC) + TfidfTopicExtractor (sklearn)
├── models/message.py        -> Message ORM (id, live_id, author, message, platform, created_at)
├── repositories/messages.py -> create_message, list_messages_by_live, list_lives
├── core/config.py           -> Configuracoes do .env (pydantic-settings)
├── core/stopwords.py        -> stopwords em portugues
├── infrastructure/database.py -> SQLAlchemy engine + SessionLocal
├── templates/dashboard.html -> Dashboard interativo com Chart.js
└── main.py                  -> App factory, lifespan, CORS, healthcheck, /dashboard
frontend/
└── content.js               -> Extensao Chrome (v4): MutationObserver + POST /api/chat/messages + platform
tests/
├── conftest.py              -> Fixtures: db_session, mock_analyzer, mock_topic_extractor, client
├── test_deps.py
├── test_dashboard.py
├── test_models.py
├── test_repositories.py
├── test_routes.py
├── test_schemas.py
└── test_services.py
```

## Decisoes de design

- **Sentimento desacoplado:** Interface `SentimentAnalyzer` permite trocar o analisador sem mexer no ChatService.
- **Topicos desacoplados:** Interface `TopicExtractor` (ABC) + `TfidfTopicExtractor` (sklearn), mesmo padrao do SentimentAnalyzer.
- **Platform:** Coluna `platform VARCHAR(50) DEFAULT 'youtube'`. Extensao envia `"platform": "youtube"`. Migracao automatica no lifespan para bancos legados.
- **Banco:** SQLite em `data/app.db`. Tabela `messages` com colunas: id, live_id, author, message, platform, created_at.
- **Extensao:** Observa o iframe `#chatframe` do YouTube via MutationObserver. Posta em `http://127.0.0.1:8000/api/chat/messages`.
- **Type hints modernos:** Python 3.10+ sintaxe (`list[X]`, `X | None`, `dict[K,V]`).

## Endpoints

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | / | Healthcheck |
| POST | /api/chat/messages | Salvar mensagem |
| GET | /api/chat/lives | Lista lives capturadas |
| GET | /api/chat/{live_id}/word-frequency | Top-N palavras |
| GET | /api/chat/{live_id}/sentiment | Analise de sentimentos |
| GET | /api/chat/{live_id}/sentiment-timeline | Linha do tempo por bucket |
| GET | /api/chat/{live_id}/engagement-peaks | Picos de engajamento |
| GET | /api/chat/{live_id}/topics | Topicos via TF-IDF |
| GET | /dashboard | Dashboard HTML (Chart.js) |

## Tarefas concluidas

### Fase 1 — Migracao e testes
1. Rota da extensao alinhada com API
2. Sentimento funcional com LeIA
3. Chamada dupla do word_frequency removida
4. Migracao para Pydantic v2 (model_validate, SettingsConfigDict, json_schema_extra)
5. Substituicao de on_event por lifespan handler
6. Corrigido DeprecationWarning do datetime.utcnow
7. Type hints modernos (list, dict, X | None)
8. Tratamento de erro 500 no endpoint de sentimento
9. 28+ testes, 97% de cobertura

### Fase 2 — Analises temporais, topicos, dashboard e plataformas
1. Coluna platform adicionada ao Message (default youtube)
2. Migracao automatica ALTER TABLE no startup
3. Endpoint GET /api/chat/lives (GROUP BY lives)
4. Endpoint GET /{live_id}/sentiment-timeline (buckets temporais)
5. Endpoint GET /{live_id}/engagement-peaks (janelas de mensagens)
6. Endpoint GET /{live_id}/topics (TF-IDF via sklearn)
7. TopicExtractor ABC + TfidfTopicExtractor
8. Dashboard HTML interativo em /dashboard (Chart.js CDN)
9. 51+ testes, 93% de cobertura

## Comandos uteis

```bash
# Iniciar servidor
uvicorn app.main:app --reload

# Instalar dependencias
pip install -r requirements.txt

# Testar endpoints
curl -X POST http://127.0.0.1:8000/api/chat/messages -H "Content-Type: application/json" -d '{"author":"Test","message":"Boa noite","live_id":"test"}'
curl http://127.0.0.1:8000/api/chat/lives
curl http://127.0.0.1:8000/api/chat/test/sentiment-timeline?interval_minutes=5
curl http://127.0.0.1:8000/api/chat/test/topics?top_n=10

# Rodar testes
pytest -v --cov=app --cov-report=term-missing
```
