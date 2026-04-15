"""
Caso de uso: Cerrar Lote Recepcion

Cierra el lote abierto una vez que el operador termino de ingresar bins.
Despues del cierre no se pueden agregar mas bins al lote.

Flujo:
  cerrar_lote_recepcion(payload)
    → valida que el lote exista y este en estado 'abierto'
    → valida que el lote tenga al menos un bin asociado
    → cambia estado del lote a 'cerrado'
    → registra evento de cierre
    → retorna lote_id, lote_code y estado final
"""
from django.db import transaction

from operaciones.application.results import UseCaseResult
from operaciones.application.exceptions import PayloadValidationError
from operaciones.models import TipoEvento, LotePlantaEstado
from operaciones.services.validators import require_fields
from operaciones.services.normalizers import normalize_code, normalize_temporada, normalize_operator_code
from operaciones.services.event_builder import build_event_key
from operaciones.services.timestamps import ahora_utc
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories


@transaction.atomic
def cerrar_lote_recepcion(payload: dict, *, repos: Repositories | None = None) -> UseCaseResult:
    """
    Cierra el lote planta: cambia estado de 'abierto' a 'cerrado'.

    Reglas:
    - El lote debe existir y estar en estado 'abierto'.
    - El lote debe tener al menos un bin asociado.
    - Despues del cierre no se pueden agregar mas bins.

    Parametros del payload:
      - temporada (requerido).
      - lote_code (requerido).
      - requiere_desverdizado (opcional): se puede actualizar al cerrar.
      - disponibilidad_camara_desverdizado (opcional): idem.
    """
    if repos is None:
        repos = get_repositories()

    try:
        require_fields(payload, ["temporada", "lote_code"])
    except PayloadValidationError as exc:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="Payload invalido para cerrar lote recepcion",
            errors=exc.errors,
        )

    temporada       = normalize_temporada(payload["temporada"])
    lote_code       = normalize_code(payload["lote_code"])
    operator_code   = normalize_operator_code(payload.get("operator_code", ""))
    source_system   = payload.get("source_system", "local").strip() or "local"
    source_event_id = payload.get("source_event_id", "").strip()

    lote_record = repos.lotes.find_by_code(temporada, lote_code)
    if not lote_record:
        return UseCaseResult.reject(
            code="LOTE_NOT_FOUND",
            message=f"No existe el lote {lote_code} en temporada {temporada}",
            errors=[f"Lote no encontrado: {lote_code}"],
        )

    if lote_record.estado != LotePlantaEstado.ABIERTO:
        return UseCaseResult.reject(
            code="LOTE_NOT_OPEN",
            message=f"El lote {lote_code} no esta abierto (estado: {lote_record.estado})",
            errors=[f"Solo se puede cerrar un lote en estado '{LotePlantaEstado.ABIERTO}'"],
        )

    if lote_record.cantidad_bins == 0:
        return UseCaseResult.reject(
            code="LOTE_SIN_BINS",
            message=f"El lote {lote_code} no tiene bins asociados",
            errors=["Debe agregar al menos un bin antes de cerrar el lote"],
        )

    # Campos a actualizar al cerrar
    campos_update: dict = {
        "estado":                  LotePlantaEstado.CERRADO,
        "etapa_actual":            "Pesaje",   # persiste etapa en Dataverse desde 2026-03-31
        "ultimo_cambio_estado_at": ahora_utc(),
    }
    for campo in ["requiere_desverdizado", "disponibilidad_camara_desverdizado",
                  "kilos_bruto_conformacion", "kilos_neto_conformacion"]:
        if payload.get(campo) not in [None, ""]:
            campos_update[campo] = payload[campo]

    # Poblar codigo_productor desde el primer bin del lote (para filtro jefatura en Dataverse)
    try:
        bins = repos.bins.list_by_lote(lote_record.id)
        if bins:
            codigo_productor = bins[0].codigo_productor
            if codigo_productor:
                campos_update["codigo_productor"] = codigo_productor
    except Exception:
        pass

    repos.lotes.update(lote_record.id, campos_update)

    event_key = build_event_key(temporada, "LOTE", lote_code, "RECEPCION", "CERRADO")
    repos.registros.create(
        temporada=temporada,
        event_key=event_key,
        tipo_evento=TipoEvento.PESAJE,
        lote_id=lote_record.id,
        operator_code=operator_code,
        source_system=source_system,
        source_event_id=source_event_id,
        payload={
            "lote_code":  lote_code,
            "estado":     LotePlantaEstado.CERRADO,
            "cantidad_bins": lote_record.cantidad_bins,
            "accion":     "cerrar_lote_recepcion",
        },
    )

    return UseCaseResult.success(
        code="LOTE_CERRADO",
        message=f"Lote {lote_code} cerrado correctamente ({lote_record.cantidad_bins} bins)",
        data={
            "lote_id":       lote_record.id,
            "lote_code":     lote_code,
            "temporada":     temporada,
            "estado":        LotePlantaEstado.CERRADO,
            "cantidad_bins": lote_record.cantidad_bins,
        },
    )
