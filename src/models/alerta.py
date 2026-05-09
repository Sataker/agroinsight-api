import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, Numeric, Text, DateTime, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base


class Alerta(Base):
    __tablename__ = "alertas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)        # PRECO_COMMODITY, PRECO_INSUMO, CLIMA, RELACAO_TROCA
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    # Configuracao do gatilho
    item: Mapped[str] = mapped_column(String(100), nullable=False)       # SOJA, UREIA, PRECIPITACAO
    condicao: Mapped[str] = mapped_column(String(10), nullable=False)    # ACIMA, ABAIXO, VARIACAO
    valor_gatilho: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    unidade: Mapped[str | None] = mapped_column(String(20))

    # Canais de notificacao
    notificar_email: Mapped[bool] = mapped_column(Boolean, default=False)
    notificar_whatsapp: Mapped[bool] = mapped_column(Boolean, default=True)
    notificar_push: Mapped[bool] = mapped_column(Boolean, default=True)

    ultimo_disparo: Mapped[datetime | None] = mapped_column(DateTime)
    cooldown_horas: Mapped[int] = mapped_column(Integer, default=24)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="alertas")
    historico = relationship("AlertaHistorico", back_populates="alerta", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_alertas_user", "user_id", "ativo"),
    )


class AlertaHistorico(Base):
    __tablename__ = "alertas_historico"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alerta_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("alertas.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    valor_atual: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    canais_enviados: Mapped[str | None] = mapped_column(String(200))     # "whatsapp,email,push"
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    alerta = relationship("Alerta", back_populates="historico")
