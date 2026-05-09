from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from src.database import get_db
from src.models.user import User
from src.api.deps import create_access_token, get_current_user

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class RegisterRequest(BaseModel):
    email: str
    password: str
    nome: str
    whatsapp: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check existing
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email ja cadastrado")

    user = User(
        email=body.email,
        password_hash=pwd_context.hash(body.password),
        nome=body.nome,
        whatsapp=body.whatsapp,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user={"id": str(user.id), "email": user.email, "nome": user.nome, "plano": user.plano},
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not pwd_context.verify(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user={"id": str(user.id), "email": user.email, "nome": user.nome, "plano": user.plano},
    )


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "email": user.email,
        "nome": user.nome,
        "whatsapp": user.whatsapp,
        "plano": user.plano,
        "plano_expira": user.plano_expira,
    }
