# gestorIA

## Que es esto

En Argentina, transferir un auto usado requiere 9 pasos, 3-5 dias habiles, multiples organismos publicos (DNRPA, AFIP, municipios) y un profesional llamado "gestor" que navega todo el tramite. No existe ninguna plataforma digital que integre todo esto.

**gestorIA** es un proyecto para construir esa plataforma. Arrancamos por lo mas basico: una herramienta de consulta vehicular donde pones una patente y obtenes toda la informacion que un gestor necesita antes de arrancar una transferencia.

## Que hace hoy

El usuario ingresa una patente y provincia en una web. El sistema ejecuta en paralelo multiples consultas a organismos publicos y muestra los resultados en un checklist en tiempo real. **7 de 9 scrapers funcionan 100% automaticamente** con resolucion de captcha via CapSolver, sin intervencion humana.

### Que funciona end-to-end (7 scrapers automaticos)
- **AGIP (patentes CABA)** — consulta deuda de patentes. CapSolver reCAPTCHA v2 + Playwright headless. Devuelve datos del vehiculo + deudas impagas.
- **VTV PBA** — verificacion tecnica vehicular Provincia BA. CapSolver Turnstile + httpx API directa (sin browser). Devuelve estado VTV, oblea, planta.
- **VTV CABA** — verificacion tecnica vehicular CABA. CapSolver reCAPTCHA v2 + httpx API directa (sin browser). Devuelve historial completo de VTV (10 verificaciones).
- **Calculadora de costos** — calculo local, sin captcha. Devuelve desglose de costos (arancel DNRPA + sellos + verificacion policial).
- **DNRPA dominio** — informe de radicacion del vehiculo. ddddocr OCR (gratis) + Chrome CDP para popup. Devuelve datos de radicacion (registro, localidad, provincia).
- **Multas CABA** — infracciones de transito CABA. CapSolver reCAPTCHA Enterprise + Chrome CDP. Devuelve infracciones con numero de acta, montos.
- **ANSV Nacional** — infracciones nacionales. CapSolver reCAPTCHA v2 + Chrome CDP. Devuelve infracciones nacionales (requiere DNI, no patente).

### Parcialmente funcional
- **Multas PBA** — el flujo funciona pero el token de captcha Enterprise a veces es rechazado por el servidor.

### Pausado
- **ARBA (patentes PBA)** — requiere credenciales CUIT + CIT que no tenemos.

### Ya no se necesita
- **Multabot** — era un servicio intermediario. Ahora scrapeamos las fuentes gubernamentales directamente (CABA, PBA, ANSV).

## Por que "provincia" importa

Los impuestos y consultas dependen de donde esta radicado el auto:
- **CABA:** patentes las cobra AGIP, VTV la gestiona suvtv.com.ar
- **Provincia de Buenos Aires:** patentes las cobra ARBA, VTV la gestiona vtv.gba.gob.ar
- Las multas y el informe de dominio (DNRPA) son nacionales, no dependen de la provincia

Cuando el usuario elige "CABA", se ejecutan AGIP + VTV CABA. Cuando elige "Buenos Aires", se ejecutan ARBA + VTV PBA. Costos, multas y dominio se ejecutan siempre.

---

## Stack

- **Backend:** Python 3.12+ / FastAPI / SQLAlchemy async / SQLite (dev) / PostgreSQL (prod)
- **Scraping:** Playwright + Chrome CDP + httpx (segun el sitio)
- **Captcha:** CapSolver (reCAPTCHA v2, Enterprise, Turnstile) + ddddocr (OCR gratis para DNRPA)
- **Frontend:** Next.js 16 / TypeScript / Tailwind CSS
- **Tests:** pytest + pytest-asyncio

---

## Levantar el proyecto

### Requisitos
- Python 3.12+
- Node.js 18+
- Google Chrome instalado (los scrapers lo usan via CDP y Playwright)

### Backend

```bash
cd backend
pip install -r requirements.txt
python run.py
# Corre en http://localhost:8000
```

**Importante:** En Windows usar `python run.py` y NO `uvicorn main:app` directo. El wrapper configura ProactorEventLoop que es necesario para las operaciones async con subprocesos.

Al iniciar, crea automaticamente la base de datos SQLite (`gestoria.db`) y las tablas.

### Frontend

```bash
cd frontend
npm install
npm run dev
# Corre en http://localhost:3000
```

### Variables de entorno

