"""
Scraper Multas CABA - Consulta de infracciones de transito en CABA.
Usa Chrome real via CDP + CapSolver para resolver reCAPTCHA automaticamente.
"""

import asyncio
import logging
import os
import re
import socket
import subprocess
import tempfile

from playwright.async_api import async_playwright
from config import settings
from scrapers.base import BaseScraper
from services import capsolver_client

logger = logging.getLogger(__name__)

MULTAS_CABA_URL = "https://buenosaires.gob.ar/licenciasdeconducir/consulta-de-infracciones/?actas=transito"
CHROME_PATH = settings.chrome_path


def _find_free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class MultasCabaScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="multas_caba", max_retries=3, timeout=150)

    async def _ejecutar(self, patente: str, **kwargs) -> dict:
        pat = patente.upper().replace("-", "").replace(" ", "")

        port = _find_free_port()
        temp_dir = tempfile.mkdtemp(prefix="caba_multas_chrome_")
        chrome_proc = None

        try:
            # Launch Chrome with remote debugging
            chrome_proc = subprocess.Popen([
                CHROME_PATH,
                f"--remote-debugging-port={port}",
                f"--user-data-dir={temp_dir}",
                "--headless=new",
                "--no-sandbox",
                "--disable-dev-shm-usage",
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

                # Intercept AJAX responses from Drupal
                ajax_responses = []

                async def handle_response(response):
                    url = response.url
                    if ("system/ajax" in url or "infracciones" in url) and response.status == 200:
                        try:
                            ct = response.headers.get("content-type", "")
                            if "json" in ct or "html" in ct:
                                body = await response.text()
                                ajax_responses.append({"url": url, "body": body})
                        except Exception:
                            pass

                page.on("response", handle_response)

                logger.info(f"Multas CABA: navegando a {MULTAS_CABA_URL}")
                await page.goto(MULTAS_CABA_URL, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)

                # Click radio button "Una patente"
                await page.click("text=Una patente")
                await asyncio.sleep(2)

                # Fill the patente input
                dominio_input = await page.query_selector('input[name*="dominio"], input[name*="patente"]')
                if dominio_input:
                    await dominio_input.fill(pat)
                else:
                    # Fallback: find visible text inputs
                    inputs = await page.query_selector_all('input[type="text"]')
                    for inp in inputs:
                        if await inp.is_visible():
                            await inp.fill(pat)
                            break

                logger.info(f"Multas CABA: patente {pat} ingresada, buscando sitekey")

                # Get reCAPTCHA sitekey
                sitekey = await page.evaluate("""() => {
                    const el = document.querySelector('[data-sitekey]');
                    if (el) return el.getAttribute('data-sitekey');
                    const gre = document.querySelector('.g-recaptcha');
                    if (gre) return gre.getAttribute('data-sitekey');
                    const iframe = document.querySelector('iframe[src*="recaptcha"]');
                    if (iframe) {
                        const match = iframe.src.match(/[?&]k=([^&]+)/);
                        if (match) return match[1];
                    }
                    return null;
                }""")

                if not sitekey:
                    raise RuntimeError("No se pudo obtener el sitekey de reCAPTCHA en Multas CABA")

                # Detect if Enterprise
                is_enterprise = await page.evaluate("""() => {
                    const scripts = document.querySelectorAll('script[src*="recaptcha"]');
                    for (const s of scripts) {
                        if (s.src.includes('enterprise')) return true;
                    }
                    const iframes = document.querySelectorAll('iframe[src*="recaptcha"]');
                    for (const f of iframes) {
                        if (f.src.includes('enterprise')) return true;
                    }
                    return false;
                }""")

                task_type = "ReCaptchaV2EnterpriseTaskProxyLess" if is_enterprise else "ReCaptchaV2TaskProxyLess"
                logger.info(f"Multas CABA: sitekey={sitekey[:20]}..., enterprise={is_enterprise}, resolviendo captcha")

                # Solve captcha with CapSolver
                solution = await capsolver_client.solve({
                    "type": task_type,
                    "websiteURL": MULTAS_CABA_URL,
                    "websiteKey": sitekey,
                })
                captcha_token = solution["gRecaptchaResponse"]
                logger.info("Multas CABA: captcha resuelto")

                # Inject token and trigger callback
                await page.evaluate("""(token) => {
                    // Set textarea value
                    const ta = document.querySelector('#g-recaptcha-response');
                    if (ta) {
                        ta.style.display = 'block';
                        ta.value = token;
                    }
                    // Also try all textareas with that name
                    document.querySelectorAll('textarea[name="g-recaptcha-response"]').forEach(el => {
                        el.value = token;
                    });

                    // Trigger reCAPTCHA callback
                    if (typeof ___grecaptcha_cfg !== 'undefined') {
                        const clients = ___grecaptcha_cfg.clients;
                        if (clients) {
                            for (const cid in clients) {
                                const client = clients[cid];
                                for (const key in client) {
                                    const val = client[key];
                                    if (val && typeof val === 'object') {
                                        for (const k2 in val) {
                                            if (val[k2] && typeof val[k2] === 'object' && val[k2].callback) {
                                                val[k2].callback(token);
                                                return;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }""", captcha_token)

                await asyncio.sleep(1)

                # Click "Consultar" button
                consultar_btn = await page.query_selector('input[value*="Consultar"], button:has-text("Consultar"), input[type="submit"]')
                if consultar_btn:
                    initial_count = len(ajax_responses)
                    await consultar_btn.click()
                    logger.info("Multas CABA: boton Consultar clickeado, esperando respuesta AJAX")
                else:
                    raise RuntimeError("No se encontro el boton Consultar en Multas CABA")

                # Wait for AJAX response
                start = asyncio.get_event_loop().time()
                while len(ajax_responses) <= initial_count and (asyncio.get_event_loop().time() - start) < 30:
                    await asyncio.sleep(1)

                # Give DOM time to update
                await asyncio.sleep(3)

                # Parse results from page text
                body_text = await page.evaluate("() => document.body.innerText") or ""
                result_html = await page.evaluate("() => document.body.innerHTML") or ""

                await browser.close()

        finally:
            if chrome_proc:
                chrome_proc.terminate()

        return _parse_multas_caba(pat, body_text, result_html)


def _parse_multas_caba(patente: str, body_text: str, html: str = "") -> dict:
    """Parse CABA multas results from page text."""
    infracciones = []

    # Check for no infractions
    lower_text = body_text.lower()
    if any(kw in lower_text for kw in [
        "no posee", "no registra", "0 infracciones",
        "no se encontraron infracciones", "sin infracciones",
    ]):
        return {
            "fuente": "multas_caba",
            "patente": patente,
            "tiene_infracciones": False,
            "infracciones": [],
            "cantidad": 0,
            "monto_total": "",
            "mensaje": "No se encontraron infracciones",
        }

    # Extract total count
    total_match = re.search(r"(\d+)\s*infracciones?", body_text)
    total = int(total_match.group(1)) if total_match else 0

    # Extract total amount - try multiple patterns
    monto_total = ""
    monto_match = re.search(r"[Mm]onto\s+total[:\s]*\$?\s*([\d.,]+)", body_text)
    if monto_match:
        monto_total = monto_match.group(1)
    else:
        monto_match = re.search(r"\$\s*([\d.,]+)", body_text)
        if monto_match:
            monto_total = monto_match.group(1)

    # Extract individual actas - try multiple patterns
    # Pattern 1: "Acta Nro Q25941651" style
    acta_blocks = re.split(r'(?=Acta\s*(?:Nro|N[°º]|numero)?\.?\s*[A-Z0-9])', body_text)
    for block in acta_blocks:
        if not re.search(r'Acta\s*(?:Nro|N[°º]|numero)?', block):
            continue

        nro_match = re.search(r'Acta\s*(?:Nro|N[°º]|numero)?\.?\s*([A-Z0-9]+)', block)
        if not nro_match:
            continue

        nro_acta = nro_match.group(1).strip()
        fecha = ""
        descripcion = ""
        monto = ""

        fecha_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', block)
        if fecha_match:
            fecha = fecha_match.group(1)

        monto_ind = re.search(r'\$\s*([\d.,]+)', block)
        if monto_ind:
            monto = monto_ind.group(1)

        # Try to get description
        desc_match = re.search(r'(?:Descripci[oó]n|Motivo|Infracci[oó]n)[:\s]*([^\n]+)', block)
        if desc_match:
            descripcion = desc_match.group(1).strip()

        infracciones.append({
            "nro_acta": nro_acta,
            "fecha": fecha,
            "descripcion": descripcion,
            "monto": monto,
        })

    # Fallback: try to extract acta numbers from plain text
    if not infracciones:
        actas_found = re.findall(r'([A-Z]\d{7,})', body_text)
        for acta_id in actas_found:
            infracciones.append({
                "nro_acta": acta_id,
                "fecha": "",
                "descripcion": "",
                "monto": "",
            })

    return {
        "fuente": "multas_caba",
        "patente": patente,
        "tiene_infracciones": total > 0 or len(infracciones) > 0,
        "infracciones": infracciones,
        "cantidad": total or len(infracciones),
        "monto_total": monto_total,
        "texto_raw": body_text[:3000] if not infracciones and total == 0 else "",
    }
