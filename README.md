# PulsoDaLive / LiveScribe

Captura e análise de discurso em tempo real de chats de lives do YouTube.

## Funcionalidades

- Extensão Chrome que coleta mensagens de chat de lives do YouTube
- API FastAPI para armazenar e analisar as mensagens
- Frequência de palavras (com stopwords em português)
- Análise de sentimentos com léxico LeIA (VADER adaptado para português)
- Linha do tempo de sentimentos por intervalos de tempo
- Picos de engajamento (janelas de maior atividade)
- Tópicos emergentes via TF-IDF
- Dashboard HTML interativo com Chart.js
- Arquitetura desacoplada para fácil troca de modelos (sentimento e tópicos)
- Suporte a múltiplas plataformas (campo `platform`)

## Stack

- **Backend:** FastAPI, SQLAlchemy, SQLite
- **ML/NLP:** LeIA (léxico de sentimentos), scikit-learn (TF-IDF para tópicos)
- **Frontend:** Extensão Chrome Manifest v3 + Dashboard HTML (Chart.js CDN)
- **Testes:** pytest + pytest-cov (93% cobertura)

## Estrutura

```
LiveScribe/
├── app/                    # Backend FastAPI
│   ├── api/                # Rotas e injeção de dependências
│   ├── core/               # Configurações e stopwords
│   ├── infrastructure/     # Banco de dados (SQLite)
│   ├── models/             # Modelos SQLAlchemy
│   ├── repositories/       # Acesso a dados (CRUD, consultas agregadas)
│   ├── schemas/            # Schemas Pydantic v2
│   ├── services/           # Lógica de negócio e analisadores
│   └── templates/          # Dashboard HTML
├── frontend/               # Extensão Chrome "PulsoDaLive"
├── backend/                # Protótipo antigo (não utilizado)
├── tests/                  # 51 testes (pytest)
├── data/                   # Banco SQLite (app.db)
└── requirements.txt
```

## Como rodar

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Acesse a documentação interativa em http://127.0.0.1:8000/docs
Dashboard em http://127.0.0.1:8000/dashboard

## Extensão Chrome

1. Acesse `chrome://extensions/`
2. Ative o "Modo do desenvolvedor"
3. Clique em "Carregar sem compactação" e selecione a pasta `frontend/`
4. Abra uma live do YouTube com chat ativo
5. As mensagens começarão a ser enviadas automaticamente para o backend

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/` | Healthcheck |
| `GET` | `/dashboard` | Dashboard HTML interativo |
| `POST` | `/api/chat/messages` | Salvar uma mensagem |
| `GET` | `/api/chat/lives` | Listar lives capturadas |
| `GET` | `/api/chat/{live_id}/word-frequency` | Top palavras (frequência) |
| `GET` | `/api/chat/{live_id}/sentiment` | Análise de sentimentos |
| `GET` | `/api/chat/{live_id}/sentiment-timeline` | Sentimentos por bucket de tempo |
| `GET` | `/api/chat/{live_id}/engagement-peaks` | Picos de mensagens |
| `GET` | `/api/chat/{live_id}/topics` | Tópicos via TF-IDF |

## Arquitetura de serviços (injeção de dependência)

### Sentimento

```
SentimentAnalyzer (ABC) ← LeiaSentimentAnalyzer (LeIA)
                              ↓ injetado em
                         ChatService
```

### Tópicos

```
TopicExtractor (ABC) ← TfidfTopicExtractor (scikit-learn)
                              ↓ injetado em
                         ChatService
```

Para trocar de analisador: criar nova classe que implementa a ABC e alterar a injeção em `app/api/deps.py`.

## Testes

```bash
# Instalar dependências de teste
pip install pytest pytest-cov httpx

# Executar todos os testes com cobertura
pytest -v --cov=app --cov-report=term-missing

# Executar apenas um arquivo
pytest tests/test_routes.py -v
```

**Cobertura atual: 93% (51 testes passando).**

## Arquivos de teste

| Arquivo | Cobertura |
|---------|-----------|
| `tests/test_routes.py` | Rotas da API (healthcheck, CRUD, lives, timeline, picos, tópicos, plataforma) |
| `tests/test_services.py` | ChatService + LeiaSentimentAnalyzer real |
| `tests/test_schemas.py` | Schemas Pydantic (validação, serialização) |
| `tests/test_repositories.py` | Repositório de mensagens |
| `tests/test_models.py` | Modelo Message (created_at) |
| `tests/test_deps.py` | Injeção de dependências |
| `tests/test_dashboard.py` | Rota do dashboard HTML |
| `tests/conftest.py` | Fixtures compartilhadas (DB em memória, mocks) |

## Migração de banco

A coluna `platform` é adicionada automaticamente em bancos legados na inicialização (ALTER TABLE via `lifespan`).
