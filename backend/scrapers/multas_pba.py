"""
Scraper Multas PBA - Consulta de infracciones de transito en Provincia de Buenos Aires.
Usa Chrome real via CDP + CapSolver para resolver reCAPTCHA automaticamente.

Arquitectura del sitio (infraccionesba.gba.gob.ar):
- La pagina tiene un input #filtroDominio y un reCAPTCHA v2 standard (NO enterprise).
- El boton "Buscar" (#calltoaction) llama a busquedaPorDominio() que valida y luego
  llama a consultarPorDominio(dominio).
- consultarPorDominio() hace un jQuery AJAX POST a /consultar-infraccion con
  {dominio, reCaptcha} y renderiza el HTML de respuesta en un div #accordion.
- Problema: varios elementos del DOM referenciados por el JS no existen
  (#formularioDominio, #respuestaCor1, #flag, #accordion, #recaptcha1), causando
  que el flujo normal del boton falle silenciosamente.
- Solucion: en lugar de clickear el boton, inyectamos el token del captcha resuelto
  y ejecutamos el AJAX POST directamente desde page.evaluate().
"""

import asyncio
import logging
import re
import socket
import subprocess
import tempfile

from playwright.async_api import async_playwright
from config import settings
from scrapers.base import BaseScraper
from services import capsolver_client

logger = logging.getLogger(__name__)

MULTAS_PBA_URL = "https://infraccionesba.gba.gob.ar/consulta-infraccion"
CHROME_PATH = settings.chrome_path


