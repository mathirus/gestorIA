import asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select
from db.models import Consulta, SubConsulta, EstadoConsulta, TipoConsulta
from scrapers.base import BaseScraper, ScraperResult

_scrapers: dict[str, BaseScraper] = {}


def registrar_scraper(tipo: TipoConsulta, scraper: BaseScraper):
    _scrapers[tipo.value] = scraper


async def ejecutar_consulta(consulta_id: int, db_session_factory: async_sessionmaker):
    async with db_session_factory() as db:
        result = await db.execute(
            select(Consulta).where(Consulta.id == consulta_id)
        )
        consulta = result.scalar_one()
        patente = consulta.patente
        provincia = consulta.provincia

        result = await db.execute(
            select(SubConsulta).where(SubConsulta.consulta_id == consulta_id)
        )
        subs = result.scalars().all()

    tasks = []
    for sub in subs:
        tipo_str = sub.tipo if isinstance(sub.tipo, str) else sub.tipo.value
        if tipo_str in _scrapers:
            tasks.append(
                _ejecutar_sub(sub.id, tipo_str, patente, provincia, db_session_factory)
            )

    await asyncio.gather(*tasks)


async def ejecutar_sub_consulta(
    consulta_id: int, tipo: TipoConsulta, db_session_factory: async_sessionmaker
):
    async with db_session_factory() as db:
        result = await db.execute(
            select(Consulta).where(Consulta.id == consulta_id)
        )
        consulta = result.scalar_one()
        tipo_str = tipo.value if isinstance(tipo, TipoConsulta) else tipo
        result = await db.execute(
            select(SubConsulta).where(
                SubConsulta.consulta_id == consulta_id,
                SubConsulta.tipo == tipo_str,
            )
        )
        sub = result.scalar_one()

    await _ejecutar_sub(
        sub.id, tipo_str, consulta.patente, consulta.provincia, db_session_factory
    )


async def _ejecutar_sub(
    sub_id: int,
    tipo: str,
    patente: str,
    provincia: str,
    db_session_factory: async_sessionmaker,
):
    scraper = _scrapers[tipo]

    async with db_session_factory() as db:
        result = await db.execute(select(SubConsulta).where(SubConsulta.id == sub_id))
        sub = result.scalar_one()
        sub.estado = EstadoConsulta.ejecutando.value
        await db.commit()

    resultado: ScraperResult = await scraper.ejecutar(patente, provincia=provincia)

    async with db_session_factory() as db:
        result = await db.execute(select(SubConsulta).where(SubConsulta.id == sub_id))
        sub = result.scalar_one()
        sub.intentos = resultado.intentos
        if resultado.exito:
            sub.estado = EstadoConsulta.completado.value
            sub.datos = resultado.datos
            sub.error = None
        else:
            sub.estado = EstadoConsulta.fallido.value
            sub.error = resultado.error
        await db.commit()
