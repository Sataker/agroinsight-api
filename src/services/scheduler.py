"""
Scheduler — APScheduler rodando os pipelines automaticamente.

DIARIO 06:00 BRT: CEPEA, INMET, NASA POWER, B3, relacao de troca
SEMANAL segunda 07:00: IA recomendacoes, previsao clima
MENSAL dia 15: CONAB, IBGE, World Bank, COMEX STAT
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import structlog

from src.database import SessionLocal
from src.models.user import User
from src.models.fazenda import Fazenda
from src.pipelines.daily import cepea_pipeline, inmet_pipeline, nasa_power_pipeline, b3_pipeline, relacao_troca_pipeline
from src.pipelines.monthly import conab_pipeline, ibge_pipeline, worldbank_pipeline, comexstat_pipeline
from src.services.ia_engine import processar_recomendacoes

logger = structlog.get_logger()

scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")


async def run_daily_pipelines():
    """Executa todos os pipelines diarios."""
    logger.info("scheduler_daily_start")
    async with SessionLocal() as db:
        results = {}
        results["cepea"] = await cepea_pipeline.run(db)
        results["inmet"] = await inmet_pipeline.run(db)
        results["nasa_power"] = await nasa_power_pipeline.run(db)
        results["b3"] = await b3_pipeline.run(db)
        results["relacao_troca"] = await relacao_troca_pipeline.run(db)
        logger.info("scheduler_daily_done", results=results)


async def run_weekly_ia():
    """Gera recomendacoes da IA para todos os usuarios."""
    logger.info("scheduler_weekly_ia_start")
    async with SessionLocal() as db:
        # Buscar todos os usuarios com fazendas
        result = await db.execute(
            select(User).options(selectinload(User.fazendas))
        )
        users = result.scalars().all()

        total = 0
        for user in users:
            for fazenda in user.fazendas:
                saved = await processar_recomendacoes(db, user, fazenda)
                total += saved

        logger.info("scheduler_weekly_ia_done", total_recomendacoes=total)


async def run_monthly_pipelines():
    """Executa todos os pipelines mensais."""
    logger.info("scheduler_monthly_start")
    async with SessionLocal() as db:
        results = {}
        results["conab"] = await conab_pipeline.run(db)
        results["ibge"] = await ibge_pipeline.run(db)
        results["worldbank"] = await worldbank_pipeline.run(db)
        results["comexstat"] = await comexstat_pipeline.run(db)
        logger.info("scheduler_monthly_done", results=results)


def setup_scheduler():
    """Configura os jobs do scheduler."""
    # DIARIO — 06:00 BRT (horario de Sao Paulo)
    scheduler.add_job(
        run_daily_pipelines,
        CronTrigger(hour=6, minute=0, timezone="America/Sao_Paulo"),
        id="daily_pipelines",
        name="Pipelines diarios (CEPEA, INMET, B3)",
        replace_existing=True,
    )

    # SEMANAL — Segunda 07:00 BRT
    scheduler.add_job(
        run_weekly_ia,
        CronTrigger(day_of_week="mon", hour=7, minute=0, timezone="America/Sao_Paulo"),
        id="weekly_ia",
        name="IA recomendacoes semanais",
        replace_existing=True,
    )

    # MENSAL — Dia 15 as 08:00 BRT
    scheduler.add_job(
        run_monthly_pipelines,
        CronTrigger(day=15, hour=8, minute=0, timezone="America/Sao_Paulo"),
        id="monthly_pipelines",
        name="Pipelines mensais (CONAB, IBGE, World Bank)",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("scheduler_started", jobs=len(scheduler.get_jobs()))


def shutdown_scheduler():
    """Para o scheduler."""
    scheduler.shutdown()
    logger.info("scheduler_stopped")
