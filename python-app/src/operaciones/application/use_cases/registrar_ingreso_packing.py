from django.db import transaction

from operaciones.application.results import UseCaseResult
from operaciones.application.exceptions import PayloadValidationError
from operaciones.models import TipoEvento
from operaciones.services.validators import validate_ingreso_packing_payload
from operaciones.services.event_builder import build_event_key
from operaciones.services.timestamps import ahora_utc
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories


@transaction.atomic
def registrar_ingreso_packing(
    payload: dict, *, repos: Repositories | None = None
) -> UseCaseResult:
    """
    Registra el ingreso de un lote al area de packing.

    Reglas:
    - El lote debe existir.
    - Un lote puede tener exactamente un registro de ingreso a packing (1:1).
    - Es obligatorio para todos los lotes independientemente del flujo previo.
    - via_desverdizado = True si el lote paso por desverdizado.
    """
    if repos is None:
        repos = get_repositories()

    try:
        data = validate_ingreso_packing_payload(payload)
    except PayloadValidationError as exc:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="Payload invalido para registrar ingreso a packing",
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

    existente = repos.ingresos_packing.find_by_lote(lote.id)
    if existente:
        return UseCaseResult.reject(
            code="INGRESO_PACKING_ALREADY_EXISTS",
            message="El lote ya tiene un registro de ingreso a packing",
            errors=[f"Ya existe un registro de IngresoAPacking para lote {lote_code}"],
        )

    # Determinar automaticamente via_desverdizado si no se indica
    extra = data.get("extra", {})
    if "via_desverdizado" not in extra:
        desv = repos.desverdizados.find_by_lote(lote.id)
        extra["via_desverdizado"] = desv is not None

    record = repos.ingresos_packing.create(
        lote.id,
        operator_code=data["operator_code"],
        source_system=data["source_system"],
        extra=extra,
    )

    # Persiste etapa en Dataverse; no-op en SQLite (campo desconocido ignorado)
    repos.lotes.update(lote.id, {"etapa_actual": "Ingreso Packing", "ultimo_cambio_estado_at": ahora_utc()})

    event_key = build_event_key(temporada, "LOTE", lote_code, TipoEvento.INGRESO_PACKING)
    repos.registros.get_or_create(
        event_key=event_key,
        temporada=temporada,
        tipo_evento=TipoEvento.INGRESO_PACKING,
        lote_id=lote.id,
        operator_code=data["operator_code"],
        source_system=data["source_system"],
        payload={
            "lote_code": lote_code,
            "via_desverdizado": extra.get("via_desverdizado", False),
            "ingreso_id": record.id,
        },
    )

    return UseCaseResult.success(
        code="INGRESO_PACKING_REGISTERED",
        message="Ingreso a packing registrado correctamente",
        data={
            "id": record.id,
            "lote_code": lote_code,
            "temporada": temporada,
            "via_desverdizado": extra.get("via_desverdizado", False),
        },
    )
