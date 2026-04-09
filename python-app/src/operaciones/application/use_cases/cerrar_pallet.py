from django.db import transaction

from operaciones.application.results import UseCaseResult
from operaciones.application.exceptions import PayloadValidationError
from operaciones.models import TipoEvento
from operaciones.services.validators import require_fields
from operaciones.services.normalizers import (
    normalize_code,
    normalize_temporada,
    normalize_operator_code,
)
from operaciones.services.code_generators import build_pallet_code
from operaciones.services.event_builder import build_event_key
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories


@transaction.atomic
def cerrar_pallet(payload: dict, *, repos: Repositories | None = None) -> UseCaseResult:
    """
    Cierra un pallet asociando los lotes que contiene.

    Reglas:
    - Todos los lotes referenciados deben existir en la temporada.
    - Si el pallet ya existe se reutiliza (idempotencia).
    - Se registran eventos: PALLET_CREADO (si es nuevo), LOTE_ASIGNADO_PALLET, PALLET_CERRADO.
    - El evento de cierre se emite solo si hay cambios reales y existe source_event_id.
    """
    if repos is None:
        repos = get_repositories()

    try:
        require_fields(payload, ["temporada", "lote_codes"])
    except PayloadValidationError as exc:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="Payload invalido para cierre de pallet",
            errors=exc.errors,
        )

    temporada       = normalize_temporada(payload["temporada"])
    # Generar pallet_code automaticamente si no se provee
    pallet_code_raw = (payload.get("pallet_code") or "").strip()
    pallet_code     = normalize_code(pallet_code_raw) if pallet_code_raw else build_pallet_code()
    raw_lote_codes  = payload.get("lote_codes", [])
    operator_code   = normalize_operator_code(payload.get("operator_code", ""))
    source_system   = payload.get("source_system", "local").strip() or "local"
    source_event_id = payload.get("source_event_id", "").strip()

    if not isinstance(raw_lote_codes, list) or not raw_lote_codes:
        return UseCaseResult.reject(
            code="INVALID_LOTE_CODES",
            message="Debe enviar una lista no vacía de lotes",
            errors=["lote_codes debe contener al menos un lote"],
        )

    lote_codes_normalizados: list[str] = []
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

    lote_records = repos.lotes.filter_by_codes(temporada, lote_codes_normalizados)

    found_codes   = {l.lote_code for l in lote_records}
    missing_codes = [c for c in lote_codes_normalizados if c not in found_codes]

    if missing_codes:
        return UseCaseResult.reject(
            code="LOTES_NOT_FOUND",
            message="Uno o más lotes no existen",
            errors=[f"Lotes no encontrados: {', '.join(missing_codes)}"],
        )

    pallet_record, pallet_created = repos.pallets.get_or_create(
        temporada,
        pallet_code,
        operator_code=operator_code,
        source_system=source_system,
        source_event_id=source_event_id,
    )

    pallet_created_event = False
    if pallet_created:
        _, pallet_created_event = repos.registros.get_or_create(
            event_key=build_event_key(temporada, "PALLET", pallet_code, "CREADO"),
            temporada=temporada,
            tipo_evento=TipoEvento.PALLET_CREADO,
            pallet_id=pallet_record.id,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
            payload={"pallet_code": pallet_code, "accion": "crear_pallet"},
        )

    linked = []
    relaciones_nuevas     = 0
    relaciones_existentes = 0
    lotes_por_codigo = {l.lote_code: l for l in lote_records}

    for lote_code in lote_codes_normalizados:
        lote_record = lotes_por_codigo[lote_code]

        _, relation_created = repos.pallet_lotes.get_or_create(
            pallet_record.id,
            lote_record.id,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
        )

        if relation_created:
            relaciones_nuevas += 1
            # Persiste etapa en Dataverse; no-op en SQLite (campo desconocido ignorado)
            repos.lotes.update(lote_record.id, {"etapa_actual": "Paletizado"})
            repos.registros.get_or_create(
                event_key=build_event_key(
                    temporada, "PALLET", pallet_code, "LOTE", lote_code, "ASIGNADO"
                ),
                temporada=temporada,
                tipo_evento=TipoEvento.LOTE_ASIGNADO_PALLET,
                pallet_id=pallet_record.id,
                lote_id=lote_record.id,
                operator_code=operator_code,
                source_system=source_system,
                source_event_id=source_event_id,
                payload={
                    "pallet_code": pallet_code,
                    "lote_code":   lote_code,
                    "accion":      "asignar_lote_a_pallet",
                },
            )
        else:
            relaciones_existentes += 1

        linked.append({
            "lote_id":          lote_record.id,
            "lote_code":        lote_code,
            "relation_created": relation_created,
        })

    pallet_closed_event = False
    hubo_cambios = pallet_created or relaciones_nuevas > 0

    if hubo_cambios and source_event_id:
        _, pallet_closed_event = repos.registros.get_or_create(
            event_key=build_event_key(temporada, "PALLET", pallet_code, "CIERRE", source_event_id),
            temporada=temporada,
            tipo_evento=TipoEvento.PALLET_CERRADO,
            pallet_id=pallet_record.id,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
            payload={
                "pallet_code": pallet_code,
                "lote_codes":  lote_codes_normalizados,
                "accion":      "cierre_pallet",
            },
        )

    return UseCaseResult.success(
        code="PALLET_CLOSED",
        message=f"Pallet {pallet_record.pallet_code} procesado correctamente",
        data={
            "pallet_id":              pallet_record.id,
            "pallet_code":            pallet_record.pallet_code,
            "pallet_created":         pallet_created,
            "pallet_created_event":   pallet_created_event,
            "pallet_closed_event":    pallet_closed_event,
            "relaciones_nuevas":      relaciones_nuevas,
            "relaciones_existentes":  relaciones_existentes,
            "lotes":                  linked,
        },
    )
