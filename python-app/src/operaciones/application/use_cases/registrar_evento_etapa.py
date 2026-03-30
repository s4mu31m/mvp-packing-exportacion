from datetime import datetime, timezone

from django.db import transaction

from operaciones.application.results import UseCaseResult
from operaciones.models import TipoEvento
from operaciones.services.event_builder import build_event_key
from operaciones.services.normalizers import normalize_code, normalize_temporada
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories


@transaction.atomic
def registrar_evento_etapa(payload: dict, *, repos: Repositories | None = None) -> UseCaseResult:
    """
    Registra un evento de etapa operacional para un lote (y opcionalmente un bin o pallet).

    Acepta cualquier TipoEvento válido. Útil para registrar hitos como desverdizado,
    packing, control de calidad, ingreso a cámaras, etc.

    El campo lote_code es obligatorio. bin_code y pallet_code son opcionales y, si se
    proveen, deben existir en la temporada indicada.
    """
    if repos is None:
        repos = get_repositories()

    tipo_evento_raw = payload.get("tipo_evento", "")
    valid_values    = {choice.value for choice in TipoEvento}
    if tipo_evento_raw not in valid_values:
        return UseCaseResult.reject(
            code="INVALID_TIPO_EVENTO",
            message="tipo_evento no es un valor válido",
            errors=[
                f"'{tipo_evento_raw}' no es un TipoEvento válido. "
                f"Valores posibles: {sorted(valid_values)}"
            ],
        )

    temporada  = normalize_temporada(payload.get("temporada", ""))
    lote_code  = normalize_code(payload.get("lote_code", ""))

    if not lote_code:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="lote_code es obligatorio",
            errors=["El campo lote_code es requerido y no puede estar vacío"],
        )

    lote_record = repos.lotes.find_by_code(temporada, lote_code)
    if not lote_record:
        return UseCaseResult.reject(
            code="LOTE_NOT_FOUND",
            message="El lote no existe para la temporada indicada",
            errors=[f"No se encontró lote '{lote_code}' en temporada '{temporada}'"],
        )

    bin_id = None
    bin_code_raw = payload.get("bin_code", "")
    if bin_code_raw:
        bin_code   = normalize_code(bin_code_raw)
        bin_record = repos.bins.find_by_code(temporada, bin_code)
        if not bin_record:
            return UseCaseResult.reject(
                code="BIN_NOT_FOUND",
                message="El bin no existe para la temporada indicada",
                errors=[f"No se encontró bin '{bin_code}' en temporada '{temporada}'"],
            )
        bin_id = bin_record.id

    pallet_id = None
    pallet_code_raw = payload.get("pallet_code", "")
    if pallet_code_raw:
        pallet_code   = normalize_code(pallet_code_raw)
        pallet_record = repos.pallets.find_by_code(temporada, pallet_code)
        if not pallet_record:
            return UseCaseResult.reject(
                code="PALLET_NOT_FOUND",
                message="El pallet no existe para la temporada indicada",
                errors=[f"No se encontró pallet '{pallet_code}' en temporada '{temporada}'"],
            )
        pallet_id = pallet_record.id

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d%H%M%S%f")
    event_key = build_event_key(temporada, tipo_evento_raw, lote_code, timestamp)

    operator_code = payload.get("operator_code", "")
    datos         = payload.get("datos") or {}

    registro = repos.registros.create(
        temporada=temporada,
        event_key=event_key,
        tipo_evento=tipo_evento_raw,
        bin_id=bin_id,
        lote_id=lote_record.id,
        pallet_id=pallet_id,
        operator_code=operator_code,
        payload=datos,
    )

    return UseCaseResult.success(
        code="EVENTO_REGISTRADO",
        message="Evento de etapa registrado correctamente",
        data={"registro_id": registro.id, "event_key": event_key},
    )
