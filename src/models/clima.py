from datetime import datetime, date
from sqlalchemy import String, BigInteger, Numeric, Date, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base


class DadoClima(Base):
    __tablename__ = "dados_clima"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fonte: Mapped[str] = mapped_column(String(20), nullable=False)       # INMET, NASA_POWER
    estacao_id: Mapped[str | None] = mapped_column(String(20))
    latitude: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    temp_max: Mapped[float | None] = mapped_column(Numeric(5, 2))
    temp_min: Mapped[float | None] = mapped_column(Numeric(5, 2))
    temp_media: Mapped[float | None] = mapped_column(Numeric(5, 2))
    precipitacao: Mapped[float | None] = mapped_column(Numeric(8, 2))    # mm
    umidade_media: Mapped[float | None] = mapped_column(Numeric(5, 2))   # %
    radiacao: Mapped[float | None] = mapped_column(Numeric(8, 2))        # MJ/m2/dia
    vento_medio: Mapped[float | None] = mapped_column(Numeric(5, 2))     # m/s
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_clima", "latitude", "longitude", "data"),
        Index("idx_clima_estacao", "estacao_id", "data"),
    )


class PrevisaoClima(Base):
    __tablename__ = "previsao_clima"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fonte: Mapped[str] = mapped_column(String(20), nullable=False)
    latitude: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    data_previsao: Mapped[date] = mapped_column(Date, nullable=False)
    data_emissao: Mapped[date] = mapped_column(Date, nullable=False)
    temp_max: Mapped[float | None] = mapped_column(Numeric(5, 2))
    temp_min: Mapped[float | None] = mapped_column(Numeric(5, 2))
    precipitacao: Mapped[float | None] = mapped_column(Numeric(8, 2))
    prob_chuva: Mapped[float | None] = mapped_column(Numeric(5, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
