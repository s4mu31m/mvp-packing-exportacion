from django.db import transaction

from operaciones.application.results import UseCaseResult
from operaciones.application.exceptions import PayloadValidationError
from operaciones.models import TipoEvento
from operaciones.services.validators import validate_control_proceso_packing_payload
from operaciones.services.event_builder import build_event_key
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories


@transaction.atomic
def registrar_control_proceso_packing(
    payload: dict, *, repos: Repositories | None = None
) -> UseCaseResult:
    """
    Registra la configuracion de la linea de proceso packing.

    Reglas:
    - El lote debe existir y tener IngresoAPacking previo.
    - Multiples registros por lote si los parametros cambian en el turno.
    """
    if repos is None:
        repos = get_repositories()

    try:
        data = validate_control_proceso_packing_payload(payload)
    except PayloadValidationError as exc:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="Payload invalido para registrar control de proceso packing",
            errors=exc.errors,
        )

    temporada = data["temporada"]
    lote_code = data["lote_code"]

    lote = repos.lotes.find_by_code(temporada, lote_code)
    if not lote:
        return UseCaseResult.reject(
            code="LOTE_NOT_FOUND",
            message="El lote no existe",
            errors=[f"No se encontro lote {lote_code} en temporada {temporada}"],
        )

    ingreso = repos.ingresos_packing.find_by_lote(lote.id)
    if not ingreso:
        return UseCaseResult.reject(
            code="INGRESO_PACKING_REQUIRED",
            message="El lote debe tener IngresoAPacking antes de registrar control de proceso",
            errors=["Registre IngresoAPacking antes de ControlProcesoPacking"],
        )

    record = repos.control_proceso_packings.create(
        lote.id,
        operator_code=data["operator_code"],
        source_system=data["source_system"],
        extra=data.get("extra", {}),
    )

    # Persiste etapa en Dataverse; no-op en SQLite (campo desconocido ignorado)
    repos.lotes.update(lote.id, {"etapa_actual": "Packing / Proceso"})

    event_key = build_event_key(
        temporada, "LOTE", lote_code, "CONTROL_PROCESO_PACKING", str(record.id)
    )
    repos.registros.get_or_create(
        event_key=event_key,
        temporada=temporada,
        tipo_evento=TipoEvento.CONTROL_CALIDAD,
        lote_id=lote.id,
        operator_code=data["operator_code"],
        source_system=data["source_system"],
        payload={"lote_code": lote_code, "control_proceso_id": record.id},
    )

    return UseCaseResult.success(
        code="CONTROL_PROCESO_PACKING_REGISTERED",
        message="Control de proceso packing registrado correctamente",
        data={
            "id": record.id,
            "lote_code": lote_code,
            "temporada": temporada,
        },
    )
