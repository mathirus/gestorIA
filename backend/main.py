from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.consulta import router as consulta_router
from scrapers.costos import CostosScraper
from scrapers.agip import AgipScraper
from scrapers.arba import ArbaScraper
from scrapers.vtv_pba import VtvPbaScraper
from scrapers.vtv_caba import VtvCabaScraper
from scrapers.multabot import MultabotScraper
from scrapers.dnrpa_dominio import DnrpaDominioScraper
from services.consulta_manager import registrar_scraper
from db.models import TipoConsulta


@asynccontextmanager
async def lifespan(app: FastAPI):
    registrar_scraper(TipoConsulta.costos, CostosScraper())
    registrar_scraper(TipoConsulta.patentes_caba, AgipScraper())
    registrar_scraper(TipoConsulta.patentes_pba, ArbaScraper())
    registrar_scraper(TipoConsulta.vtv_pba, VtvPbaScraper())
    registrar_scraper(TipoConsulta.vtv_caba, VtvCabaScraper())
    registrar_scraper(TipoConsulta.multas, MultabotScraper())
    registrar_scraper(TipoConsulta.dominio, DnrpaDominioScraper())
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
