"""
Pipeline diario: CEPEA → precos_commodities

Roda todo dia as 06:00 BRT. Scrape os indicadores do CEPEA,
salva no banco e dispara alertas se necessario.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from src.scrapers.cepea import scrape_all_commodities
from src.models.precos import PrecoCommodity
import structlog

logger = structlog.get_logger()


async def run(db: AsyncSession):
    """Executa pipeline CEPEA: scrape → salvar → verificar alertas."""
    logger.info("pipeline_cepea_start")

    registros = await scrape_all_commodities()
    if not registros:
        logger.warning("pipeline_cepea_empty")
        return {"status": "empty", "saved": 0}

    saved = 0
    for r in registros:
        # Upsert: se ja existe (fonte+commodity+praca+data), atualiza preco
        stmt = pg_insert(PrecoCommodity).values(
            fonte=r["fonte"],
            commodity=r["commodity"],
            praca=r["praca"],
            data=r["data"],
            preco=r["preco"],
            unidade=r["unidade"],
            variacao_dia=r["variacao_dia"],
        ).on_conflict_do_update(
            constraint="uq_precos_comm",
            set_={
                "preco": r["preco"],
                "variacao_dia": r["variacao_dia"],
            },
        )
        await db.execute(stmt)
        saved += 1

    await db.commit()
    logger.info("pipeline_cepea_done", saved=saved)
    return {"status": "ok", "saved": saved}
