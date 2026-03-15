# Plataforma de Consultas Vehiculares — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a web platform where a user enters a license plate (patente) and province, and gets a real-time checklist of vehicle queries (costs, patent debt, VTV, fines, domain report) executed in parallel.

**Architecture:** Python FastAPI backend with Playwright scrapers + Multabot API integration, orchestrated via asyncio. Next.js frontend polls the backend every 10s. PostgreSQL stores consultation state and results. Each scraper is an independent module with retry logic.

**Tech Stack:** Python 3.12, FastAPI, Playwright, SQLAlchemy (async), Alembic, PostgreSQL, Next.js 14, TypeScript, Tailwind CSS, Docker Compose.

---

### Task 1: Project scaffolding + backend skeleton

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/main.py`
- Create: `backend/config.py`
- Create: `docker-compose.yml`
- Create: `backend/.env.example`

**Step 1: Create backend requirements**

```
# backend/requirements.txt
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy[asyncio]==2.0.35
asyncpg==0.30.0
alembic==1.13.0
pydantic==2.9.0
pydantic-settings==2.5.0
playwright==1.48.0
httpx==0.27.0
python-dotenv==1.0.1
```

**Step 2: Create config**

```python
# backend/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://gestoria:gestoria@localhost:5432/gestoria"
    multabot_api_key: str = ""

    scraper_timeout: int = 30
    scraper_max_retries: int = 3
    scraper_backoff: list[int] = [2, 8, 20]

    # URLs de sitios a scrapear
    agip_url: str = "https://lb.agip.gob.ar/ConsultaPat/"
    arba_url: str = "https://web.arba.gov.ar/consulta-de-deuda-automotor"
    vtv_pba_url: str = "https://vtv.gba.gov.ar/consultar-vtv"
    vtv_caba_url: str = "https://www.infovtv.com.ar/ng"
    multabot_url: str = "https://multabot.com.ar/api"
    dnrpa_valuacion_url: str = "https://www.dnrpa.gov.ar/valuacion/cons_valuacion.php"

    class Config:
        env_file = ".env"

settings = Settings()
```

**Step 3: Create FastAPI app**

```python
# backend/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: init DB, init Playwright browser
    yield
    # shutdown: close connections

