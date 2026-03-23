from datetime import datetime, timezone

from django.db import transaction

from operaciones.application.results import UseCaseResult
from operaciones.models import Bin, Lote, Pallet, TipoEvento
from operaciones.services.event_builder import build_event_key, create_registro_etapa
from operaciones.services.normalizers import normalize_code, normalize_temporada


@transaction.atomic
def registrar_evento_etapa(payload: dict) -> UseCaseResult:
    tipo_evento_raw = payload.get("tipo_evento", "")
    valid_values = {choice.value for choice in TipoEvento}
    if tipo_evento_raw not in valid_values:
        return UseCaseResult.reject(
            code="INVALID_TIPO_EVENTO",
            message="tipo_evento no es un valor válido",
            errors=[f"'{tipo_evento_raw}' no es un TipoEvento válido. Valores posibles: {sorted(valid_values)}"],
        )

    temporada = normalize_temporada(payload.get("temporada", ""))
    lote_code_raw = payload.get("lote_code", "")
    lote_code = normalize_code(lote_code_raw)

    if not lote_code:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="lote_code es obligatorio",
            errors=["El campo lote_code es requerido y no puede estar vacío"],
        )

    lote_obj = Lote.objects.filter(temporada=temporada, lote_code=lote_code).first()
    if not lote_obj:
        return UseCaseResult.reject(
            code="LOTE_NOT_FOUND",
            message="El lote no existe para la temporada indicada",
            errors=[f"No se encontró lote '{lote_code}' en temporada '{temporada}'"],
        )

    bin_obj = None
    bin_code_raw = payload.get("bin_code", "")
    if bin_code_raw:
        bin_code = normalize_code(bin_code_raw)
        bin_obj = Bin.objects.filter(temporada=temporada, bin_code=bin_code).first()
        if not bin_obj:
            return UseCaseResult.reject(
                code="BIN_NOT_FOUND",
                message="El bin no existe para la temporada indicada",
                errors=[f"No se encontró bin '{bin_code}' en temporada '{temporada}'"],
            )

    pallet_obj = None
    pallet_code_raw = payload.get("pallet_code", "")
    if pallet_code_raw:
        pallet_code = normalize_code(pallet_code_raw)
        pallet_obj = Pallet.objects.filter(temporada=temporada, pallet_code=pallet_code).first()
        if not pallet_obj:
            return UseCaseResult.reject(
                code="PALLET_NOT_FOUND",
                message="El pallet no existe para la temporada indicada",
                errors=[f"No se encontró pallet '{pallet_code}' en temporada '{temporada}'"],
            )

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d%H%M%S%f")
    event_key = build_event_key(temporada, tipo_evento_raw, lote_code, timestamp)

    operator_code = payload.get("operator_code", "")
    datos = payload.get("datos") or {}

    registro = create_registro_etapa(
        temporada=temporada,
        event_key=event_key,
        tipo_evento=tipo_evento_raw,
        bin_obj=bin_obj,
        lote_obj=lote_obj,
        pallet_obj=pallet_obj,
        operator_code=operator_code,
        payload=datos,
    )

    return UseCaseResult.success(
        code="EVENTO_REGISTRADO",
        message="Evento de etapa registrado correctamente",
        data={"registro_id": registro.id, "event_key": event_key},
    )
