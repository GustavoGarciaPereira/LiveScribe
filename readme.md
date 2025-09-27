### LiveScribe – Chat Analytics API

#### Sobre o projeto
LiveScribe é uma API em FastAPI para armazenar mensagens de lives e extrair insights em tempo real.  
O serviço oferece endpoints para:

- Persistir mensagens em um banco relacional (SQLite por padrão).
- Calcular frequência de palavras, filtrando stopwords em português.
- Realizar análise de sentimento usando pipelines do Hugging Face.

A arquitetura segue uma separação em camadas (API, serviços, repositórios, infraestrutura) para facilitar manutenção e testes.

#### Principais tecnologias
- Python 3.12+
- FastAPI & Uvicorn
- SQLAlchemy
- Pydantic v2
- Transformers (Hugging Face)
- SQLite (padrão, facilmente substituível)

#### Pré-requisitos
- Python 3.12 ou superior
- `pip` atualizado
- (Opcional) Token do Hugging Face se usar modelos privados

#### Como rodar localmente
1. **Clonar o repositório e entrar na pasta:**
   ```bash
   git clone https://github.com/<seu-usuario>/LiveScribe.git
   cd LiveScribe
   ```

2. **Criar e ativar o ambiente virtual:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Instalar dependências:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Instalar PyTorch (necessário para Transformers):**
   ```bash
   pip install torch --index-url https://download.pytorch.org/whl/cpu
   # ou siga instruções em https://pytorch.org para GPU
   ```

5. **Rodar a aplicação:**
   ```bash
   uvicorn app.main:app --reload
   ```

6. **Acessar a documentação interativa:**
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

#### Estrutura de pastas (resumo)
```
app/
├── api/
│   ├── deps.py
│   └── routes/
│       └── chat.py
├── core/
│   ├── config.py
│   └── stopwords.py
├── infrastructure/
│   ├── database.py
│   └── ml.py
├── models/
│   └── message.py
├── repositories/
│   └── messages.py
├── schemas/
│   └── chat.py
└── services/
    └── chat.py
```

#### Endpoints principais
- `GET /` – Health check.
- `POST /api/chat/messages` – Salva mensagem.
  - Body (`application/json`):
    ```json
    {
      "live_id": "live-123",
      "author": "joao",
      "message": "Gostei demais!"
    }
    ```
- `GET /api/chat/{live_id}/word-frequency?top_n=10`
  - Retorna as palavras mais frequentes (sem stopwords).
- `GET /api/chat/{live_id}/sentiment`
  - Faz análise de sentimento das mensagens salvas.

#### Modelos e análise de sentimento
O pipeline padrão usa o modelo [`tabularisai/multilingual-sentiment-analysis`](https://huggingface.co/tabularisai/multilingual-sentiment-analysis), que cobre 23 idiomas (incluindo português).  
Para trocar o modelo, edite `app/infrastructure/ml.py` e ajuste o `MODEL_NAME` e o mapeamento de rótulos no serviço.

> Antes do primeiro request, o modelo é baixado e cacheado pelo Transformers. Em conexões lentas pode levar alguns minutos.

#### Variáveis de ambiente
As configurações podem ser feitas via `.env` (ver `app/core/config.py`). Exemplos:
```
PROJECT_NAME=LiveScribe API
VERSION=0.1.0
API_PREFIX=/api
```

#### Testes
Ainda não há suíte de testes configurada. Recomenda-se adicionar testes unitários para:
- Serviços de negócio (`app/services`)
- Repositórios (`app/repositories`)
- Endpoints (via `TestClient` do FastAPI)

#### Próximos passos sugeridos
- Adicionar autenticação/autorização (ex.: tokens JWT).
- Paginação ou limites para requisições que retornam muitas mensagens.
- Melhorar logging e observabilidade.
- Cobertura de testes automatizados.
- Dockerizar a aplicação para deployment fácil.

#### Contribuindo
1. Faça um fork.
2. Crie uma branch: `git checkout -b feature/nova-feature`.
3. Commit e push.
4. Abra um Pull Request descrevendo sua alteração.

#### Licença
Defina a licença desejada (ex.: MIT, Apache 2.0) e adicione um arquivo `LICENSE`.