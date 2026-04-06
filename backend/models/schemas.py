from pydantic import BaseModel
from datetime import datetime


class ConsultaCreate(BaseModel):
    patente: str
    dni: str | None = None
    cit: str | None = None  # Clave CIT de ARBA (opcional, para PBA)
    # provincia se auto-detecta desde DNRPA. Opcional como override manual si el usuario lo sabe.
    provincia: str | None = None  # "caba" | "buenos_aires"


class SubConsultaResponse(BaseModel):
    tipo: str
    estado: str
    intentos: int
    datos: dict | None
    error: str | None
    updated_at: datetime


class ConsultaResponse(BaseModel):
    id: int
    patente: str
    provincia: str | None  # null hasta que DNRPA la detecte
    created_at: datetime
    sub_consultas: list[SubConsultaResponse]
    estado_general: str  # "en_proceso" | "completado" | "con_errores"
