from django.db import transaction

from operaciones.application.results import UseCaseResult
from operaciones.application.exceptions import PayloadValidationError
from operaciones.models import TipoEvento
from operaciones.services.validators import require_fields
from operaciones.services.normalizers import normalize_code, normalize_temporada, normalize_operator_code
from operaciones.services.event_builder import build_event_key
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories


@transaction.atomic
def crear_lote_recepcion(payload: dict, *, repos: Repositories | None = None) -> UseCaseResult:
    """
    Crea un lote en recepción y asocia los bins que lo componen.

    Reglas:
    - Todos los bins referenciados deben existir en la temporada.
    - El lote_code debe ser único por temporada.
    - Ningún bin puede estar ya asignado a otro lote (estrategia strict).
    - Se registra un evento LOTE_CREADO para trazabilidad.
    """
    if repos is None:
        repos = get_repositories()

    try:
        require_fields(payload, ["temporada", "lote_code", "bin_codes"])
    except PayloadValidationError as exc:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="Payload inválido para crear lote en recepción",
            errors=exc.errors,
        )

    temporada      = normalize_temporada(payload["temporada"])
    lote_code      = normalize_code(payload["lote_code"])
    bin_codes      = payload.get("bin_codes", [])
    operator_code  = normalize_operator_code(payload.get("operator_code", ""))
    source_system  = payload.get("source_system", "local").strip() or "local"
    source_event_id = payload.get("source_event_id", "").strip()

    if not isinstance(bin_codes, list) or not bin_codes:
        return UseCaseResult.reject(
            code="INVALID_BIN_CODES",
            message="Debe enviar una lista no vacía de bins",
            errors=["bin_codes debe contener al menos un bin"],
        )

    bin_codes = [normalize_code(code) for code in bin_codes]

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
            message="Uno o más bins no existen",
            errors=[f"Bins no encontrados: {', '.join(missing_codes)}"],
        )

    bin_ids = [b.id for b in bin_records]
    conflicts = repos.bin_lotes.find_existing_assignments(bin_ids)
    if conflicts:
        errores = [
            f"El bin {c.bin_code} ya está asociado al lote {c.lote_code}"
            for c in conflicts
        ]
        return UseCaseResult.reject(
            code="BINS_ALREADY_ASSIGNED",
            message="Uno o más bins ya están asociados a un lote",
            errors=errores,
        )

    lote_record = repos.lotes.create(
        temporada,
        lote_code,
        operator_code=operator_code,
        source_system=source_system,
        source_event_id=source_event_id,
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
            "lote_code": lote_code,
            "bin_codes": bin_codes,
            "etapa": "recepcion",
            "accion": "crear_lote",
        },
    )

    return UseCaseResult.success(
        code="LOTE_CREATED",
        message="Lote creado en recepción correctamente",
        data={
            "lote_id":   lote_record.id,
            "lote_code": lote_record.lote_code,
            "temporada": lote_record.temporada,
            "bins":      relaciones,
        },
    )
