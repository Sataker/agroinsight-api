"""
Pipeline diario: B3 → precos_futuros

Coleta precos de ajuste dos contratos futuros agricolas da B3.
Endpoint publico de cotacoes de fim de dia.
"""

from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
import httpx
import structlog

from src.models.precos import PrecoFuturo

logger = structlog.get_logger()

# Contratos agricolas B3
B3_COMMODITIES = {
    "SJC": "SOJA",       # Soja CME
    "CCM": "MILHO",      # Milho
    "ICF": "CAFE_ARABICA",  # Cafe Arabica
    "BGI": "BOI_GORDO",  # Boi Gordo
    "ACF": "ACUCAR",     # Acucar Cristal
    "ETH": "ETANOL",     # Etanol Hidratado
}

B3_SETTLEMENT_URL = "https://cotacao.b3.com.br/mds/api/v1/DailySettlementPrice"


async def fetch_b3_futuros(client: httpx.AsyncClient) -> list[dict]:
    """Busca precos de ajuste diario da B3."""
    registros = []

    for codigo, commodity in B3_COMMODITIES.items():
        try:
            # A B3 expoe dados via APIs diferentes dependendo da epoca
            # Fallback: tentar endpoint de Market Data
            resp = await client.get(
                f"https://cotacao.b3.com.br/mds/api/v1/DailySettlementPrice/date/{date.today().strftime('%Y-%m-%d')}",
                timeout=30,
                headers={"Accept": "application/json"},
            )

            if resp.status_code != 200:
                # Tentar endpoint alternativo
                resp = await client.get(
                    f"https://www2.bmf.com.br/pages/portal/bmfbovespa/boletim1/SissemIntercambio1.asp?txtData={date.today().strftime('%d/%m/%Y')}&txtMercadoria={codigo}",
                    timeout=30,
                )

            # Parse varia conforme o endpoint que responder
            # Por ora, estrutura para quando a API estiver disponivel
            logger.info("b3_fetch", commodity=commodity, status=resp.status_code)

        except Exception as e:
            logger.warning("b3_error", commodity=commodity, error=str(e))

    return registros


async def run(db: AsyncSession):
    """Coleta futuros agricolas da B3."""
    logger.info("pipeline_b3_start")

    async with httpx.AsyncClient() as client:
        registros = await fetch_b3_futuros(client)

    if not registros:
        logger.info("pipeline_b3_no_data", note="B3 API pode exigir ajustes no parsing")
        return {"status": "no_data", "saved": 0}

    saved = 0
    for r in registros:
        stmt = pg_insert(PrecoFuturo).values(**r).on_conflict_do_nothing()
        await db.execute(stmt)
        saved += 1

    await db.commit()
    logger.info("pipeline_b3_done", saved=saved)
    return {"status": "ok", "saved": saved}
