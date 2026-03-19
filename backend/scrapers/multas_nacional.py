"""
Scraper ANSV - Consulta de infracciones nacionales (SINAI).
Usa Chrome real via CDP + CapSolver para resolver reCAPTCHA.
NOTA: ANSV requiere DNI + genero, no patente. Se usa DNI del kwargs o default.
"""

import asyncio
import logging
import os
import re
import socket
import subprocess
import tempfile

from playwright.async_api import async_playwright
from scrapers.base import BaseScraper
from services import capsolver_client

logger = logging.getLogger(__name__)

ANSV_URL = "https://consultainfracciones.seguridadvial.gob.ar/"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# DNI por defecto para consultas (configurable via kwargs)
DEFAULT_DNI = "47700071"
DEFAULT_GENERO = "masculino"


def _find_free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class MultasNacionalScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="multas_nacional", max_retries=3, timeout=150)

    async def _ejecutar(self, patente: str, **kwargs) -> dict:
        dni = kwargs.get("dni", DEFAULT_DNI)
        genero = kwargs.get("genero", DEFAULT_GENERO)

        # Mapear genero al indice del radio button ASP.NET
        # rdioSexo_0 = Femenino, rdioSexo_1 = Masculino, rdioSexo_2 = No Binario
        genero_idx = "1"  # masculino
        if "fem" in genero.lower():
            genero_idx = "0"
        elif "no" in genero.lower() or "binari" in genero.lower():
            genero_idx = "2"

        port = _find_free_port()
        temp_dir = tempfile.mkdtemp(prefix="ansv_chrome_")
        chrome_proc = None

        try:
            chrome_proc = subprocess.Popen([
                CHROME_PATH,
                f"--remote-debugging-port={port}",
                f"--user-data-dir={temp_dir}",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-background-timer-throttling",
                "about:blank",
            ])

            await asyncio.sleep(3)

            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
                context = browser.contexts[0]
                page = await context.new_page()

                logger.info(f"ANSV: navegando a {ANSV_URL}")
                await page.goto(ANSV_URL, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)

                # Fill DNI - find the documento input (not the dominio one)
                await page.evaluate(f"""(dni) => {{
                    const input = document.getElementById('ctl00_ContentPlaceHolder1_txDocumento');
                    if (input) {{
                        input.value = dni;
                        input.dispatchEvent(new Event('input', {{bubbles: true}}));
                        input.dispatchEvent(new Event('change', {{bubbles: true}}));
                    }}
                }}""", dni)

                # Select gender via JS
                await page.evaluate(f"""(idx) => {{
                    const radio = document.getElementById('ctl00_ContentPlaceHolder1_rdioSexo_' + idx);
                    if (radio) {{
                        radio.checked = true;
                        radio.dispatchEvent(new Event('change', {{bubbles: true}}));
                        radio.dispatchEvent(new Event('click', {{bubbles: true}}));
                    }}
                    // Also click the label
                    const label = document.querySelector('label[for="ctl00_ContentPlaceHolder1_rdioSexo_' + idx + '"]');
                    if (label) label.click();
                }}""", genero_idx)

                logger.info(f"ANSV: DNI={dni}, genero idx={genero_idx}")

                # Get reCAPTCHA sitekey
                sitekey = await page.evaluate("""() => {
                    const el = document.querySelector('[data-sitekey]');
                    if (el) return el.getAttribute('data-sitekey');
                    const iframe = document.querySelector('iframe[src*="recaptcha"]');
                    if (iframe) {
                        const match = iframe.src.match(/[?&]k=([^&]+)/);
                        if (match) return match[1];
                    }
                    return null;
                }""")

                if not sitekey:
                    raise RuntimeError("No se pudo obtener sitekey de reCAPTCHA en ANSV")

                # Solve captcha
                logger.info(f"ANSV: sitekey={sitekey[:20]}..., resolviendo captcha")
                solution = await capsolver_client.solve({
                    "type": "ReCaptchaV2TaskProxyLess",
                    "websiteURL": ANSV_URL,
                    "websiteKey": sitekey,
                })
                captcha_token = solution["gRecaptchaResponse"]
                logger.info("ANSV: captcha resuelto")

                # Inject token
                await page.evaluate("""(token) => {
                    const ta = document.querySelector('#g-recaptcha-response');
                    if (ta) {
                        ta.style.display = 'block';
                        ta.value = token;
                    }
                    document.querySelectorAll('textarea[name="g-recaptcha-response"]').forEach(el => {
                        el.value = token;
                    });
                }""", captcha_token)

                await asyncio.sleep(1)

                # Click "Consultar infracciones" - ASP.NET PostBack
                # Track navigation
                navigated = asyncio.Event()

                def on_navigated(frame):
                    if frame == page.main_frame:
                        navigated.set()

                page.on("framenavigated", on_navigated)

                btn = await page.query_selector('#ctl00_ContentPlaceHolder1_btnConsultar, button:has-text("Consultar"), input[type="submit"]')
                if btn:
                    await btn.click()
                else:
                    await page.evaluate("""() => {
                        const btn = document.querySelector('input[type="submit"], button[type="submit"]');
                        if (btn) btn.click();
                    }""")

                logger.info("ANSV: boton clickeado, esperando PostBack")

                # Wait for page reload (ASP.NET PostBack)
                try:
                    await asyncio.wait_for(navigated.wait(), timeout=30)
                except asyncio.TimeoutError:
                    pass

                await asyncio.sleep(3)

                # Get result page text
                body_text = await page.evaluate("() => document.body.innerText") or ""

                await browser.close()

        finally:
            if chrome_proc:
                chrome_proc.terminate()

        return _parse_ansv(patente, dni, body_text)


