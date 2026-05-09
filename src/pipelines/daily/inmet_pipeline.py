"""
Pipeline diario: INMET API → dados_clima

Coleta dados de todas as estacoes meteorologicas automaticas do INMET.
API publica: https://apitempo.inmet.gov.br/
"""

from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
import httpx
import structlog

from src.models.clima import DadoClima

logger = structlog.get_logger()

INMET_BASE = "https://apitempo.inmet.gov.br"


async def fetch_estacoes(client: httpx.AsyncClient) -> list[dict]:
    """Lista todas as estacoes automaticas do INMET."""
    try:
        resp = await client.get(f"{INMET_BASE}/estacoes/T", timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("inmet_estacoes_error", error=str(e))
        return []


async def fetch_dados_estacao(client: httpx.AsyncClient, data_ini: str, data_fim: str) -> list[dict]:
    """Busca dados de TODAS as estacoes para um periodo."""
    try:
        resp = await client.get(
            f"{INMET_BASE}/estacao/{data_ini}/{data_fim}",
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("inmet_dados_error", error=str(e))
        return []


def safe_decimal(val) -> Decimal | None:
    if val is None or val == "" or val == "null":
        return None
    try:
        return Decimal(str(val))
    except Exception:
        return None


async def run(db: AsyncSession):
    """Coleta dados climaticos do INMET das ultimas 24h."""
    logger.info("pipeline_inmet_start")

    ontem = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    hoje = date.today().strftime("%Y-%m-%d")

    async with httpx.AsyncClient() as client:
        dados = await fetch_dados_estacao(client, ontem, hoje)

    if not dados:
        logger.warning("pipeline_inmet_empty")
        return {"status": "empty", "saved": 0}

    saved = 0
    for d in dados:
        estacao = d.get("CD_ESTACAO")
        lat = safe_decimal(d.get("VL_LATITUDE"))
        lon = safe_decimal(d.get("VL_LONGITUDE"))
        data_str = d.get("DT_MEDICAO")

        if not estacao or not lat or not lon or not data_str:
            continue

        try:
            data_medicao = date.fromisoformat(data_str)
        except ValueError:
            continue

        registro = {
            "fonte": "INMET",
            "estacao_id": estacao,
            "latitude": lat,
            "longitude": lon,
            "data": data_medicao,
            "temp_max": safe_decimal(d.get("TEM_MAX")),
            "temp_min": safe_decimal(d.get("TEM_MIN")),
            "temp_media": safe_decimal(d.get("TEM_INS")),
            "precipitacao": safe_decimal(d.get("CHUVA")),
            "umidade_media": safe_decimal(d.get("UMD_INS")),
            "radiacao": safe_decimal(d.get("RAD_GLO")),
            "vento_medio": safe_decimal(d.get("VEN_VEL")),
        }

        stmt = pg_insert(DadoClima).values(**registro).on_conflict_do_nothing()
        await db.execute(stmt)
        saved += 1

    await db.commit()
    logger.info("pipeline_inmet_done", saved=saved)
    return {"status": "ok", "saved": saved}
