import asyncio
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class ScraperResult:
    exito: bool
    datos: dict | None = None
    error: str | None = None
    intentos: int = 0


class BaseScraper(ABC):
    def __init__(self, name: str, max_retries: int = 3, backoff: list[int] = None, timeout: int = 30):
        self.name = name
        self.max_retries = max_retries
        self.backoff = backoff if backoff is not None else [2, 8, 20]
        self.timeout = timeout

    async def ejecutar(self, patente: str, **kwargs) -> ScraperResult:
        for intento in range(1, self.max_retries + 1):
            try:
                datos = await asyncio.wait_for(
                    self._ejecutar(patente, **kwargs),
                    timeout=self.timeout,
                )
                return ScraperResult(exito=True, datos=datos, intentos=intento)
            except Exception as e:
                if intento < self.max_retries:
                    await asyncio.sleep(self.backoff[intento - 1])
                else:
                    return ScraperResult(exito=False, error=str(e), intentos=intento)

    @abstractmethod
    async def _ejecutar(self, patente: str, **kwargs) -> dict:
        ...
