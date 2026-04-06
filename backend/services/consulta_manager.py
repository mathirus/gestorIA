import logging
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select
from db.models import Consulta, SubConsulta, EstadoConsulta, TipoConsulta
from scrapers.base import BaseScraper, ScraperResult

logger = logging.getLogger(__name__)

_scrapers: dict[str, BaseScraper] = {}


# Mapeo de provincia DNRPA a codigo interno
def _normalizar_provincia(prov_dnrpa: str | None) -> str | None:
    if not prov_dnrpa:
        return None
    p = prov_dnrpa.upper().strip()
    if "CAPITAL FEDERAL" in p or "CABA" in p or "CIUDAD" in p:
        return "caba"
    if "BUENOS AIRES" in p:
        return "buenos_aires"
    return None  # Otras provincias: no hay scrapers province-specific implementados


# Sub-consultas que dependen de la provincia (se agregan dinamicamente)
_TIPOS_POR_PROVINCIA = {
    "caba": [TipoConsulta.patentes_caba, TipoConsulta.vtv_caba, TipoConsulta.multas_caba],
    "buenos_aires": [TipoConsulta.patentes_pba, TipoConsulta.vtv_pba, TipoConsulta.multas_pba],
}


def registrar_scraper(tipo: TipoConsulta, scraper: BaseScraper):
    _scrapers[tipo.value] = scraper


async def ejecutar_consulta(consulta_id: int, db_session_factory: async_sessionmaker):
    """
    Estrategia:
    1. Ejecutar dominio (DNRPA) PRIMERO - es el que detecta la provincia.
    2. Parsear provincia del resultado de DNRPA.
    3. Si no estaba provincia o el usuario no la especifico, agregar dinamicamente
       las sub_consultas province-specific (patentes/vtv/multas).
    4. Ejecutar el resto de las sub_consultas en secuencia.
    """
    async with db_session_factory() as db:
        result = await db.execute(
            select(Consulta).where(Consulta.id == consulta_id)
        )
        consulta = result.scalar_one()
        patente = consulta.patente
        provincia = consulta.provincia
        dni = consulta.dni
        cit = consulta.cit

        result = await db.execute(
            select(SubConsulta).where(SubConsulta.consulta_id == consulta_id)
        )
        subs = result.scalars().all()

    # Separar dominio del resto. Dominio corre primero.
    dominio_sub = None
    otras_subs = []
    for sub in subs:
        tipo_str = sub.tipo if isinstance(sub.tipo, str) else sub.tipo.value
        if tipo_str not in _scrapers:
            continue
        if tipo_str == TipoConsulta.dominio.value:
            dominio_sub = (sub.id, tipo_str)
        else:
            otras_subs.append((sub.id, tipo_str))

    # 1. Ejecutar DNRPA (dominio) primero
    if dominio_sub:
        logger.info(f"Consulta #{consulta_id}: ejecutando DNRPA primero para detectar provincia")
        await _ejecutar_sub(dominio_sub[0], dominio_sub[1], patente, provincia, dni, cit, db_session_factory)

        # Leer resultado de DNRPA y detectar provincia
        async with db_session_factory() as db:
            result = await db.execute(select(SubConsulta).where(SubConsulta.id == dominio_sub[0]))
            sub_dnrpa = result.scalar_one()
            datos_dnrpa = sub_dnrpa.datos or {}

        prov_detectada = _normalizar_provincia(datos_dnrpa.get("provincia"))
        logger.info(f"Consulta #{consulta_id}: DNRPA reporta provincia '{datos_dnrpa.get('provincia')}' -> '{prov_detectada}'")

        # 2. Si el usuario no especifico provincia y DNRPA detecto una valida,
        #    agregar las sub_consultas province-specific.
        if not provincia and prov_detectada:
            tipos_a_agregar = _TIPOS_POR_PROVINCIA.get(prov_detectada, [])
            async with db_session_factory() as db:
                # Persistir provincia detectada en la consulta
                result = await db.execute(select(Consulta).where(Consulta.id == consulta_id))
                consulta_db = result.scalar_one()
                consulta_db.provincia = prov_detectada

                # Agregar las nuevas sub_consultas
                for tipo in tipos_a_agregar:
                    nueva = SubConsulta(
                        consulta_id=consulta_id,
                        tipo=tipo.value,
                        estado=EstadoConsulta.pendiente.value,
                    )
                    db.add(nueva)
                    await db.flush()
                    otras_subs.append((nueva.id, tipo.value))
                await db.commit()

            provincia = prov_detectada
            logger.info(f"Consulta #{consulta_id}: agregadas {len(tipos_a_agregar)} sub_consultas para provincia {prov_detectada}")

    # 3. Ejecutar el resto de los scrapers en secuencia
    logger.info(f"Consulta #{consulta_id}: ejecutando {len(otras_subs)} scrapers restantes en secuencia")
    for sub_id, tipo_str in otras_subs:
        await _ejecutar_sub(sub_id, tipo_str, patente, provincia, dni, cit, db_session_factory)


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
        sub.id, tipo_str, consulta.patente, consulta.provincia, consulta.dni, consulta.cit, db_session_factory
    )


async def _ejecutar_sub(
    sub_id: int,
    tipo: str,
    patente: str,
    provincia: str,
    dni: str | None,
    cit: str | None,
    db_session_factory: async_sessionmaker,
):
    scraper = _scrapers[tipo]

    async with db_session_factory() as db:
        result = await db.execute(select(SubConsulta).where(SubConsulta.id == sub_id))
        sub = result.scalar_one()
        sub.estado = EstadoConsulta.ejecutando.value
        await db.commit()

    resultado: ScraperResult = await scraper.ejecutar(patente, provincia=provincia, dni=dni, cit=cit)

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
