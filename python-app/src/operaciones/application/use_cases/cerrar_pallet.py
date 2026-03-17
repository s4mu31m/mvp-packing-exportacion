from django.db import transaction

from operaciones.application.results import UseCaseResult
from operaciones.application.exceptions import PayloadValidationError
from operaciones.models import Lote, Pallet, PalletLote, TipoEvento
from operaciones.services.validators import require_fields
from operaciones.services.normalizers import normalize_code, normalize_temporada, normalize_operator_code
from operaciones.services.event_builder import build_event_key, create_registro_etapa


@transaction.atomic
def cerrar_pallet(payload: dict) -> UseCaseResult:
    try:
        require_fields(payload, ["temporada", "pallet_code", "lote_codes"])
    except PayloadValidationError as exc:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="Payload inválido para cierre de pallet",
            errors=exc.errors,
        )

    temporada = normalize_temporada(payload["temporada"])
    pallet_code = normalize_code(payload["pallet_code"])
    lote_codes = payload.get("lote_codes", [])
    operator_code = normalize_operator_code(payload.get("operator_code", ""))
    source_system = payload.get("source_system", "local").strip() or "local"
    source_event_id = payload.get("source_event_id", "").strip()

    if not isinstance(lote_codes, list) or not lote_codes:
        return UseCaseResult.reject(
            code="INVALID_LOTE_CODES",
            message="Debe enviar una lista no vacía de lotes",
            errors=["lote_codes debe contener al menos un lote"],
        )

    lote_codes = [normalize_code(code) for code in lote_codes]

    lotes = list(
        Lote.objects.filter(
            temporada=temporada,
            lote_code__in=lote_codes,
        )
    )

    found_codes = {l.lote_code for l in lotes}
    missing_codes = [code for code in lote_codes if code not in found_codes]

    if missing_codes:
        return UseCaseResult.reject(
            code="LOTES_NOT_FOUND",
            message="Uno o más lotes no existen",
            errors=[f"Lotes no encontrados: {', '.join(missing_codes)}"],
        )

    pallet_obj, pallet_created = Pallet.objects.get_or_create(
        temporada=temporada,
        pallet_code=pallet_code,
        defaults={
            "operator_code": operator_code,
            "source_system": source_system,
            "source_event_id": source_event_id,
        },
    )

    linked = []
    for lote_obj in lotes:
        _, relation_created = PalletLote.objects.get_or_create(
            pallet=pallet_obj,
            lote=lote_obj,
            defaults={
                "operator_code": operator_code,
                "source_system": source_system,
                "source_event_id": source_event_id,
            },
        )
        linked.append({
            "lote_id": lote_obj.id,
            "lote_code": lote_obj.lote_code,
            "relation_created": relation_created,
        })

    event_key = build_event_key(
        temporada,
        "PALLET",
        pallet_code,
        "CIERRE",
    )

    create_registro_etapa(
        temporada=temporada,
        event_key=event_key,
        tipo_evento=TipoEvento.PALLET_CREADO,
        pallet_obj=pallet_obj,
        operator_code=operator_code,
        source_system=source_system,
        source_event_id=source_event_id,
        payload={
            "pallet_code": pallet_code,
            "lote_codes": lote_codes,
            "accion": "cierre_pallet",
        },
    )

    return UseCaseResult.success(
        code="PALLET_CLOSED",
        message="Pallet cerrado correctamente",
        data={
            "pallet_id": pallet_obj.id,
            "pallet_code": pallet_obj.pallet_code,
            "pallet_created": pallet_created,
            "lotes": linked,
        },
    )
