from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from src.database import get_db
from src.models.precos import PrecoCommodity, PrecoFuturo, RelacaoTroca
from src.api.deps import get_current_user
from src.models.user import User

router = APIRouter()


@router.get("/commodities")
async def listar_precos_commodities(
    commodity: str | None = None,
    dias: int = Query(default=30, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Precos de commodities (CEPEA, CONAB). Filtrar por commodity e periodo."""
    data_inicio = date.today() - timedelta(days=dias)
    query = select(PrecoCommodity).where(PrecoCommodity.data >= data_inicio)

    if commodity:
        query = query.where(PrecoCommodity.commodity == commodity.upper())

    query = query.order_by(desc(PrecoCommodity.data)).limit(500)
    result = await db.execute(query)
    precos = result.scalars().all()

    return [
        {
            "id": p.id,
            "fonte": p.fonte,
            "commodity": p.commodity,
            "praca": p.praca,
            "data": p.data.isoformat(),
            "preco": float(p.preco),
            "unidade": p.unidade,
            "variacao_dia": float(p.variacao_dia) if p.variacao_dia else None,
        }
        for p in precos
    ]


@router.get("/futuros")
async def listar_futuros(
    commodity: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Precos de futuros B3/CME. Mostra contratos ativos."""
    query = (
        select(PrecoFuturo)
        .where(PrecoFuturo.vencimento >= date.today())
        .order_by(PrecoFuturo.commodity, PrecoFuturo.vencimento, desc(PrecoFuturo.data))
    )

    if commodity:
        query = query.where(PrecoFuturo.commodity == commodity.upper())

    result = await db.execute(query.limit(200))
    futuros = result.scalars().all()

    return [
        {
            "id": f.id,
            "bolsa": f.bolsa,
            "contrato": f.contrato,
            "commodity": f.commodity,
            "vencimento": f.vencimento.isoformat(),
            "data": f.data.isoformat(),
            "preco_ajuste": float(f.preco_ajuste),
            "volume": f.volume,
        }
        for f in futuros
    ]


@router.get("/relacao-troca")
async def listar_relacao_troca(
    commodity: str = Query(default="SOJA"),
    insumo: str = Query(default="UREIA"),
    dias: int = Query(default=365, le=1825),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Relacao de troca: quantas sacas de commodity compram 1 ton do insumo."""
    data_inicio = date.today() - timedelta(days=dias)
    query = (
        select(RelacaoTroca)
        .where(
            RelacaoTroca.commodity == commodity.upper(),
            RelacaoTroca.insumo == insumo.upper(),
            RelacaoTroca.data >= data_inicio,
        )
        .order_by(desc(RelacaoTroca.data))
        .limit(500)
    )
    result = await db.execute(query)
    registros = result.scalars().all()

    return [
        {
            "data": r.data.isoformat(),
            "sacas_por_ton": float(r.sacas_por_ton),
            "preco_commodity": float(r.preco_commodity) if r.preco_commodity else None,
            "preco_insumo": float(r.preco_insumo) if r.preco_insumo else None,
            "favorabilidade": r.favorabilidade,
        }
        for r in registros
    ]
