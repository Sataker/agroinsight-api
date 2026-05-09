from datetime import datetime
from sqlalchemy import String, Integer, BigInteger, Boolean, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base


class Comprador(Base):
    __tablename__ = "compradores"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[str | None] = mapped_column(String(30))                 # COOPERATIVA, CEREALISTA, INDUSTRIA, TRADING
    culturas: Mapped[str | None] = mapped_column(String(255))            # "SOJA,MILHO,GRAO_DE_BICO"
    estado: Mapped[str] = mapped_column(String(2), nullable=False)
    municipio: Mapped[str | None] = mapped_column(String(255))
    micro_regiao_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("micro_regioes.id"))
    telefone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    website: Mapped[str | None] = mapped_column(String(500))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    fonte: Mapped[str | None] = mapped_column(String(50))                # CROWDSOURCE, CADASTRO, COOPERATIVA
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_compradores", "micro_regiao_id"),
    )
