import uuid
from datetime import datetime, date
from sqlalchemy import String, BigInteger, Numeric, Boolean, Date, DateTime, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base


class PrecoInformado(Base):
    """Precos de insumos informados pelos produtores (crowdsourcing)"""
    __tablename__ = "precos_informados"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    categoria: Mapped[str] = mapped_column(String(30), nullable=False)   # FERTILIZANTE, DEFENSIVO, SEMENTE
    produto: Mapped[str] = mapped_column(String(100), nullable=False)
    marca: Mapped[str | None] = mapped_column(String(100))
    fornecedor: Mapped[str | None] = mapped_column(String(200))
    estado: Mapped[str] = mapped_column(String(2), nullable=False)
    municipio: Mapped[str | None] = mapped_column(String(100))
    preco: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    unidade: Mapped[str] = mapped_column(String(20), nullable=False)     # tonelada, litro, saca
    data_compra: Mapped[date] = mapped_column(Date, nullable=False)
    verificado: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_crowd", "produto", "estado", "data_compra"),
    )
