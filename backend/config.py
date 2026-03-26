import sys
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Entorno ---
    environment: str = "development"  # "development" | "production"

    # --- Base de datos ---
    database_url: str = "sqlite+aiosqlite:///./gestoria.db"

    # --- API keys (sin defaults, obligatorias en prod) ---
    multabot_api_key: str = ""
    capsolver_api_key: str = ""

    # --- Scrapers ---
    scraper_timeout: int = 30
    scraper_max_retries: int = 3
    scraper_backoff: List[int] = [2, 8, 20]

    # --- URLs de sitios gobierno ---
    agip_url: str = "https://lb.agip.gob.ar/ConsultaPat/"
    arba_url: str = "https://web.arba.gov.ar/consulta-de-deuda-automotor"
    vtv_pba_url: str = "https://vtv.gba.gov.ar/consultar-vtv"
    vtv_caba_url: str = "https://www.infovtv.com.ar/ng"
    multabot_url: str = "https://multabot.com.ar/api"
    dnrpa_valuacion_url: str = "https://www.dnrpa.gov.ar/valuacion/cons_valuacion.php"

    # --- Chrome: detecta automáticamente según OS ---
    chrome_path: str = (
        "C:/Program Files/Google/Chrome/Application/chrome.exe"
        if sys.platform == "win32"
        else "/usr/bin/chromium-browser"
    )

    # --- CORS ---
    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    # --- Server ---
    host: str = "127.0.0.1"
    port: int = 8001

    class Config:
        env_file = ".env"


settings = Settings()
