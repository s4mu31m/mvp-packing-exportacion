"""
Caso de uso: Registrar Pesaje de Lote

Registra el pesaje bruto y neto de un lote cerrado post-recepcion.
Tambien define si el lote requiere desverdizado.

Flujo:
  registrar_pesaje_lote(payload)
    → valida que el lote exista y este en estado 'cerrado'
    → actualiza kilos_bruto_conformacion, kilos_neto_conformacion, requiere_desverdizado
    → registra evento PESAJE
    → retorna lote_id, lote_code y datos del pesaje
"""
from django.db import transaction

from operaciones.application.results import UseCaseResult
from operaciones.application.exceptions import PayloadValidationError
from operaciones.models import TipoEvento, LotePlantaEstado
from operaciones.services.validators import require_fields
from operaciones.services.normalizers import normalize_code, normalize_temporada, normalize_operator_code
from operaciones.services.event_builder import build_event_key
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories


@transaction.atomic
def registrar_pesaje_lote(payload: dict, *, repos: Repositories | None = None) -> UseCaseResult:
    """
    Registra el pesaje de un lote cerrado.

    Reglas:
    - El lote debe existir y estar en estado 'cerrado'.
    - Se actualiza kilos_bruto_conformacion, kilos_neto_conformacion y requiere_desverdizado.

    Parametros del payload:
      - temporada (requerido)
      - lote_code (requerido)
      - kilos_bruto_conformacion (requerido)
      - kilos_neto_conformacion (requerido)
      - requiere_desverdizado (opcional, default False)
      - operator_code (opcional)
    """
    if repos is None:
        repos = get_repositories()

    try:
        require_fields(payload, ["temporada", "lote_code", "kilos_bruto_conformacion", "kilos_neto_conformacion"])
    except PayloadValidationError as exc:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="Payload invalido para registrar pesaje de lote",
            errors=exc.errors,
        )

    temporada     = normalize_temporada(payload["temporada"])
    lote_code     = normalize_code(payload["lote_code"])
    operator_code = normalize_operator_code(payload.get("operator_code", ""))
    source_system = payload.get("source_system", "local").strip() or "local"

    lote_record = repos.lotes.find_by_code(temporada, lote_code)
    if not lote_record:
        return UseCaseResult.reject(
            code="LOTE_NOT_FOUND",
            message=f"No existe el lote {lote_code} en temporada {temporada}",
            errors=[f"Lote no encontrado: {lote_code}"],
        )

    if lote_record.estado != LotePlantaEstado.CERRADO:
        return UseCaseResult.reject(
            code="LOTE_NOT_CLOSED",
            message=f"El lote {lote_code} no esta cerrado (estado: {lote_record.estado})",
            errors=[f"Solo se puede pesar un lote en estado '{LotePlantaEstado.CERRADO}'"],
        )

    try:
        kilos_bruto = float(payload["kilos_bruto_conformacion"])
        kilos_neto  = float(payload["kilos_neto_conformacion"])
    except (TypeError, ValueError):
        return UseCaseResult.reject(
            code="INVALID_KILOS",
            message="Los valores de kilos deben ser numericos",
            errors=["kilos_bruto_conformacion y kilos_neto_conformacion deben ser numeros validos"],
        )

    if kilos_neto > kilos_bruto:
        return UseCaseResult.reject(
            code="KILOS_INVALIDOS",
            message="Kilos neto no puede superar kilos bruto",
            errors=["kilos_neto_conformacion no puede ser mayor que kilos_bruto_conformacion"],
        )

    requiere_desverdizado = bool(payload.get("requiere_desverdizado", False))

    repos.lotes.update(lote_record.id, {
        "kilos_bruto_conformacion": payload["kilos_bruto_conformacion"],
        "kilos_neto_conformacion":  payload["kilos_neto_conformacion"],
        "requiere_desverdizado":    requiere_desverdizado,
    })

    event_key = build_event_key(temporada, "LOTE", lote_code, "PESAJE", "RECEPCION")
    repos.registros.get_or_create(
        temporada=temporada,
        event_key=event_key,
        tipo_evento=TipoEvento.PESAJE,
        lote_id=lote_record.id,
        operator_code=operator_code,
        source_system=source_system,
        payload={
            "lote_code":               lote_code,
            "kilos_bruto_conformacion": str(payload["kilos_bruto_conformacion"]),
            "kilos_neto_conformacion":  str(payload["kilos_neto_conformacion"]),
            "requiere_desverdizado":    requiere_desverdizado,
            "accion":                  "registrar_pesaje_lote",
        },
    )

    return UseCaseResult.success(
        code="PESAJE_REGISTRADO",
        message=f"Pesaje del lote {lote_code} registrado correctamente",
        data={
            "lote_id":                 lote_record.id,
            "lote_code":               lote_code,
            "temporada":               temporada,
            "kilos_bruto_conformacion": str(payload["kilos_bruto_conformacion"]),
            "kilos_neto_conformacion":  str(payload["kilos_neto_conformacion"]),
            "requiere_desverdizado":    requiere_desverdizado,
        },
    )