def _find_free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class MultasPbaScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="multas_pba", max_retries=3, timeout=120)

    async def _ejecutar(self, patente: str, **kwargs) -> dict:
        pat = patente.upper().replace("-", "").replace(" ", "")

        port = _find_free_port()
        temp_dir = tempfile.mkdtemp(prefix="pba_multas_chrome_")
        chrome_proc = None

        try:
            # Launch Chrome with remote debugging
            chrome_proc = subprocess.Popen([
                CHROME_PATH,
                f"--remote-debugging-port={port}",
                f"--user-data-dir={temp_dir}",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "about:blank",
            ])

            await asyncio.sleep(3)

            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
                context = browser.contexts[0]
                page = await context.new_page()

                logger.info(f"Multas PBA: navegando a {MULTAS_PBA_URL}")
                await page.goto(MULTAS_PBA_URL, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)

                # --- 1. Fill the dominio input (#filtroDominio) ---
                dominio_input = await page.query_selector("input#filtroDominio")
                if not dominio_input:
                    # Fallback selectors
                    dominio_input = await page.query_selector(
                        "input[name='dominio'], "
                        "input[placeholder*='FLY'], "
                        "input[placeholder*='ominio']"
                    )
                if dominio_input and await dominio_input.is_visible():
                    await dominio_input.fill(pat)
                    logger.info(f"Multas PBA: patente {pat} ingresada en #filtroDominio")
                else:
                    # Last resort: find first visible text input in #x-domain tab
                    inputs = await page.query_selector_all('#x-domain input[type="text"]')
                    filled = False
                    for inp in inputs:
                        if await inp.is_visible():
                            await inp.fill(pat)
                            filled = True
                            break
                    if not filled:
                        raise RuntimeError("No se encontro el campo de dominio en Multas PBA")

                # --- 2. Get reCAPTCHA sitekey ---
                sitekey = await page.evaluate("""() => {
                    const el = document.querySelector('.g-recaptcha[data-sitekey]');
                    if (el) return el.getAttribute('data-sitekey');
                    const el2 = document.querySelector('[data-sitekey]');
                    if (el2) return el2.getAttribute('data-sitekey');
                    const iframe = document.querySelector('iframe[src*="recaptcha"]');
                    if (iframe) {
                        const match = iframe.src.match(/[?&]k=([^&]+)/);
                        if (match) return match[1];
                    }
                    return null;
                }""")

                if not sitekey:
                    raise RuntimeError("No se pudo obtener el sitekey de reCAPTCHA en Multas PBA")

                # This site uses standard reCAPTCHA v2 (NOT Enterprise).
                # The iframe mentions "Enterprise" only in a billing info link,
                # but the script loads from google.com/recaptcha/api.js (not enterprise.js).
                task_type = "ReCaptchaV2EnterpriseTaskProxyLess"
                logger.info(f"Multas PBA: sitekey={sitekey[:20]}..., resolviendo captcha con {task_type}")

                # --- 3. Solve captcha with CapSolver ---
                solution = await capsolver_client.solve({
                    "type": task_type,
                    "websiteURL": MULTAS_PBA_URL,
                    "websiteKey": sitekey,
                })
                captcha_token = solution["gRecaptchaResponse"]
                logger.info("Multas PBA: captcha resuelto")

                # --- 4. Patch broken DOM and call original consultarPorDominio ---
                # The site's JS needs elements that don't exist. We create them.
                result_html = await page.evaluate("""({dominio, token}) => {
                    return new Promise((resolve, reject) => {
                        // Create missing DOM elements the site's JS expects
                        if (!document.getElementById('accordion')) {
                            const div = document.createElement('div');
                            div.id = 'accordion';
                            document.body.appendChild(div);
                        }
                        if (!document.getElementById('cargando')) {
                            const div = document.createElement('div');
                            div.id = 'cargando';
                            div.className = 'hidden';
                            document.body.appendChild(div);
                        }
                        if (!document.getElementById('contexto')) {
                            const inp = document.createElement('input');
                            inp.type = 'hidden';
                            inp.id = 'contexto';
                            inp.value = '';
                            document.body.appendChild(inp);
                        }
                        if (!document.getElementById('recaptcha1')) {
                            const inp = document.createElement('input');
                            inp.type = 'hidden';
                            inp.id = 'recaptcha1';
                            inp.value = '0';
                            document.body.appendChild(inp);
                        }
                        if (!document.getElementById('respuestaCor1')) {
                            const inp = document.createElement('input');
                            inp.type = 'hidden';
                            inp.id = 'respuestaCor1';
                            inp.value = '';
                            document.body.appendChild(inp);
                        }

                        // Override grecaptcha.getResponse to return our token
                        if (typeof grecaptcha !== 'undefined') {
                            grecaptcha.getResponse = function() { return token; };
                            grecaptcha.reset = function() {};
                        }

                        // Now call the original function
                        try {
                            // The function makes the AJAX call internally
                            consultarPorDominio(dominio);
                            // Wait for the AJAX to complete by watching #accordion
                            let checks = 0;
                            const interval = setInterval(() => {
                                checks++;
                                const acc = document.getElementById('accordion');
                                if (acc && acc.innerHTML.trim().length > 10) {
                                    clearInterval(interval);
                                    resolve(acc.innerHTML);
                                } else if (checks > 20) {
                                    clearInterval(interval);
                                    resolve(acc ? acc.innerHTML : '');
                                }
                            }, 500);
                        } catch(e) {
                            reject(new Error('consultarPorDominio failed: ' + e.message));
                        }
                    });
                }""", {"dominio": pat, "token": captcha_token})

                logger.info(f"Multas PBA: respuesta AJAX recibida ({len(result_html)} chars)")

                # Also inject the result into the page for debugging / screenshot purposes
                await page.evaluate("""(html) => {
                    let container = document.getElementById('accordion');
                    if (!container) {
                        container = document.createElement('div');
                        container.id = 'accordion';
                        document.body.appendChild(container);
                    }
                    container.innerHTML = html;
                }""", result_html)

                await asyncio.sleep(1)

                # Get the plain text from the injected result for parsing
                result_text = await page.evaluate("""() => {
                    const el = document.getElementById('accordion');
                    return el ? el.innerText : '';
                }""") or ""

                await browser.close()

        finally:
            if chrome_proc:
                chrome_proc.terminate()

        return _parse_multas_pba(pat, result_text, result_html)


