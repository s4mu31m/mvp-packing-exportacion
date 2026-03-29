from django.db import transaction

from operaciones.application.results import UseCaseResult
from operaciones.application.exceptions import PayloadValidationError
from operaciones.models import TipoEvento
from operaciones.services.validators import validate_calidad_pallet_payload
from operaciones.services.event_builder import build_event_key
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories


@transaction.atomic
def registrar_calidad_pallet(
    payload: dict, *, repos: Repositories | None = None
) -> UseCaseResult:
    """
    Registra un control de calidad post-paletizaje.

    Reglas:
    - El pallet debe existir.
    - Multiples registros de calidad por pallet.
    """
    if repos is None:
        repos = get_repositories()

    try:
        data = validate_calidad_pallet_payload(payload)
    except PayloadValidationError as exc:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="Payload invalido para registrar calidad pallet",
            errors=exc.errors,
        )

    temporada = data["temporada"]
    pallet_code = data["pallet_code"]

    pallet = repos.pallets.find_by_code(temporada, pallet_code)
    if not pallet:
        return UseCaseResult.reject(
            code="PALLET_NOT_FOUND",
            message="El pallet no existe",
            errors=[f"No se encontro pallet {pallet_code} en temporada {temporada}"],
        )

    record = repos.calidad_pallets.create(
        pallet.id,
        operator_code=data["operator_code"],
        source_system=data["source_system"],
        extra=data.get("extra", {}),
    )

    event_key = build_event_key(
        temporada, "PALLET", pallet_code, TipoEvento.CALIDAD_PALLET, str(record.id)
    )
    repos.registros.get_or_create(
        event_key=event_key,
        temporada=temporada,
        tipo_evento=TipoEvento.CALIDAD_PALLET,
        pallet_id=pallet.id,
        operator_code=data["operator_code"],
        source_system=data["source_system"],
        payload={"pallet_code": pallet_code, "calidad_id": record.id},
    )

    return UseCaseResult.success(
        code="CALIDAD_PALLET_REGISTERED",
        message="Control de calidad de pallet registrado correctamente",
        data={
            "id": record.id,
            "pallet_code": pallet_code,
            "temporada": temporada,
            "aprobado": record.aprobado,
        },
    )