app = FastAPI(title="gestorIA API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

**Step 4: Create docker-compose**

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: gestoria
      POSTGRES_PASSWORD: gestoria
      POSTGRES_DB: gestoria
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://gestoria:gestoria@db:5432/gestoria
    depends_on:
      - db
    volumes:
      - ./backend:/app

volumes:
  pgdata:
```

**Step 5: Create .env.example**

```
DATABASE_URL=postgresql+asyncpg://gestoria:gestoria@localhost:5432/gestoria
MULTABOT_API_KEY=
```

**Step 6: Verify backend starts**

Run: `cd backend && pip install -r requirements.txt && uvicorn main:app --reload`
Then: `curl http://localhost:8000/api/health`
Expected: `{"status": "ok"}`

**Step 7: Commit**

```bash
git init
git add backend/ docker-compose.yml
git commit -m "feat: backend scaffolding with FastAPI + PostgreSQL"
```

---

### Task 2: Database models + migrations

**Files:**
- Create: `backend/db/database.py`
- Create: `backend/db/models.py`
- Create: `backend/alembic.ini`
- Create: `backend/db/migrations/env.py`

**Step 1: Create database connection**

```python
# backend/db/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from config import settings

engine = create_async_engine(settings.database_url)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session
```

**Step 2: Create DB models**

```python
# backend/db/models.py
import enum
from datetime import datetime
from sqlalchemy import String, Enum, DateTime, Integer, JSON, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class EstadoConsulta(str, enum.Enum):
    pendiente = "pendiente"
    ejecutando = "ejecutando"
    completado = "completado"
    fallido = "fallido"
    reintentando = "reintentando"
    pendiente_24hs = "pendiente_24hs"

class TipoConsulta(str, enum.Enum):
    costos = "costos"
    patentes_caba = "patentes_caba"
    patentes_pba = "patentes_pba"
    vtv_pba = "vtv_pba"
    vtv_caba = "vtv_caba"
    multas = "multas"
    dominio = "dominio"

class Consulta(Base):
    __tablename__ = "consultas"

    id: Mapped[int] = mapped_column(primary_key=True)
    patente: Mapped[str] = mapped_column(String(10), index=True)
    provincia: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    sub_consultas: Mapped[list["SubConsulta"]] = relationship(back_populates="consulta")

class SubConsulta(Base):
    __tablename__ = "sub_consultas"

    id: Mapped[int] = mapped_column(primary_key=True)
    consulta_id: Mapped[int] = mapped_column(ForeignKey("consultas.id"))
    tipo: Mapped[TipoConsulta] = mapped_column(Enum(TipoConsulta))
    estado: Mapped[EstadoConsulta] = mapped_column(Enum(EstadoConsulta), default=EstadoConsulta.pendiente)
    intentos: Mapped[int] = mapped_column(Integer, default=0)
    datos: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    consulta: Mapped["Consulta"] = relationship(back_populates="sub_consultas")
```

**Step 3: Initialize Alembic and create first migration**

Run:
```bash
cd backend
pip install alembic
alembic init db/migrations
```

Edit `alembic.ini` to set `sqlalchemy.url` and `db/migrations/env.py` to import models.

Run:
```bash
alembic revision --autogenerate -m "initial tables"
alembic upgrade head
```

Expected: Tables `consultas` and `sub_consultas` created in PostgreSQL.

**Step 4: Commit**

```bash
git add backend/db/ backend/alembic.ini
git commit -m "feat: database models for consultas and sub_consultas"
```

---

### Task 3: Pydantic schemas + API routes

**Files:**
- Create: `backend/models/schemas.py`
- Create: `backend/routes/consulta.py`
- Modify: `backend/main.py` (add router)

**Step 1: Create Pydantic schemas**

```python
# backend/models/schemas.py
from pydantic import BaseModel
from datetime import datetime

class ConsultaCreate(BaseModel):
    patente: str
    provincia: str  # "caba" | "buenos_aires"

class SubConsultaResponse(BaseModel):
    tipo: str
    estado: str
    intentos: int
    datos: dict | None
    error: str | None
    updated_at: datetime

class ConsultaResponse(BaseModel):
    id: int
    patente: str
    provincia: str
    created_at: datetime
    sub_consultas: list[SubConsultaResponse]
    estado_general: str  # "en_proceso" | "completado" | "con_errores"
```

**Step 2: Create routes**

```python
# backend/routes/consulta.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.database import get_db
from db.models import Consulta, SubConsulta, EstadoConsulta, TipoConsulta
from models.schemas import ConsultaCreate, ConsultaResponse

router = APIRouter(prefix="/api")

@router.post("/consulta", response_model=ConsultaResponse)
async def crear_consulta(
    data: ConsultaCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Normalizar patente (mayusculas, sin espacios ni guiones)
    patente = data.patente.upper().replace("-", "").replace(" ", "")

    # Crear consulta
    consulta = Consulta(patente=patente, provincia=data.provincia)
    db.add(consulta)
    await db.flush()

    # Determinar que sub-consultas lanzar segun provincia
    tipos = [TipoConsulta.costos, TipoConsulta.multas, TipoConsulta.dominio]
    if data.provincia == "caba":
        tipos.extend([TipoConsulta.patentes_caba, TipoConsulta.vtv_caba])
    elif data.provincia == "buenos_aires":
        tipos.extend([TipoConsulta.patentes_pba, TipoConsulta.vtv_pba])

    for tipo in tipos:
        sub = SubConsulta(consulta_id=consulta.id, tipo=tipo, estado=EstadoConsulta.pendiente)
        db.add(sub)

    await db.commit()
    await db.refresh(consulta, ["sub_consultas"])

    # Lanzar scrapers en background
    # background_tasks.add_task(ejecutar_consulta, consulta.id)

    return _build_response(consulta)

@router.get("/consulta/{consulta_id}", response_model=ConsultaResponse)
async def obtener_consulta(
    consulta_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Consulta).where(Consulta.id == consulta_id).options(selectinload(Consulta.sub_consultas))
    )
    consulta = result.scalar_one_or_none()
    if not consulta:
        raise HTTPException(status_code=404, detail="Consulta no encontrada")
    return _build_response(consulta)

@router.post("/consulta/{consulta_id}/reintentar/{tipo}")
async def reintentar_sub_consulta(
    consulta_id: int,
    tipo: TipoConsulta,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SubConsulta).where(
            SubConsulta.consulta_id == consulta_id,
            SubConsulta.tipo == tipo,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404)
    sub.estado = EstadoConsulta.pendiente
    sub.intentos = 0
    sub.error = None
    await db.commit()
    # background_tasks.add_task(ejecutar_sub_consulta, consulta_id, tipo)
    return {"status": "reintentando"}

def _build_response(consulta: Consulta) -> dict:
    subs = consulta.sub_consultas
    todos_terminados = all(s.estado in (EstadoConsulta.completado, EstadoConsulta.fallido, EstadoConsulta.pendiente_24hs) for s in subs)
    tiene_fallos = any(s.estado == EstadoConsulta.fallido for s in subs)

    if todos_terminados and tiene_fallos:
        estado_general = "con_errores"
    elif todos_terminados:
        estado_general = "completado"
    else:
        estado_general = "en_proceso"

    return {
        "id": consulta.id,
        "patente": consulta.patente,
        "provincia": consulta.provincia,
        "created_at": consulta.created_at,
        "estado_general": estado_general,
        "sub_consultas": [
            {
                "tipo": s.tipo.value,
                "estado": s.estado.value,
                "intentos": s.intentos,
                "datos": s.datos,
                "error": s.error,
                "updated_at": s.updated_at,
            }
            for s in subs
        ],
    }
```

**Step 3: Register router in main.py**

Add to `backend/main.py`:
```python
from routes.consulta import router as consulta_router
app.include_router(consulta_router)
```

**Step 4: Test manually**

```bash
curl -X POST http://localhost:8000/api/consulta -H "Content-Type: application/json" -d '{"patente": "AB123CD", "provincia": "caba"}'
```

Expected: JSON with consulta id, 5 sub_consultas all in "pendiente".

**Step 5: Commit**

```bash
git add backend/models/ backend/routes/ backend/main.py
git commit -m "feat: API routes for creating and polling consultas"
```

---

### Task 4: Scraper base class with retry logic

**Files:**
- Create: `backend/scrapers/__init__.py`
- Create: `backend/scrapers/base.py`
- Create: `backend/tests/test_scraper_base.py`

**Step 1: Write test for retry logic**

```python
# backend/tests/test_scraper_base.py
import pytest
from scrapers.base import BaseScraper, ScraperResult

class FakeScraper(BaseScraper):
    def __init__(self, fail_times=0):
        super().__init__(name="fake", max_retries=3, backoff=[0, 0, 0], timeout=5)
        self.fail_times = fail_times
        self.call_count = 0

    async def _ejecutar(self, patente: str) -> dict:
        self.call_count += 1
        if self.call_count <= self.fail_times:
            raise Exception("sitio caido")
        return {"resultado": "ok"}

@pytest.mark.asyncio
async def test_scraper_exito():
    s = FakeScraper(fail_times=0)
    result = await s.ejecutar("AB123CD")
    assert result.exito is True
    assert result.datos == {"resultado": "ok"}
    assert result.intentos == 1

@pytest.mark.asyncio
async def test_scraper_reintento_y_exito():
    s = FakeScraper(fail_times=2)
    result = await s.ejecutar("AB123CD")
    assert result.exito is True
    assert result.intentos == 3

@pytest.mark.asyncio
async def test_scraper_fallo_total():
    s = FakeScraper(fail_times=5)
    result = await s.ejecutar("AB123CD")
    assert result.exito is False
    assert result.intentos == 3
    assert "sitio caido" in result.error
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pip install pytest pytest-asyncio && python -m pytest tests/test_scraper_base.py -v`
Expected: FAIL (module not found)

**Step 3: Implement BaseScraper**

```python
# backend/scrapers/base.py
import asyncio
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

@dataclass
class ScraperResult:
    exito: bool
    datos: dict | None = None
    error: str | None = None
    intentos: int = 0

class BaseScraper(ABC):
    def __init__(self, name: str, max_retries: int = 3, backoff: list[int] = [2, 8, 20], timeout: int = 30):
        self.name = name
        self.max_retries = max_retries
        self.backoff = backoff
        self.timeout = timeout

    async def ejecutar(self, patente: str) -> ScraperResult:
        for intento in range(1, self.max_retries + 1):
            try:
                datos = await asyncio.wait_for(
                    self._ejecutar(patente),
                    timeout=self.timeout,
                )
                return ScraperResult(exito=True, datos=datos, intentos=intento)
            except Exception as e:
                if intento < self.max_retries:
                    await asyncio.sleep(self.backoff[intento - 1])
                else:
                    return ScraperResult(exito=False, error=str(e), intentos=intento)

    @abstractmethod
    async def _ejecutar(self, patente: str) -> dict:
        """Implementar en cada scraper. Devuelve dict con datos o lanza excepcion."""
        ...
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_scraper_base.py -v`
Expected: 3 PASSED

**Step 5: Commit**

```bash
git add backend/scrapers/ backend/tests/
git commit -m "feat: BaseScraper with retry logic and backoff"
```

---

### Task 5: Calculadora de costos

**Files:**
- Create: `backend/services/calculadora.py`
- Create: `backend/services/alicuotas.py`
- Create: `backend/tests/test_calculadora.py`

**Step 1: Write test**

```python
# backend/tests/test_calculadora.py
from services.calculadora import calcular_costos

def test_costos_caba():
    resultado = calcular_costos(valuacion=15_000_000, provincia="caba")
    assert resultado["arancel_dnrpa"] == 150_000       # 1%
    assert resultado["sellos"] == 375_000               # 2.5% CABA
    assert resultado["verificacion_policial"] == 20_000  # estimado fijo
    assert resultado["total"] == 150_000 + 375_000 + 20_000

def test_costos_buenos_aires():
    resultado = calcular_costos(valuacion=15_000_000, provincia="buenos_aires")
    assert resultado["arancel_dnrpa"] == 150_000
    assert resultado["sellos"] == 450_000               # 3% PBA
```

**Step 2: Run test, verify fail**

Run: `python -m pytest tests/test_calculadora.py -v`
Expected: FAIL

**Step 3: Create alicuotas (tax rates by province)**

```python
# backend/services/alicuotas.py
# Alicuotas de sellos por provincia (porcentaje sobre valor del vehiculo)
ALICUOTAS_SELLOS = {
    "caba": 2.5,
    "buenos_aires": 3.0,
    "cordoba": 3.0,
    "santa_fe": 2.4,
    "mendoza": 2.5,
    "tucuman": 2.5,
    "entre_rios": 2.0,
    "san_juan": 0.5,
    "san_luis": 0.5,
    "santa_cruz": 3.0,
    # Agregar mas provincias a medida que se necesiten
}

COSTO_VERIFICACION_POLICIAL = 20_000  # Estimado en ARS, actualizar periodicamente
ARANCEL_DNRPA_PORCENTAJE = 1.0
```

**Step 4: Implement calculadora**

```python
# backend/services/calculadora.py
from services.alicuotas import ALICUOTAS_SELLOS, COSTO_VERIFICACION_POLICIAL, ARANCEL_DNRPA_PORCENTAJE

def calcular_costos(valuacion: int, provincia: str) -> dict:
    alicuota_sellos = ALICUOTAS_SELLOS.get(provincia, 2.5)

    arancel_dnrpa = int(valuacion * ARANCEL_DNRPA_PORCENTAJE / 100)
    sellos = int(valuacion * alicuota_sellos / 100)
    verificacion = COSTO_VERIFICACION_POLICIAL
    total = arancel_dnrpa + sellos + verificacion

    return {
        "valuacion_fiscal": valuacion,
        "arancel_dnrpa": arancel_dnrpa,
        "arancel_dnrpa_porcentaje": ARANCEL_DNRPA_PORCENTAJE,
        "sellos": sellos,
        "sellos_porcentaje": alicuota_sellos,
        "verificacion_policial": verificacion,
        "total": total,
        "provincia": provincia,
    }
```

**Step 5: Run tests**

Run: `python -m pytest tests/test_calculadora.py -v`
Expected: 2 PASSED

**Step 6: Commit**

```bash
git add backend/services/ backend/tests/test_calculadora.py
git commit -m "feat: cost calculator with provincial tax rates"
```

---

### Task 6: Consulta manager (orchestrator)

**Files:**
- Create: `backend/services/consulta_manager.py`

**Step 1: Implement orchestrator**

```python
# backend/services/consulta_manager.py
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import Consulta, SubConsulta, EstadoConsulta, TipoConsulta
from scrapers.base import BaseScraper, ScraperResult

# Registry: se registra cada scraper por tipo
_scrapers: dict[TipoConsulta, BaseScraper] = {}

def registrar_scraper(tipo: TipoConsulta, scraper: BaseScraper):
    _scrapers[tipo] = scraper

async def ejecutar_consulta(consulta_id: int, db_session_factory):
    """Lanza todas las sub-consultas de una consulta en paralelo."""
    async with db_session_factory() as db:
        result = await db.execute(
            select(Consulta).where(Consulta.id == consulta_id)
        )
        consulta = result.scalar_one()

        result = await db.execute(
            select(SubConsulta).where(SubConsulta.consulta_id == consulta_id)
        )
        subs = result.scalars().all()

    tasks = []
    for sub in subs:
        if sub.tipo in _scrapers:
            tasks.append(_ejecutar_sub(sub.id, sub.tipo, consulta.patente, db_session_factory))

    await asyncio.gather(*tasks)

async def _ejecutar_sub(sub_id: int, tipo: TipoConsulta, patente: str, db_session_factory):
    """Ejecuta un scraper y actualiza el estado en la DB."""
    scraper = _scrapers[tipo]

    async with db_session_factory() as db:
        result = await db.execute(select(SubConsulta).where(SubConsulta.id == sub_id))
        sub = result.scalar_one()
        sub.estado = EstadoConsulta.ejecutando
        await db.commit()

    resultado: ScraperResult = await scraper.ejecutar(patente)

    async with db_session_factory() as db:
        result = await db.execute(select(SubConsulta).where(SubConsulta.id == sub_id))
        sub = result.scalar_one()
        sub.intentos = resultado.intentos
        if resultado.exito:
            sub.estado = EstadoConsulta.completado
            sub.datos = resultado.datos
            sub.error = None
        else:
            sub.estado = EstadoConsulta.fallido
            sub.error = resultado.error
        await db.commit()
```

**Step 2: Wire up in routes (uncomment background_tasks)**

In `backend/routes/consulta.py`, uncomment the background task line and import:
```python
from services.consulta_manager import ejecutar_consulta
from db.database import async_session

# In crear_consulta:
background_tasks.add_task(ejecutar_consulta, consulta.id, async_session)
```

**Step 3: Commit**

```bash
git add backend/services/consulta_manager.py backend/routes/consulta.py
git commit -m "feat: consulta manager orchestrates scrapers in parallel"
```

---

### Task 7: First real scraper — AGIP CABA (patentes)

**Files:**
- Create: `backend/scrapers/agip.py`
- Create: `backend/tests/test_agip.py`

**Step 1: Inspect the AGIP site manually**

Open `https://lb.agip.gob.ar/ConsultaPat/` in a browser. Observe:
- What form fields exist
- What the DOM looks like when results load
- Whether it uses JavaScript to render results
- Any captchas or rate limiting

Document findings in a comment at the top of `agip.py`.

**Step 2: Write scraper**

```python
# backend/scrapers/agip.py
from scrapers.base import BaseScraper
from playwright.async_api import async_playwright
from config import settings

class AgipScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="agip_caba")

    async def _ejecutar(self, patente: str) -> dict:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(settings.agip_url, wait_until="networkidle")

                # TODO: inspeccionar el sitio real y completar los selectores
                # Esto es un esqueleto — los selectores exactos se definen
                # despues de inspeccionar el DOM del sitio
                await page.fill("input#patente", patente)  # selector placeholder
                await page.click("button#consultar")        # selector placeholder
                await page.wait_for_selector(".resultados", timeout=15000)

                # Extraer todos los datos visibles
                datos = await page.evaluate("""() => {
                    // TODO: extraer datos del DOM segun estructura real
                    return { raw: document.querySelector('.resultados').innerText }
                }""")

                return datos
            finally:
                await browser.close()
```

**Step 3: Write integration test (manual, requires network)**

```python
# backend/tests/test_agip.py
import pytest
from scrapers.agip import AgipScraper

@pytest.mark.skipif(True, reason="Requires network + real site. Run manually.")
@pytest.mark.asyncio
async def test_agip_real():
    scraper = AgipScraper()
    result = await scraper.ejecutar("AB123CD")  # patente de prueba
    print(result)
    # No assert especifico — este test es para desarrollo manual
```

**Step 4: Register scraper in app startup**

In `backend/main.py` lifespan:
```python
from scrapers.agip import AgipScraper
from services.consulta_manager import registrar_scraper
from db.models import TipoConsulta

@asynccontextmanager
async def lifespan(app: FastAPI):
    registrar_scraper(TipoConsulta.patentes_caba, AgipScraper())
    yield
```

**Step 5: Commit**

```bash
git add backend/scrapers/agip.py backend/tests/test_agip.py backend/main.py
git commit -m "feat: AGIP CABA scraper skeleton"
```

**Note:** This task creates the skeleton. The actual selectors and extraction logic get refined by running the scraper against the real site and inspecting the DOM. Each subsequent scraper (Tasks 8-12) follows the exact same pattern.

---

### Task 8: ARBA scraper (patentes PBA)

Same pattern as Task 7 but for `web.arba.gov.ar/consulta-de-deuda-automotor`.

**Files:** `backend/scrapers/arba.py`, `backend/tests/test_arba.py`

---

### Task 9: VTV PBA scraper

Same pattern for `vtv.gba.gov.ar/consultar-vtv`.

**Files:** `backend/scrapers/vtv_pba.py`, `backend/tests/test_vtv_pba.py`

---

### Task 10: VTV CABA scraper

Same pattern for `infovtv.com.ar/ng`.

**Files:** `backend/scrapers/vtv_caba.py`, `backend/tests/test_vtv_caba.py`

---

### Task 11: Multabot client (multas via API)

**Files:**
- Create: `backend/scrapers/multabot.py`
- Create: `backend/tests/test_multabot.py`

**Step 1: Implement Multabot client (no Playwright needed — es API REST)**

```python
# backend/scrapers/multabot.py
import httpx
from scrapers.base import BaseScraper
from config import settings

class MultabotScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="multabot")

    async def _ejecutar(self, patente: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.multabot_url}/consulta/{patente}",
                headers={"Authorization": f"Bearer {settings.multabot_api_key}"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
```

**Step 2: Register in lifespan, commit**

---

### Task 12: DNRPA dominio (informe de dominio)

**Files:**
- Create: `backend/scrapers/dnrpa_dominio.py`

Este scraper es diferente: no devuelve datos inmediatos. Inicia la solicitud y marca el estado como `pendiente_24hs`. Se necesitara un mecanismo separado (cron/webhook/polling manual) para verificar cuando llega el resultado.

**Step 1: Implement placeholder**

```python
# backend/scrapers/dnrpa_dominio.py
from scrapers.base import BaseScraper

class DnrpaDominioScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="dnrpa_dominio")

    async def _ejecutar(self, patente: str) -> dict:
        # TODO: Implementar solicitud automatizada a DNRPA
        # Por ahora, marca como pendiente_24hs
        return {"estado": "solicitud_enviada", "nota": "Resultado estimado en 24hs"}
```

---

### Task 13: Frontend — Next.js scaffold + main page

**Files:**
- Create: `frontend/` (via `npx create-next-app@latest`)
- Create: `frontend/app/page.tsx`
- Create: `frontend/app/consulta/[id]/page.tsx`

**Step 1: Scaffold Next.js**

```bash
cd gestorIA
npx create-next-app@latest frontend --typescript --tailwind --app --no-src-dir --no-import-alias
```

**Step 2: Create home page with input form**

`frontend/app/page.tsx` — Form with patente input, province dropdown, submit button.

**Step 3: Create results page with polling checklist**

`frontend/app/consulta/[id]/page.tsx` — Calls GET /api/consulta/{id} every 10s, renders checklist with states (pendiente, ejecutando, completado, fallido), expandable results per item, retry button for failed items.

**Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: Next.js frontend with consultation form and polling results"
```

---

### Task 14: Integration test end-to-end

**Step 1:** Start PostgreSQL, backend, frontend
**Step 2:** Create a consultation via the UI
**Step 3:** Verify polling works, states update, results display
**Step 4:** Test retry on a failed scraper
**Step 5:** Fix any issues found

---

### Task 15: Docker Compose + deployment config

**Step 1:** Create `backend/Dockerfile`
**Step 2:** Create `frontend/Dockerfile`
**Step 3:** Update `docker-compose.yml` with all services
**Step 4:** Install Playwright browsers in backend Dockerfile (`playwright install chromium`)
**Step 5:** Test full stack with `docker-compose up`
**Step 6:** Commit

```bash
git add Dockerfile docker-compose.yml
git commit -m "feat: Docker setup for full stack deployment"
```
