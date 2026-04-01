from django.db import transaction

from operaciones.application.results import UseCaseResult
from operaciones.application.exceptions import PayloadValidationError
from operaciones.models import TipoEvento, DisponibilidadCamara
from operaciones.services.validators import validate_camara_mantencion_payload
from operaciones.services.event_builder import build_event_key
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories


@transaction.atomic
def registrar_camara_mantencion(
    payload: dict, *, repos: Repositories | None = None
) -> UseCaseResult:
    """
    Registra el ingreso de un lote a camara de mantencion.

    Reglas:
    - El lote debe existir.
    - El lote debe tener requiere_desverdizado=True y
      disponibilidad_camara_desverdizado=no_disponible.
    - Un lote puede tener como maximo un registro de camara de mantencion.
    """
    if repos is None:
        repos = get_repositories()

    try:
        data = validate_camara_mantencion_payload(payload)
    except PayloadValidationError as exc:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="Payload invalido para registrar camara de mantencion",
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

    # Validacion de regla de negocio: solo si requiere desverdizado y no hay disponibilidad
    if not lote.requiere_desverdizado:
        return UseCaseResult.reject(
            code="CAMARA_MANTENCION_NO_APLICA",
            message="El lote no requiere desverdizado",
            errors=["CamaraMantencion solo aplica si requiere_desverdizado=True"],
        )

    if lote.disponibilidad_camara_desverdizado == DisponibilidadCamara.DISPONIBLE:
        return UseCaseResult.reject(
            code="CAMARA_DISPONIBLE",
            message="La camara de desverdizado esta disponible — ir directamente a desverdizado",
            errors=["CamaraMantencion solo se crea cuando disponibilidad_camara_desverdizado=no_disponible"],
        )

    # Verificar que no exista ya un registro
    existente = repos.camara_mantencions.find_by_lote(lote.id)
    if existente:
        return UseCaseResult.reject(
            code="CAMARA_MANTENCION_ALREADY_EXISTS",
            message="El lote ya tiene un registro de camara de mantencion",
            errors=[f"Ya existe un registro de CamaraMantencion para lote {lote_code}"],
        )

    record = repos.camara_mantencions.create(
        lote.id,
        operator_code=data["operator_code"],
        source_system=data["source_system"],
        extra=data.get("extra", {}),
    )

    # Persiste etapa en Dataverse; no-op en SQLite (campo desconocido ignorado)
    repos.lotes.update(lote.id, {"etapa_actual": "Mantencion"})

    event_key = build_event_key(temporada, "LOTE", lote_code, TipoEvento.CAMARA_MANTENCION)
    repos.registros.get_or_create(
        event_key=event_key,
        temporada=temporada,
        tipo_evento=TipoEvento.CAMARA_MANTENCION,
        lote_id=lote.id,
        operator_code=data["operator_code"],
        source_system=data["source_system"],
        payload={"lote_code": lote_code, "camara_mantencion_id": record.id},
    )

    return UseCaseResult.success(
        code="CAMARA_MANTENCION_REGISTERED",
        message="Camara de mantencion registrada correctamente",
        data={
            "id": record.id,
            "lote_code": lote_code,
            "temporada": temporada,
        },
    )
