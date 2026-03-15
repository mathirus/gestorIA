from scrapers.base import BaseScraper
from playwright.async_api import async_playwright
from config import settings


class VtvCabaScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="vtv_caba")

    async def _ejecutar(self, patente: str, **kwargs) -> dict:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, channel="chrome")
            page = await browser.new_page()
            try:
                await page.goto(settings.vtv_caba_url, wait_until="networkidle")

                # TODO: verify selector — infovtv.com.ar is an Angular app,
                # may need to wait for specific elements to render
                await page.wait_for_timeout(2000)

                # TODO: verify selector — fill patente input
                await page.fill(
                    "input[name='dominio'], input#dominio, "
                    "input[placeholder*='atente'], input[type='text']",
                    patente,
                )

                # TODO: verify selector — click search button
                await page.click(
                    "button[type='submit'], input[type='submit'], "
                    "button:has-text('Consultar'), button:has-text('Buscar')"
                )

                # Wait for results to load
                await page.wait_for_timeout(3000)

                # TODO: verify selector — adapt to actual DOM structure
                datos = await page.evaluate("""() => {
                    const results = document.querySelector(
                        '.resultados, .resultado, #resultados, '
                        + '.vtv-result, table, .card, .mat-card'
                    );
                    if (results) {
                        return { html: results.innerHTML, text: results.innerText };
                    }
                    return {
                        html: document.body.innerHTML.substring(0, 5000),
                        text: document.body.innerText.substring(0, 3000)
                    };
                }""")

                return {"fuente": "vtv_caba", "patente": patente, "raw": datos}
            finally:
                await browser.close()
