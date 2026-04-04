from django.db import transaction

from operaciones.application.results import UseCaseResult
from operaciones.application.exceptions import PayloadValidationError
from operaciones.models import TipoEvento, DisponibilidadCamara
from operaciones.services.validators import validate_desverdizado_payload
from operaciones.services.event_builder import build_event_key
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories


@transaction.atomic
def registrar_desverdizado(
    payload: dict, *, repos: Repositories | None = None
) -> UseCaseResult:
    """
    Registra el proceso de desverdizado de un lote.

    Reglas:
    - El lote debe existir y tener requiere_desverdizado=True.
    - La camara debe estar disponible (disponibilidad_camara_desverdizado=disponible).
    - Un lote puede tener como maximo un registro de desverdizado.
    """
    if repos is None:
        repos = get_repositories()

    try:
        data = validate_desverdizado_payload(payload)
    except PayloadValidationError as exc:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="Payload invalido para registrar desverdizado",
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

    if not lote.requiere_desverdizado:
        return UseCaseResult.reject(
            code="DESVERDIZADO_NO_APLICA",
            message="El lote no requiere desverdizado",
            errors=["Desverdizado solo aplica si requiere_desverdizado=True"],
        )

    if lote.disponibilidad_camara_desverdizado == DisponibilidadCamara.NO_DISPONIBLE:
        return UseCaseResult.reject(
            code="CAMARA_NO_DISPONIBLE",
            message="La camara de desverdizado no esta disponible",
            errors=["Actualice disponibilidad_camara_desverdizado a 'disponible' antes de crear el desverdizado"],
        )

    existente = repos.desverdizados.find_by_lote(lote.id)
    if existente:
        return UseCaseResult.reject(
            code="DESVERDIZADO_ALREADY_EXISTS",
            message="El lote ya tiene un registro de desverdizado",
            errors=[f"Ya existe un registro de Desverdizado para lote {lote_code}"],
        )

    record = repos.desverdizados.create(
        lote.id,
        operator_code=data["operator_code"],
        source_system=data["source_system"],
        extra=data.get("extra", {}),
    )

    # Persiste etapa en Dataverse; no-op en SQLite (campo desconocido ignorado)
    repos.lotes.update(lote.id, {"etapa_actual": "Desverdizado"})

    event_key = build_event_key(temporada, "LOTE", lote_code, TipoEvento.DESVERDIZADO_INGRESO)
    repos.registros.get_or_create(
        event_key=event_key,
        temporada=temporada,
        tipo_evento=TipoEvento.DESVERDIZADO_INGRESO,
        lote_id=lote.id,
        operator_code=data["operator_code"],
        source_system=data["source_system"],
        payload={"lote_code": lote_code, "desverdizado_id": record.id},
    )

    return UseCaseResult.success(
        code="DESVERDIZADO_REGISTERED",
        message="Desverdizado registrado correctamente",
        data={
            "id": record.id,
            "lote_code": lote_code,
            "temporada": temporada,
        },
    )
