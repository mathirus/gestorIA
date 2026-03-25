from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.database import get_db, async_session
from db.models import Consulta, SubConsulta, EstadoConsulta, TipoConsulta
from models.schemas import ConsultaCreate, ConsultaResponse
from services.consulta_manager import ejecutar_consulta, ejecutar_sub_consulta

router = APIRouter(prefix="/api")


@router.post("/consulta", response_model=ConsultaResponse)
async def crear_consulta(
    data: ConsultaCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    patente = data.patente.upper().replace("-", "").replace(" ", "")

    consulta = Consulta(patente=patente, provincia=data.provincia, dni=data.dni)
    db.add(consulta)
    await db.flush()

    tipos = [TipoConsulta.costos, TipoConsulta.multas, TipoConsulta.multas_nacional, TipoConsulta.dominio]
    if data.provincia == "caba":
        tipos.extend([TipoConsulta.patentes_caba, TipoConsulta.vtv_caba, TipoConsulta.multas_caba])
    elif data.provincia == "buenos_aires":
        tipos.extend([TipoConsulta.patentes_pba, TipoConsulta.vtv_pba, TipoConsulta.multas_pba])

    for tipo in tipos:
        sub = SubConsulta(consulta_id=consulta.id, tipo=tipo.value, estado=EstadoConsulta.pendiente.value)
        db.add(sub)

    await db.commit()
    await db.refresh(consulta, ["sub_consultas"])

    background_tasks.add_task(ejecutar_consulta, consulta.id, async_session)

    return _build_response(consulta)


@router.get("/consulta/{consulta_id}", response_model=ConsultaResponse)
async def obtener_consulta(
    consulta_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Consulta)
        .where(Consulta.id == consulta_id)
        .options(selectinload(Consulta.sub_consultas))
    )
    consulta = result.scalar_one_or_none()
    if not consulta:
        raise HTTPException(status_code=404, detail="Consulta no encontrada")
    return _build_response(consulta)


@router.post("/consulta/{consulta_id}/reintentar/{tipo}")
async def reintentar_sub_consulta(
    consulta_id: int,
    tipo: TipoConsulta,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SubConsulta).where(
            SubConsulta.consulta_id == consulta_id,
            SubConsulta.tipo == tipo,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404)
    sub.estado = EstadoConsulta.pendiente.value
    sub.intentos = 0
    sub.error = None
    await db.commit()
    background_tasks.add_task(ejecutar_sub_consulta, consulta_id, tipo, async_session)
    return {"status": "reintentando"}


@router.get("/consultas")
async def listar_consultas(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Consulta)
        .options(selectinload(Consulta.sub_consultas))
        .order_by(Consulta.created_at.desc())
        .limit(50)
    )
    consultas = result.scalars().all()
    return [_build_response(c) for c in consultas]


def _build_response(consulta: Consulta) -> dict:
    subs = consulta.sub_consultas
    todos_terminados = all(
        s.estado in (EstadoConsulta.completado.value, EstadoConsulta.fallido.value, EstadoConsulta.pendiente_24hs.value)
        for s in subs
    )
    tiene_fallos = any(s.estado == EstadoConsulta.fallido.value for s in subs)

    if todos_terminados and tiene_fallos:
        estado_general = "con_errores"
    elif todos_terminados:
        estado_general = "completado"
    else:
        estado_general = "en_proceso"

    return {
        "id": consulta.id,
        "patente": consulta.patente,
        "provincia": consulta.provincia,
        "created_at": consulta.created_at,
        "estado_general": estado_general,
        "sub_consultas": [
            {
                "tipo": s.tipo if isinstance(s.tipo, str) else s.tipo.value,
                "estado": s.estado if isinstance(s.estado, str) else s.estado.value,
                "intentos": s.intentos,
                "datos": s.datos,
                "error": s.error,
                "updated_at": s.updated_at,
            }
            for s in subs
        ],
    }