def _parse_ansv(patente: str, dni: str, text: str) -> dict:
    """Parse ANSV results."""
    infracciones = []

    # Check if no infractions
    lower = text.lower()
    sin_infracciones = any(kw in lower for kw in [
        "no se hallaron", "no se encontraron", "sin infracciones",
        "no registra infracciones", "no posee infracciones",
    ])

    if sin_infracciones:
        return {
            "fuente": "multas_nacional",
            "patente": patente,
            "dni": dni,
            "tiene_infracciones": False,
            "infracciones": [],
            "cantidad": 0,
            "mensaje": "No se encontraron infracciones nacionales",
        }

    # Check if page didn't change (still shows form = no results or captcha failed)
    if "Ingres" in text and "datos personales" in text and "Consultar infracciones" in text:
        # Check if there are result elements too (sometimes results show below form)
        if "Acta" not in text and "infraccion" not in text.lower().replace("consulta de infracciones", ""):
            return {
                "fuente": "multas_nacional",
                "patente": patente,
                "dni": dni,
                "tiene_infracciones": False,
                "infracciones": [],
                "cantidad": 0,
                "mensaje": "Sin infracciones nacionales registradas",
            }

    # Try to parse infractions
    acta_blocks = re.split(r'(?=Acta|N[°º]\s*\d)', text)
    for block in acta_blocks:
        if len(block) < 15:
            continue
        infraccion = {}
        nro = re.search(r'(?:Acta|N[°º])\s*[:\s]*([^\n]+)', block)
        if nro:
            infraccion["nro_acta"] = nro.group(1).strip()
        jurisdiccion = re.search(r'Jurisdicci[oó]n[:\s]*([^\n]+)', block)
        if jurisdiccion:
            infraccion["jurisdiccion"] = jurisdiccion.group(1).strip()
        fecha = re.search(r'Fecha[:\s]*([^\n]+)', block)
        if fecha:
            infraccion["fecha"] = fecha.group(1).strip()
        monto = re.search(r'(?:Monto|Importe)[:\s]*\$?\s*([\d.,]+)', block)
        if monto:
            infraccion["monto"] = monto.group(1).strip()
        estado = re.search(r'Estado[:\s]*([^\n]+)', block)
        if estado:
            infraccion["estado"] = estado.group(1).strip()
        if infraccion:
            infracciones.append(infraccion)

    # Parse from tables
    if not infracciones:
        rows = re.findall(r'(?:(?:\d+[/.-]\d+[/.-]\d+).*?(?:\$[\d.,]+|[A-Z]{2,}))', text)
        for row in rows:
            infracciones.append({"texto": row.strip()})

    # If still no infractions found, it means no national infractions
    if not infracciones:
        return {
            "fuente": "multas_nacional",
            "patente": patente,
            "dni": dni,
            "tiene_infracciones": False,
            "infracciones": [],
            "cantidad": 0,
            "mensaje": "Sin infracciones nacionales registradas",
        }

    return {
        "fuente": "multas_nacional",
        "patente": patente,
        "dni": dni,
        "tiene_infracciones": True,
        "infracciones": infracciones,
        "cantidad": len(infracciones),
    }
