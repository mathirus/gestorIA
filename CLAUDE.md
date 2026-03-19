# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**gestorIA** is an AI-powered platform that automates vehicle administrative services ("gestoria automotor") in Argentina. The system scrapes multiple government websites to gather vehicle information (debts, fines, VTV status, domain records) and presents it in a unified dashboard. **7 out of 9 scrapers are fully working** with automatic captcha resolution via CapSolver — no human intervention needed.

### Core Problem
Vehicle transfers in Argentina require 9 steps, 3-5 business days, multiple government agencies (DNRPA, AFIP, municipalities), physical presence at various offices, and a professional "gestor" to navigate it all. There is no private player offering an integrated digital end-to-end experience.

### Reference Models
Two successful international platforms were studied as benchmarks:

- **ICAR (Chile)** — B2C platform. 100% remote vehicle transfers in <48 hours using advanced electronic signatures and biometric verification. Products: icartransfer, icarcheck (vehicle history report), icarwallet. 50,000+ operations/month. Partnership with ANAC.
- **Gesthispania (Spain)** — B2B/enterprise platform. Fleet management, fines, corporate clients (Avis, Hertz, Sixt). 45,000+ procedures/year. Platforms: Gesthionline, Mira Tus Multas, Pay Your Fines. 20+ years of operation.

### Planned Phases for Argentina
1. **Phase 1 — Digital B2C Gestoria**: Guide users step-by-step through vehicle transfer. Pre-fill Form 08, coordinate police verification, manage debt clearances, transparent cost calculator, track process status. Fixed fee per service.
2. **Phase 2 — Complementary Services**: Digital vehicle report (history, debts, domain status), real-time cost calculator, seller identity verification. Like icarcheck.
3. **Phase 3 — B2B for Dealerships**: API and integration platform for used car agencies, dealerships, and finance companies for bulk transfer management. Like Gesthispania.
4. **Phase 4 — Fines & Registration Tax Management**: Traffic fine management, registration tax clearance, and other vehicle lifecycle procedures.

### The 9-Step Transfer Process (Argentina)
0. **Consulta Inicial** — Collect vehicle data, quote total costs
1. **Due Diligence** — Informe de Dominio (liens, theft, seizure), Form 13D (fines), patent debts
2. **Verificacion Policial** — Physical inspection at authorized plant (chassis, motor, VIN). Mandatory for vehicles 2-12 years old. Valid 150 days.
3. **Formulario 08** — Central transfer document. Can be pre-filled digitally (08D on DNRPA portal). Contains buyer/seller data, vehicle data, declared price.
4. **Certificacion de Firmas** — Both parties sign Form 08, certified by Registry official (free, reform 2024) or notary ($10K-$30K ARS).
5. **Gestion Impositiva** — DNRPA fee (1% of vehicle value), provincial stamp tax (varies: 3% in Buenos Aires), AFIP/UIF declaration if amount > ~$92M ARS.
6. **Presentacion en Registro** — Full dossier submitted to any Registro Seccional nationwide (reform 2024).
7. **Emision de Documentacion** — New title + green card issued to buyer (24-48 business hours).
8. **Post-Transferencia** — Insurance, patent ownership change, GNC sticker if applicable, seller de-registration.

