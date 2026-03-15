import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scrapers.base import BaseScraper, ScraperResult

class FakeScraper(BaseScraper):
    def __init__(self, fail_times=0):
        super().__init__(name="fake", max_retries=3, backoff=[0, 0, 0], timeout=5)
        self.fail_times = fail_times
        self.call_count = 0

    async def _ejecutar(self, patente: str) -> dict:
        self.call_count += 1
        if self.call_count <= self.fail_times:
            raise Exception("sitio caido")
        return {"resultado": "ok"}

@pytest.mark.asyncio
async def test_scraper_exito():
    s = FakeScraper(fail_times=0)
    result = await s.ejecutar("AB123CD")
    assert result.exito is True
    assert result.datos == {"resultado": "ok"}
    assert result.intentos == 1

@pytest.mark.asyncio
async def test_scraper_reintento_y_exito():
    s = FakeScraper(fail_times=2)
    result = await s.ejecutar("AB123CD")
    assert result.exito is True
    assert result.intentos == 3

@pytest.mark.asyncio
async def test_scraper_fallo_total():
    s = FakeScraper(fail_times=5)
    result = await s.ejecutar("AB123CD")
    assert result.exito is False
    assert result.intentos == 3
    assert "sitio caido" in result.error
