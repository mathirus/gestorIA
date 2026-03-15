from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.consulta import router as consulta_router
from scrapers.costos import CostosScraper
from services.consulta_manager import registrar_scraper
from db.models import TipoConsulta


@asynccontextmanager
async def lifespan(app: FastAPI):
    registrar_scraper(TipoConsulta.costos, CostosScraper())
    yield


app = FastAPI(title="gestorIA API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(consulta_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