### Key Regulatory Context (2026)
- Government (DNU 70/2023) is actively deregulating: reduced fees to 1%, eliminated charges for cards/titles/stamps, freed geographic restrictions on Registry choice.
- 70% of transfers already processed digitally via DNRPA Digital.
- No advanced electronic signature available yet for vehicle transfers (unlike Chile's Clave Unica).
- Announced closure of 40% of Registros Automotores (not yet fully executed).

### Existing Competitors in Argentina
- **Traditional gestorias** (RAM, Integral Norte, ACA) — physical, slow, poor UX
- **Quicktram S.A.** — 20+ years, claims innovation but mostly traditional
- **Autoforms** — B2B software for gestorias, automates 135 electronic forms (not a B2C platform)
- **El Cero Km** — 100% digital new car sales (not used car transfers), has online cost calculator

**No direct ICAR/Gesthispania equivalent exists in Argentina.** This is the market gap.

## Repository Contents

- `backend/` — FastAPI application with async scrapers, database models, and REST API
  - `main.py` — FastAPI app, lifespan, CORS, scraper registration
  - `config.py` — Settings (URLs, timeouts, DB, capsolver_api_key)
  - `run.py` — Windows wrapper for uvicorn (sets ProactorEventLoop)
  - `requirements.txt` — Python dependencies
  - `db/` — SQLAlchemy async engine, ORM models (Consulta, SubConsulta, TipoConsulta enum)
  - `models/` — Pydantic schemas
  - `routes/` — REST endpoints (consulta CRUD, retry)
  - `services/` — Business logic (calculadora, alicuotas, consulta_manager, capsolver_client)
  - `scrapers/` — One module per data source (agip, vtv_pba, vtv_caba, dnrpa_dominio, multas_caba, multas_pba, multas_nacional, costos, arba)
  - `tests/` — pytest tests for calculadora and scraper base
- `frontend/` — Next.js 16 / TypeScript / Tailwind CSS application
- `docs/plans/` — Design documents and implementation plans
- `docker-compose.yml` — PostgreSQL for production
- `Investigacion_Gestoria_Digital_Automotor.docx` — Market research: ICAR (Chile) and Gesthispania (Spain) models, Argentine market analysis
- `Tutorial_Transferencia_Vehicular_Argentina.docx` — Complete step-by-step guide of the 9-step transfer process
- `Diagrama_Transferencia_Vehicular.html` — Interactive flowchart of the transfer process (standalone HTML)
- `grabacion_*.txt` — Meeting transcriptions

## How to Run

### Backend (Windows)
```bash
cd backend
pip install -r requirements.txt
python run.py
# Runs on http://localhost:8000
```
**Important:** On Windows, use `python run.py` instead of `uvicorn main:app` directly. The wrapper sets up ProactorEventLoop which is required for async subprocess operations.

### Frontend
```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:3000
```

### Environment Variables
The backend needs a `.env` file with:
- `DATABASE_URL` — SQLite for dev (default), PostgreSQL for prod
- `capsolver_api_key` — CapSolver API key for automatic captcha resolution

## Architecture

### Captcha Resolution
All captcha-protected scrapers use **CapSolver** for fully automatic resolution:
- **reCAPTCHA v2**: AGIP, VTV CABA, ANSV Nacional
- **reCAPTCHA Enterprise**: Multas CABA
- **Cloudflare Turnstile**: VTV PBA
- **Image OCR (ddddocr)**: DNRPA dominio (free, no CapSolver needed)

### Browser Strategies
Scrapers use different approaches depending on the target site:
- **Chrome CDP** (subprocess.Popen Chrome + connect_over_cdp): For sites with Cloudflare/headless detection (DNRPA, Multas CABA, ANSV)
- **Playwright headless with channel="chrome"**: For sites without strong bot detection (AGIP)
- **httpx direct API calls**: For sites where the API endpoint was discovered (VTV PBA, VTV CABA) — fastest, no browser needed

### Scraper Status (as of 2026-03-19)
| # | Scraper | Status | Captcha Method |
|---|---------|--------|----------------|
| 1 | AGIP (patentes CABA) | WORKING | CapSolver reCAPTCHA v2 + Playwright |
| 2 | VTV PBA | WORKING | CapSolver Turnstile + httpx API |
| 3 | VTV CABA | WORKING | CapSolver reCAPTCHA v2 + httpx API |
| 4 | Costos | WORKING | No captcha (local calculation) |
| 5 | DNRPA dominio | WORKING | ddddocr OCR + Chrome CDP |
| 6 | Multas CABA | WORKING | CapSolver reCAPTCHA Enterprise + Chrome CDP |
| 7 | ANSV Nacional | WORKING | CapSolver reCAPTCHA v2 + Chrome CDP |
| 8 | Multas PBA | PARTIAL | Enterprise captcha token sometimes rejected |
| 9 | ARBA (patentes PBA) | PAUSED | Requires CUIT+CIT credentials |

## Language

All domain content and documents are in **Spanish (Argentine)**. The product targets the Argentine automotive market.
