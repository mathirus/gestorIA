from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://gestoria:gestoria@localhost:5432/gestoria"
    multabot_api_key: str = ""

    scraper_timeout: int = 30
    scraper_max_retries: int = 3
    scraper_backoff: list[int] = [2, 8, 20]

    agip_url: str = "https://lb.agip.gob.ar/ConsultaPat/"
    arba_url: str = "https://web.arba.gov.ar/consulta-de-deuda-automotor"
    vtv_pba_url: str = "https://vtv.gba.gov.ar/consultar-vtv"
    vtv_caba_url: str = "https://www.infovtv.com.ar/ng"
    multabot_url: str = "https://multabot.com.ar/api"
    dnrpa_valuacion_url: str = "https://www.dnrpa.gov.ar/valuacion/cons_valuacion.php"

    class Config:
        env_file = ".env"


settings = Settings()
