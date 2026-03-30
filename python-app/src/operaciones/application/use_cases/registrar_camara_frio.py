from django.db import transaction

from operaciones.application.results import UseCaseResult
from operaciones.application.exceptions import PayloadValidationError
from operaciones.models import TipoEvento
from operaciones.services.validators import validate_camara_frio_payload
from operaciones.services.event_builder import build_event_key
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories


@transaction.atomic
def registrar_camara_frio(
    payload: dict, *, repos: Repositories | None = None
) -> UseCaseResult:
    """
    Registra el ingreso de un pallet a la camara de frio.

    Reglas:
    - El pallet debe existir.
    - Un pallet tiene exactamente un registro de camara de frio (1:1).
    """
    if repos is None:
        repos = get_repositories()

    try:
        data = validate_camara_frio_payload(payload)
    except PayloadValidationError as exc:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="Payload invalido para registrar camara de frio",
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

    existente = repos.camara_frios.find_by_pallet(pallet.id)
    if existente:
        return UseCaseResult.reject(
            code="CAMARA_FRIO_ALREADY_EXISTS",
            message="El pallet ya tiene un registro de camara de frio",
            errors=[f"Ya existe un registro de CamaraFrio para pallet {pallet_code}"],
        )

    record = repos.camara_frios.create(
        pallet.id,
        operator_code=data["operator_code"],
        source_system=data["source_system"],
        extra=data.get("extra", {}),
    )

    event_key = build_event_key(temporada, "PALLET", pallet_code, TipoEvento.CAMARA_FRIO_INGRESO)
    repos.registros.get_or_create(
        event_key=event_key,
        temporada=temporada,
        tipo_evento=TipoEvento.CAMARA_FRIO_INGRESO,
        pallet_id=pallet.id,
        operator_code=data["operator_code"],
        source_system=data["source_system"],
        payload={"pallet_code": pallet_code, "camara_frio_id": record.id},
    )

    return UseCaseResult.success(
        code="CAMARA_FRIO_REGISTERED",
        message="Camara de frio registrada correctamente",
        data={
            "id": record.id,
            "pallet_code": pallet_code,
            "temporada": temporada,
        },
    )
