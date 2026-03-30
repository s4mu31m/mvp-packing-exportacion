from django.db import transaction

from operaciones.application.results import UseCaseResult
from operaciones.application.exceptions import PayloadValidationError
from operaciones.models import TipoEvento
from operaciones.services.validators import validate_registro_packing_payload
from operaciones.services.event_builder import build_event_key
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories


@transaction.atomic
def registrar_registro_packing(
    payload: dict, *, repos: Repositories | None = None
) -> UseCaseResult:
    """
    Registra la produccion de un lote en packing.

    Reglas:
    - El lote debe existir.
    - El lote debe tener un IngresoAPacking previo.
    - Multiples registros por lote segun combinacion de categoria/calibre/linea.
    """
    if repos is None:
        repos = get_repositories()

    try:
        data = validate_registro_packing_payload(payload)
    except PayloadValidationError as exc:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="Payload invalido para registrar produccion packing",
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
            message="El lote debe tener un IngresoAPacking antes de registrar produccion",
            errors=["Registre IngresoAPacking antes de RegistroPacking"],
        )

    record = repos.registros_packing.create(
        lote.id,
        operator_code=data["operator_code"],
        source_system=data["source_system"],
        extra=data.get("extra", {}),
    )

    event_key = build_event_key(
        temporada, "LOTE", lote_code, TipoEvento.PACKING_PROCESO, str(record.id)
    )
    repos.registros.get_or_create(
        event_key=event_key,
        temporada=temporada,
        tipo_evento=TipoEvento.PACKING_PROCESO,
        lote_id=lote.id,
        operator_code=data["operator_code"],
        source_system=data["source_system"],
        payload={"lote_code": lote_code, "registro_packing_id": record.id},
    )

    return UseCaseResult.success(
        code="REGISTRO_PACKING_REGISTERED",
        message="Registro de produccion packing registrado correctamente",
        data={
            "id": record.id,
            "lote_code": lote_code,
            "temporada": temporada,
        },
    )
