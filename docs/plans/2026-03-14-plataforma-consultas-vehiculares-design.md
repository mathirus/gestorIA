# Plataforma de Consultas Vehiculares — Documento de Diseno

**Fecha:** 2026-03-14
**Proyecto:** gestorIA
**Estado:** Aprobado

## Contexto

gestorIA es un gestor digital automotor con IA para Argentina. Esta es la primera pieza concreta: una plataforma web donde se ingresa una patente y se obtienen todos los datos del vehiculo en un solo lugar, ejecutando consultas en paralelo a multiples fuentes.

Esto es el paso 0 y 1 del proceso de transferencia vehicular: consulta de costos y due diligence del vehiculo. Eventualmente, esta plataforma sera la base sobre la que se construye el gestor IA completo.

## Que hace

El usuario ingresa una patente y provincia. La plataforma ejecuta hasta 7 consultas en paralelo y muestra los resultados en un checklist en tiempo real:

1. **Calculadora de costos** — calculo propio con tablas DNRPA + alicuotas provinciales
2. **Deuda patentes CABA** — scraping AGIP (lb.agip.gob.ar/ConsultaPat/)
3. **Deuda patentes PBA** — scraping ARBA (web.arba.gov.ar/consulta-de-deuda-automotor)
4. **VTV Provincia BA** — scraping vtv.gba.gov.ar/consultar-vtv
5. **VTV CABA** — scraping infovtv.com.ar/ng
6. **Multas** — API REST Multabot (multabot.com.ar/api)
7. **Informe de dominio** — solicitud DNRPA (asincrono, ~24hs, pago)

Segun la provincia seleccionada, se ejecutan las consultas correspondientes (AGIP para CABA, ARBA para PBA, etc.).

## Stack

- **Backend:** Python + FastAPI
- **Scraping:** Playwright (navegador headless para manejar JS, formularios dinamicos)
- **Frontend:** Next.js (React)
- **Base de datos:** PostgreSQL
- **Infraestructura:** Digital Ocean

## Arquitectura

```
Frontend (Next.js)
    │
    │ REST API (polling cada 10s)
    ▼
Backend (FastAPI)
    ├── consulta_manager (orquesta scrapers en paralelo con asyncio)
    ├── scrapers/ (un modulo por fuente)
    ├── services/calculadora (calculo de costos)
    └── db (PostgreSQL)
```

### Flujo

1. Usuario ingresa patente + provincia
2. Frontend llama POST /api/consulta con los datos
3. Backend crea un registro de consulta en la DB y lanza scrapers en paralelo
4. Frontend hace polling GET /api/consulta/{id} cada 10 segundos
5. A medida que cada scraper termina, actualiza su estado en la DB
6. Frontend muestra el checklist actualizandose en tiempo real
7. Cuando todo termina (o falla), el polling se detiene

### Estados de cada consulta

```
PENDIENTE → EJECUTANDO → COMPLETADO (con datos)
                       → FALLIDO (con razon del error)
                       → REINTENTANDO (intento 2/3 o 3/3)
```

- 3 reintentos automaticos con backoff (2s, 8s, 20s)
- Timeout de 30 segundos por scraper
- Reintento manual disponible para el usuario en consultas fallidas
- El informe de dominio tiene estado especial: PENDIENTE_24HS

### Manejo de errores

Cada intento se guarda en la DB con:
- Timestamp
- Estado (exito/fallo)
- Mensaje de error si fallo (timeout, sitio caido, captcha, estructura HTML cambio, etc.)
- Datos obtenidos si tuvo exito

Esto permite diagnosticar problemas: si un scraper empieza a fallar consistentemente, sabemos que el sitio cambio y hay que actualizar el scraper.

## Estructura del proyecto

```
gestorIA/
├── backend/
│   ├── main.py                  # FastAPI app, CORS, lifespan
│   ├── config.py                # URLs de sitios, timeouts, reintentos, API keys
│   ├── models/
│   │   ├── consulta.py          # Estado general de una consulta
│   │   ├── costos.py            # Schema resultado calculadora
│   │   ├── patentes.py          # Schema resultado deuda patentes
│   │   ├── vtv.py               # Schema resultado VTV
│   │   ├── multas.py            # Schema resultado multas
│   │   └── dominio.py           # Schema resultado informe dominio
│   ├── scrapers/
│   │   ├── base.py              # Clase base con logica de reintentos/timeout
│   │   ├── agip.py              # Scraper AGIP CABA
│   │   ├── arba.py              # Scraper ARBA PBA
│   │   ├── vtv_pba.py           # Scraper VTV provincia
│   │   ├── vtv_caba.py          # Scraper VTV CABA
│   │   ├── multabot.py          # Cliente API Multabot
│   │   └── dnrpa_dominio.py     # Solicitud informe dominio
│   ├── services/
│   │   ├── calculadora.py       # Logica de calculo de costos
│   │   ├── consulta_manager.py  # Orquesta scrapers, maneja estados
│   │   └── valuaciones.py       # Cache/tablas valuacion DNRPA
│   ├── db/
│   │   ├── database.py          # Conexion PostgreSQL (SQLAlchemy async)
│   │   ├── models.py            # Modelos de tablas
│   │   └── migrations/          # Alembic
│   └── routes/
│       ├── consulta.py          # POST/GET /api/consulta
│       └── costos.py            # GET /api/costos (standalone)
├── frontend/
│   └── (Next.js app)
├── docs/
│   └── plans/
└── docker-compose.yml           # PostgreSQL + backend + frontend
```

## Datos capturados por scraper

Cada scraper obtiene TODO lo que el sitio devuelve. Los schemas de Pydantic se definen despues de inspeccionar cada sitio. Lo que esperamos segun la investigacion:

- **Calculadora:** valuacion fiscal, arancel DNRPA, sellos provinciales, verificacion, total
- **AGIP/ARBA:** cuotas pendientes, montos, vencimientos, total adeudado
- **VTV:** fecha ultima verificacion, vigencia, resultado, planta, kilometros
- **Multabot:** lista de infracciones con jurisdiccion, fecha, monto, estado
- **DNRPA dominio:** titular, prendas, embargos, robo, inhibiciones, datos vehiculo

## Fuera de scope (por ahora)

- Autenticacion de usuarios / login
- Pagos online
- Integracion con IA
- Formulario 08 digital
- Soporte para provincias fuera de CABA/PBA (se agrega despues)
- App mobile
