# AgroInsight API

Backend Python (FastAPI) da plataforma AgroInsight — consultor agricola com IA para o produtor rural brasileiro.

## Stack

- **FastAPI** — API REST async
- **PostgreSQL + TimescaleDB** — banco de dados com series temporais
- **SQLAlchemy 2.0** — ORM async
- **Alembic** — migrations
- **Playwright** — scraping CEPEA
- **Anthropic Claude API** — IA prescritiva
- **APScheduler** — cron jobs para pipelines de dados
- **Redis** — cache e filas

## Setup

```bash
# Criar venv
python3 -m venv venv
source venv/bin/activate

# Instalar deps
pip install -r requirements.txt

# Configurar
cp .env.example .env
# Editar .env com suas credenciais

# Criar banco
createdb agroinsight

# Rodar migrations
alembic upgrade head

# Iniciar
uvicorn src.main:app --reload --port 8000
```

## Estrutura

```
src/
├── api/            # Rotas FastAPI
│   ├── deps.py     # Auth, dependencias
│   └── routes/     # Endpoints por dominio
├── models/         # SQLAlchemy models
├── services/       # Logica de negocio
├── scrapers/       # CEPEA, news
├── pipelines/      # Ingestao de dados (daily, weekly, monthly)
│   ├── daily/      # CEPEA, B3, INMET, alertas
│   ├── weekly/     # CONAB precos, previsao clima, IA relatorios
│   └── monthly/    # IBGE, COMEX STAT, USDA WASDE
└── utils/          # Helpers
```

## API Docs

Com o servidor rodando: http://localhost:8000/docs

## Frontend

Dashboard Next.js separado: [agroinsight-web](https://github.com/Sataker/agroinsight-web)
