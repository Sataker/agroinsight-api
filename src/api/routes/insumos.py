from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from src.database import get_db
from src.models.precos import PrecoInsumo, ImportacaoFertilizante
from src.api.deps import get_current_user
from src.models.user import User

router = APIRouter()


@router.get("/precos")
async def listar_precos_insumos(
    categoria: str | None = None,
    produto: str | None = None,
    dias: int = Query(default=180, le=1825),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Precos de insumos (CONAB, World Bank, crowdsourcing)."""
    data_inicio = date.today() - timedelta(days=dias)
    query = select(PrecoInsumo).where(PrecoInsumo.data >= data_inicio)

    if categoria:
        query = query.where(PrecoInsumo.categoria == categoria.upper())
    if produto:
        query = query.where(PrecoInsumo.produto.ilike(f"%{produto}%"))

    query = query.order_by(desc(PrecoInsumo.data)).limit(500)
    result = await db.execute(query)
    precos = result.scalars().all()

    return [
        {
            "id": p.id,
            "fonte": p.fonte,
            "categoria": p.categoria,
            "produto": p.produto,
            "estado": p.estado,
            "data": p.data.isoformat(),
            "preco": float(p.preco),
            "unidade": p.unidade,
            "moeda": p.moeda,
        }
        for p in precos
    ]


@router.get("/importacoes")
async def listar_importacoes(
    produto: str | None = None,
    meses: int = Query(default=12, le=60),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Importacoes de fertilizantes (COMEX STAT) — proxy para tendencia de precos."""
    data_inicio = date.today() - timedelta(days=meses * 30)
    query = select(ImportacaoFertilizante).where(ImportacaoFertilizante.mes >= data_inicio)

    if produto:
        query = query.where(ImportacaoFertilizante.produto.ilike(f"%{produto}%"))

    query = query.order_by(desc(ImportacaoFertilizante.mes)).limit(200)
    result = await db.execute(query)
    imports = result.scalars().all()

    return [
        {
            "produto": i.produto,
            "pais_origem": i.pais_origem,
            "mes": i.mes.isoformat(),
            "peso_kg": i.peso_kg,
            "valor_fob_usd": float(i.valor_fob_usd) if i.valor_fob_usd else None,
            "preco_ton_usd": float(i.preco_ton_usd) if i.preco_ton_usd else None,
        }
        for i in imports
    ]
