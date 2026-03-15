# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**gestorIA** is a planned AI-powered platform to automate vehicle administrative services ("gestoría automotor") in Argentina. The project is in the **research and planning phase** — no application code yet.

### Core Problem
Vehicle transfers in Argentina require 9 steps, 3-5 business days, multiple government agencies (DNRPA, AFIP, municipalities), physical presence at various offices, and a professional "gestor" to navigate it all. There is no private player offering an integrated digital end-to-end experience.

### Reference Models
Two successful international platforms were studied as benchmarks:

- **ICAR (Chile)** — B2C platform. 100% remote vehicle transfers in <48 hours using advanced electronic signatures and biometric verification. Products: icartransfer, icarcheck (vehicle history report), icarwallet. 50,000+ operations/month. Partnership with ANAC.
- **Gesthispania (Spain)** — B2B/enterprise platform. Fleet management, fines, corporate clients (Avis, Hertz, Sixt). 45,000+ procedures/year. Platforms: Gesthionline, Mira Tus Multas, Pay Your Fines. 20+ years of operation.

### Planned Phases for Argentina
1. **Phase 1 — Digital B2C Gestoría**: Guide users step-by-step through vehicle transfer. Pre-fill Form 08, coordinate police verification, manage debt clearances, transparent cost calculator, track process status. Fixed fee per service.
2. **Phase 2 — Complementary Services**: Digital vehicle report (history, debts, domain status), real-time cost calculator, seller identity verification. Like icarcheck.
3. **Phase 3 — B2B for Dealerships**: API and integration platform for used car agencies, dealerships, and finance companies for bulk transfer management. Like Gesthispania.
4. **Phase 4 — Fines & Registration Tax Management**: Traffic fine management, registration tax clearance, and other vehicle lifecycle procedures.

### The 9-Step Transfer Process (Argentina)
0. **Consulta Inicial** — Collect vehicle data, quote total costs
1. **Due Diligence** — Informe de Dominio (liens, theft, seizure), Form 13D (fines), patent debts
2. **Verificación Policial** — Physical inspection at authorized plant (chassis, motor, VIN). Mandatory for vehicles 2-12 years old. Valid 150 days.
3. **Formulario 08** — Central transfer document. Can be pre-filled digitally (08D on DNRPA portal). Contains buyer/seller data, vehicle data, declared price.
4. **Certificación de Firmas** — Both parties sign Form 08, certified by Registry official (free, reform 2024) or notary ($10K-$30K ARS).
5. **Gestión Impositiva** — DNRPA fee (1% of vehicle value), provincial stamp tax (varies: 3% in Buenos Aires), AFIP/UIF declaration if amount > ~$92M ARS.
6. **Presentación en Registro** — Full dossier submitted to any Registro Seccional nationwide (reform 2024).
7. **Emisión de Documentación** — New title + green card issued to buyer (24-48 business hours).
8. **Post-Transferencia** — Insurance, patent ownership change, GNC sticker if applicable, seller de-registration.

### Key Regulatory Context (2026)
- Government (DNU 70/2023) is actively deregulating: reduced fees to 1%, eliminated charges for cards/titles/stamps, freed geographic restrictions on Registry choice.
- 70% of transfers already processed digitally via DNRPA Digital.
- No advanced electronic signature available yet for vehicle transfers (unlike Chile's Clave Única).
- Announced closure of 40% of Registros Automotores (not yet fully executed).

### Existing Competitors in Argentina
- **Traditional gestorías** (RAM, Integral Norte, ACA) — physical, slow, poor UX
- **Quicktram S.A.** — 20+ years, claims innovation but mostly traditional
- **Autoforms** — B2B software for gestorías, automates 135 electronic forms (not a B2C platform)
- **El Cero Km** — 100% digital new car sales (not used car transfers), has online cost calculator

**No direct ICAR/Gesthispania equivalent exists in Argentina.** This is the market gap.

## Repository Contents

- `Investigacion_Gestoria_Digital_Automotor.docx` — Market research: ICAR (Chile) and Gesthispania (Spain) models, Argentine market analysis, proposed phases
- `Tutorial_Transferencia_Vehicular_Argentina.docx` — Complete step-by-step guide of what a gestor does during a vehicle transfer, costs, timelines, digitalization opportunities
- `Diagrama_Transferencia_Vehicular.html` — Interactive flowchart of the 9-step vehicle transfer process (standalone HTML, dark theme)
- `grabacion_*.txt` — Meeting transcriptions (project discussions)

## Language

All domain content and documents are in **Spanish (Argentine)**. The product targets the Argentine automotive market.
