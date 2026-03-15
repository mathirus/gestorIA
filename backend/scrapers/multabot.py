import httpx
from scrapers.base import BaseScraper
from config import settings


class MultabotScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="multabot")

    async def _ejecutar(self, patente: str, **kwargs) -> dict:
        async with httpx.AsyncClient() as client:
            # TODO: verify actual API endpoint structure
            response = await client.get(
                f"{settings.multabot_url}/consulta/{patente}",
                headers={"Authorization": f"Bearer {settings.multabot_api_key}"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return {"fuente": "multabot", "patente": patente, "data": response.json()}
