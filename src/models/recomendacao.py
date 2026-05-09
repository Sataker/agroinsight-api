import uuid
from datetime import datetime, date
from sqlalchemy import String, Integer, BigInteger, Numeric, Boolean, Text, Date, DateTime, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base


class Recomendacao(Base):
    """Recomendacoes geradas pela IA para cada produtor"""
    __tablename__ = "recomendacoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    fazenda_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("fazendas.id"))
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)        # PLANTIO, COMPRA_INSUMO, VENDA, ALERTA_CLIMA, CULTURA_EMERGENTE
    prioridade: Mapped[str] = mapped_column(String(10), nullable=False)  # URGENTE, ALTA, MEDIA, BAIXA

    titulo: Mapped[str] = mapped_column(String(500), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    acao_sugerida: Mapped[str | None] = mapped_column(Text)

    # Dados que fundamentaram
    dados_base: Mapped[str | None] = mapped_column(Text)                 # JSON snapshot
    confianca: Mapped[float | None] = mapped_column(Numeric(3, 2))       # 0.0 a 1.0

    # Feedback do produtor
    aceita: Mapped[bool | None] = mapped_column(Boolean)                 # true=seguiu, false=ignorou
    feedback: Mapped[str | None] = mapped_column(Text)

    # Controle
    validade: Mapped[date | None] = mapped_column(Date)
    lida: Mapped[bool] = mapped_column(Boolean, default=False)
    notificada: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="recomendacoes")

    __table_args__ = (
        Index("idx_recom", "user_id", "created_at"),
        Index("idx_recom_tipo", "tipo", "created_at"),
    )


class EventoMercado(Base):
    """Eventos geopoliticos e de mercado com impacto traduzido pela IA"""
    __tablename__ = "eventos_mercado"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)        # GUERRA, EMBARGO, QUEBRA_SAFRA, REGULACAO, CLIMA_GLOBAL
    titulo: Mapped[str] = mapped_column(String(500), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text)
    fonte_url: Mapped[str | None] = mapped_column(String(500))
    pais_origem: Mapped[str | None] = mapped_column(String(100))
    data_evento: Mapped[date] = mapped_column(Date, nullable=False)

    # Impacto previsto pela IA
    commodities_afetadas: Mapped[str | None] = mapped_column(String(500))  # "SOJA,UREIA,PETROLEO"
    direcao_impacto: Mapped[str | None] = mapped_column(String(10))        # ALTA, BAIXA, NEUTRO
    magnitude_impacto: Mapped[int | None] = mapped_column(Integer)          # 1-10
    analise_ia: Mapped[str | None] = mapped_column(Text)

    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_eventos", "data_evento"),
    )


class CulturaEmergente(Base):
    """Culturas detectadas com crescimento anomalo em micro-regioes"""
    __tablename__ = "culturas_emergentes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    cultura: Mapped[str] = mapped_column(String(50), nullable=False)     # GRAO_DE_BICO, TRIGO
    micro_regiao_origem_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("micro_regioes.id"))
    area_plantada_ha: Mapped[float | None] = mapped_column(Numeric(12, 2))
    crescimento_pct: Mapped[float | None] = mapped_column(Numeric(6, 2))
    safra: Mapped[str | None] = mapped_column(String(20))

    # Recomendacao
    micro_regioes_alvo: Mapped[str | None] = mapped_column(String(500))  # IDs separados por virgula
    compradores_disponiveis: Mapped[int | None] = mapped_column(Integer)
    analise_ia: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_emergentes", "cultura", "safra"),
    )
