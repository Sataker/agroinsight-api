from datetime import datetime, date
from sqlalchemy import String, Integer, BigInteger, Numeric, Date, DateTime, func, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base


class PrecoCommodity(Base):
    __tablename__ = "precos_commodities"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fonte: Mapped[str] = mapped_column(String(20), nullable=False)       # CEPEA, B3, CONAB
    commodity: Mapped[str] = mapped_column(String(50), nullable=False)   # SOJA, MILHO, CAFE_ARABICA
    praca: Mapped[str | None] = mapped_column(String(100))               # Paranagua, Campinas/SP
    data: Mapped[date] = mapped_column(Date, nullable=False)
    preco: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    unidade: Mapped[str] = mapped_column(String(20), nullable=False)     # saca_60kg, arroba, tonelada
    variacao_dia: Mapped[float | None] = mapped_column(Numeric(8, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("fonte", "commodity", "praca", "data", name="uq_precos_comm"),
        Index("idx_precos_comm", "commodity", "data"),
    )


class PrecoFuturo(Base):
    __tablename__ = "precos_futuros"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    bolsa: Mapped[str] = mapped_column(String(10), nullable=False)       # B3, CME
    contrato: Mapped[str] = mapped_column(String(20), nullable=False)    # SJCN26
    commodity: Mapped[str] = mapped_column(String(50), nullable=False)
    vencimento: Mapped[date] = mapped_column(Date, nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    preco_ajuste: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    volume: Mapped[int | None] = mapped_column(Integer)
    contratos_abertos: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_futuros", "commodity", "data"),
    )


class PrecoInsumo(Base):
    __tablename__ = "precos_insumos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fonte: Mapped[str] = mapped_column(String(30), nullable=False)       # CONAB, WORLD_BANK, CROWDSOURCE
    categoria: Mapped[str] = mapped_column(String(30), nullable=False)   # FERTILIZANTE, DEFENSIVO, SEMENTE
    produto: Mapped[str] = mapped_column(String(100), nullable=False)    # Ureia, MAP, KCl
    estado: Mapped[str | None] = mapped_column(String(2))
    data: Mapped[date] = mapped_column(Date, nullable=False)
    preco: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    unidade: Mapped[str] = mapped_column(String(20), nullable=False)     # tonelada, litro, kg
    moeda: Mapped[str] = mapped_column(String(3), default="BRL")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_precos_ins", "produto", "data"),
        Index("idx_precos_ins_cat", "categoria", "data"),
    )


class ImportacaoFertilizante(Base):
    __tablename__ = "importacoes_fertilizantes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ncm: Mapped[str] = mapped_column(String(10), nullable=False)
    produto: Mapped[str] = mapped_column(String(100), nullable=False)
    pais_origem: Mapped[str | None] = mapped_column(String(100))
    mes: Mapped[date] = mapped_column(Date, nullable=False)
    peso_kg: Mapped[int | None] = mapped_column(BigInteger)
    valor_fob_usd: Mapped[float | None] = mapped_column(Numeric(14, 2))
    preco_ton_usd: Mapped[float | None] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_import_fert", "produto", "mes"),
    )


class RelacaoTroca(Base):
    __tablename__ = "relacao_troca"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    commodity: Mapped[str] = mapped_column(String(50), nullable=False)   # SOJA, MILHO
    insumo: Mapped[str] = mapped_column(String(100), nullable=False)     # UREIA, MAP, KCL
    data: Mapped[date] = mapped_column(Date, nullable=False)
    sacas_por_ton: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    preco_commodity: Mapped[float | None] = mapped_column(Numeric(12, 4))
    preco_insumo: Mapped[float | None] = mapped_column(Numeric(12, 4))
    favorabilidade: Mapped[str | None] = mapped_column(String(20))       # BOM, NEUTRO, RUIM
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_troca", "commodity", "insumo", "data"),
    )
