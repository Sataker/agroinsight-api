"""
Pipeline diario: NASA POWER API → dados_clima

Complementa INMET com dados de satelite para areas sem estacao.
API 100% gratuita, sem autenticacao.
https://power.larc.nasa.gov/api/
"""

from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
import httpx
import structlog

from src.models.clima import DadoClima
from src.models.fazenda import Fazenda

logger = structlog.get_logger()

NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"


async def fetch_nasa_power(client: httpx.AsyncClient, lat: float, lon: float, start: str, end: str) -> dict | None:
    """Busca dados NASA POWER para uma coordenada."""
    params = {
        "parameters": "T2M_MAX,T2M_MIN,T2M,PRECTOTCORR,RH2M,ALLSKY_SFC_SW_DWN,WS2M",
        "community": "ag",
        "longitude": str(lon),
        "latitude": str(lat),
        "start": start,
        "end": end,
        "format": "json",
    }
    try:
        resp = await client.get(NASA_POWER_URL, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("nasa_power_error", lat=lat, lon=lon, error=str(e))
        return None


def safe_decimal(val) -> Decimal | None:
    if val is None or val == -999 or val == -999.0:
        return None
    try:
        return Decimal(str(round(val, 2)))
    except Exception:
        return None


async def run(db: AsyncSession):
    """Busca dados climaticos NASA POWER para todas as fazendas cadastradas."""
    logger.info("pipeline_nasa_power_start")

    # Pegar coordenadas unicas de todas as fazendas
    result = await db.execute(
        select(Fazenda.latitude, Fazenda.longitude)
        .where(Fazenda.latitude.isnot(None), Fazenda.longitude.isnot(None))
        .distinct()
    )
    fazendas = result.all()

    if not fazendas:
        logger.info("pipeline_nasa_power_no_fazendas")
        return {"status": "no_fazendas", "saved": 0}

    # Ultimos 3 dias (NASA tem delay de ~2 dias)
    end_date = (date.today() - timedelta(days=2)).strftime("%Y%m%d")
    start_date = (date.today() - timedelta(days=4)).strftime("%Y%m%d")

    saved = 0
    async with httpx.AsyncClient() as client:
        for lat, lon in fazendas:
            lat_f = float(lat)
            lon_f = float(lon)

            data = await fetch_nasa_power(client, lat_f, lon_f, start_date, end_date)
            if not data or "properties" not in data:
                continue

            params = data["properties"]["parameter"]
            dates = list(params.get("T2M", {}).keys())

            for d_str in dates:
                try:
                    data_date = date(int(d_str[:4]), int(d_str[4:6]), int(d_str[6:8]))
                except ValueError:
                    continue

                registro = {
                    "fonte": "NASA_POWER",
                    "estacao_id": None,
                    "latitude": Decimal(str(lat_f)),
                    "longitude": Decimal(str(lon_f)),
                    "data": data_date,
                    "temp_max": safe_decimal(params.get("T2M_MAX", {}).get(d_str)),
                    "temp_min": safe_decimal(params.get("T2M_MIN", {}).get(d_str)),
                    "temp_media": safe_decimal(params.get("T2M", {}).get(d_str)),
                    "precipitacao": safe_decimal(params.get("PRECTOTCORR", {}).get(d_str)),
                    "umidade_media": safe_decimal(params.get("RH2M", {}).get(d_str)),
                    "radiacao": safe_decimal(params.get("ALLSKY_SFC_SW_DWN", {}).get(d_str)),
                    "vento_medio": safe_decimal(params.get("WS2M", {}).get(d_str)),
                }

                stmt = pg_insert(DadoClima).values(**registro).on_conflict_do_nothing()
                await db.execute(stmt)
                saved += 1

    await db.commit()
    logger.info("pipeline_nasa_power_done", saved=saved)
    return {"status": "ok", "saved": saved}
