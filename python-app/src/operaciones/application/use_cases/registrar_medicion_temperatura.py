from django.db import transaction

from operaciones.application.results import UseCaseResult
from operaciones.application.exceptions import PayloadValidationError
from operaciones.models import TipoEvento
from operaciones.services.validators import validate_medicion_temperatura_payload
from operaciones.services.event_builder import build_event_key
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories


@transaction.atomic
def registrar_medicion_temperatura(
    payload: dict, *, repos: Repositories | None = None
) -> UseCaseResult:
    """
    Registra una medicion de temperatura del pallet al salir de camara de frio.

    Reglas:
    - El pallet debe existir.
    - El pallet debe tener un registro de camara de frio previo.
    - Multiples mediciones por pallet.
    """
    if repos is None:
        repos = get_repositories()

    try:
        data = validate_medicion_temperatura_payload(payload)
    except PayloadValidationError as exc:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="Payload invalido para registrar medicion de temperatura",
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

    camara = repos.camara_frios.find_by_pallet(pallet.id)
    if not camara:
        return UseCaseResult.reject(
            code="CAMARA_FRIO_REQUIRED",
            message="El pallet debe tener un registro de CamaraFrio antes de registrar la medicion",
            errors=["Registre CamaraFrio antes de MedicionTemperaturaSalida"],
        )

    record = repos.mediciones_temperatura.create(
        pallet.id,
        operator_code=data["operator_code"],
        source_system=data["source_system"],
        extra=data.get("extra", {}),
    )

    # Actualizar etapa del lote asociado al pallet (si la relacion es accesible)
    # find_by_pallet: no-op en SQLite (retorna None), implementado en Dataverse.
    try:
        pl = repos.pallet_lotes.find_by_pallet(pallet.id)
        if pl and pl.lote_id:
            repos.lotes.update(pl.lote_id, {"etapa_actual": "Temperatura Salida"})
    except Exception:
        pass  # no bloquear el flujo si falla la actualizacion de etapa

    event_key = build_event_key(
        temporada, "PALLET", pallet_code, TipoEvento.CONTROL_TEMPERATURA, str(record.id)
    )
    repos.registros.get_or_create(
        event_key=event_key,
        temporada=temporada,
        tipo_evento=TipoEvento.CONTROL_TEMPERATURA,
        pallet_id=pallet.id,
        operator_code=data["operator_code"],
        source_system=data["source_system"],
        payload={
            "pallet_code": pallet_code,
            "medicion_id": record.id,
            "dentro_rango": record.dentro_rango,
        },
    )

    return UseCaseResult.success(
        code="MEDICION_TEMPERATURA_REGISTERED",
        message="Medicion de temperatura registrada correctamente",
        data={
            "id": record.id,
            "pallet_code": pallet_code,
            "temporada": temporada,
            "dentro_rango": record.dentro_rango,
        },
    )
