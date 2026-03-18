# gestorIA

## Que es esto

En Argentina, transferir un auto usado requiere 9 pasos, 3-5 dias habiles, multiples organismos publicos (DNRPA, AFIP, municipios) y un profesional llamado "gestor" que navega todo el tramite. No existe ninguna plataforma digital que integre todo esto.

**gestorIA** es un proyecto para construir esa plataforma. Arrancamos por lo mas basico: una herramienta de consulta vehicular donde pones una patente y obtenes toda la informacion que un gestor necesita antes de arrancar una transferencia.

## Que hace hoy

El usuario ingresa una patente y provincia en una web. El sistema ejecuta en paralelo multiples consultas a organismos publicos y muestra los resultados en un checklist en tiempo real.

### Que funciona end-to-end (podes probarlo ahora)
- **Calculadora de costos** — calcula arancel DNRPA (1%) + sellos provinciales + verificacion policial
- **DNRPA placeholder** — devuelve mensaje de que el informe se solicita manualmente

### Que esta construido pero bloqueado por protecciones anti-bot
- **AGIP (deuda de patentes CABA)** — scraper escrito con selectores reales, bloqueado por reCAPTCHA
- **VTV PBA (verificacion tecnica)** — formulario identificado, bloqueado por Cloudflare
- **Multabot (multas)** — no tiene API publica, Cloudflare en el formulario web

### Que no se puede hacer (no existe la consulta publica)
- **ARBA (patentes PBA)** — no hay formulario publico, requiere autogestion con CUIT
- **VTV CABA** — no existe consulta de estado online, solo turnos

## Por que "provincia" importa

Los impuestos y consultas dependen de donde esta radicado el auto:
- **CABA:** patentes las cobra AGIP, VTV la gestiona suvtv.com.ar
- **Provincia de Buenos Aires:** patentes las cobra ARBA, VTV la gestiona vtv.gba.gob.ar
- Las multas y el informe de dominio (DNRPA) son nacionales, no dependen de la provincia

Cuando el usuario elige "CABA", se ejecutan AGIP + VTV CABA. Cuando elige "Buenos Aires", se ejecutan ARBA + VTV PBA. Costos, multas y dominio se ejecutan siempre.

---

## Stack

- **Backend:** Python 3.12+ / FastAPI / SQLAlchemy async / SQLite (dev) / PostgreSQL (prod)
- **Scraping:** Playwright (usa Chrome instalado via `channel="chrome"`)
- **Frontend:** Next.js 16 / TypeScript / Tailwind CSS
- **Tests:** pytest + pytest-asyncio

---

## Levantar el proyecto

### Requisitos
- Python 3.12+
- Node.js 18+
- Google Chrome instalado (Playwright lo usa para scraping)

### Backend

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload
# Corre en http://localhost:8000
```

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
MULTABOT_API_KEY=                                  # Si se consigue acceso API a Multabot
```

No hace falta configurar nada para desarrollo. SQLite se crea solo y los scrapers usan Chrome del sistema.

### Tests

```bash
cd backend
python -m pytest tests/ -v
```

7 tests: 4 de calculadora de costos + 3 de logica de reintentos del scraper base.

### Ejemplo: que pasa cuando probas la app

1. Abris http://localhost:3000
2. Pones patente "OZL491", provincia "CABA", click "Consultar"
3. Te redirige a la pagina de resultados con 5 items en el checklist:
   - ✅ **Calculadora de costos** — completa al instante con desglose ($545.000 para auto de $15M)
   - ✅ **Informe de dominio** — completa al instante con mensaje placeholder
   - ❌ **Deuda patentes CABA** — falla (reCAPTCHA de AGIP)
   - ❌ **VTV CABA** — falla (no existe consulta publica)
   - ❌ **Multas** — falla (Multabot sin API key)
4. Los items fallidos muestran el error y un boton "Reintentar"
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
│   ├── config.py                  # Settings (URLs de sitios, timeouts, DB)
│   ├── requirements.txt           # Dependencias Python
│   ├── .env.example               # Template de variables de entorno
│   ├── gestoria.db                # SQLite (se crea automaticamente)
│   │
│   ├── db/
│   │   ├── database.py            # Engine async + session factory + get_db dependency
│   │   ├── models.py              # ORM: Consulta, SubConsulta, enums de estado/tipo
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
│   │   └── consulta_manager.py    # Orquestador: lanza scrapers en paralelo, actualiza DB
│   │
│   ├── scrapers/
│   │   ├── base.py                # BaseScraper ABC con reintentos/timeout/backoff
│   │   ├── costos.py              # CostosScraper: wrapper de calculadora como scraper
│   │   ├── agip.py                # AGIP CABA: deuda de patentes (Playwright)
│   │   ├── arba.py                # ARBA PBA: deuda de patentes (Playwright) [skeleton]
│   │   ├── vtv_pba.py             # VTV Provincia BA (Playwright) [skeleton]
│   │   ├── vtv_caba.py            # VTV CABA (Playwright) [skeleton]
│   │   ├── multabot.py            # Multabot: multas de transito (httpx) [skeleton]
│   │   └── dnrpa_dominio.py       # DNRPA informe de dominio [placeholder]
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

