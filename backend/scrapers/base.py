import asyncio
import logging
import traceback
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


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
        last_error = ""
        for intento in range(1, self.max_retries + 1):
            try:
                datos = await asyncio.wait_for(
                    self._ejecutar(patente, **kwargs),
                    timeout=self.timeout,
                )
                return ScraperResult(exito=True, datos=datos, intentos=intento)
            except Exception as e:
                last_error = f"{type(e).__name__}: {str(e)}" or repr(e)
                logger.error(f"[{self.name}] intento {intento}/{self.max_retries} fallo: {last_error}")
                logger.debug(traceback.format_exc())
                if intento < self.max_retries:
                    delay = self.backoff[intento - 1] if intento - 1 < len(self.backoff) else 5
                    await asyncio.sleep(delay)
        return ScraperResult(exito=False, error=last_error, intentos=self.max_retries)

    @abstractmethod
    async def _ejecutar(self, patente: str, **kwargs) -> dict:
        ...
