from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from src.database import get_db
from src.models.clima import DadoClima, PrevisaoClima
from src.api.deps import get_current_user
from src.models.user import User

router = APIRouter()


@router.get("/historico")
async def clima_historico(
    latitude: float = Query(...),
    longitude: float = Query(...),
    dias: int = Query(default=90, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Historico de clima para uma coordenada (estacao INMET ou NASA POWER mais proxima)."""
    data_inicio = date.today() - timedelta(days=dias)
    # Busca por proximidade (tolerancia de ~0.5 grau = ~55km)
    tolerancia = 0.5
    query = (
        select(DadoClima)
        .where(
            DadoClima.latitude.between(latitude - tolerancia, latitude + tolerancia),
            DadoClima.longitude.between(longitude - tolerancia, longitude + tolerancia),
            DadoClima.data >= data_inicio,
        )
        .order_by(desc(DadoClima.data))
        .limit(500)
    )
    result = await db.execute(query)
    dados = result.scalars().all()

    return [
        {
            "fonte": d.fonte,
            "data": d.data.isoformat(),
            "temp_max": float(d.temp_max) if d.temp_max else None,
            "temp_min": float(d.temp_min) if d.temp_min else None,
            "temp_media": float(d.temp_media) if d.temp_media else None,
            "precipitacao": float(d.precipitacao) if d.precipitacao else None,
            "umidade_media": float(d.umidade_media) if d.umidade_media else None,
        }
        for d in dados
    ]


@router.get("/previsao")
async def clima_previsao(
    latitude: float = Query(...),
    longitude: float = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Previsao de clima para os proximos 14 dias."""
    tolerancia = 0.3
    query = (
        select(PrevisaoClima)
        .where(
            PrevisaoClima.latitude.between(latitude - tolerancia, latitude + tolerancia),
            PrevisaoClima.longitude.between(longitude - tolerancia, longitude + tolerancia),
            PrevisaoClima.data_previsao >= date.today(),
        )
        .order_by(PrevisaoClima.data_previsao)
        .limit(14)
    )
    result = await db.execute(query)
    previsoes = result.scalars().all()

    return [
        {
            "data": p.data_previsao.isoformat(),
            "temp_max": float(p.temp_max) if p.temp_max else None,
            "temp_min": float(p.temp_min) if p.temp_min else None,
            "precipitacao": float(p.precipitacao) if p.precipitacao else None,
            "prob_chuva": float(p.prob_chuva) if p.prob_chuva else None,
        }
        for p in previsoes
    ]
