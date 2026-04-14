"""
Caso de uso: Agregar Bin a Lote Abierto

Registra un bin y lo asocia inmediatamente al lote abierto de la sesion.
El bin_code se genera automaticamente desde los atributos operativos.

Flujo:
  agregar_bin_a_lote_abierto(payload)
    → valida que el lote exista y este en estado 'abierto'
    → genera bin_code desde los atributos del bin
    → crea el bin y lo asocia al lote abierto en una operacion atomica
    → registra eventos BIN_REGISTRADO y PESAJE
    → retorna bin_id, bin_code y confirmacion de la asociacion
"""
from django.db import transaction

from operaciones.application.results import UseCaseResult
from operaciones.application.exceptions import PayloadValidationError
from operaciones.models import TipoEvento, LotePlantaEstado
from operaciones.services.validators import require_fields
from operaciones.services.normalizers import normalize_code, normalize_temporada, normalize_operator_code
from operaciones.services.code_generators import build_bin_code
from operaciones.services.event_builder import build_event_key
from infrastructure.repository_factory import get_repositories
from domain.repositories.base import Repositories


@transaction.atomic
def agregar_bin_a_lote_abierto(payload: dict, *, repos: Repositories | None = None) -> UseCaseResult:
    """
    Registra un bin y lo enlaza al lote abierto indicado.

    Reglas:
    - El lote debe existir y estar en estado 'abierto'.
    - El bin_code se genera en backend; el usuario no lo ingresa.
    - Un bin no puede ser asignado a mas de un lote.

    Parametros del payload:
      - temporada (requerido).
      - lote_code (requerido): codigo del lote abierto donde agregar el bin.
      - fecha_cosecha (opcional): se usa para construir el bin_code.
      - Cualquier atributo operativo del bin (variedad_fruta, kilos_bruto_ingreso, etc.).
    """
    if repos is None:
        repos = get_repositories()

    try:
        require_fields(payload, ["temporada", "lote_code"])
    except PayloadValidationError as exc:
        return UseCaseResult.reject(
            code="INVALID_PAYLOAD",
            message="Payload invalido para agregar bin a lote abierto",
            errors=exc.errors,
        )

    temporada       = normalize_temporada(payload["temporada"])
    lote_code       = normalize_code(payload["lote_code"])
    operator_code   = normalize_operator_code(payload.get("operator_code", ""))
    source_system   = payload.get("source_system", "local").strip() or "local"
    source_event_id = payload.get("source_event_id", "").strip()

    # Verificar lote abierto
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
            errors=[f"El lote debe estar en estado '{LotePlantaEstado.ABIERTO}' para agregar bins"],
        )

    # Generar bin_code desde los campos de la hoja "Codigo de barra" del Excel
    bin_code = build_bin_code(
        codigo_productor=payload.get("codigo_productor", ""),
        tipo_cultivo=payload.get("tipo_cultivo", ""),
        variedad_fruta=payload.get("variedad_fruta", ""),
        numero_cuartel=payload.get("numero_cuartel", ""),
        fecha_cosecha=payload.get("fecha_cosecha"),
    )

    # Calcular kilos_neto_ingreso server-side si no viene en el payload o viene vacío.
    # Formula: neto = bruto - (cantidad_bins_grupo × tara_bin)
    try:
        _bruto = payload.get("kilos_bruto_ingreso")
        _cantidad = payload.get("cantidad_bins_grupo")
        _tara = payload.get("tara_bin")
        _neto = payload.get("kilos_neto_ingreso")
        if (not _neto) and _bruto and _cantidad and _tara:
            from decimal import Decimal as _D
            payload = dict(payload)
            payload["kilos_neto_ingreso"] = float(_D(str(_bruto)) - _D(str(_cantidad)) * _D(str(_tara)))
    except Exception:
        pass

    # Construir extra con todos los atributos del bin
    campos_bin = [
        "fecha_cosecha", "codigo_productor", "nombre_productor",
        "variedad_fruta", "numero_cuartel", "nombre_cuartel",
        "predio", "sector", "lote_productor", "color", "estado_fisico",
        "a_o_r", "n_guia", "transporte", "capataz", "codigo_contratista",
        "nombre_contratista", "hora_recepcion",
        "kilos_bruto_ingreso", "kilos_neto_ingreso",
        "cantidad_bins_grupo", "tara_bin",
        "n_cajas_campo", "observaciones", "rol",
    ]
    extra = {
        k: payload[k]
        for k in campos_bin
        if k in payload and payload[k] not in [None, ""]
    }

    # Crear bin
    bin_record = repos.bins.create(
        temporada,
        bin_code,
        operator_code=operator_code,
        source_system=source_system,
        source_event_id=source_event_id,
        extra=extra,
    )

    # Verificar que el bin no este ya asignado (no deberia, recien creado)
    conflicts = repos.bin_lotes.find_existing_assignments([bin_record.id])
    if conflicts:
        return UseCaseResult.reject(
            code="BIN_ALREADY_ASSIGNED",
            message="El bin recien creado ya tenia una asignacion inesperada",
            errors=[f"Bin {bin_code} ya asignado"],
        )

    # Asociar bin al lote abierto
    bin_lote_record = repos.bin_lotes.create(
        bin_record.id,
        lote_record.id,
        operator_code=operator_code,
        source_system=source_system,
        source_event_id=source_event_id,
    )

    # Actualizar cantidad de bins en el lote
    repos.lotes.update(
        lote_record.id,
        {"cantidad_bins": lote_record.cantidad_bins + 1},
    )

    # Eventos (get_or_create para idempotencia — consistente con todos los demas use cases)
    event_key_bin = build_event_key(temporada, "BIN", bin_code, "BIN_REGISTRADO")
    repos.registros.get_or_create(
        event_key=event_key_bin,
        temporada=temporada,
        tipo_evento=TipoEvento.BIN_REGISTRADO,
        bin_id=bin_record.id,
        operator_code=operator_code,
        source_system=source_system,
        source_event_id=source_event_id,
        payload={"bin_code": bin_code},
    )

    event_key_asoc = build_event_key(temporada, "BIN", bin_code, "LOTE", lote_code, "ASOCIADO")
    repos.registros.get_or_create(
        event_key=event_key_asoc,
        temporada=temporada,
        tipo_evento=TipoEvento.PESAJE,
        bin_id=bin_record.id,
        lote_id=lote_record.id,
        operator_code=operator_code,
        source_system=source_system,
        source_event_id=source_event_id,
        payload={
            "bin_code":  bin_code,
            "lote_code": lote_code,
            "accion":    "agregar_bin_a_lote",
        },
    )

    return UseCaseResult.success(
        code="BIN_AGREGADO",
        message=f"Bin {bin_code} registrado y asociado al lote {lote_code}",
        data={
            "bin_id":       bin_record.id,
            "bin_code":     bin_code,
            "lote_id":      lote_record.id,
            "lote_code":    lote_code,
            "bin_lote_id":  bin_lote_record.id,
            "temporada":    temporada,
        },
    )
