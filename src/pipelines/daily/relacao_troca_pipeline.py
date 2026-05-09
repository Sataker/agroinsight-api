"""
Pipeline diario: Calculo da relacao de troca commodity/insumo.

Quantas sacas de soja compram 1 tonelada de ureia?
Cruza precos de commodities (CEPEA) com precos de insumos (World Bank/CONAB).
"""

from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.dialects.postgresql import insert as pg_insert
import structlog

from src.models.precos import PrecoCommodity, PrecoInsumo, RelacaoTroca

logger = structlog.get_logger()

# Pares de relacao de troca a monitorar
PARES = [
    ("SOJA", "UREIA"),
    ("SOJA", "MAP"),
    ("SOJA", "KCL"),
    ("MILHO", "UREIA"),
    ("MILHO", "MAP"),
]


async def get_ultimo_preco_commodity(db: AsyncSession, commodity: str) -> Decimal | None:
    """Pega o preco mais recente de uma commodity."""
    result = await db.execute(
        select(PrecoCommodity.preco)
        .where(PrecoCommodity.commodity == commodity, PrecoCommodity.fonte == "CEPEA")
        .order_by(desc(PrecoCommodity.data))
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return Decimal(str(row)) if row else None


async def get_ultimo_preco_insumo(db: AsyncSession, insumo: str) -> Decimal | None:
    """Pega o preco mais recente de um insumo (em R$/tonelada)."""
    result = await db.execute(
        select(PrecoInsumo.preco)
        .where(PrecoInsumo.produto.ilike(f"%{insumo}%"))
        .order_by(desc(PrecoInsumo.data))
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return Decimal(str(row)) if row else None


async def get_media_historica(db: AsyncSession, commodity: str, insumo: str, anos: int = 5) -> Decimal | None:
    """Calcula a media historica da relacao de troca."""
    data_inicio = date.today() - timedelta(days=anos * 365)
    result = await db.execute(
        select(func.avg(RelacaoTroca.sacas_por_ton))
        .where(
            RelacaoTroca.commodity == commodity,
            RelacaoTroca.insumo == insumo,
            RelacaoTroca.data >= data_inicio,
        )
    )
    avg = result.scalar_one_or_none()
    return Decimal(str(avg)) if avg else None


def classificar_favorabilidade(atual: Decimal, media: Decimal | None) -> str:
    """Classifica se o momento e favoravel para comprar."""
    if media is None:
        return "NEUTRO"
    diff_pct = ((atual - media) / media) * 100
    if diff_pct <= -10:
        return "BOM"       # Precisa de menos sacas que a media = bom momento
    elif diff_pct >= 10:
        return "RUIM"      # Precisa de mais sacas que a media = momento ruim
    return "NEUTRO"


async def run(db: AsyncSession):
    """Calcula relacao de troca para todos os pares monitorados."""
    logger.info("pipeline_relacao_troca_start")

    saved = 0
    for commodity, insumo in PARES:
        preco_comm = await get_ultimo_preco_commodity(db, commodity)
        preco_ins = await get_ultimo_preco_insumo(db, insumo)

        if not preco_comm or not preco_ins or preco_comm == 0:
            logger.warning("relacao_troca_skip", commodity=commodity, insumo=insumo,
                          preco_comm=preco_comm, preco_ins=preco_ins)
            continue

        # sacas_por_ton = preco_insumo (R$/ton) / preco_commodity (R$/saca)
        sacas_por_ton = preco_ins / preco_comm

        media = await get_media_historica(db, commodity, insumo)
        favorabilidade = classificar_favorabilidade(sacas_por_ton, media)

        registro = {
            "commodity": commodity,
            "insumo": insumo,
            "data": date.today(),
            "sacas_por_ton": sacas_por_ton,
            "preco_commodity": preco_comm,
            "preco_insumo": preco_ins,
            "favorabilidade": favorabilidade,
        }

        stmt = pg_insert(RelacaoTroca).values(**registro).on_conflict_do_nothing()
        await db.execute(stmt)
        saved += 1

        logger.info("relacao_troca_calc",
                    par=f"{commodity}/{insumo}",
                    sacas=float(sacas_por_ton),
                    favorabilidade=favorabilidade)

    await db.commit()
    logger.info("pipeline_relacao_troca_done", saved=saved)
    return {"status": "ok", "saved": saved}
