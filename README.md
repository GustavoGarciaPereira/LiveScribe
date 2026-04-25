# PulsoDaLive / LiveScribe

Captura e análise de discurso em tempo real de chats de lives do YouTube.

## Funcionalidades

- Extensão Chrome que coleta mensagens de chat de lives do YouTube
- API FastAPI para armazenar e analisar as mensagens
- Frequência de palavras (com stopwords em português)
- Análise de sentimentos com léxico LeIA (VADER adaptado para português)
- Arquitetura desacoplada para fácil troca de modelo de sentimento

## Stack

- **Backend:** FastAPI, SQLAlchemy, SQLite
- **ML/NLP:** LeIA (léxico de sentimentos em português)
- **Frontend:** Extensão Chrome Manifest v3 (JavaScript vanilla)

## Estrutura

```
LiveScribe/
├── app/                    # Backend FastAPI (código ativo)
│   ├── api/                # Rotas e injeção de dependências
│   ├── core/               # Configurações e stopwords
│   ├── infrastructure/     # Banco de dados
│   ├── models/             # Modelos SQLAlchemy
│   ├── repositories/       # Acesso a dados
│   ├── schemas/            # Schemas Pydantic
│   └── services/           # Lógica de negócio e analisadores
├── frontend/               # Extensão Chrome "PulsoDaLive"
├── backend/                # Protótipo antigo (não utilizado)
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
| `POST` | `/api/chat/messages` | Enviar uma mensagem |
| `GET` | `/api/chat/{live_id}/word-frequency` | Top palavras |
| `GET` | `/api/chat/{live_id}/sentiment` | Análise de sentimentos |

## Modelo de sentimento

Atualmente utiliza o **LeIA** (Léxico VADER adaptado para português).
A interface `SentimentAnalyzer` em `app/services/sentiment.py` permite trocar facilmente a implementação.

## Próximos passos

- Linha do tempo de sentimentos
- Detecção de picos de engajamento
- Dashboard de visualização
- Suporte a outras plataformas (Twitch, etc.)
