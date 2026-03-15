import asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select
from db.models import Consulta, SubConsulta, EstadoConsulta, TipoConsulta
from scrapers.base import BaseScraper, ScraperResult

_scrapers: dict[TipoConsulta, BaseScraper] = {}


def registrar_scraper(tipo: TipoConsulta, scraper: BaseScraper):
    _scrapers[tipo] = scraper


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
        if sub.tipo in _scrapers:
            tasks.append(
                _ejecutar_sub(sub.id, sub.tipo, patente, provincia, db_session_factory)
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
        result = await db.execute(
            select(SubConsulta).where(
                SubConsulta.consulta_id == consulta_id,
                SubConsulta.tipo == tipo,
            )
        )
        sub = result.scalar_one()

    await _ejecutar_sub(
        sub.id, tipo, consulta.patente, consulta.provincia, db_session_factory
    )


async def _ejecutar_sub(
    sub_id: int,
    tipo: TipoConsulta,
    patente: str,
    provincia: str,
    db_session_factory: async_sessionmaker,
):
    scraper = _scrapers[tipo]

    async with db_session_factory() as db:
        result = await db.execute(select(SubConsulta).where(SubConsulta.id == sub_id))
        sub = result.scalar_one()
        sub.estado = EstadoConsulta.ejecutando
        await db.commit()

    resultado: ScraperResult = await scraper.ejecutar(patente, provincia=provincia)

    async with db_session_factory() as db:
        result = await db.execute(select(SubConsulta).where(SubConsulta.id == sub_id))
        sub = result.scalar_one()
        sub.intentos = resultado.intentos
        if resultado.exito:
            sub.estado = EstadoConsulta.completado
            sub.datos = resultado.datos
            sub.error = None
        else:
            sub.estado = EstadoConsulta.fallido
            sub.error = resultado.error
        await db.commit()
