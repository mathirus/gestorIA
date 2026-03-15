from scrapers.base import BaseScraper
from playwright.async_api import async_playwright
from config import settings


class AgipScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="agip_caba")

    async def _ejecutar(self, patente: str, **kwargs) -> dict:
        # AGIP form has two fields: fldDominio (letters) and fldDominio2 (numbers)
        # For new format (AA000BB): letters part in fldDominio, numbers in fldDominio2
        # For old format (AAA000): same split
        letras = ""
        numeros = ""
        pat = patente.upper().replace("-", "").replace(" ", "")
        if len(pat) == 7 and pat[0:2].isalpha() and pat[2:5].isdigit() and pat[5:7].isalpha():
            # New format: AB123CD
            letras = pat[0:2]
            numeros = pat[2:5] + pat[5:7]
        elif len(pat) >= 6:
            # Old format: AAA000 or similar
            letras = pat[0:3]
            numeros = pat[3:]
        else:
            letras = pat
            numeros = ""

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, channel="chrome")
            page = await browser.new_page()
            try:
                await page.goto(settings.agip_url, timeout=20000)
                await page.wait_for_timeout(2000)

                await page.fill("#fldDominio", letras)
                await page.fill("#fldDominio2", numeros)
                await page.click("#btnConsultar")

                await page.wait_for_timeout(5000)

                datos = await page.evaluate("""() => {
                    const tables = document.querySelectorAll('table');
                    const results = [];
                    tables.forEach(t => {
                        if (t.offsetParent !== null) {
                            results.push(t.innerText);
                        }
                    });
                    const alerts = document.querySelectorAll('.alert, .mensaje, .error, .info');
                    const messages = [];
                    alerts.forEach(a => {
                        if (a.innerText.trim()) messages.push(a.innerText.trim());
                    });
                    return {
                        tables: results,
                        messages: messages,
                        bodyText: document.body.innerText.substring(0, 3000)
                    };
                }""")

                return {"fuente": "agip_caba", "patente": patente, "raw": datos}
            finally:
                await browser.close()
