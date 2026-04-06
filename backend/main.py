import asyncio
import sys
from contextlib import asynccontextmanager

# Windows needs ProactorEventLoop for subprocess support in async Playwright
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.consulta import router as consulta_router
from scrapers.costos import CostosScraper
from scrapers.agip import AgipScraper
from scrapers.arba import ArbaScraper
from scrapers.vtv_pba import VtvPbaScraper
from scrapers.vtv_caba import VtvCabaScraper
from scrapers.dnrpa_dominio import DnrpaDominioScraper
from scrapers.multas_caba import MultasCabaScraper
from scrapers.multas_pba import MultasPbaScraper
from scrapers.multas_nacional import MultasNacionalScraper
from services.consulta_manager import registrar_scraper
from db.models import TipoConsulta


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables (SQLite for dev)
    from db.database import engine
    from db.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    registrar_scraper(TipoConsulta.costos, CostosScraper())
    registrar_scraper(TipoConsulta.patentes_caba, AgipScraper())
    registrar_scraper(TipoConsulta.patentes_pba, ArbaScraper())
    registrar_scraper(TipoConsulta.vtv_pba, VtvPbaScraper())
    registrar_scraper(TipoConsulta.vtv_caba, VtvCabaScraper())
    registrar_scraper(TipoConsulta.multas_caba, MultasCabaScraper())
    registrar_scraper(TipoConsulta.multas_pba, MultasPbaScraper())
    registrar_scraper(TipoConsulta.multas_nacional, MultasNacionalScraper())
    registrar_scraper(TipoConsulta.dominio, DnrpaDominioScraper())
    yield


from config import settings

app = FastAPI(title="gestorIA API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(consulta_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