Copiar `backend/.env.example` a `backend/.env`:
```bash
cp backend/.env.example backend/.env
```

Contenido:
```
DATABASE_URL=sqlite+aiosqlite:///./gestoria.db    # SQLite para dev, PostgreSQL para prod
capsolver_api_key=CAP-XXXXXXXX                    # API key de CapSolver (necesario para captchas)
```

La API key de CapSolver es necesaria para que funcionen los scrapers con captcha (AGIP, VTV PBA, VTV CABA, Multas CABA, Multas PBA, ANSV).

### Tests

```bash
cd backend
python -m pytest tests/ -v
```

7 tests: 4 de calculadora de costos + 3 de logica de reintentos del scraper base.

### Ejemplo: que pasa cuando probas la app

1. Abris http://localhost:3000
2. Pones patente "OZL491", provincia "CABA", click "Consultar"
3. Te redirige a la pagina de resultados con items en el checklist:
   - ✅ **Calculadora de costos** — completa al instante con desglose
   - ✅ **AGIP deuda patentes** — consulta automatica con captcha resuelto por CapSolver
   - ✅ **VTV CABA** — historial completo de verificaciones
   - ✅ **DNRPA dominio** — datos de radicacion del vehiculo
   - ✅ **Multas CABA** — infracciones con actas y montos
4. Los items se van completando a medida que cada scraper termina
5. La pagina deja de pollear cuando todo termino

---

## Como funciona

### Flujo

1. El usuario ingresa patente + provincia en el frontend
2. Frontend hace `POST /api/consulta` al backend
3. Backend crea un registro en la DB y lanza scrapers en paralelo (`asyncio.gather`)
4. Frontend pollea `GET /api/consulta/{id}` cada 10 segundos
5. A medida que cada scraper termina, actualiza su estado en la DB
6. Frontend muestra el checklist actualizandose en tiempo real
7. Si algo falla, el usuario puede reintentar con un boton

### Estados de cada sub-consulta

```
PENDIENTE → EJECUTANDO → COMPLETADO (con datos)
                       → FALLIDO (con razon del error)
```

- 3 reintentos automaticos con backoff (2s, 8s, 20s)
- Timeout de 30 segundos por scraper
- Reintento manual disponible para consultas fallidas

