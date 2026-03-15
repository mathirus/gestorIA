from scrapers.base import BaseScraper


class DnrpaDominioScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="dnrpa_dominio", max_retries=1, backoff=[], timeout=10)

    async def _ejecutar(self, patente: str, **kwargs) -> dict:
        # TODO: implement automated DNRPA request
        # For now, return placeholder indicating this is an async process
        return {
            "fuente": "dnrpa",
            "patente": patente,
            "estado": "pendiente_manual",
            "nota": (
                "El informe de dominio debe solicitarse manualmente. "
                "Tarda ~24hs y cuesta ~$1500 ARS."
            ),
        }
