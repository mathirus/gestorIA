import logging

import httpx
from scrapers.base import BaseScraper
from playwright.async_api import async_playwright
from services import capsolver_client

logger = logging.getLogger(__name__)

VTV_CABA_URL = "https://www.suvtv.com.ar/historial-turnos/"
VTV_CABA_API_URL = "https://www.suvtv.com.ar/controller/ControllerDispatcher.php"


class VtvCabaScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="vtv_caba", max_retries=3, timeout=90)

    async def _ejecutar(self, patente: str, **kwargs) -> dict:
        pat = patente.upper().replace("-", "").replace(" ", "")

        # Get sitekey - try from page, fallback to known key
        KNOWN_SITEKEY = "6LdKVRATAAAAANKz_mugRJbHgwThU9dQbIVfr-dA"
        sitekey = None
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                try:
                    await page.goto(VTV_CABA_URL, timeout=15000)
                    await page.wait_for_load_state("networkidle")
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
                finally:
                    await browser.close()
        except Exception:
            pass

        if not sitekey:
            sitekey = KNOWN_SITEKEY
            logger.info(f"VTV CABA: usando sitekey conocido como fallback")

        logger.info(f"VTV CABA: sitekey={sitekey}, solving reCAPTCHA")

        # Solve reCAPTCHA v2 with CapSolver
        solution = await capsolver_client.solve({
            "type": "ReCaptchaV2TaskProxyLess",
            "websiteURL": VTV_CABA_URL,
            "websiteKey": sitekey,
        })
        captcha_token = solution["gRecaptchaResponse"]

        logger.info("VTV CABA: reCAPTCHA solved, calling API")

        # Call API directly with httpx
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                VTV_CABA_API_URL,
                data={
                    "controllerName": "EstadisticasController",
                    "actionName": "getHistorialVtv",
                    "dominio": pat,
                    "verify": captcha_token,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    "Referer": VTV_CABA_URL,
                    "Origin": "https://www.suvtv.com.ar",
                    "X-Requested-With": "XMLHttpRequest",
                },
            )
            response.raise_for_status()
            data = response.json()

        # Parse response: {result: [{dominio, tipoVehiculo, planta, fechaInspeccion, tipoInspeccion, fechaVencimiento, oblea, resultadoInspeccion, traKilometraje}]}
        RESULTADO_MAP = {"A": "Aprobado", "R": "Rechazado", "C": "Condicional"}
        verificaciones = []
        estado = "Sin datos"
        ultima_verificacion_data = {}

        items = []
        if isinstance(data, dict):
            items = data.get("result", []) or []
        elif isinstance(data, list):
            items = data

        if items is None:
            items = []

        for item in items:
            if not isinstance(item, dict):
                continue
            resultado_raw = item.get("resultadoInspeccion", "")
            verificaciones.append({
                "dominio": item.get("dominio", pat),
                "tipo_vehiculo": item.get("tipoVehiculo", ""),
                "planta": item.get("planta", ""),
                "fecha_inspeccion": item.get("fechaInspeccion", ""),
                "tipo_inspeccion": item.get("tipoInspeccion", ""),
                "fecha_vencimiento": item.get("fechaVencimiento", ""),
                "numero_oblea": item.get("oblea", ""),
                "resultado": RESULTADO_MAP.get(resultado_raw, resultado_raw),
                "kilometraje": item.get("traKilometraje", ""),
            })

        if verificaciones:
            ultima = verificaciones[0]
            ultima_verificacion_data = ultima
            # Determinar vigencia por fecha de vencimiento
            from datetime import datetime
            venc = ultima.get("fecha_vencimiento", "")
            try:
                for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                    try:
                        fecha = datetime.strptime(venc[:10], fmt)
                        estado = "Vigente" if fecha >= datetime.now() else "Vencida"
                        break
                    except ValueError:
                        continue
            except Exception:
                estado = ultima.get("resultado", "Sin datos")

        return {
            "fuente": "vtv_caba",
            "patente": pat,
            "estado": estado,
            "ultima_verificacion": ultima_verificacion_data,
            "verificaciones": verificaciones,
            "cantidad_verificaciones": len(verificaciones),
        }
