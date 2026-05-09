import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.database import get_db
from src.models.user import User
from src.models.fazenda import Fazenda, Talhao
from src.api.deps import get_current_user

router = APIRouter()


class FazendaCreate(BaseModel):
    nome: str
    estado: str
    municipio: str
    latitude: float | None = None
    longitude: float | None = None
    area_total_ha: float | None = None
    irrigada: bool = False
    safras_por_ano: float = 2.0


class TalhaoCreate(BaseModel):
    nome: str
    area_ha: float
    tipo_solo: str | None = None
    ultima_cultura: str | None = None


@router.get("/")
async def listar_fazendas(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Fazenda)
        .where(Fazenda.user_id == user.id)
        .options(selectinload(Fazenda.talhoes))
    )
    fazendas = result.scalars().all()
    return [
        {
            "id": str(f.id),
            "nome": f.nome,
            "estado": f.estado,
            "municipio": f.municipio,
            "latitude": float(f.latitude) if f.latitude else None,
            "longitude": float(f.longitude) if f.longitude else None,
            "area_total_ha": float(f.area_total_ha) if f.area_total_ha else None,
            "irrigada": f.irrigada,
            "safras_por_ano": float(f.safras_por_ano),
            "micro_regiao_id": f.micro_regiao_id,
            "talhoes": [
                {
                    "id": str(t.id),
                    "nome": t.nome,
                    "area_ha": float(t.area_ha),
                    "tipo_solo": t.tipo_solo,
                    "ultima_cultura": t.ultima_cultura,
                }
                for t in f.talhoes
            ],
        }
        for f in fazendas
    ]


@router.post("/")
async def criar_fazenda(body: FazendaCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    fazenda = Fazenda(
        user_id=user.id,
        nome=body.nome,
        estado=body.estado,
        municipio=body.municipio,
        latitude=body.latitude,
        longitude=body.longitude,
        area_total_ha=body.area_total_ha,
        irrigada=body.irrigada,
        safras_por_ano=body.safras_por_ano,
    )
    # TODO: auto-map micro_regiao_id based on lat/lon
    db.add(fazenda)
    await db.commit()
    await db.refresh(fazenda)
    return {"id": str(fazenda.id), "nome": fazenda.nome}


@router.post("/{fazenda_id}/talhoes")
async def criar_talhao(
    fazenda_id: uuid.UUID,
    body: TalhaoCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify ownership
    result = await db.execute(select(Fazenda).where(Fazenda.id == fazenda_id, Fazenda.user_id == user.id))
    fazenda = result.scalar_one_or_none()
    if not fazenda:
        raise HTTPException(status_code=404, detail="Fazenda nao encontrada")

    talhao = Talhao(
        fazenda_id=fazenda_id,
        nome=body.nome,
        area_ha=body.area_ha,
        tipo_solo=body.tipo_solo,
        ultima_cultura=body.ultima_cultura,
    )
    db.add(talhao)
    await db.commit()
    await db.refresh(talhao)
    return {"id": str(talhao.id), "nome": talhao.nome}
