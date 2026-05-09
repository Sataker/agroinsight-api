from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from src.database import get_db
from src.models.recomendacao import Recomendacao, EventoMercado
from src.models.user import User
from src.api.deps import get_current_user

router = APIRouter()


@router.get("/")
async def listar_recomendacoes(
    tipo: str | None = None,
    apenas_nao_lidas: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Recomendacoes da IA para o produtor."""
    query = select(Recomendacao).where(Recomendacao.user_id == user.id)

    if tipo:
        query = query.where(Recomendacao.tipo == tipo.upper())
    if apenas_nao_lidas:
        query = query.where(Recomendacao.lida == False)

    query = query.order_by(desc(Recomendacao.created_at)).limit(50)
    result = await db.execute(query)
    recs = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "tipo": r.tipo,
            "prioridade": r.prioridade,
            "titulo": r.titulo,
            "descricao": r.descricao,
            "acao_sugerida": r.acao_sugerida,
            "confianca": float(r.confianca) if r.confianca else None,
            "lida": r.lida,
            "validade": r.validade.isoformat() if r.validade else None,
            "created_at": r.created_at.isoformat(),
        }
        for r in recs
    ]


@router.get("/eventos")
async def listar_eventos_mercado(
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Eventos de mercado recentes com analise de impacto da IA."""
    query = (
        select(EventoMercado)
        .where(EventoMercado.ativo == True)
        .order_by(desc(EventoMercado.data_evento))
        .limit(limit)
    )
    result = await db.execute(query)
    eventos = result.scalars().all()

    return [
        {
            "id": e.id,
            "tipo": e.tipo,
            "titulo": e.titulo,
            "descricao": e.descricao,
            "pais_origem": e.pais_origem,
            "data_evento": e.data_evento.isoformat(),
            "commodities_afetadas": e.commodities_afetadas,
            "direcao_impacto": e.direcao_impacto,
            "magnitude_impacto": e.magnitude_impacto,
            "analise_ia": e.analise_ia,
        }
        for e in eventos
    ]
