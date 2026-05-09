import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database import get_db
from src.models.alerta import Alerta
from src.models.user import User
from src.api.deps import get_current_user

router = APIRouter()


class AlertaCreate(BaseModel):
    tipo: str              # PRECO_COMMODITY, PRECO_INSUMO, CLIMA, RELACAO_TROCA
    item: str              # SOJA, UREIA, PRECIPITACAO
    condicao: str          # ACIMA, ABAIXO, VARIACAO
    valor_gatilho: float
    unidade: str | None = None
    notificar_email: bool = False
    notificar_whatsapp: bool = True
    notificar_push: bool = True
    cooldown_horas: int = 24


@router.get("/")
async def listar_alertas(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alerta).where(Alerta.user_id == user.id).order_by(Alerta.created_at.desc()))
    alertas = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "tipo": a.tipo,
            "item": a.item,
            "condicao": a.condicao,
            "valor_gatilho": float(a.valor_gatilho),
            "unidade": a.unidade,
            "ativo": a.ativo,
            "notificar_whatsapp": a.notificar_whatsapp,
            "notificar_email": a.notificar_email,
            "ultimo_disparo": a.ultimo_disparo.isoformat() if a.ultimo_disparo else None,
        }
        for a in alertas
    ]


@router.post("/")
async def criar_alerta(body: AlertaCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    alerta = Alerta(
        user_id=user.id,
        tipo=body.tipo,
        item=body.item,
        condicao=body.condicao,
        valor_gatilho=body.valor_gatilho,
        unidade=body.unidade,
        notificar_email=body.notificar_email,
        notificar_whatsapp=body.notificar_whatsapp,
        notificar_push=body.notificar_push,
        cooldown_horas=body.cooldown_horas,
    )
    db.add(alerta)
    await db.commit()
    await db.refresh(alerta)
    return {"id": str(alerta.id), "tipo": alerta.tipo, "item": alerta.item}


@router.delete("/{alerta_id}")
async def deletar_alerta(alerta_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alerta).where(Alerta.id == alerta_id, Alerta.user_id == user.id))
    alerta = result.scalar_one_or_none()
    if not alerta:
        raise HTTPException(status_code=404, detail="Alerta nao encontrado")
    await db.delete(alerta)
    await db.commit()
    return {"ok": True}
