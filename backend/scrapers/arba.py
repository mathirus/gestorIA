from scrapers.base import BaseScraper


class ArbaScraper(BaseScraper):
    """
    ARBA — Consulta de deuda de patentes en Provincia de Buenos Aires.

    NO IMPLEMENTADO. ARBA no expone una consulta publica por dominio.
    Verificacion realizada (2026-04-06):
      - https://web.arba.gov.ar/consulta-de-deuda-automotor → solo instrucciones, sin formulario
      - https://www.arba.gov.ar/aplicaciones/automotores.asp → 404
      - https://dfe.arba.gov.ar/DomicilioElectronico/ → redirige a SSO con CUIT + CIT
    Todo el flujo requiere login en sso.arba.gov.ar con CUIT + Clave CIT del titular.

    Esto rompe el modelo de la app: el comprador (quien consulta) no tiene la CIT
    del vendedor (titular). Es decision de ARBA tener los datos fiscales privados.

    Alternativas posibles si en el futuro se quiere consultar deuda de PBA:
      a) Servicio pago de terceros (Multas.com, MultaQR, etc.) — cuesta por consulta
      b) Pedirle al vendedor que comparta su CIT — privacidad/legal sensible
      c) Esperar a que ARBA habilite consulta publica (no esta en su roadmap)
      d) Consultar al municipio si tiene API propia (varia por municipio)
    """

    def __init__(self):
        super().__init__(name="arba_pba", max_retries=1, backoff=[], timeout=5)

    async def _ejecutar(self, patente: str, **kwargs) -> dict:
        return {
            "fuente": "arba_pba",
            "patente": patente,
            "mensaje": (
                "La consulta de deuda de patentes en PBA no está disponible. "
                "ARBA no permite consultas públicas — solo puede verla el titular "
                "ingresando con su Clave CIT en arba.gov.ar."
            ),
        }