### API endpoints

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/consulta` | Crea consulta. Body: `{"patente": "ABC123", "provincia": "caba"}` |
| `GET` | `/api/consulta/{id}` | Pollea estado de la consulta |
| `POST` | `/api/consulta/{id}/reintentar/{tipo}` | Reintenta una sub-consulta fallida |

Provincias soportadas: `caba`, `buenos_aires`. Segun la provincia, se ejecutan los scrapers correspondientes.

---

## Estructura del proyecto

```
gestorIA/
├── backend/
│   ├── main.py                    # FastAPI app, lifespan, CORS, registro de scrapers
│   ├── config.py                  # Settings (URLs, timeouts, DB, capsolver_api_key)
│   ├── run.py                     # Windows wrapper para uvicorn (ProactorEventLoop)
│   ├── requirements.txt           # Dependencias Python
│   ├── .env.example               # Template de variables de entorno
│   ├── gestoria.db                # SQLite (se crea automaticamente)
│   │
│   ├── db/
│   │   ├── database.py            # Engine async + session factory + get_db dependency
│   │   ├── models.py              # ORM: Consulta, SubConsulta, enums (TipoConsulta incluye multas_caba/pba/nacional)
│   │   └── migrations/            # Alembic (para PostgreSQL en prod)
│   │
│   ├── models/
│   │   └── schemas.py             # Pydantic: ConsultaCreate, ConsultaResponse, SubConsultaResponse
│   │
│   ├── routes/
│   │   └── consulta.py            # Endpoints POST/GET consulta, reintentar, _build_response
│   │
│   ├── services/
│   │   ├── calculadora.py         # calcular_costos(valuacion, provincia) → dict con desglose
│   │   ├── alicuotas.py           # Tasas de sellos por provincia + arancel DNRPA
│   │   ├── consulta_manager.py    # Orquestador: lanza scrapers en paralelo, actualiza DB
│   │   └── capsolver_client.py    # Cliente async para CapSolver API (reCAPTCHA, Turnstile, Enterprise)
│   │
│   ├── scrapers/
│   │   ├── base.py                # BaseScraper ABC con reintentos/timeout/backoff
│   │   ├── costos.py              # CostosScraper: wrapper de calculadora como scraper
│   │   ├── agip.py                # AGIP CABA: deuda de patentes (CapSolver reCAPTCHA v2 + Playwright)
│   │   ├── arba.py                # ARBA PBA: deuda de patentes [pausado - requiere CUIT+CIT]
│   │   ├── vtv_pba.py             # VTV Provincia BA (CapSolver Turnstile + httpx API directa)
│   │   ├── vtv_caba.py            # VTV CABA (CapSolver reCAPTCHA v2 + httpx API directa)
│   │   ├── dnrpa_dominio.py       # DNRPA informe de dominio (ddddocr OCR + Chrome CDP)
│   │   ├── multas_caba.py         # Multas CABA (CapSolver reCAPTCHA Enterprise + Chrome CDP)
│   │   ├── multas_pba.py          # Multas PBA (Enterprise captcha - parcial)
│   │   └── multas_nacional.py     # ANSV infracciones nacionales (CapSolver reCAPTCHA v2 + Chrome CDP)
│   │
│   └── tests/
│       ├── test_calculadora.py    # 4 tests: CABA, PBA, default, desglose completo
│       └── test_scraper_base.py   # 3 tests: exito, reintento+exito, fallo total
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx               # Home: formulario patente + provincia
│   │   ├── layout.tsx             # Layout: dark theme, metadata
│   │   └── consulta/[id]/
│   │       └── page.tsx           # Resultados: checklist con polling cada 10s
│   ├── package.json
│   └── tailwind.config.ts
│
├── docs/
│   └── plans/
│       ├── 2026-03-14-...-design.md       # Documento de diseno aprobado
│       └── 2026-03-14-...-implementation.md # Plan de implementacion (15 tasks)
│
├── docker-compose.yml             # PostgreSQL para produccion
├── CLAUDE.md                      # Instrucciones para Claude Code
│
├── Investigacion_Gestoria_Digital_Automotor.docx  # Research: ICAR (Chile) + Gesthispania (Espana)
├── Investigacion_Gestoria_Digital_Espana.docx     # Research: mercado espanol, oportunidad IA
├── Tutorial_Transferencia_Vehicular_Argentina.docx # Los 9 pasos de una transferencia
├── Diagrama_Transferencia_Vehicular.html          # Flowchart interactivo de los 9 pasos
└── grabacion_*.txt                                # Transcripciones de reuniones
```

---

## Los 9 scrapers — Estado detallado

### 1. Calculadora de costos — ✅ FUNCIONA

**Archivo:** `backend/services/calculadora.py` + `backend/services/alicuotas.py`
**Que hace:** Calcula el costo total de una transferencia vehicular.
**Input:** Valuacion fiscal del vehiculo + provincia.
**Output:**
```json
{
  "valuacion_fiscal": 15000000,
  "arancel_dnrpa": 150000,
  "arancel_dnrpa_porcentaje": 1.0,
  "sellos": 375000,
  "sellos_porcentaje": 2.5,
  "verificacion_policial": 20000,
  "total": 545000,
  "provincia": "caba"
}
```
**Estado:** Funciona. Tiene 4 tests. Soporta 10 provincias (CABA, Buenos Aires, Cordoba, Santa Fe, Mendoza, Tucuman, Entre Rios, San Juan, San Luis, Santa Cruz). Provincias no listadas usan 2.5% por defecto.

**TODO:** Integrar con las tablas de valuacion de DNRPA para obtener la valuacion fiscal automaticamente a partir de marca/modelo/ano (hoy usa un valor fijo de $15M).

---

### 2. AGIP — Deuda de patentes CABA — ✅ FUNCIONA

**Archivo:** `backend/scrapers/agip.py`
**URL:** https://lb.agip.gob.ar/ConsultaPat/
**Que hace:** Consulta si un vehiculo radicado en CABA tiene deuda de patentes.
**Input:** Patente (ej: OZL491).
**Captcha:** CapSolver reCAPTCHA v2 + Playwright headless con channel="chrome".
**Output:** Datos del vehiculo + deudas impagas.

**Estado:** Funciona 100% automaticamente. Testeado end-to-end en servidor.

---

### 3. VTV Provincia BA — ✅ FUNCIONA

**Archivo:** `backend/scrapers/vtv_pba.py`
**URL:** https://vtv.gba.gob.ar/consultar-vtv
**Que hace:** Consulta si un vehiculo tiene la VTV vigente en Provincia de Buenos Aires.
**Input:** Patente.
**Captcha:** CapSolver Turnstile + httpx API directa (sin browser, muy rapido).
**Output:** Estado VTV, oblea, planta.

**Estado:** Funciona 100% automaticamente. No necesita browser, usa la API directamente.

---

### 4. VTV CABA — ✅ FUNCIONA

**Archivo:** `backend/scrapers/vtv_caba.py`
**URL:** suvtv.com.ar
**Que hace:** Consulta historial de VTV para vehiculos en CABA.
**Input:** Patente.
**Captcha:** CapSolver reCAPTCHA v2 + httpx API directa (sin browser).
**Output:** Historial completo de VTV (hasta 10 verificaciones).

**Estado:** Funciona 100% automaticamente. No necesita browser, usa la API directamente.

---

### 5. DNRPA — Informe de dominio — ✅ FUNCIONA

**Archivo:** `backend/scrapers/dnrpa_dominio.py`
**Que hace:** Consulta datos de radicacion del vehiculo (registro, localidad, provincia).
**Input:** Patente.
**Captcha:** ddddocr OCR (gratis, sin costo de CapSolver) + Chrome CDP para manejar popup.
**Output:** Datos de radicacion (registro, localidad, provincia).

**Estado:** Funciona 100% automaticamente.

---

### 6. Multas CABA — ✅ FUNCIONA

**Archivo:** `backend/scrapers/multas_caba.py`
**URL:** https://buenosaires.gob.ar/licenciasdeconducir/consulta-de-infracciones/
**Que hace:** Consulta infracciones de transito en CABA.
**Input:** Patente.
**Captcha:** CapSolver reCAPTCHA Enterprise + Chrome CDP.
**Output:** Lista de infracciones con numero de acta y montos.

**Estado:** Funciona 100% automaticamente. Testeado end-to-end en servidor.

---

### 7. ANSV Nacional — ✅ FUNCIONA

**Archivo:** `backend/scrapers/multas_nacional.py`
**URL:** https://consultainfracciones.seguridadvial.gob.ar/
**Que hace:** Consulta infracciones de transito a nivel nacional (ANSV).
**Input:** DNI (no patente).
**Captcha:** CapSolver reCAPTCHA v2 + Chrome CDP.
**Output:** Lista de infracciones nacionales.

**Estado:** Funciona 100% automaticamente. Nota: requiere DNI del titular, no patente.

---

### 8. Multas PBA — ⚠️ PARCIAL

**Archivo:** `backend/scrapers/multas_pba.py`
**URL:** https://infraccionesba.gba.gob.ar/consulta-infraccion
**Que hace:** Consulta infracciones de transito en Provincia de Buenos Aires.
**Input:** Patente o DNI.
**Captcha:** reCAPTCHA Enterprise.

**Estado:** El flujo completo funciona pero el token de captcha Enterprise es a veces rechazado por el servidor. Se necesita investigar por que el token no siempre es aceptado.

---

### 9. ARBA — Deuda de patentes Provincia BA — ⏸️ PAUSADO

**Archivo:** `backend/scrapers/arba.py`
**Que hace:** Consultaria si un vehiculo radicado en Provincia de Buenos Aires tiene deuda de patentes.

**Estado:** Pausado. La consulta de deuda de patentes en ARBA requiere credenciales CUIT + CIT (clave de identificacion tributaria). No hay formulario de consulta anonima.

---

## Que hay que hacer — Proximos pasos

### Prioridad alta

1. **Estabilizar Multas PBA** — Investigar por que el token Enterprise es rechazado intermitentemente.

2. **Valuaciones DNRPA** — Integrar las tablas de valuacion fiscal para que la calculadora obtenga el valor automaticamente por marca/modelo/ano en vez de usar $15M fijo. URL: `dnrpa.gov.ar/valuacion/cons_valuacion.php`

3. **Infraestructura de deploy** — Preparar el sistema para produccion (Docker, PostgreSQL, monitoreo).

### Prioridad media

4. **ARBA** — Conseguir credenciales CUIT+CIT o investigar portales alternativos para consulta de patentes PBA.

5. **Mas provincias** — Agregar scrapers para Cordoba, Santa Fe, Mendoza, etc.

6. **UI/UX improvements** — Mejorar la presentacion de resultados, agregar detalles de cada infraccion, exportar reporte.

### Prioridad baja

7. **Integracion con IA** — Interpretar resultados, recomendar si comprar o no, detectar riesgos automaticamente.

8. **B2B API** — Exponer los scrapers como API para integracion con sistemas de agencias y concesionarias.

---

## Dependencias clave

### Python (backend/requirements.txt)
- `fastapi`, `uvicorn` — Web framework
- `sqlalchemy[asyncio]`, `aiosqlite` — Database async
- `playwright` — Browser automation (AGIP)
- `httpx` — HTTP client async (VTV PBA, VTV CABA)
- `aiohttp>=3.9.0` — CapSolver API client
- `ddddocr>=1.6.0` — OCR para captcha de imagen DNRPA (gratis)
- `pydantic-settings` — Configuration

---

## Investigacion de mercado (documentos de referencia)

El repositorio incluye investigacion de mercado que contextualiza el producto:

- **Investigacion_Gestoria_Digital_Automotor.docx** — Analisis de ICAR (Chile, B2C, transferencias 100% remotas en 48hs) y Gesthispania (Espana, B2B, gestion de flotas y multas). Oportunidad en Argentina: no existe ningun equivalente.

- **Investigacion_Gestoria_Digital_Espana.docx** — Deep dive en Gesthispania (305K vehiculos, 800K multas/ano, $6.3M facturacion), mercado espanol, potencial de IA, comparacion con Argentina.

- **Tutorial_Transferencia_Vehicular_Argentina.docx** — Los 9 pasos completos de una transferencia vehicular, que hace el gestor en cada uno, costos, tiempos, y donde hay oportunidades de digitalizacion.

- **Diagrama_Transferencia_Vehicular.html** — Flowchart interactivo visual de los 9 pasos (abrir en navegador).

---

## Arquitectura

```
Frontend (Next.js :3000)
    │
    │ REST API (polling cada 10s)
    ▼