## Los 7 scrapers — Estado detallado

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

### 2. AGIP — Deuda de patentes CABA — ⚠️ PARCIAL

**Archivo:** `backend/scrapers/agip.py`
**URL:** https://lb.agip.gob.ar/ConsultaPat/
**Que hace:** Consulta si un vehiculo radicado en CABA tiene deuda de patentes.
**Input:** Patente (ej: OZL491).

**Estado actual:**
- Scraper escrito con selectores reales verificados: `#fldDominio`, `#fldDominio2`, `#btnConsultar`
- Se conecta al sitio y puede interactuar con el formulario
- **PROBLEMA:** El sitio tiene Google reCAPTCHA. Sin resolver el captcha, no se puede hacer la consulta.

**Hallazgos de la investigacion:**
- El formulario tiene DOS campos de dominio (campo + confirmacion) — hay que poner la patente en ambos
- Tiene un checkbox `#chkDigitoVerificador` — si lo marcas, aparece campo para digito verificador; si no, pide que lo marques
- Se encontro API JSON interna: `POST /Empadronados/json/captcha/GetDatos` (necesita token captcha) y `POST /Empadronados/json/nocaptcha/GetDatos` (necesita sesion/key)

**Opciones para resolver:**
1. **Servicio 2captcha / anti-captcha** (~$2-3 por 1000 resoluciones) — el servicio resuelve el reCAPTCHA y devuelve el token
2. **Semi-manual** — el usuario resuelve el captcha en el frontend, el backend usa el token para la consulta
3. **Investigar la ruta nocaptcha** — puede funcionar con cookies de sesion del navegador

---

### 3. ARBA — Deuda de patentes Provincia BA — ❌ BLOQUEADO

**Archivo:** `backend/scrapers/arba.py`
**URL:** https://web.arba.gov.ar/consulta-de-deuda-automotor
**Que hace:** Consultaria si un vehiculo radicado en Provincia de Buenos Aires tiene deuda de patentes.

**Estado actual:** Skeleton con selectores genericos. No funciona.

**Problema:** La pagina de ARBA (`web.arba.gov.ar/consulta-de-deuda-automotor`) NO tiene un formulario de consulta. Es solo texto informativo con instrucciones para usar el sistema "Host" interno de ARBA. Los portales de autogestion (`arba.gov.ar/Autogestion`, `app.arba.gov.ar`) devuelven errores HTTP o no cargan.

**Opciones:**
1. Investigar si ARBA tiene otro portal funcional de consulta de deuda automotor
2. La consulta puede requerir CUIT + clave fiscal (lo cual la hace inviable para scraping anonimo)
3. Buscar fuentes alternativas de informacion de patentes PBA

---

### 4. VTV Provincia BA — ⚠️ PARCIAL

**Archivo:** `backend/scrapers/vtv_pba.py`
**URL correcta:** https://vtv.gba.gob.ar/consultar-vtv
**Que hace:** Consulta si un vehiculo tiene la VTV vigente en Provincia de Buenos Aires.

**Estado actual:** Skeleton con selectores genericos. La URL en config.py esta correcta.

**Hallazgos:**
- El formulario existe: input `#nroObleaPatente` (patente o numero de oblea) + boton `button.consultarVTV__btn`
- **Sin captcha visible**
- **PROBLEMA:** Cloudflare challenge intercepta el submit. El scraper puede llenar el formulario pero al hacer click en "Consultar", Cloudflare bloquea la request real al backend.
- API descubierta: `https://vtv-web-api.transporte.gba.gob.ar/api/` — pero no expone endpoints de consulta publica directamente.

**Opciones:**
1. Usar stealth plugins de Playwright (`playwright-stealth`) para evadir Cloudflare
2. Usar un servicio de bypass de Cloudflare (mas complejo y costoso)
3. Consultar si la API tiene endpoints accesibles con auth

---

### 5. VTV CABA — ❌ NO EXISTE

**Archivo:** `backend/scrapers/vtv_caba.py`
**URL investigada:** https://www.infovtv.com.ar/ng (404), https://www.suvtv.com.ar/turnos/ (solo turnos)
**Que hace:** Consultaria si un vehiculo tiene la VTV vigente en CABA.

**Estado:** No existe un portal publico de consulta de estado de VTV para CABA. El sitio suvtv.com.ar es solo para sacar turnos para la verificacion, no para consultar si esta vigente. infovtv.com.ar es informativo sobre VTV de Provincia, no CABA.

**Opciones:**
1. Descartar este scraper por ahora
2. Investigar si la app miBA o el sitio de Buenos Aires Ciudad tiene alguna consulta que no encontramos

