from scrapers.base import BaseScraper


class MultabotScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="multabot", max_retries=1, backoff=[], timeout=5)

    async def _ejecutar(self, patente: str, **kwargs) -> dict:
        # Multabot no tiene API publica. Usamos scrapers directos (multas_caba, multas_pba, multas_nacional)
        return {
            "fuente": "multabot",
            "patente": patente,
            "mensaje": "Multas se consultan via scrapers directos (CABA, PBA, Nacional). Multabot no tiene API publica.",
        }
