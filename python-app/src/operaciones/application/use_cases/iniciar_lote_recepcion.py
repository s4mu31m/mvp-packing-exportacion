"""
Caso de uso: Iniciar Lote Recepcion

Crea un lote planta en estado 'abierto' al comenzar una sesion de recepcion.
El lote_code se genera automaticamente con correlativo por temporada.
Los bins se agregan posteriormente via agregar_bin_a_lote_abierto.

Flujo:
  iniciar_lote_recepcion(payload)
    → crea lote con estado=abierto y lote_code autogenerado
    → registra evento LOTE_CREADO
    → retorna lote_id y lote_code al operador
"""
import datetime

from django.db import transaction

from operaciones.application.results import UseCaseResult
from operaciones.application.exceptions import PayloadValidationError
from operaciones.models import TipoEvento, LotePlantaEstado
from operaciones.services.validators import require_fields
from operaciones.services.normalizers import normalize_temporada, normalize_operator_code
from operaciones.services.season import resolve_temporada_codigo
from operaciones.services.code_generators import next_lote_correlativo
from operaciones.services.event_builder import build_event_key
from operaciones.services.timestamps import ahora_utc
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories


@transaction.atomic
def iniciar_lote_recepcion(payload: dict, *, repos: Repositories | None = None) -> UseCaseResult:
    """
    Inicia una sesion de recepcion creando un lote planta abierto.

    El lote queda en estado 'abierto' listo para recibir bins.
    El lote_code y el correlativo_temporada son generados automaticamente.

    Parametros del payload:
      - temporada (requerido): temporada operativa (ej: '2026').
      - temporada_codigo (opcional): codigo de temporada (ej: '2025-2026').
        Si no se provee, se resuelve desde la fecha operativa.
      - operator_code, source_system (opcionales).
    """
    if repos is None:
        repos = get_repositories()

    try:
        require_fields(payload, ["temporada"])
    except PayloadValidationError as exc:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="Payload invalido para iniciar lote recepcion",
            errors=exc.errors,
        )

    temporada       = normalize_temporada(payload["temporada"])
    operator_code   = normalize_operator_code(payload.get("operator_code", ""))
    source_system   = payload.get("source_system", "local").strip() or "local"
    source_event_id = payload.get("source_event_id", "").strip()

    # Resolver temporada_codigo explicitamente o por fecha
    temporada_codigo = (payload.get("temporada_codigo") or "").strip()
    if not temporada_codigo:
        temporada_codigo = resolve_temporada_codigo()

    # Generar lote_code con correlativo por temporada
    lote_code, correlativo = next_lote_correlativo(temporada_codigo)

    # fecha_conformacion: fecha operativa de conformacion del lote en recepcion.
    # Regla de negocio: es la fecha en que el operador inicia la sesion de recepcion.
    # Si el payload la provee explicitamente (ej: tests de integracion o flujos futuros)
    # se respeta; de lo contrario se establece automaticamente como hoy (UTC local).
    fecha_conformacion = payload.get("fecha_conformacion") or datetime.date.today()

    extra = {
        "temporada_codigo":      temporada_codigo,
        "correlativo_temporada": correlativo,
        "estado":                LotePlantaEstado.ABIERTO,
        "etapa_actual":          "Recepcion",   # persiste en Dataverse desde 2026-03-31
        "ultimo_cambio_estado_at": ahora_utc(),
        "fecha_conformacion":    fecha_conformacion,
    }
    # Propagar campos opcionales adicionales de conformacion
    for campo in ["requiere_desverdizado", "disponibilidad_camara_desverdizado", "rol"]:
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

    event_key = build_event_key(temporada, "LOTE", lote_code, "RECEPCION", "INICIADO")
    repos.registros.create(
        temporada=temporada,
        event_key=event_key,
        tipo_evento=TipoEvento.LOTE_CREADO,
        lote_id=lote_record.id,
        operator_code=operator_code,
        source_system=source_system,
        source_event_id=source_event_id,
        payload={
            "lote_code":             lote_code,
            "temporada_codigo":      temporada_codigo,
            "correlativo_temporada": correlativo,
            "estado":                LotePlantaEstado.ABIERTO,
            "etapa":                 "recepcion",
            "accion":                "iniciar_lote",
        },
    )

    return UseCaseResult.success(
        code="LOTE_INICIADO",
        message=f"Lote {lote_code} creado y abierto para recepcion",
        data={
            "lote_id":               lote_record.id,
            "lote_code":             lote_record.lote_code,
            "temporada":             lote_record.temporada,
            "temporada_codigo":      temporada_codigo,
            "correlativo_temporada": correlativo,
            "estado":                LotePlantaEstado.ABIERTO,
        },
    )
