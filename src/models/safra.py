import uuid
from datetime import datetime, date
from sqlalchemy import String, Integer, BigInteger, Numeric, Text, Date, DateTime, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base


class DadoSafra(Base):
    __tablename__ = "dados_safra"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fonte: Mapped[str] = mapped_column(String(10), nullable=False)       # CONAB, IBGE
    safra: Mapped[str] = mapped_column(String(20), nullable=False)       # 2025/26
    cultura: Mapped[str] = mapped_column(String(50), nullable=False)     # SOJA, MILHO_1, MILHO_2
    estado: Mapped[str | None] = mapped_column(String(2))
    municipio_ibge: Mapped[str | None] = mapped_column(String(7))
    area_plantada_ha: Mapped[float | None] = mapped_column(Numeric(14, 2))
    area_colhida_ha: Mapped[float | None] = mapped_column(Numeric(14, 2))
    producao_ton: Mapped[float | None] = mapped_column(Numeric(14, 2))
    produtividade_kg_ha: Mapped[float | None] = mapped_column(Numeric(10, 2))
    levantamento: Mapped[int | None] = mapped_column(Integer)
    data_referencia: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_safra", "cultura", "safra", "estado"),
    )


class CustoProducao(Base):
    __tablename__ = "custos_producao"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    safra: Mapped[str] = mapped_column(String(20), nullable=False)
    cultura: Mapped[str] = mapped_column(String(50), nullable=False)
    estado: Mapped[str] = mapped_column(String(2), nullable=False)
    municipio: Mapped[str | None] = mapped_column(String(100))
    componente: Mapped[str] = mapped_column(String(100), nullable=False)  # Ureia, MAP, Glifosato
    categoria: Mapped[str] = mapped_column(String(50), nullable=False)    # FERTILIZANTE, DEFENSIVO
    valor_por_ha: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    quantidade_por_ha: Mapped[float | None] = mapped_column(Numeric(10, 4))
    unidade: Mapped[str | None] = mapped_column(String(20))
    preco_unitario: Mapped[float | None] = mapped_column(Numeric(10, 4))
    custo_total_ha: Mapped[float | None] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_custos", "cultura", "safra", "estado"),
    )


class HistoricoSafra(Base):
    """Historico informado pelo produtor — o que plantou, resultados, problemas"""
    __tablename__ = "historico_safras"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    fazenda_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("fazendas.id"))
    talhao_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("talhoes.id"))
    safra: Mapped[str] = mapped_column(String(20), nullable=False)       # 2025/26
    tipo_safra: Mapped[str] = mapped_column(String(20), nullable=False)  # PRINCIPAL, SAFRINHA, TERCEIRA
    cultura: Mapped[str] = mapped_column(String(50), nullable=False)
    variedade: Mapped[str | None] = mapped_column(String(100))
    area_ha: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # Resultado
    produtividade: Mapped[float | None] = mapped_column(Numeric(10, 2))
    unidade_prod: Mapped[str | None] = mapped_column(String(20))
    preco_venda_medio: Mapped[float | None] = mapped_column(Numeric(10, 2))
    receita_total: Mapped[float | None] = mapped_column(Numeric(14, 2))
    custo_total: Mapped[float | None] = mapped_column(Numeric(14, 2))
    margem: Mapped[float | None] = mapped_column(Numeric(14, 2))

    # Problemas
    problemas: Mapped[str | None] = mapped_column(Text)  # JSON array: ["MOSCA_BRANCA", "SECA"]
    perda_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    observacoes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_hist_safra", "user_id", "safra"),
        Index("idx_hist_micro", "fazenda_id", "cultura", "safra"),
    )
