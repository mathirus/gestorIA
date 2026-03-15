from scrapers.base import BaseScraper
from services.calculadora import calcular_costos


class CostosScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="costos", max_retries=1, backoff=[], timeout=5)

    async def _ejecutar(self, patente: str, **kwargs) -> dict:
        valuacion = kwargs.get("valuacion", 15_000_000)
        provincia = kwargs.get("provincia", "caba")
        return calcular_costos(valuacion=valuacion, provincia=provincia)
