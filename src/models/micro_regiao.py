from datetime import datetime
from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base


class MicroRegiao(Base):
    __tablename__ = "micro_regioes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo_ibge: Mapped[str | None] = mapped_column(String(10), unique=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[str] = mapped_column(String(2), nullable=False)
    latitude_centro: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude_centro: Mapped[float | None] = mapped_column(Numeric(10, 7))
    clima_predominante: Mapped[str | None] = mapped_column(String(50))  # TROPICAL, SUBTROPICAL, SEMIARIDO
    solo_predominante: Mapped[str | None] = mapped_column(String(50))   # ARGILOSO, ARENOSO, LATOSSOLO
    risco_geada: Mapped[str | None] = mapped_column(String(10))         # ALTO, MEDIO, BAIXO, NENHUM
    culturas_principais: Mapped[str | None] = mapped_column(String(255))  # "SOJA,MILHO,CANA"
    altitude_media: Mapped[int | None] = mapped_column(Integer)
    pluviometria_anual_mm: Mapped[int | None] = mapped_column(Integer)
    estacao_inmet_ref: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    fazendas = relationship("Fazenda", back_populates="micro_regiao")


class MicroRegiaoSimilar(Base):
    __tablename__ = "micro_regioes_similares"

    micro_regiao_id: Mapped[int] = mapped_column(Integer, ForeignKey("micro_regioes.id"), primary_key=True)
    similar_id: Mapped[int] = mapped_column(Integer, ForeignKey("micro_regioes.id"), primary_key=True)
    score_similaridade: Mapped[float] = mapped_column(Numeric(5, 3))
    # fatores stored as JSON string for simplicity
    fatores: Mapped[str | None] = mapped_column(String(500))
