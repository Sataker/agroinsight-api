"""Endpoints para executar pipelines manualmente (admin/dev)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.api.deps import get_current_user
from src.models.user import User
from src.pipelines.daily import cepea_pipeline, inmet_pipeline, nasa_power_pipeline, b3_pipeline, relacao_troca_pipeline
from src.pipelines.monthly import conab_pipeline, ibge_pipeline, worldbank_pipeline, comexstat_pipeline

router = APIRouter()


@router.post("/daily/cepea")
async def run_cepea(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await cepea_pipeline.run(db)


@router.post("/daily/inmet")
async def run_inmet(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await inmet_pipeline.run(db)


@router.post("/daily/nasa")
async def run_nasa(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await nasa_power_pipeline.run(db)


@router.post("/daily/b3")
async def run_b3(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await b3_pipeline.run(db)


@router.post("/daily/relacao-troca")
async def run_relacao_troca(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await relacao_troca_pipeline.run(db)


@router.post("/monthly/conab")
async def run_conab(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await conab_pipeline.run(db)


@router.post("/monthly/ibge")
async def run_ibge(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await ibge_pipeline.run(db)


@router.post("/monthly/worldbank")
async def run_worldbank(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await worldbank_pipeline.run(db)


@router.post("/monthly/comexstat")
async def run_comexstat(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await comexstat_pipeline.run(db)


@router.post("/all")
async def run_all(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Roda todos os pipelines de uma vez."""
    results = {}
    results["cepea"] = await cepea_pipeline.run(db)
    results["inmet"] = await inmet_pipeline.run(db)
    results["nasa_power"] = await nasa_power_pipeline.run(db)
    results["b3"] = await b3_pipeline.run(db)
    results["relacao_troca"] = await relacao_troca_pipeline.run(db)
    results["conab"] = await conab_pipeline.run(db)
    results["ibge"] = await ibge_pipeline.run(db)
    results["worldbank"] = await worldbank_pipeline.run(db)
    results["comexstat"] = await comexstat_pipeline.run(db)
    return results
