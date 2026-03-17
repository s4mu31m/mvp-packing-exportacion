from django.db import transaction

from operaciones.application.results import UseCaseResult
from operaciones.application.exceptions import PayloadValidationError
from operaciones.models import Bin, Lote, BinLote, TipoEvento
from operaciones.services.validators import require_fields
from operaciones.services.normalizers import normalize_code, normalize_temporada, normalize_operator_code
from operaciones.services.event_builder import build_event_key, create_registro_etapa


@transaction.atomic
def crear_lote_recepcion(payload: dict) -> UseCaseResult:
    try:
        require_fields(payload, ["temporada", "lote_code", "bin_codes"])
    except PayloadValidationError as exc:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="Payload inválido para crear lote en recepción",
            errors=exc.errors,
        )

    temporada = normalize_temporada(payload["temporada"])
    lote_code = normalize_code(payload["lote_code"])
    bin_codes = payload.get("bin_codes", [])
    operator_code = normalize_operator_code(payload.get("operator_code", ""))
    source_system = payload.get("source_system", "local").strip() or "local"
    source_event_id = payload.get("source_event_id", "").strip()

    if not isinstance(bin_codes, list) or not bin_codes:
        return UseCaseResult.reject(
            code="INVALID_BIN_CODES",
            message="Debe enviar una lista no vacía de bins",
            errors=["bin_codes debe contener al menos un bin"],
        )

    bin_codes = [normalize_code(code) for code in bin_codes]

    lote_existente = Lote.objects.filter(
        temporada=temporada,
        lote_code=lote_code,
    ).first()

    if lote_existente:
        return UseCaseResult.reject(
            code="LOTE_ALREADY_EXISTS",
            message="El lote ya existe para la temporada indicada",
            errors=[f"Ya existe lote {lote_code} en temporada {temporada}"],
        )

    bins = list(
        Bin.objects.filter(
            temporada=temporada,
            bin_code__in=bin_codes,
        )
    )

    found_codes = {b.bin_code for b in bins}
    missing_codes = [code for code in bin_codes if code not in found_codes]

    if missing_codes:
        return UseCaseResult.reject(
            code="BINS_NOT_FOUND",
            message="Uno o más bins no existen",
            errors=[f"Bins no encontrados: {', '.join(missing_codes)}"],
        )

    # Regla opcional fuerte:
    # rechazar bins que ya estén ligados a otro lote
    bins_ya_asignados = BinLote.objects.filter(
        bin__in=bins).select_related("bin", "lote")
    if bins_ya_asignados.exists():
        errores = [
            f"El bin {rel.bin.bin_code} ya está asociado al lote {rel.lote.lote_code}"
            for rel in bins_ya_asignados
        ]
        return UseCaseResult.reject(
            code="BINS_ALREADY_ASSIGNED",
            message="Uno o más bins ya están asociados a un lote",
            errors=errores,
        )

    lote_obj = Lote.objects.create(
        temporada=temporada,
        lote_code=lote_code,
        operator_code=operator_code,
        source_system=source_system,
        source_event_id=source_event_id,
    )

    relaciones = []
    for bin_obj in bins:
        relacion = BinLote.objects.create(
            bin=bin_obj,
            lote=lote_obj,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
        )
        relaciones.append(
            {
                "bin_id": bin_obj.id,
                "bin_code": bin_obj.bin_code,
                "bin_lote_id": relacion.id,
            }
        )

    event_key = build_event_key(
        temporada,
        "LOTE",
        lote_code,
        "RECEPCION",
        "CREACION",
    )

    create_registro_etapa(
        temporada=temporada,
        event_key=event_key,
        tipo_evento=TipoEvento.LOTE_CREADO,
        lote_obj=lote_obj,
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
            "lote_id": lote_obj.id,
            "lote_code": lote_obj.lote_code,
            "temporada": lote_obj.temporada,
            "bins": relaciones,
        },
    )
