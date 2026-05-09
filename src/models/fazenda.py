import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Numeric, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base


class Fazenda(Base):
    __tablename__ = "fazendas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[str] = mapped_column(String(2), nullable=False)
    municipio: Mapped[str] = mapped_column(String(255), nullable=False)
    micro_regiao_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("micro_regioes.id"))
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    area_total_ha: Mapped[float | None] = mapped_column(Numeric(12, 2))
    irrigada: Mapped[bool] = mapped_column(Boolean, default=False)
    safras_por_ano: Mapped[float] = mapped_column(Numeric(3, 1), default=2.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="fazendas")
    micro_regiao = relationship("MicroRegiao", back_populates="fazendas")
    talhoes = relationship("Talhao", back_populates="fazenda", cascade="all, delete-orphan")


class Talhao(Base):
    __tablename__ = "talhoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fazenda_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("fazendas.id", ondelete="CASCADE"), nullable=False)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    area_ha: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    tipo_solo: Mapped[str | None] = mapped_column(String(50))
    ultima_cultura: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    fazenda = relationship("Fazenda", back_populates="talhoes")