def _parse_multas_pba(patente: str, body_text: str, html: str = "") -> dict:
    """Parse PBA multas results from page text and/or HTML."""
    infracciones = []

    lower_text = body_text.lower()

    # Check for no infractions
    sin_infracciones = any(kw in lower_text for kw in [
        "no se encontraron",
        "sin infracciones",
        "no posee infracciones",
        "no registra",
        "0 resultado",
        "sin resultado",
        "no existen infracciones",
    ])

    has_acta = any(kw in lower_text for kw in [
        "de acta", "nro acta", "nro. acta",
        "n\u00ba de acta", "n\u00b0 de acta",
        "acta nro", "acta n\u00ba", "acta n\u00b0",
    ])

    if sin_infracciones and not has_acta:
        return {
            "fuente": "multas_pba",
            "patente": patente,
            "tiene_infracciones": False,
            "infracciones": [],
            "cantidad": 0,
            "mensaje": "No se encontraron infracciones",
        }

    # --- Strategy 1: Parse from HTML using regex on structured elements ---
    if html:
        infracciones = _parse_from_html(patente, html)

    # --- Strategy 2: Parse from plain text if HTML parsing didn't find results ---
    if not infracciones and body_text:
        infracciones = _parse_from_text(patente, body_text)

    return {
        "fuente": "multas_pba",
        "patente": patente,
        "tiene_infracciones": len(infracciones) > 0,
        "infracciones": infracciones,
        "cantidad": len(infracciones),
        "texto_raw": body_text[:3000] if not infracciones else "",
    }


def _parse_from_html(patente: str, html: str) -> list[dict]:
    """Parse infractions from the AJAX HTML response."""
    infracciones = []

    # The response is typically a series of panel/accordion blocks.
    # Try to split by panel-heading or acta blocks.
    # Common patterns in the HTML:
    #   <div class="panel-heading">... Nro Acta: XX-XXX-XXXXXXX-X ...</div>
    #   <td>label</td><td>value</td> rows inside tables

    # Pattern: split by panel blocks
    panels = re.split(r'(?=<div[^>]*class="[^"]*panel)', html, flags=re.IGNORECASE)
    if len(panels) <= 1:
        # Try splitting by heading/acta patterns
        panels = re.split(r'(?=(?:Nro?\.?\s*(?:de\s*)?Acta|panel-heading))', html, flags=re.IGNORECASE)

    for panel_html in panels:
        infraccion = _extract_infraccion_from_html_block(patente, panel_html)
        if infraccion and (infraccion.get("nro_acta") or infraccion.get("importe")):
            infracciones.append(infraccion)

    # Fallback: try to extract acta numbers with a broad regex
    if not infracciones:
        actas = re.findall(r'(\d{2}-\d{3}-\d{8,}-\d)', html)
        for acta_id in actas:
            infracciones.append({
                "nro_acta": acta_id,
                "dominio": patente,
                "fecha_generacion": "",
                "fecha_vencimiento": "",
                "importe": "",
                "estado_cupon": "",
                "estado_causa": "",
            })

    return infracciones


