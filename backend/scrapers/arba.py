from scrapers.base import BaseScraper


class ArbaScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="arba_pba", max_retries=1, backoff=[], timeout=5)

    async def _ejecutar(self, patente: str, **kwargs) -> dict:
        return {
            "fuente": "arba_pba",
            "patente": patente,
            "mensaje": "ARBA requiere CUIT + Clave CIT. Pendiente de implementacion.",
        }