Backend (FastAPI :8000)
    ├── routes/consulta.py          → endpoints REST
    ├── services/consulta_manager.py → orquesta scrapers en paralelo
    ├── services/capsolver_client.py → resolucion automatica de captchas
    ├── scrapers/                    → un modulo por fuente de datos
    │   ├── base.py                  → clase abstracta con reintentos
    │   ├── agip.py                  → CapSolver reCAPTCHA v2 + Playwright headless
    │   ├── vtv_pba.py               → CapSolver Turnstile + httpx API directa
    │   ├── vtv_caba.py              → CapSolver reCAPTCHA v2 + httpx API directa
    │   ├── dnrpa_dominio.py         → ddddocr OCR + Chrome CDP
    │   ├── multas_caba.py           → CapSolver reCAPTCHA Enterprise + Chrome CDP
    │   ├── multas_pba.py            → reCAPTCHA Enterprise + Chrome CDP (parcial)
    │   ├── multas_nacional.py       → CapSolver reCAPTCHA v2 + Chrome CDP
    │   ├── costos.py                → calculo local (sin browser)
    │   └── arba.py                  → pausado (requiere CUIT+CIT)
    └── db/ (SQLite dev / PostgreSQL prod)
        ├── consultas                → patente, provincia, timestamp
        └── sub_consultas            → tipo, estado, intentos, datos, error
```

### Estrategias de scraping

| Estrategia | Cuando se usa | Scrapers |
|------------|---------------|----------|
| **httpx API directa** | Cuando se descubrio el endpoint de API del sitio | VTV PBA, VTV CABA |
| **Playwright headless** | Sitios sin deteccion fuerte de bots | AGIP |
| **Chrome CDP** | Sitios con Cloudflare/deteccion de headless | DNRPA, Multas CABA, Multas PBA, ANSV |
| **Calculo local** | No requiere scraping | Costos |

### Como agregar un nuevo scraper

1. Crear `backend/scrapers/mi_scraper.py`:
```python
from scrapers.base import BaseScraper

class MiScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="mi_scraper")

    async def _ejecutar(self, patente: str, **kwargs) -> dict:
        # Logica de scraping aqui
        # Devolver dict con los datos obtenidos
        # Lanzar excepcion si falla (BaseScraper la catchea y reintenta)
        return {"dato1": "valor1"}
```

2. Agregar el tipo en `backend/db/models.py` → `TipoConsulta`
3. Registrar en `backend/main.py` → `lifespan()`
4. Agregar a la logica de seleccion por provincia en `backend/routes/consulta.py` → `crear_consulta()`
