from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from src.database import get_db
from src.models.safra import DadoSafra
from src.api.deps import get_current_user
from src.models.user import User

router = APIRouter()


@router.get("/dados")
async def listar_dados_safra(
    cultura: str | None = None,
    estado: str | None = None,
    safra: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Dados de safra (CONAB, IBGE) — area plantada, producao, produtividade."""
    query = select(DadoSafra)

    if cultura:
        query = query.where(DadoSafra.cultura == cultura.upper())
    if estado:
        query = query.where(DadoSafra.estado == estado.upper())
    if safra:
        query = query.where(DadoSafra.safra == safra)

    query = query.order_by(desc(DadoSafra.data_referencia)).limit(500)
    result = await db.execute(query)
    dados = result.scalars().all()

    return [
        {
            "fonte": d.fonte,
            "safra": d.safra,
            "cultura": d.cultura,
            "estado": d.estado,
            "area_plantada_ha": float(d.area_plantada_ha) if d.area_plantada_ha else None,
            "producao_ton": float(d.producao_ton) if d.producao_ton else None,
            "produtividade_kg_ha": float(d.produtividade_kg_ha) if d.produtividade_kg_ha else None,
            "levantamento": d.levantamento,
            "data_referencia": d.data_referencia.isoformat() if d.data_referencia else None,
        }
        for d in dados
    ]
