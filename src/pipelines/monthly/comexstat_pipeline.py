"""
Pipeline mensal: COMEX STAT API → importacoes_fertilizantes

Dados de importacao de fertilizantes do Brasil — proxy para tendencia de precos.
API publica: https://api-comexstat.mdic.gov.br/
"""

from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
import httpx
import structlog

from src.models.precos import ImportacaoFertilizante

logger = structlog.get_logger()

COMEXSTAT_URL = "https://api-comexstat.mdic.gov.br/general"

# NCMs de fertilizantes
NCM_FERTILIZANTES = {
    "31021000": "UREIA",
    "31031010": "SUPERFOSFATO_SIMPLES",
    "31031090": "SUPERFOSFATO_TRIPLO",
    "31042010": "KCL",          # Cloreto de potassio
    "31053000": "MAP",          # Fosfato monoamonico
    "31054000": "DAP",          # Fosfato diamonico
}


async def fetch_comexstat(client: httpx.AsyncClient, ano: int, mes: int) -> list[dict]:
    """Busca dados de importacao de fertilizantes do COMEX STAT."""
    registros = []

    for ncm, produto in NCM_FERTILIZANTES.items():
        try:
            # COMEX STAT API — filtrar por NCM + tipo (importacao)
            payload = {
                "type": "import",
                "flow": "general",
                "monthDetail": True,
                "period": {
                    "from": f"{ano}-{mes:02d}",
                    "to": f"{ano}-{mes:02d}",
                },
                "filters": [
                    {"filter": "ncm", "values": [ncm]},
                ],
                "details": [
                    {"detail": "country"},
                ],
                "metrics": ["metricFOB", "metricKG"],
            }

            resp = await client.post(
                COMEXSTAT_URL,
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"},
            )

            if resp.status_code != 200:
                logger.warning("comexstat_http", ncm=ncm, status=resp.status_code)
                continue

            data = resp.json()
            items = data.get("data", [])

            for item in items:
                peso = item.get("metricKG", 0)
                valor = item.get("metricFOB", 0)
                pais = item.get("noCountry", "")

                if peso and peso > 0:
                    preco_ton = (valor / peso) * 1000 if peso > 0 else None
                else:
                    preco_ton = None

                registros.append({
                    "ncm": ncm,
                    "produto": produto,
                    "pais_origem": pais,
                    "mes": date(ano, mes, 1),
                    "peso_kg": int(peso) if peso else None,
                    "valor_fob_usd": Decimal(str(round(valor, 2))) if valor else None,
                    "preco_ton_usd": Decimal(str(round(preco_ton, 2))) if preco_ton else None,
                })

        except Exception as e:
            logger.warning("comexstat_error", ncm=ncm, error=str(e))

    return registros


async def run(db: AsyncSession):
    """Coleta dados de importacao de fertilizantes."""
    logger.info("pipeline_comexstat_start")

    # Buscar dados do mes anterior (COMEX STAT tem ~2 meses de defasagem)
    hoje = date.today()
    if hoje.month <= 2:
        ano, mes = hoje.year - 1, hoje.month + 10
    else:
        ano, mes = hoje.year, hoje.month - 2

    async with httpx.AsyncClient() as client:
        registros = await fetch_comexstat(client, ano, mes)

    if not registros:
        logger.warning("pipeline_comexstat_empty")
        return {"status": "empty", "saved": 0}

    saved = 0
    for r in registros:
        stmt = pg_insert(ImportacaoFertilizante).values(**r).on_conflict_do_nothing()
        await db.execute(stmt)
        saved += 1

    await db.commit()
    logger.info("pipeline_comexstat_done", saved=saved)
    return {"status": "ok", "saved": saved}
