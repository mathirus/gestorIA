from pydantic import BaseModel
from datetime import datetime


class ConsultaCreate(BaseModel):
    patente: str
    provincia: str  # "caba" | "buenos_aires"


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
    provincia: str
    created_at: datetime
    sub_consultas: list[SubConsultaResponse]
    estado_general: str  # "en_proceso" | "completado" | "con_errores"
