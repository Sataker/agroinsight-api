import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    whatsapp: Mapped[str | None] = mapped_column(String(20))
    plano: Mapped[str] = mapped_column(String(20), default="TRIAL")  # TRIAL, BASICO, PRO, ENTERPRISE
    plano_expira: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    fazendas = relationship("Fazenda", back_populates="user", cascade="all, delete-orphan")
    alertas = relationship("Alerta", back_populates="user", cascade="all, delete-orphan")
    recomendacoes = relationship("Recomendacao", back_populates="user", cascade="all, delete-orphan")
