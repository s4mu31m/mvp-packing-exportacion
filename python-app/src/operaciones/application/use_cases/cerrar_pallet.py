from django.db import transaction

from operaciones.application.results import UseCaseResult
from operaciones.application.exceptions import PayloadValidationError
from operaciones.models import (
    Lote,
    Pallet,
    PalletLote,
    RegistroEtapa,
    TipoEvento,
)
from operaciones.services.validators import require_fields
from operaciones.services.normalizers import (
    normalize_code,
    normalize_temporada,
    normalize_operator_code,
)
from operaciones.services.event_builder import build_event_key


def _registrar_evento_si_no_existe(
    *,
    temporada: str,
    event_key: str,
    tipo_evento: str,
    pallet_obj=None,
    lote_obj=None,
    operator_code: str = "",
    source_system: str = "local",
    source_event_id: str = "",
    payload: dict | None = None,
) -> tuple[RegistroEtapa, bool]:
    return RegistroEtapa.objects.get_or_create(
        event_key=event_key,
        defaults={
            "temporada": temporada,
            "tipo_evento": tipo_evento,
            "pallet": pallet_obj,
            "lote": lote_obj,
            "operator_code": operator_code,
            "source_system": source_system,
            "source_event_id": source_event_id,
            "payload": payload or {},
        },
    )


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
    raw_lote_codes = payload.get("lote_codes", [])
    operator_code = normalize_operator_code(payload.get("operator_code", ""))
    source_system = payload.get("source_system", "local").strip() or "local"
    source_event_id = payload.get("source_event_id", "").strip()

    if not isinstance(raw_lote_codes, list) or not raw_lote_codes:
        return UseCaseResult.reject(
            code="INVALID_LOTE_CODES",
            message="Debe enviar una lista no vacía de lotes",
            errors=["lote_codes debe contener al menos un lote"],
        )

    lote_codes_normalizados = []
    for code in raw_lote_codes:
        normalizado = normalize_code(code)
        if normalizado and normalizado not in lote_codes_normalizados:
            lote_codes_normalizados.append(normalizado)

    if not lote_codes_normalizados:
        return UseCaseResult.reject(
            code="INVALID_LOTE_CODES",
            message="Debe enviar una lista válida de lotes",
            errors=["lote_codes no contiene códigos válidos"],
        )

    lotes = list(
        Lote.objects.filter(
            temporada=temporada,
            lote_code__in=lote_codes_normalizados,
        )
    )

    found_codes = {l.lote_code for l in lotes}
    missing_codes = [
        code for code in lote_codes_normalizados
        if code not in found_codes
    ]

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

    pallet_created_event = False
    if pallet_created:
        _, pallet_created_event = _registrar_evento_si_no_existe(
            temporada=temporada,
            event_key=build_event_key(
                temporada,
                "PALLET",
                pallet_code,
                "CREADO",
            ),
            tipo_evento=TipoEvento.PALLET_CREADO,
            pallet_obj=pallet_obj,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
            payload={
                "pallet_code": pallet_code,
                "accion": "crear_pallet",
            },
        )

    linked = []
    relaciones_nuevas = 0
    relaciones_existentes = 0

    lotes_por_codigo = {l.lote_code: l for l in lotes}

    for lote_code in lote_codes_normalizados:
        lote_obj = lotes_por_codigo[lote_code]

        _, relation_created = PalletLote.objects.get_or_create(
            pallet=pallet_obj,
            lote=lote_obj,
            defaults={
                "operator_code": operator_code,
                "source_system": source_system,
                "source_event_id": source_event_id,
            },
        )

        if relation_created:
            relaciones_nuevas += 1

            _registrar_evento_si_no_existe(
                temporada=temporada,
                event_key=build_event_key(
                    temporada,
                    "PALLET",
                    pallet_code,
                    "LOTE",
                    lote_obj.lote_code,
                    "ASIGNADO",
                ),
                tipo_evento=TipoEvento.LOTE_ASIGNADO_PALLET,
                pallet_obj=pallet_obj,
                lote_obj=lote_obj,
                operator_code=operator_code,
                source_system=source_system,
                source_event_id=source_event_id,
                payload={
                    "pallet_code": pallet_code,
                    "lote_code": lote_obj.lote_code,
                    "accion": "asignar_lote_a_pallet",
                },
            )
        else:
            relaciones_existentes += 1

        linked.append({
            "lote_id": lote_obj.id,
            "lote_code": lote_obj.lote_code,
            "relation_created": relation_created,
        })

    # El evento de cierre solo se registra si la invocación realmente produjo
    # cambios y existe un identificador externo que permita idempotencia clara.
    pallet_closed_event = False
    hubo_cambios = pallet_created or relaciones_nuevas > 0

    if hubo_cambios and source_event_id:
        _, pallet_closed_event = _registrar_evento_si_no_existe(
            temporada=temporada,
            event_key=build_event_key(
                temporada,
                "PALLET",
                pallet_code,
                "CIERRE",
                source_event_id,
            ),
            tipo_evento=TipoEvento.PALLET_CERRADO,
            pallet_obj=pallet_obj,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
            payload={
                "pallet_code": pallet_code,
                "lote_codes": lote_codes_normalizados,
                "accion": "cierre_pallet",
            },
        )

    return UseCaseResult.success(
        code="PALLET_CLOSED",
        message="Pallet procesado correctamente",
        data={
            "pallet_id": pallet_obj.id,
            "pallet_code": pallet_obj.pallet_code,
            "pallet_created": pallet_created,
            "pallet_created_event": pallet_created_event,
            "pallet_closed_event": pallet_closed_event,
            "relaciones_nuevas": relaciones_nuevas,
            "relaciones_existentes": relaciones_existentes,
            "lotes": linked,
        },
    )