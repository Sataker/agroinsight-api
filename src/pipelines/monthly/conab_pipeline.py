"""
Pipeline mensal: CONAB → dados_safra + custos_producao

Coleta estimativas de safra e custos de producao da CONAB.
Portal de Informacoes: https://portaldeinformacoes.conab.gov.br/
"""

from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
import httpx
import structlog

from src.models.safra import DadoSafra

logger = structlog.get_logger()

CONAB_API_BASE = "https://portaldeinformacoes.conab.gov.br/api"

# Culturas principais monitoradas
CULTURAS = [
    "SOJA", "MILHO_1", "MILHO_2", "ALGODAO", "FEIJAO_1", "FEIJAO_2",
    "ARROZ", "TRIGO", "CANA_DE_ACUCAR", "CAFE_ARABICA", "CAFE_CONILON",
]


async def fetch_safra_conab(client: httpx.AsyncClient, safra: str) -> list[dict]:
    """Busca dados de safra da CONAB via Portal de Informacoes."""
    registros = []

    try:
        # Endpoint de estimativas de safra
        # A documentacao da CONAB e limitada — tentar endpoints conhecidos
        endpoints = [
            f"{CONAB_API_BASE}/safras/estimativa",
            f"{CONAB_API_BASE}/safras/serie-historica",
        ]

        for endpoint in endpoints:
            try:
                resp = await client.get(
                    endpoint,
                    params={"safra": safra},
                    timeout=30,
                    headers={"Accept": "application/json"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        for item in data:
                            registros.append({
                                "fonte": "CONAB",
                                "safra": safra,
                                "cultura": item.get("cultura", "").upper().replace(" ", "_"),
                                "estado": item.get("uf"),
                                "area_plantada_ha": Decimal(str(item["area_plantada"])) if item.get("area_plantada") else None,
                                "producao_ton": Decimal(str(item["producao"])) if item.get("producao") else None,
                                "produtividade_kg_ha": Decimal(str(item["produtividade"])) if item.get("produtividade") else None,
                                "data_referencia": date.today(),
                            })
                    break
            except Exception:
                continue

    except Exception as e:
        logger.error("conab_safra_error", error=str(e))

    return registros


async def run(db: AsyncSession):
    """Coleta dados de safra da CONAB."""
    logger.info("pipeline_conab_start")

    # Determinar safra atual (ex: 2025/26)
    ano = date.today().year
    mes = date.today().month
    safra = f"{ano}/{str(ano+1)[2:]}" if mes >= 7 else f"{ano-1}/{str(ano)[2:]}"

    async with httpx.AsyncClient() as client:
        registros = await fetch_safra_conab(client, safra)

    if not registros:
        logger.warning("pipeline_conab_empty", note="CONAB API pode precisar de ajustes")
        return {"status": "empty", "saved": 0}

    saved = 0
    for r in registros:
        stmt = pg_insert(DadoSafra).values(**r).on_conflict_do_nothing()
        await db.execute(stmt)
        saved += 1

    await db.commit()
    logger.info("pipeline_conab_done", saved=saved)
    return {"status": "ok", "saved": saved}
