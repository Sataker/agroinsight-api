"""
Pipeline mensal: World Bank Commodity Prices → precos_insumos

Precos internacionais de fertilizantes (ureia, DAP, TSP, KCl).
API publica, sem autenticacao.
https://www.worldbank.org/en/research/commodity-markets
"""

from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
import httpx
import structlog

from src.models.precos import PrecoInsumo

logger = structlog.get_logger()

# World Bank Commodity Price API
# Pink Sheet data — monthly commodity prices
WB_URL = "https://api.worldbank.org/v2/country/WLD/indicator"

# Fertilizer price indicators
FERTILIZER_INDICATORS = {
    "COMMODITY.FERT.UREA": {"produto": "UREIA", "categoria": "FERTILIZANTE"},
    "COMMODITY.FERT.DAP": {"produto": "DAP", "categoria": "FERTILIZANTE"},
    "COMMODITY.FERT.TSP": {"produto": "TSP", "categoria": "FERTILIZANTE"},
    "COMMODITY.FERT.POTASH": {"produto": "KCL", "categoria": "FERTILIZANTE"},
}

# Alternativa: Pink Sheet CSV direto
PINK_SHEET_URL = "https://thedocs.worldbank.org/en/doc/5d903e848db1d1b83e0ec8f744e55570-0350012021/related/CMO-Historical-Data-Monthly.xlsx"


async def fetch_worldbank_prices(client: httpx.AsyncClient) -> list[dict]:
    """Busca precos de fertilizantes do World Bank."""
    registros = []

    for indicator, config in FERTILIZER_INDICATORS.items():
        try:
            resp = await client.get(
                f"{WB_URL}/{indicator}",
                params={
                    "date": f"{date.today().year - 1}:{date.today().year}",
                    "format": "json",
                    "per_page": 24,
                },
                timeout=30,
            )

            if resp.status_code != 200:
                continue

            data = resp.json()
            if not data or len(data) < 2:
                continue

            entries = data[1] if len(data) > 1 else []
            for entry in entries:
                valor = entry.get("value")
                data_str = entry.get("date")

                if valor is None or data_str is None:
                    continue

                # date format: "2026M01" ou "2026"
                try:
                    if "M" in str(data_str):
                        parts = str(data_str).split("M")
                        data_date = date(int(parts[0]), int(parts[1]), 1)
                    else:
                        data_date = date(int(data_str), 1, 1)
                except ValueError:
                    continue

                registros.append({
                    "fonte": "WORLD_BANK",
                    "categoria": config["categoria"],
                    "produto": config["produto"],
                    "estado": None,
                    "data": data_date,
                    "preco": Decimal(str(round(float(valor), 2))),
                    "unidade": "tonelada",
                    "moeda": "USD",
                })

        except Exception as e:
            logger.warning("worldbank_error", indicator=indicator, error=str(e))

    return registros


async def run(db: AsyncSession):
    """Coleta precos de fertilizantes do World Bank."""
    logger.info("pipeline_worldbank_start")

    async with httpx.AsyncClient() as client:
        registros = await fetch_worldbank_prices(client)

    if not registros:
        logger.warning("pipeline_worldbank_empty")
        return {"status": "empty", "saved": 0}

    saved = 0
    for r in registros:
        stmt = pg_insert(PrecoInsumo).values(**r).on_conflict_do_nothing()
        await db.execute(stmt)
        saved += 1

    await db.commit()
    logger.info("pipeline_worldbank_done", saved=saved)
    return {"status": "ok", "saved": saved}
