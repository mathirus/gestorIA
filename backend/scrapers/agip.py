import asyncio
import logging

from scrapers.base import BaseScraper
from playwright.async_api import async_playwright
from services import capsolver_client

logger = logging.getLogger(__name__)


class AgipScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="agip_caba", max_retries=3, timeout=120)

    async def _ejecutar(self, patente: str, **kwargs) -> dict:
        dominio = patente.upper().replace("-", "").replace(" ", "")

        vehicle_data = {}
        debt_data = {}

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, channel="chrome")
            page = await browser.new_page()
            try:
                # Set up response interceptors before navigating
                async def handle_response(response):
                    nonlocal vehicle_data, debt_data
                    url = response.url
                    try:
                        if "/Empadronados/json/captcha/GetDatos" in url:
                            vehicle_data = await response.json()
                        elif "/Empadronados/json/GetPosicionesImpagas" in url:
                            debt_data = await response.json()
                    except Exception:
                        pass

                page.on("response", handle_response)

                await page.goto("https://lb.agip.gob.ar/ConsultaPat/", timeout=30000)
                await page.wait_for_load_state("networkidle")

                # Fill the domain fields (same value in both)
                await page.fill("#fldDominio", dominio)
                await page.fill("#fldDominio2", dominio)

                # Get the reCAPTCHA sitekey dynamically
                sitekey = await page.evaluate("""() => {
                    // Try to get from grecaptcha iframe
                    const iframe = document.querySelector('iframe[src*="recaptcha"]');
                    if (iframe) {
                        const src = iframe.src;
                        const match = src.match(/[?&]k=([^&]+)/);
                        if (match) return match[1];
                    }
                    // Try data-sitekey attribute
                    const el = document.querySelector('[data-sitekey]');
                    if (el) return el.getAttribute('data-sitekey');
                    // Try .g-recaptcha div
                    const gre = document.querySelector('.g-recaptcha');
                    if (gre) return gre.getAttribute('data-sitekey');
                    return null;
                }""")

                if not sitekey:
                    # Try fetching the sitekey from the AGIP API
                    try:
                        key_resp = await page.evaluate("""async () => {
                            const resp = await fetch('/Empadronados/json/getKeyC');
                            const data = await resp.json();
                            return data;
                        }""")
                        if isinstance(key_resp, dict):
                            sitekey = key_resp.get("key") or key_resp.get("siteKey") or key_resp.get("sitekey")
                        elif isinstance(key_resp, str):
                            sitekey = key_resp
                    except Exception:
                        pass

                if not sitekey:
                    raise RuntimeError("No se pudo obtener el sitekey de reCAPTCHA de AGIP")

                logger.info(f"AGIP sitekey: {sitekey}")

                # Solve reCAPTCHA v2 with CapSolver
                solution = await capsolver_client.solve({
                    "type": "ReCaptchaV2TaskProxyLess",
                    "websiteURL": "https://lb.agip.gob.ar/ConsultaPat/",
                    "websiteKey": sitekey,
                })
                token = solution["gRecaptchaResponse"]

                # Inject the token and trigger the callback
                await page.evaluate(f"""(token) => {{
                    document.getElementById('g-recaptcha-response').value = token;
                    // Also set textarea if hidden
                    const ta = document.querySelector('textarea[name="g-recaptcha-response"]');
                    if (ta) ta.value = token;
                    // Try to trigger the callback
                    if (typeof ___grecaptcha_cfg !== 'undefined') {{
                        const clients = ___grecaptcha_cfg.clients;
                        if (clients) {{
                            for (const cid in clients) {{
                                const client = clients[cid];
                                for (const key in client) {{
                                    const val = client[key];
                                    if (val && typeof val === 'object') {{
                                        for (const k2 in val) {{
                                            if (val[k2] && typeof val[k2] === 'object' && val[k2].callback) {{
                                                val[k2].callback(token);
                                                return;
                                            }}
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }}
                    // Fallback: trigger via known callback names
                    if (typeof verifyCallback === 'function') verifyCallback(token);
                    if (typeof captchaCallback === 'function') captchaCallback(token);
                }}""", token)

                await page.wait_for_timeout(500)

                # Click consultar button
                await page.click("#btnConsultar")

                # Wait for API responses
                await page.wait_for_timeout(8000)

                # Parse vehicle data from AGIP response: {statusCode: 0, result: {cabecera: {...}}}
                vehiculo = {}
                if vehicle_data and isinstance(vehicle_data, dict):
                    if vehicle_data.get("statusCode") == 0:
                        cab = vehicle_data.get("result", {}).get("cabecera", {})
                        if cab:
                            vehiculo = {
                                "dominio": cab.get("dominio", patente),
                                "marca": cab.get("tipoFabrica", {}).get("descripcion", ""),
                                "modelo": cab.get("tipoModeloFabrica", {}).get("descripcion", ""),
                                "rubro": cab.get("tipoRubro", {}).get("descripcion", ""),
                                "uso": cab.get("tipoCodUso", {}).get("descripcion", ""),
                                "estado": cab.get("tipoEstado", {}).get("descripcion", ""),
                                "categoria": cab.get("categoria", ""),
                                "fecha_alta": cab.get("fechaAlta", ""),
                            }

                # Parse debt data from: {statusCode: 0, result: {deudas: [...]}}
                deudas = []
                total_deuda = 0
                if debt_data and isinstance(debt_data, dict):
                    if debt_data.get("statusCode") == 0:
                        items = debt_data.get("result", {}).get("deudas", [])
                        for item in items:
                            if isinstance(item, dict):
                                imp_actual = float(item.get("importeActualizado", 0) or 0)
                                total_deuda += imp_actual
                                deudas.append({
                                    "anio": item.get("anio", ""),
                                    "cuota": item.get("cuota", ""),
                                    "fecha_vencimiento": item.get("fechaVencimiento", ""),
                                    "importe_original": item.get("importeOriginal", 0),
                                    "importe_actualizado": imp_actual,
                                })

                return {
                    "fuente": "agip_caba",
                    "patente": patente,
                    "vehiculo": vehiculo,
                    "deudas": deudas,
                    "total_deuda": round(total_deuda, 2),
                    "cantidad_cuotas_impagas": len(deudas),
                }
            finally:
                await browser.close()
