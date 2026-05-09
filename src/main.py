from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import get_settings
from src.api.routes import auth, precos, clima, alertas, recomendacoes, fazendas, safra, insumos, pipelines


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()
    print(f"AgroInsight API starting on {settings.host}:{settings.port} [{settings.env}]")

    # Iniciar scheduler de pipelines
    from src.services.scheduler import setup_scheduler, shutdown_scheduler
    setup_scheduler()

    yield

    # Shutdown
    shutdown_scheduler()
    print("AgroInsight API shutting down")


app = FastAPI(
    title="AgroInsight API",
    description="Consultor agricola com IA para o produtor rural brasileiro",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — permitir frontend Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3200",
        "http://178.156.138.144:3200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(fazendas.router, prefix="/api/v1/fazendas", tags=["Fazendas"])
app.include_router(precos.router, prefix="/api/v1/precos", tags=["Precos"])
app.include_router(clima.router, prefix="/api/v1/clima", tags=["Clima"])
app.include_router(insumos.router, prefix="/api/v1/insumos", tags=["Insumos"])
app.include_router(safra.router, prefix="/api/v1/safra", tags=["Safra"])
app.include_router(alertas.router, prefix="/api/v1/alertas", tags=["Alertas"])
app.include_router(recomendacoes.router, prefix="/api/v1/recomendacoes", tags=["Recomendacoes"])
app.include_router(pipelines.router, prefix="/api/v1/pipelines", tags=["Pipelines"])


@app.get("/")
async def root():
    return {
        "app": "AgroInsight API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