---

### 6. Multabot — Multas de transito — ⚠️ PARCIAL

**Archivo:** `backend/scrapers/multabot.py`
**URL:** https://multabot.com.ar
**Que hace:** Consulta multas de transito en 150+ jurisdicciones de Argentina.

**Estado actual:** Cliente httpx apuntando a una API que no existe.

**Hallazgos:**
- Multabot **NO tiene API REST publica**. Todas las rutas `/api/...` devuelven 404 o la pagina HTML.
- SI tiene un formulario web: input `#hero-query` + boton "Consultar" — **sin captcha**
- Al hacer submit, redirige a `/pedir-informe?domain=OZL491` que pide un **email** para enviar el reporte
- Tiene proteccion **Cloudflare challenge**
- En su FAQ mencionan "API de Integracion" para empresas — hay que contactarlos

**Alternativas para multas:**
- **CABA:** https://buenosaires.gob.ar/licenciasdeconducir/consulta-de-infracciones/ (pide DNI o patente)
- **Provincia BA:** https://infraccionesba.gba.gob.ar/consulta-infraccion (pide DNI o patente)
- **Nacional (ANSV):** https://consultainfracciones.seguridadvial.gob.ar/ (pide DNI + patente + captcha)

**Opciones:**
1. Contactar a Multabot para acceso API comercial
2. Scrapear las fuentes oficiales directamente (CABA, PBA) en vez de Multabot
3. Scrapear el formulario web de Multabot (requiere resolver Cloudflare)

---

### 7. DNRPA — Informe de dominio — ✅ PLACEHOLDER

**Archivo:** `backend/scrapers/dnrpa_dominio.py`
**URL:** https://www.dnrpa.gov.ar/portal_dnrpa/guia_tramites/informe_dominio.htm
**Que hace:** Informaria si el vehiculo tiene embargos, prendas, robo, inhibiciones del titular.

**Estado actual:** Devuelve un mensaje placeholder:
```json
{
  "fuente": "dnrpa",
  "patente": "OZL491",
  "estado": "pendiente_manual",
  "nota": "El informe de dominio debe solicitarse manualmente. Tarda ~24hs y cuesta ~$1500 ARS."
}
```

**Como funciona el informe real:** Se pide online en el portal DNRPA, se paga ~$1500 ARS, y llega por email en ~24 horas. No hay API publica. Existen revendedores (dnrpa.digital, informes.app) que automatizaron el proceso.

**Opciones:**
1. Automatizar la solicitud via Playwright en el portal DNRPA
2. Integrar con un revendedor que tenga API
3. Dejarlo semi-manual: el sistema registra que se necesita, el gestor lo solicita por fuera

---

## Que hay que hacer — Proximos pasos

### Prioridad alta (desbloquean funcionalidad)

1. **Resolver captcha de AGIP** — Es el quick win mas grande. Tiene API JSON limpia, solo falta resolver el reCAPTCHA. Opciones: servicio 2captcha ($2/1000) o modo semi-manual.

2. **Scrapear multas CABA y PBA directo** — En vez de depender de Multabot, scrapear las fuentes oficiales: `buenosaires.gob.ar` para CABA y `infraccionesba.gba.gob.ar` para PBA. Hay que inspeccionar esos sitios (captcha, selectores, etc).

3. **VTV PBA: resolver Cloudflare** — El formulario existe y funciona, solo Cloudflare bloquea. Probar `playwright-stealth` o investigar la API `vtv-web-api.transporte.gba.gob.ar`.

### Prioridad media

4. **Valuaciones DNRPA** — Integrar las tablas de valuacion fiscal para que la calculadora obtenga el valor automaticamente por marca/modelo/ano en vez de usar $15M fijo. URL: `dnrpa.gov.ar/valuacion/cons_valuacion.php`

5. **ARBA** — Investigar portales alternativos o si la consulta requiere autenticacion con CUIT.

6. **DNRPA dominio** — Implementar la solicitud real (pago + asincrona).

### Prioridad baja

7. **VTV CABA** — Descartar o buscar fuente alternativa. No hay consulta publica.

8. **Mas provincias** — Agregar scrapers para Cordoba, Santa Fe, Mendoza, etc.

9. **Integracion con IA** — Interpretar resultados, recomendar si comprar o no, detectar riesgos automaticamente.

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
    ├── scrapers/                    → un modulo por fuente de datos
    │   ├── base.py                  → clase abstracta con reintentos
    │   ├── agip.py                  → Playwright + Chrome
    │   ├── arba.py                  → Playwright + Chrome
    │   ├── vtv_pba.py               → Playwright + Chrome
    │   ├── multabot.py              → httpx (API/scraping)
    │   └── ...
    └── db/ (SQLite)
        ├── consultas                → patente, provincia, timestamp
        └── sub_consultas            → tipo, estado, intentos, datos, error
```

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
