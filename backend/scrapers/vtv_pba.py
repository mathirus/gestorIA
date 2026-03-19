import logging

import httpx
from scrapers.base import BaseScraper
from services import capsolver_client

logger = logging.getLogger(__name__)

TURNSTILE_SITEKEY = "0x4AAAAAAB8GkEqt6sgz9dUq"
VTV_PBA_PAGE_URL = "https://vtv.gba.gob.ar/consultar-vtv"
VTV_PBA_API_URL = "https://vtv-web-api.transporte.gba.gob.ar/api/historialvtvs/patente"


class VtvPbaScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="vtv_pba", max_retries=3, timeout=90)

    async def _ejecutar(self, patente: str, **kwargs) -> dict:
        pat = patente.upper().replace("-", "").replace(" ", "")

        # Solve Cloudflare Turnstile with CapSolver
        logger.info(f"VTV PBA: solving Turnstile for {pat}")
        solution = await capsolver_client.solve({
            "type": "AntiTurnstileTaskProxyLess",
            "websiteURL": VTV_PBA_PAGE_URL,
            "websiteKey": TURNSTILE_SITEKEY,
        })
        turnstile_token = solution.get("token", solution.get("gRecaptchaResponse", ""))

        if not turnstile_token:
            raise RuntimeError("No se obtuvo token de Turnstile")

        logger.info("VTV PBA: Turnstile solved, calling API")

        # Call API directly with the Turnstile token
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{VTV_PBA_API_URL}/{pat}",
                headers={
                    "X-Turnstile-Token": turnstile_token,
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    "Referer": VTV_PBA_PAGE_URL,
                    "Origin": "https://vtv.gba.gob.ar",
                },
            )
            response.raise_for_status()
            data = response.json()

        # Parse API response: {payload: [{verificacion: {...}, planta: {...}}]}
        verificaciones = []
        estado = "Sin datos"
        numero_oblea = ""
        ultima_verificacion = ""
        vencimiento = ""
        planta = ""
        resultado_ultima = ""

        RESULTADO_MAP = {"1": "Aprobada", "2": "Rechazada", "3": "Condicional"}

        payload = []
        if isinstance(data, dict):
            payload = data.get("payload", [])
            if isinstance(payload, dict) and payload.get("vigencia_por_dominio"):
                # Alternative format
                vig = payload["vigencia_por_dominio"]
                return {
                    "fuente": "vtv_pba",
                    "patente": pat,
                    "estado": "Vigente" if vig.get("vigente") else "Vencida",
                    "numero_oblea": vig.get("numero_oblea", ""),
                    "ultima_verificacion": vig.get("fecha_verificacion", ""),
                    "vencimiento": vig.get("fecha_vencimiento", ""),
                    "planta": vig.get("planta", ""),
                    "resultado_ultima": "",
                    "verificaciones": [],
                    "cantidad_verificaciones": 0,
                }
        elif isinstance(data, list):
            payload = data

        for item in payload:
            if not isinstance(item, dict):
                continue
            ver = item.get("verificacion", item)
            pl = item.get("planta", {})
            resultado_id = str(ver.get("tipo_resultado_id", ""))
            verificaciones.append({
                "fecha_verificacion": ver.get("fecha_verificacion", ""),
                "fecha_vencimiento": ver.get("fecha_vencimiento", ""),
                "resultado": RESULTADO_MAP.get(resultado_id, resultado_id),
                "planta": pl.get("nombre", "") if isinstance(pl, dict) else str(pl),
                "numero_oblea": ver.get("numero_oblea", ""),
                "tipo_inspeccion": "Reverificacion" if ver.get("reverificacion") else "Verificacion",
            })

        if verificaciones:
            ultima = verificaciones[0]
            ultima_verificacion = ultima.get("fecha_verificacion", "")
            vencimiento = ultima.get("fecha_vencimiento", "")
            planta = ultima.get("planta", "")
            resultado_ultima = ultima.get("resultado", "")
            numero_oblea = ultima.get("numero_oblea", "")

            from datetime import datetime
            try:
                for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y-%m-%d"):
                    try:
                        fecha = datetime.strptime(vencimiento[:10], fmt)
                        estado = "Vigente" if fecha >= datetime.now() else "Vencida"
                        break
                    except ValueError:
                        continue
            except Exception:
                estado = resultado_ultima or "Sin datos"

        return {
            "fuente": "vtv_pba",
            "patente": pat,
            "estado": estado,
            "numero_oblea": numero_oblea,
            "ultima_verificacion": ultima_verificacion,
            "vencimiento": vencimiento,
            "planta": planta,
            "resultado_ultima": resultado_ultima,
            "verificaciones": verificaciones,
            "cantidad_verificaciones": len(verificaciones),
        }
