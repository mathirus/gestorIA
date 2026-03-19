import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class EstadoConsulta(str, enum.Enum):
    pendiente = "pendiente"
    ejecutando = "ejecutando"
    completado = "completado"
    fallido = "fallido"
    reintentando = "reintentando"
    pendiente_24hs = "pendiente_24hs"


class TipoConsulta(str, enum.Enum):
    costos = "costos"
    patentes_caba = "patentes_caba"
    patentes_pba = "patentes_pba"
    vtv_pba = "vtv_pba"
    vtv_caba = "vtv_caba"
    multas = "multas"
    multas_caba = "multas_caba"
    multas_pba = "multas_pba"
    multas_nacional = "multas_nacional"
    dominio = "dominio"


class Consulta(Base):
    __tablename__ = "consultas"

    id: Mapped[int] = mapped_column(primary_key=True)
    patente: Mapped[str] = mapped_column(String(10), index=True)
    provincia: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sub_consultas: Mapped[list["SubConsulta"]] = relationship(back_populates="consulta")


class SubConsulta(Base):
    __tablename__ = "sub_consultas"

    id: Mapped[int] = mapped_column(primary_key=True)
    consulta_id: Mapped[int] = mapped_column(ForeignKey("consultas.id"))
    tipo: Mapped[str] = mapped_column(String(30))
    estado: Mapped[str] = mapped_column(String(20), default=EstadoConsulta.pendiente.value)
    intentos: Mapped[int] = mapped_column(Integer, default=0)
    datos: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    consulta: Mapped["Consulta"] = relationship(back_populates="sub_consultas")
