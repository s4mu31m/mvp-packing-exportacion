from django.db import transaction

from operaciones.application.results import UseCaseResult
from operaciones.application.exceptions import PayloadValidationError
from operaciones.models import TipoEvento
from operaciones.services.validators import validate_bin_payload
from operaciones.services.event_builder import build_event_key
from operaciones.services.code_generators import build_bin_code
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories


@transaction.atomic
def registrar_bin_recibido(payload: dict, *, repos: Repositories | None = None) -> UseCaseResult:
    """
    Registra un bin recibido.

    El bin_code se genera automaticamente en backend desde los atributos
    operativos (fecha_cosecha, correlativo diario). Si el caller lo provee
    explicitamente, se respeta para compatibilidad con integraciones upstream.

    Reglas:
    - El bin debe ser unico por temporada y bin_code.
    - Si ya existe, se rechaza (estrategia strict).
    - Se registra un evento BIN_REGISTRADO para trazabilidad.
    """
    if repos is None:
        repos = get_repositories()

    try:
        data = validate_bin_payload(payload)
    except PayloadValidationError as exc:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="Payload invalido para registrar bin",
            errors=exc.errors,
        )

    # Generar bin_code si no se provee explicitamente
    if data.get("bin_code"):
        bin_code = data["bin_code"]
    else:
        extra = data.get("extra", {})
        bin_code = build_bin_code(
            codigo_productor=extra.get("codigo_productor", ""),
            tipo_cultivo=extra.get("tipo_cultivo", ""),
            variedad_fruta=extra.get("variedad_fruta", ""),
            numero_cuartel=extra.get("numero_cuartel", ""),
            fecha_cosecha=extra.get("fecha_cosecha"),
        )

    existing = repos.bins.find_by_code(data["temporada"], bin_code)
    if existing:
        return UseCaseResult.reject(
            code="BIN_ALREADY_EXISTS",
            message="El bin ya existe para la temporada indicada",
            errors=[f"Ya existe bin {bin_code} en temporada {data['temporada']}"],
            data={
                "bin_id":    existing.id,
                "temporada": existing.temporada,
                "bin_code":  existing.bin_code,
            },
        )

    bin_record = repos.bins.create(
        data["temporada"],
        bin_code,
        operator_code=data["operator_code"],
        source_system=data["source_system"],
        source_event_id=data["source_event_id"],
        extra=data.get("extra", {}),
    )

    event_key = build_event_key(
        data["temporada"],
        "BIN",
        bin_code,
        "BIN_REGISTRADO",
    )

    repos.registros.create(
        temporada=data["temporada"],
        event_key=event_key,
        tipo_evento=TipoEvento.BIN_REGISTRADO,
        bin_id=bin_record.id,
        operator_code=data["operator_code"],
        source_system=data["source_system"],
        source_event_id=data["source_event_id"],
        payload={"bin_code": bin_code},
    )

    return UseCaseResult.success(
        code="BIN_REGISTERED",
        message="Bin registrado correctamente",
        data={
            "bin_id":    bin_record.id,
            "temporada": bin_record.temporada,
            "bin_code":  bin_record.bin_code,
        },
    )