def _extract_infraccion_from_html_block(patente: str, block: str) -> dict | None:
    """Extract infraction data from a single HTML panel block."""
    # Strip HTML tags for text-based extraction
    text = re.sub(r'<[^>]+>', ' ', block)
    text = re.sub(r'\s+', ' ', text).strip()

    if not text:
        return None

    infraccion = {
        "nro_acta": "",
        "dominio": patente,
        "fecha_generacion": "",
        "fecha_vencimiento": "",
        "importe": "",
        "estado_cupon": "",
        "estado_causa": "",
    }

    # Acta number - multiple formats: "02-143-02083184-5", "Nro Acta: ...", etc.
    nro = re.search(
        r'(?:Nro?\.?\s*(?:de\s*)?Acta|N[°º]\s*(?:de\s*)?Acta)[:\s]*([^\s<]+(?:\s*-\s*[^\s<]+)*)',
        text, re.IGNORECASE
    )
    if not nro:
        # Try the dash-separated acta format directly
        nro = re.search(r'(\d{2}-\d{2,3}-\d{7,}-\d)', text)
    if nro:
        infraccion["nro_acta"] = nro.group(1).strip()
    else:
        return None  # No acta found in this block

    # Dominio
    dom = re.search(r'Dominio[:\s]*([A-Z0-9]+)', text, re.IGNORECASE)
    if dom:
        infraccion["dominio"] = dom.group(1).strip()

    # Fecha Generacion
    gen = re.search(r'(?:Fecha\s*(?:de\s*)?)?Generaci[oó]n[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text, re.IGNORECASE)
    if gen:
        infraccion["fecha_generacion"] = gen.group(1).strip()

    # Fecha Vencimiento
    venc = re.search(r'(?:Fecha\s*(?:de\s*)?)?Vencimiento[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text, re.IGNORECASE)
    if venc:
        infraccion["fecha_vencimiento"] = venc.group(1).strip()

    # Importe - look for currency amounts
    imp = re.search(r'Importe[:\s]*\$?\s*([\d.,]+)', text, re.IGNORECASE)
    if imp:
        infraccion["importe"] = imp.group(1).strip()

    # Estado Cupon
    ec = re.search(r'Estado\s*(?:del?\s*)?Cup[oó]n[:\s]*([A-Z\s]+?)(?:\s*(?:Estado|Importe|Fecha|Dominio|$))', text, re.IGNORECASE)
    if ec:
        infraccion["estado_cupon"] = ec.group(1).strip()

    # Estado Causa
    eca = re.search(r'Estado\s*(?:de\s*(?:la\s*)?)?Causa[:\s]*([A-Z\s]+?)(?:\s*(?:Estado|Importe|Fecha|Dominio|Nro|$))', text, re.IGNORECASE)
    if eca:
        infraccion["estado_causa"] = eca.group(1).strip()

    return infraccion


def _parse_from_text(patente: str, body_text: str) -> list[dict]:
    """Parse infractions from plain text (fallback)."""
    infracciones = []

    # Split by acta blocks using various separators
    actas_raw = re.split(r'(?=(?:Nro?\.?\s*(?:de\s*)?Acta|N[°º]\s*(?:de\s*)?Acta))', body_text, flags=re.IGNORECASE)

    for acta_text in actas_raw:
        if not re.search(r'Acta', acta_text, re.IGNORECASE):
            continue

        infraccion = {
            "nro_acta": "",
            "dominio": patente,
            "fecha_generacion": "",
            "fecha_vencimiento": "",
            "importe": "",
            "estado_cupon": "",
            "estado_causa": "",
        }

        nro = re.search(r'(?:Nro?\.?\s*(?:de\s*)?Acta|N[°º]\s*(?:de\s*)?Acta)[:\s]*([^\n]+)', acta_text, re.IGNORECASE)
        if nro:
            infraccion["nro_acta"] = nro.group(1).strip()

        dominio = re.search(r'Dominio[:\s]*([^\n]+)', acta_text, re.IGNORECASE)
        if dominio:
            infraccion["dominio"] = dominio.group(1).strip()

        generacion = re.search(r'Generaci[oó]n[:\s]*([^\n]+)', acta_text, re.IGNORECASE)
        if generacion:
            infraccion["fecha_generacion"] = generacion.group(1).strip()

        vencimiento = re.search(r'Vencimiento[:\s]*([^\n]+)', acta_text, re.IGNORECASE)
        if vencimiento:
            infraccion["fecha_vencimiento"] = vencimiento.group(1).strip()

        importe = re.search(r'Importe[:\s]*\$?\s*([\d.,]+)', acta_text, re.IGNORECASE)
        if importe:
            infraccion["importe"] = importe.group(1).strip()

        estado_cupon = re.search(r'Estado\s*Cup[oó]n[:\s]*([^\n]+)', acta_text, re.IGNORECASE)
        if estado_cupon:
            infraccion["estado_cupon"] = estado_cupon.group(1).strip()

        estado_causa = re.search(r'Estado\s*Causa[:\s]*([^\n]+)', acta_text, re.IGNORECASE)
        if estado_causa:
            infraccion["estado_causa"] = estado_causa.group(1).strip()

        # Only add if we found meaningful data
        if infraccion["nro_acta"] or infraccion["importe"]:
            infracciones.append(infraccion)

    return infracciones
