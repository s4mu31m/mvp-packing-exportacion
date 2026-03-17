from django.db import transaction

from operaciones.application.results import UseCaseResult
from operaciones.application.exceptions import PayloadValidationError
from operaciones.models import Bin, TipoEvento, RegistroEtapa
from operaciones.services.validators import validate_bin_payload
from operaciones.services.event_builder import build_event_key, create_registro_etapa


@transaction.atomic
def registrar_bin_recibido(payload: dict) -> UseCaseResult:
    try:
        data = validate_bin_payload(payload)
    except PayloadValidationError as exc:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="Payload inválido para registrar bin",
            errors=exc.errors,
        )

    existing = Bin.objects.filter(
        temporada=data["temporada"],
        bin_code=data["bin_code"],
    ).first()

    if existing:
        return UseCaseResult.reject(
            code="BIN_ALREADY_EXISTS",
            message="El bin ya existe para la temporada indicada",
            errors=[
                f"Ya existe bin {data['bin_code']} en temporada {data['temporada']}"],
            data={
                "bin_id": existing.id,
                "temporada": existing.temporada,
                "bin_code": existing.bin_code,
            },
        )

    bin_obj = Bin.objects.create(
        temporada=data["temporada"],
        bin_code=data["bin_code"],
        operator_code=data["operator_code"],
        source_system=data["source_system"],
        source_event_id=data["source_event_id"],
    )

    event_key = build_event_key(
        data["temporada"],
        "BIN",
        data["bin_code"],
        "BIN_REGISTRADO",
    )

    create_registro_etapa(
        temporada=data["temporada"],
        event_key=event_key,
        tipo_evento=TipoEvento.BIN_REGISTRADO,
        bin_obj=bin_obj,
        operator_code=data["operator_code"],
        source_system=data["source_system"],
        source_event_id=data["source_event_id"],
        payload={
            "bin_code": data["bin_code"],
        },
    )

    return UseCaseResult.success(
        code="BIN_REGISTERED",
        message="Bin registrado correctamente",
        data={
            "bin_id": bin_obj.id,
            "temporada": bin_obj.temporada,
            "bin_code": bin_obj.bin_code,
        },
    )
