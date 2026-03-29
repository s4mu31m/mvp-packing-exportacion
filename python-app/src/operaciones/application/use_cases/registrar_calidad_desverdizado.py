from django.db import transaction

from operaciones.application.results import UseCaseResult
from operaciones.application.exceptions import PayloadValidationError
from operaciones.models import TipoEvento
from operaciones.services.validators import validate_calidad_desverdizado_payload
from operaciones.services.event_builder import build_event_key
from operaciones.services.normalizers import normalize_temporada
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories


@transaction.atomic
def registrar_calidad_desverdizado(
    payload: dict, *, repos: Repositories | None = None
) -> UseCaseResult:
    """
    Registra un control de calidad post-desverdizado.

    Reglas:
    - El lote debe existir.
    - El lote debe haber pasado por desverdizado (tener un registro Desverdizado).
    - Pueden registrarse multiples evaluaciones por lote.
    """
    if repos is None:
        repos = get_repositories()

    try:
        data = validate_calidad_desverdizado_payload(payload)
    except PayloadValidationError as exc:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="Payload invalido para registrar calidad desverdizado",
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

    desv = repos.desverdizados.find_by_lote(lote.id)
    if not desv:
        return UseCaseResult.reject(
            code="DESVERDIZADO_NOT_FOUND",
            message="El lote no tiene un registro de desverdizado",
            errors=["CalidadDesverdizado solo aplica si el lote paso por Desverdizado"],
        )

    record = repos.calidad_desverdizados.create(
        lote.id,
        operator_code=data["operator_code"],
        source_system=data["source_system"],
        extra=data.get("extra", {}),
    )

    import time
    event_key = build_event_key(
        temporada, "LOTE", lote_code, TipoEvento.CALIDAD_DESVERDIZADO, str(record.id)
    )
    repos.registros.get_or_create(
        event_key=event_key,
        temporada=temporada,
        tipo_evento=TipoEvento.CALIDAD_DESVERDIZADO,
        lote_id=lote.id,
        operator_code=data["operator_code"],
        source_system=data["source_system"],
        payload={"lote_code": lote_code, "calidad_id": record.id},
    )

    return UseCaseResult.success(
        code="CALIDAD_DESVERDIZADO_REGISTERED",
        message="Control de calidad post-desverdizado registrado correctamente",
        data={
            "id": record.id,
            "lote_code": lote_code,
            "temporada": temporada,
            "aprobado": record.aprobado,
        },
    )
