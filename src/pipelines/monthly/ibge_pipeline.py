"""
Pipeline mensal: IBGE SIDRA API → dados_safra

LSPA (Levantamento Sistematico da Producao Agricola) — estimativas mensais.
API 100% publica, sem autenticacao.
https://apisidra.ibge.gov.br/
"""

from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
import httpx
import structlog

from src.models.safra import DadoSafra

logger = structlog.get_logger()

SIDRA_BASE = "https://apisidra.ibge.gov.br/values"

# Tabela 6588 = LSPA (area plantada, area colhida, producao, rendimento)
# n3 = nivel UF, p = ultimo periodo
LSPA_TABLE = "6588"

# Codigos de produto IBGE
PRODUTOS_IBGE = {
    "39443": "SOJA",
    "39441": "MILHO_1",
    "39442": "MILHO_2",
    "39432": "ALGODAO",
    "39446": "ARROZ",
    "39439": "FEIJAO_1",
    "39438": "TRIGO",
    "39436": "CANA_DE_ACUCAR",
    "39448": "CAFE_ARABICA",
}


async def fetch_lspa(client: httpx.AsyncClient) -> list[dict]:
    """Busca LSPA do IBGE via API SIDRA."""
    registros = []

    try:
        # Tabela 6588: LSPA
        # v/109 = area plantada, v/216 = area colhida, v/214 = producao, v/112 = rendimento
        # n3/all = todos os estados
        # p/last = ultimo periodo
        url = f"{SIDRA_BASE}/t/{LSPA_TABLE}/n3/all/v/109,216,214,112/p/last%201/c48/39441,39442,39443,39432,39446,39439,39438,39436,39448"

        resp = await client.get(url, timeout=60, headers={"Accept": "application/json"})
        resp.raise_for_status()
        data = resp.json()

        if not data or len(data) <= 1:
            return registros

        # Primeira linha e header
        headers_row = data[0]
        for row in data[1:]:
            try:
                cultura_cod = row.get("D3C")
                cultura = PRODUTOS_IBGE.get(cultura_cod, cultura_cod)
                estado = row.get("D1C", "")[:2] if row.get("D1C") else None
                variavel = row.get("D2C")
                valor = row.get("V")

                if not valor or valor == "..." or valor == "-" or valor == "X":
                    continue

                # Montar registro baseado na variavel
                # Vamos agregar por cultura+estado+periodo
                registros.append({
                    "fonte": "IBGE",
                    "safra": row.get("D4N", ""),
                    "cultura": cultura,
                    "estado": estado,
                    "variavel": variavel,  # 109=area_plantada, 216=area_colhida, 214=producao, 112=rendimento
                    "valor": Decimal(str(valor).replace(".", "").replace(",", ".")),
                    "data_referencia": date.today(),
                })
            except Exception as e:
                logger.warning("ibge_parse_error", error=str(e))

    except Exception as e:
        logger.error("ibge_lspa_error", error=str(e))

    return registros


async def run(db: AsyncSession):
    """Coleta LSPA do IBGE."""
    logger.info("pipeline_ibge_start")

    async with httpx.AsyncClient() as client:
        registros = await fetch_lspa(client)

    if not registros:
        logger.warning("pipeline_ibge_empty")
        return {"status": "empty", "saved": 0}

    # Agregar por cultura+estado — transformar variaveis em colunas
    aggregated: dict[str, dict] = {}
    for r in registros:
        key = f"{r['cultura']}_{r['estado']}_{r['safra']}"
        if key not in aggregated:
            aggregated[key] = {
                "fonte": "IBGE",
                "safra": r["safra"],
                "cultura": r["cultura"],
                "estado": r["estado"],
                "data_referencia": r["data_referencia"],
            }

        variavel = r["variavel"]
        if variavel == "109":
            aggregated[key]["area_plantada_ha"] = r["valor"]
        elif variavel == "216":
            aggregated[key]["area_colhida_ha"] = r["valor"]
        elif variavel == "214":
            aggregated[key]["producao_ton"] = r["valor"]
        elif variavel == "112":
            aggregated[key]["produtividade_kg_ha"] = r["valor"]

    saved = 0
    for registro in aggregated.values():
        stmt = pg_insert(DadoSafra).values(**registro).on_conflict_do_nothing()
        await db.execute(stmt)
        saved += 1

    await db.commit()
    logger.info("pipeline_ibge_done", saved=saved)
    return {"status": "ok", "saved": saved}
