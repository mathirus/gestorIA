from scrapers.base import BaseScraper


class ArbaScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="arba_pba", max_retries=1, backoff=[], timeout=5)

    async def _ejecutar(self, patente: str, **kwargs) -> dict:
        cit = kwargs.get("cit")
        dni = kwargs.get("dni")

        if not cit:
            return {
                "fuente": "arba_pba",
                "patente": patente,
                "mensaje": "Para consultar deuda de patentes en ARBA, ingresá tu Clave CIT en el formulario.",
            }

        # TODO: Implementar scraping de ARBA con CUIT (derivado del DNI) + CIT
        # El flujo sería:
        # 1. Derivar CUIT del DNI (20-DNI-X para masculino, 27-DNI-X para femenino)
        # 2. Login en https://sso.arba.gov.ar con CUIT + CIT
        # 3. Navegar a autogestion → deuda automotor
        # 4. Consultar por patente
        # 5. Parsear resultado
        return {
            "fuente": "arba_pba",
            "patente": patente,
            "mensaje": f"Clave CIT proporcionada. Implementacion del scraping de ARBA pendiente.",
        }
