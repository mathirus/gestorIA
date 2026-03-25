import asyncio
import logging
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select
from db.models import Consulta, SubConsulta, EstadoConsulta, TipoConsulta
from scrapers.base import BaseScraper, ScraperResult

logger = logging.getLogger(__name__)

_scrapers: dict[str, BaseScraper] = {}

# Scrapers que usan Chrome CDP — deben correr en secuencia para no pisarse
CDP_SCRAPERS = {"multas_caba", "multas_pba", "multas_nacional", "dominio"}


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
        dni = consulta.dni

        result = await db.execute(
            select(SubConsulta).where(SubConsulta.consulta_id == consulta_id)
        )
        subs = result.scalars().all()

    # Separar en dos grupos: rápidos (sin Chrome) y CDP (con Chrome)
    parallel_tasks = []
    cdp_subs = []

    for sub in subs:
        tipo_str = sub.tipo if isinstance(sub.tipo, str) else sub.tipo.value
        if tipo_str not in _scrapers:
            continue
        if tipo_str in CDP_SCRAPERS:
            cdp_subs.append((sub.id, tipo_str))
        else:
            parallel_tasks.append(
                _ejecutar_sub(sub.id, tipo_str, patente, provincia, dni, db_session_factory)
            )

    # 1. Correr scrapers rápidos en paralelo
    if parallel_tasks:
        logger.info(f"Consulta #{consulta_id}: lanzando {len(parallel_tasks)} scrapers en paralelo")
        await asyncio.gather(*parallel_tasks)

    # 2. Correr scrapers CDP en secuencia (uno a la vez)
    if cdp_subs:
        logger.info(f"Consulta #{consulta_id}: ejecutando {len(cdp_subs)} scrapers CDP en secuencia")
        for sub_id, tipo_str in cdp_subs:
            await _ejecutar_sub(sub_id, tipo_str, patente, provincia, dni, db_session_factory)


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
        sub.id, tipo_str, consulta.patente, consulta.provincia, consulta.dni, db_session_factory
    )


async def _ejecutar_sub(
    sub_id: int,
    tipo: str,
    patente: str,
    provincia: str,
    dni: str | None,
    db_session_factory: async_sessionmaker,
):
    scraper = _scrapers[tipo]

    async with db_session_factory() as db:
        result = await db.execute(select(SubConsulta).where(SubConsulta.id == sub_id))
        sub = result.scalar_one()
        sub.estado = EstadoConsulta.ejecutando.value
        await db.commit()

    resultado: ScraperResult = await scraper.ejecutar(patente, provincia=provincia, dni=dni)

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
