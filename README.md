# AgroInsight API

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-SQLAlchemy_2.0-4169E1?logo=postgresql&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-structured_output-D97757)
[![tests](https://github.com/Sataker/agroinsight-api/actions/workflows/tests.yml/badge.svg)](https://github.com/Sataker/agroinsight-api/actions/workflows/tests.yml)

Backend of AgroInsight, an AI advisor for Brazilian farmers. It pulls public market and climate data on a schedule,
builds a per-farm context and asks an LLM for a short list of prioritized actions: when to buy fertilizer, what to plant
next season, when to sell, and weather alerts.

It started from a conversation with a soybean and corn producer who makes these decisions from WhatsApp groups and
spreadsheets. **Status: prototype.** The API, data pipelines and AI engine are written; it has not run in production.

> The product targets Brazil, so domain names (fazenda, safra, insumo) and the prompt are in Portuguese.

## How it works

```
 scheduled pipelines (APScheduler, America/Sao_Paulo)
   daily   : CEPEA prices · B3 futures · INMET + NASA POWER weather · barter ratio (bags per ton)
   monthly : CONAB · IBGE SIDRA · Comexstat · World Bank commodity prices
        |
        v
   PostgreSQL (SQLAlchemy 2.0 async)
        |
        v
 ia_engine.coletar_contexto_fazenda()   -> one JSON context per farm: region, soil, recent prices,
        |                                  barter ratios, 14-day weather + forecast, the farm's own
        |                                  harvest history, market events of the last 30 days
        v
 Claude (system prompt cached)          -> JSON array of 1-5 recommendations
        |
        v
 parse_recomendacoes()                  -> validated against the prompt contract before it is saved
        |
        v
 REST API (JWT)  ->  Next.js dashboard (Sataker/agroinsight-web)
```

## LLM integration details

- **Structured output with a contract.** The prompt defines the allowed `tipo` (PLANTIO, COMPRA_INSUMO, VENDA,
  ALERTA_CLIMA, CULTURA_EMERGENTE) and `prioridade` values. `parse_recomendacoes` strips code fences, drops any item
  outside that contract or without a title, and clamps `confianca` to [0, 1], so a malformed answer never reaches the
  database or the farmer.
- **Grounded context, not open questions.** The model only sees numbers the pipelines collected for that farm and
  region, and is told to say so when data is missing instead of guessing.
- **Prompt caching.** The system prompt is sent with `cache_control: ephemeral`; only the farm context changes per call.
- **Non-blocking.** Uses `AsyncAnthropic`, so a slow model call does not stall the FastAPI event loop.
- **Fails closed.** No API key, invalid JSON or an API error returns an empty list and is logged with structlog.

## API

Interactive docs at `/docs` once running. All `/api/v1/*` routes except auth require a Bearer JWT.

| Prefix | What it serves |
|---|---|
| `/api/v1/auth` | register, login (bcrypt + JWT) |
| `/api/v1/fazendas` | the user's farms |
| `/api/v1/precos`, `/insumos`, `/clima`, `/safra` | collected market, input, weather and harvest data |
| `/api/v1/recomendacoes` | AI recommendations and market events |
| `/api/v1/alertas` | price and weather alerts |
| `/api/v1/pipelines` | trigger a pipeline manually |

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # DATABASE_URL, JWT_SECRET, ANTHROPIC_API_KEY, CORS_ORIGINS
uvicorn src.main:app --reload
```

Or with Docker: `docker build -t agroinsight-api . && docker run --env-file .env -p 8000:8000 agroinsight-api`.

Outside `ENV=development` the app refuses to start with the default `JWT_SECRET`. CORS origins come from
`CORS_ORIGINS` (comma-separated).

## Tests

```bash
pytest -q
```

The suite runs without a database or API key (it also runs in GitHub Actions on every push): health check, auth
enforcement on protected routes, JWT round-trip, the output parser against valid, fenced, malformed and
out-of-contract answers, and the AI engine with a mocked client, including a response where a thinking block comes
before the text block.

## Known gaps

- No Alembic migrations generated yet (`alembic/versions` is empty); tables were created from the models.
- CEPEA blocks automated access (HTTP 403), so the CEPEA scraper needs a licensed data source to be reliable.
- Pipelines are covered by manual runs, not by automated tests.

## License

MIT
