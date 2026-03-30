from django.db import transaction

from operaciones.application.results import UseCaseResult
from operaciones.application.exceptions import PayloadValidationError
from operaciones.models import TipoEvento, LotePlantaEstado
from operaciones.services.validators import require_fields
from operaciones.services.normalizers import normalize_code, normalize_temporada, normalize_operator_code
from operaciones.services.season import resolve_temporada_codigo
from operaciones.services.code_generators import next_lote_correlativo
from operaciones.services.event_builder import build_event_key
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories


@transaction.atomic
def crear_lote_recepcion(payload: dict, *, repos: Repositories | None = None) -> UseCaseResult:
    """
    Crea un lote en recepcion y asocia los bins que lo componen.

    El lote_code se genera automaticamente con correlativo por temporada.
    Si el caller lo provee explicitamente, se respeta para compatibilidad.

    Reglas:
    - Todos los bins referenciados deben existir en la temporada.
    - El lote_code debe ser unico por temporada.
    - Ningun bin puede estar ya asignado a otro lote (estrategia strict).
    - Se registra un evento LOTE_CREADO para trazabilidad.
    """
    if repos is None:
        repos = get_repositories()

    try:
        require_fields(payload, ["temporada", "bin_codes"])
    except PayloadValidationError as exc:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="Payload invalido para crear lote en recepcion",
            errors=exc.errors,
        )

    temporada       = normalize_temporada(payload["temporada"])
    bin_codes       = payload.get("bin_codes", [])
    operator_code   = normalize_operator_code(payload.get("operator_code", ""))
    source_system   = payload.get("source_system", "local").strip() or "local"
    source_event_id = payload.get("source_event_id", "").strip()

    # Resolver temporada_codigo
    temporada_codigo = (payload.get("temporada_codigo") or "").strip()
    if not temporada_codigo:
        temporada_codigo = resolve_temporada_codigo()

    if not isinstance(bin_codes, list) or not bin_codes:
        return UseCaseResult.reject(
            code="INVALID_BIN_CODES",
            message="Debe enviar una lista no vacia de bins",
            errors=["bin_codes debe contener al menos un bin"],
        )

    bin_codes = [normalize_code(code) for code in bin_codes]

    # Generar lote_code automaticamente si no se provee
    lote_code_raw = (payload.get("lote_code") or "").strip()
    if lote_code_raw:
        lote_code = normalize_code(lote_code_raw)
        correlativo = None
    else:
        lote_code, correlativo = next_lote_correlativo(temporada_codigo)

    lote_existente = repos.lotes.find_by_code(temporada, lote_code)
    if lote_existente:
        return UseCaseResult.reject(
            code="LOTE_ALREADY_EXISTS",
            message="El lote ya existe para la temporada indicada",
            errors=[f"Ya existe lote {lote_code} en temporada {temporada}"],
        )

    bin_records = repos.bins.filter_by_codes(temporada, bin_codes)

    found_codes   = {b.bin_code for b in bin_records}
    missing_codes = [code for code in bin_codes if code not in found_codes]

    if missing_codes:
        return UseCaseResult.reject(
            code="BINS_NOT_FOUND",
            message="Uno o mas bins no existen",
            errors=[f"Bins no encontrados: {', '.join(missing_codes)}"],
        )

    bin_ids    = [b.id for b in bin_records]
    conflicts  = repos.bin_lotes.find_existing_assignments(bin_ids)
    if conflicts:
        errores = [
            f"El bin {c.bin_code} ya esta asociado al lote {c.lote_code}"
            for c in conflicts
        ]
        return UseCaseResult.reject(
            code="BINS_ALREADY_ASSIGNED",
            message="Uno o mas bins ya estan asociados a un lote",
            errors=errores,
        )

    extra: dict = {
        "temporada_codigo": temporada_codigo,
        "estado":           LotePlantaEstado.CERRADO,
        "cantidad_bins":    len(bin_codes),
    }
    if correlativo is not None:
        extra["correlativo_temporada"] = correlativo
    for campo in ["fecha_conformacion", "kilos_bruto_conformacion", "kilos_neto_conformacion",
                  "requiere_desverdizado", "disponibilidad_camara_desverdizado", "rol"]:
        if payload.get(campo) not in [None, ""]:
            extra[campo] = payload[campo]

    lote_record = repos.lotes.create(
        temporada,
        lote_code,
        operator_code=operator_code,
        source_system=source_system,
        source_event_id=source_event_id,
        extra=extra,
    )

    bins_por_code = {b.bin_code: b for b in bin_records}
    relaciones = []
    for code in bin_codes:
        bin_r = bins_por_code[code]
        bin_lote_record = repos.bin_lotes.create(
            bin_r.id,
            lote_record.id,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
        )
        relaciones.append({
            "bin_id":      bin_r.id,
            "bin_code":    bin_r.bin_code,
            "bin_lote_id": bin_lote_record.id,
        })

    event_key = build_event_key(temporada, "LOTE", lote_code, "RECEPCION", "CREACION")
    repos.registros.create(
        temporada=temporada,
        event_key=event_key,
        tipo_evento=TipoEvento.LOTE_CREADO,
        lote_id=lote_record.id,
        operator_code=operator_code,
        source_system=source_system,
        source_event_id=source_event_id,
        payload={
            "lote_code":        lote_code,
            "temporada_codigo": temporada_codigo,
            "bin_codes":        bin_codes,
            "etapa":            "recepcion",
            "accion":           "crear_lote",
        },
    )

    return UseCaseResult.success(
        code="LOTE_CREATED",
        message="Lote creado en recepcion correctamente",
        data={
            "lote_id":          lote_record.id,
            "lote_code":        lote_record.lote_code,
            "temporada":        lote_record.temporada,
            "temporada_codigo": temporada_codigo,
            "bins":             relaciones,
        },
    )
