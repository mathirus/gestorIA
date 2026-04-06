"""
Scraper DNRPA Dominio - Consulta de radicacion de vehiculo por dominio.
Usa Chrome real via CDP + ddddocr para resolver captcha de imagen.
Los resultados se abren en una ventana popup, capturada via context.on("page").
"""

import asyncio
import logging
import os
import re
import socket
import subprocess
import tempfile

import ddddocr
from playwright.async_api import async_playwright
from config import settings
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

DNRPA_URL = "https://www.dnrpa.gov.ar/portal_dnrpa/radicacion2.php"
CHROME_PATH = settings.chrome_path


def _find_free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class DnrpaDominioScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="dnrpa_dominio", max_retries=3, timeout=120)

    async def _ejecutar(self, patente: str, **kwargs) -> dict:
        pat = patente.upper().replace("-", "").replace(" ", "")

        port = _find_free_port()
        temp_dir = tempfile.mkdtemp(prefix="dnrpa_chrome_")
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

                logger.info(f"DNRPA: navegando a {DNRPA_URL}")
                await page.goto(DNRPA_URL, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)

                # Find captcha image - it's inline base64 (data:image/png;base64,...)
                captcha_b64 = await page.evaluate("""() => {
                    const img = document.querySelector('img[alt*="digo verificador"]')
                        || document.querySelector('img[alt*="Codigo"]');
                    if (img && img.src && img.src.startsWith('data:image')) {
                        return img.src.split(',')[1];
                    }
                    // Fallback: find any base64 image in tables
                    const imgs = document.querySelectorAll('table img');
                    for (const i of imgs) {
                        if (i.src && i.src.startsWith('data:image')) {
                            return i.src.split(',')[1];
                        }
                    }
                    return null;
                }""")

                if not captcha_b64:
                    raise RuntimeError("No se encontro la imagen de captcha en DNRPA")

                # Decode base64 and solve with OCR
                import base64
                captcha_bytes = base64.b64decode(captcha_b64)
                ocr = ddddocr.DdddOcr(show_ad=False)
                captcha_text = ocr.classification(captcha_bytes)
                if not captcha_text:
                    raise RuntimeError("OCR no pudo resolver el captcha")

                logger.info(f"DNRPA: OCR resolvio captcha: {captcha_text}")

                # Fill form fields - find visible text inputs in the table
                inputs = await page.query_selector_all("table input[type='text']")
                visible_inputs = []
                for inp in inputs:
                    if await inp.is_visible():
                        visible_inputs.append(inp)

                if len(visible_inputs) < 2:
                    # Fallback: try all text inputs
                    all_inputs = await page.query_selector_all("input[type='text']")
                    visible_inputs = []
                    for inp in all_inputs:
                        if await inp.is_visible():
                            visible_inputs.append(inp)

                if len(visible_inputs) < 2:
                    raise RuntimeError("No se encontraron los campos del formulario DNRPA")

                # First input = dominio, second = captcha code
                await visible_inputs[0].fill(pat)
                await visible_inputs[1].fill(captcha_text)
                logger.info(f"DNRPA: formulario llenado con dominio={pat}, captcha={captcha_text}")

                # Set up popup capture BEFORE clicking submit
                popup_future = asyncio.get_event_loop().create_future()

                async def on_new_page(new_page):
                    if not popup_future.done():
                        popup_future.set_result(new_page)

                context.on("page", on_new_page)

                # Click the "Consultar" button - specifically the one in the radicacion form
                # It's an input[type="button"] with value "Consultar" inside a table
                await page.evaluate("""() => {
                    // Find the Consultar button specifically (not the search form submit)
                    const buttons = document.querySelectorAll('input[type="button"], input[type="submit"], button');
                    for (const btn of buttons) {
                        const val = (btn.value || btn.textContent || '').trim();
                        if (val === 'Consultar' && btn.closest('table')) {
                            btn.click();
                            return true;
                        }
                    }
                    // Fallback: find button with onclick that has submit/consultar
                    for (const btn of buttons) {
                        const onclick = btn.getAttribute('onclick') || '';
                        if (onclick.includes('submit') || onclick.includes('consultar')) {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                }""")
                logger.info("DNRPA: boton Consultar clickeado, esperando popup")

                # Wait for popup window
                popup_page = None
                try:
                    popup_page = await asyncio.wait_for(popup_future, timeout=15)
                except asyncio.TimeoutError:
                    # Popup may not have opened; check all pages in context
                    logger.warning("DNRPA: timeout esperando popup, buscando en paginas existentes")

                # Get result text - check popup first, then all context pages
                result_text = ""

                if popup_page:
                    try:
                        await popup_page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        pass
                    await asyncio.sleep(2)
                    try:
                        result_text = await popup_page.evaluate("() => document.body.innerText") or ""
                    except Exception:
                        pass

                # If popup didn't yield results, check all pages
                if not result_text or len(result_text) < 30:
                    for pg in context.pages:
                        try:
                            txt = await pg.evaluate("() => document.body.innerText") or ""
                            if "Registro Seccional" in txt or "RADICACION" in txt.upper():
                                result_text = txt
                                break
                            if "incorrecto" in txt.lower():
                                result_text = txt
                                break
                        except Exception:
                            continue

                # Fallback to current page
                if not result_text or len(result_text) < 30:
                    result_text = await page.evaluate("() => document.body.innerText") or ""

                if not result_text or len(result_text) < 30:
                    raise RuntimeError("No se obtuvieron resultados de DNRPA")

                # Check for captcha error
                if "incorrecto" in result_text.lower() or "ya utilizado" in result_text.lower():
                    raise RuntimeError("Captcha incorrecto o expirado")

                # Check if still on form page
                if "digo verificador" in result_text.lower() and "Registro Seccional" not in result_text:
                    raise RuntimeError("Captcha incorrecto (pagina no cambio)")

                logger.info("DNRPA: resultados obtenidos, parseando")

                await browser.close()

        finally:
            if chrome_proc:
                chrome_proc.terminate()

        return _parse_dnrpa(pat, result_text)


def _parse_dnrpa(patente: str, result_text: str) -> dict:
    """Parse DNRPA radicacion results from page text."""
    result = {
        "fuente": "dnrpa",
        "patente": patente,
        "encontrado": True,
        "registro_seccional": "",
        "localidad": "",
        "provincia": "",
        "direccion": "",
        "tipo_vehiculo": "",
    }

    # Check if not found
    if "no se encontr" in result_text.lower() or "sin resultado" in result_text.lower():
        result["encontrado"] = False
        return result

    # Parse fields using regex
    reg = re.search(r"Registro Seccional[.\s:]*([^\n]+)", result_text)
    if reg:
        result["registro_seccional"] = reg.group(1).strip()

    loc = re.search(r"Localidad[.\s:]*([^\t\n]+)", result_text)
    if loc:
        result["localidad"] = loc.group(1).strip()

    prov = re.search(r"Provincia[.\s:]*([^\n]+)", result_text)
    if prov:
        result["provincia"] = prov.group(1).strip()

    dir_match = re.search(r"Direcci[oó]n[.\s:]*([^\n]+)", result_text)
    if dir_match:
        result["direccion"] = dir_match.group(1).strip()

    tipo = re.search(r"Tipo de Veh[ií]culo[.\s:]*([^\n]+)", result_text)
    if tipo:
        result["tipo_vehiculo"] = tipo.group(1).strip()

    # If none of the key fields were found, mark as not found
    if not any([result["registro_seccional"], result["localidad"], result["provincia"]]):
        result["encontrado"] = False
        result["texto_raw"] = result_text[:3000]

    return result
