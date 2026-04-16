"""
Implementaciones Dataverse de los repositorios de dominio.

Cada repositorio usa DataverseClient para realizar operaciones OData v4 contra
el ambiente configurado en las variables de entorno DATAVERSE_*.

ADAPTACIONES BACKEND → DATAVERSE (schema real validado 2026-03-29):
  - Los nombres de tabla y campo provienen del esquema real (prefijo crf21_).
  - ``temporada`` no existe en Dataverse; se filtra por rango de fechas cuando
    sea necesario, o se ignora si el filtro por codigo es suficientemente
    selectivo.
  - ``lote_code`` se almacena en ``crf21_id_lote_planta``.
  - ``pallet_code`` se almacena en ``crf21_id_pallet``.
  - ``estado``, ``temporada_codigo``, ``correlativo_temporada`` no existen en
    Dataverse; el LoteRecord devuelto los rellena con valores por defecto.
  - No existe tabla registro_etapas; DataverseRegistroEtapaRepository es no-op
    (registra en log local sin persistir en Dataverse).
  - DataverseSequenceCounterRepository genera correlativos contando registros
    existentes en Dataverse — no requiere tabla dedicada. No es atomico, pero
    es aceptable para la escala del MVP.

ESTADO (derivado en Dataverse):
  El campo ``estado`` no existe en Dataverse. La estrategia adoptada es:
  - Al leer un lote de Dataverse, se retorna estado="abierto" por defecto.
  - ``cerrar_lote_recepcion`` llama a repos.lotes.update(..., {"estado": "cerrado"})
    pero el campo es ignorado silenciosamente por DataverseLoteRepository.update.
  - La vista RecepcionView limpia la sesion activa al cerrar (session pop), por
    lo que el usuario no puede seguir agregando bins aunque el estado en
    Dataverse no cambie formalmente.
  - Esta es una limitacion conocida del modelo Dataverse. Ver TECHNICAL_CHANGES.md.

TRANSACCIONES:
  Dataverse Web API no soporta transacciones ACID. En error parcial en
  operaciones multi-paso se requieren compensaciones manuales. Brecha conocida.
"""
from __future__ import annotations

import datetime
import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from domain.repositories.base import (
    BinAssignmentConflict,
    BinLoteRecord,
    BinRecord,
    BinLoteRepository,
    BinRepository,
    LoteRecord,
    LoteRepository,
    PalletLoteRecord,
    PalletLoteRepository,
    PalletRecord,
    PalletRepository,
    Repositories,
    RegistroEtapaRecord,
    RegistroEtapaRepository,
    SequenceCounterRecord,
    SequenceCounterRepository,
    CamaraMantencionRecord,
    CamaraMantencionRepository,
    DesverdizadoRecord,
    DesverdizadoRepository,
    CalidadDesverdizadoRecord,
    CalidadDesverdizadoRepository,
    IngresoAPackingRecord,
    IngresoAPackingRepository,
    RegistroPackingRecord,
    RegistroPackingRepository,
    ControlProcesoPackingRecord,
    ControlProcesoPackingRepository,
    CalidadPalletRecord,
    CalidadPalletRepository,
    CalidadPalletMuestraRecord,
    CalidadPalletMuestraRepository,
    CamaraFrioRecord,
    CamaraFrioRepository,
    MedicionTemperaturaSalidaRecord,
    MedicionTemperaturaSalidaRepository,
    PlanillaDesverdizadoCalibreRecord,
    PlanillaDesverdizadoCalibreRepository,
    PlanillaDesverdizadoSemillasRecord,
    PlanillaDesverdizadoSemillasRepository,
    PlanillaCalidadPackingRecord,
    PlanillaCalidadPackingRepository,
    PlanillaCalidadCamaraRecord,
    PlanillaCalidadCamaraRepository,
)
from infrastructure.dataverse.mapping import (
    ENTITY_SET_BIN,
    ENTITY_SET_BIN_LOTE,
    ENTITY_SET_LOTE,
    ENTITY_SET_PALLET,
    ENTITY_SET_PALLET_LOTE,
    ENTITY_SET_CAMARA_MANTENCION,
    ENTITY_SET_DESVERDIZADO,
    ENTITY_SET_CALIDAD_DESVERDIZADO,
    ENTITY_SET_INGRESO_PACKING,
    ENTITY_SET_REGISTRO_PACKING,
    ENTITY_SET_CONTROL_PROCESO_PACKING,
    ENTITY_SET_CALIDAD_PALLET,
    ENTITY_SET_CALIDAD_PALLET_MUESTRA,
    ENTITY_SET_CAMARA_FRIO,
    ENTITY_SET_MEDICION_TEMPERATURA,
    ENTITY_SET_PLANILLA_DESV_CALIBRE,
    ENTITY_SET_PLANILLA_DESV_SEMILLAS,
    ENTITY_SET_PLANILLA_CALIDAD_PACKING,
    ENTITY_SET_PLANILLA_CALIDAD_CAMARA,
    AOR_DV,
    BIN_FIELDS,
    BIN_LOTE_FIELDS,
    LOTE_PLANTA_FIELDS,
    LOTE_FIELDS,
    PALLET_FIELDS,
    PALLET_LOTE_FIELDS,
    CAMARA_MANTENCION_FIELDS,
    DESVERDIZADO_FIELDS,
    CALIDAD_DESVERDIZADO_FIELDS,
    INGRESO_PACKING_FIELDS,
    REGISTRO_PACKING_FIELDS,
    CONTROL_PROCESO_PACKING_FIELDS,
    CALIDAD_PALLET_FIELDS,
    CALIDAD_PALLET_MUESTRA_FIELDS,
    CAMARA_FRIO_FIELDS,
    MEDICION_TEMPERATURA_FIELDS,
    PLANILLA_DESV_CALIBRE_FIELDS,
    PLANILLA_DESV_SEMILLAS_FIELDS,
    PLANILLA_CALIDAD_PACKING_FIELDS,
    PLANILLA_CALIDAD_CAMARA_FIELDS,
    odata_bind,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers: parsing de valores OData
# ---------------------------------------------------------------------------

def _parse_date(val: Any) -> Optional[datetime.date]:
    """Convierte un string OData de fecha a datetime.date. Retorna None si falla."""
    if not val:
        return None
    try:
        s = str(val)
        if "T" in s:
            # ISO datetime con o sin timezone: "2026-03-29T00:00:00Z"
            s = s.split("T")[0]
        return datetime.date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _parse_datetime(val: Any) -> Optional[datetime.datetime]:
    """Convierte un string OData de datetime a datetime.datetime (aware UTC). Retorna None si falla."""
    if not val:
        return None
    try:
        s = str(val).strip()
        # Normalizar zona horaria: "2026-04-15T10:30:00Z" → aware UTC
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _parse_decimal(val: Any) -> Optional[Decimal]:
    """Convierte un numero OData a Decimal. Retorna None si falla."""
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _str(val: Any) -> str:
    """Convierte a str, retorna '' si es None."""
    return str(val) if val is not None else ""


# ---------------------------------------------------------------------------
# Helpers: OData row → record type
# ---------------------------------------------------------------------------

def _row_to_bin(row: dict) -> BinRecord:
    return BinRecord(
        id=row.get(BIN_FIELDS["id"]),
        temporada="",                               # no existe en Dataverse
        bin_code=_str(row.get(BIN_FIELDS["bin_code"])),
        operator_code=_str(row.get(BIN_FIELDS["operator_code"])),
        source_system=_str(row.get(BIN_FIELDS["source_system"])) or "dataverse",
        source_event_id=_str(row.get(BIN_FIELDS["source_event_id"])),
        is_active=row.get("statecode", 0) == 0,
        id_bin=_str(row.get(BIN_FIELDS["id_bin"])),
        nombre_productor=_str(row.get(BIN_FIELDS["nombre_productor"])),
        tipo_cultivo=_str(row.get(BIN_FIELDS["tipo_cultivo"])),
        variedad_fruta=_str(row.get(BIN_FIELDS["variedad_fruta"])),
        numero_cuartel=_str(row.get(BIN_FIELDS["numero_cuartel"])),
        nombre_cuartel=_str(row.get(BIN_FIELDS["nombre_cuartel"])),
        sector=_str(row.get(BIN_FIELDS["sector"])),
        kilos_bruto_ingreso=_parse_decimal(row.get(BIN_FIELDS["kilos_bruto_ingreso"])),
        kilos_neto_ingreso=_parse_decimal(row.get(BIN_FIELDS["kilos_neto_ingreso"])),
        cantidad_bins_grupo=int(row[BIN_FIELDS["cantidad_bins_grupo"]]) if row.get(BIN_FIELDS["cantidad_bins_grupo"]) is not None else None,
        tara_bin=_parse_decimal(row.get(BIN_FIELDS["tara_bin"])),
        codigo_productor=_str(row.get(BIN_FIELDS["codigo_productor"])),
        color=_str(row.get(BIN_FIELDS["color"])),
        fecha_cosecha=_parse_date(row.get(BIN_FIELDS["fecha_cosecha"])),
    )


def _row_to_lote(row: dict) -> LoteRecord:
    return LoteRecord(
        id=row.get(LOTE_FIELDS["id"]),
        temporada="",                               # no existe en Dataverse
        lote_code=_str(row.get(LOTE_FIELDS["lote_code"])),
        operator_code=_str(row.get(LOTE_FIELDS["operator_code"])),
        source_system=_str(row.get(LOTE_FIELDS["source_system"])) or "dataverse",
        source_event_id=_str(row.get(LOTE_FIELDS["source_event_id"])),
        is_active=row.get("statecode", 0) == 0,
        id_lote_planta=_str(row.get(LOTE_FIELDS["id_lote_planta"])),
        fecha_conformacion=_parse_date(row.get(LOTE_FIELDS["fecha_conformacion"])),
        cantidad_bins=int(row.get(LOTE_FIELDS["cantidad_bins"]) or 0),
        kilos_bruto_conformacion=_parse_decimal(row.get(LOTE_FIELDS["kilos_bruto_conformacion"])),
        kilos_neto_conformacion=_parse_decimal(row.get(LOTE_FIELDS["kilos_neto_conformacion"])),
        requiere_desverdizado=bool(row.get(LOTE_FIELDS["requiere_desverdizado"])),
        disponibilidad_camara_desverdizado=(
            "disponible" if row.get(LOTE_FIELDS["disponibilidad_camara_desverdizado"]) is True
            else "no_disponible" if row.get(LOTE_FIELDS["disponibilidad_camara_desverdizado"]) is False
            else None
        ),
        # estado, temporada_codigo, correlativo_temporada no existen en Dataverse.
        # etapa_actual se lee desde crf21_etapa_actual; None si no ha sido escrito aún.
        estado="abierto",
        temporada_codigo="",
        correlativo_temporada=None,
        etapa_actual=_str(row.get(LOTE_FIELDS["etapa_actual"])) or None,
        # codigo_productor disponible si el campo crf21_codigo_productor existe en Dataverse.
        codigo_productor=_str(row.get(LOTE_FIELDS["codigo_productor"])),
        # ultimo_cambio_estado_at: None hasta que crf21_ultimo_cambio_estado_at exista en Dataverse.
        ultimo_cambio_estado_at=_parse_datetime(row.get(LOTE_FIELDS["ultimo_cambio_estado_at"])),
    )


def _row_to_pallet(row: dict) -> PalletRecord:
    return PalletRecord(
        id=row.get(PALLET_FIELDS["id"]),
        temporada="",                               # no existe en Dataverse
        pallet_code=_str(row.get(PALLET_FIELDS["pallet_code"])),
        operator_code=_str(row.get(PALLET_FIELDS["operator_code"])),
        source_system="dataverse",
        source_event_id="",
        is_active=row.get("statecode", 0) == 0,
        id_pallet=_str(row.get(PALLET_FIELDS["id_pallet"])),
        fecha=_parse_date(row.get(PALLET_FIELDS["fecha"])),
        tipo_caja=_str(row.get(PALLET_FIELDS["tipo_caja"])),
        cajas_por_pallet=int(row.get(PALLET_FIELDS["cajas_por_pallet"]) or 0) or None,
        peso_total_kg=_parse_decimal(row.get(PALLET_FIELDS["peso_total_kg"])),
        destino_mercado=_str(row.get(PALLET_FIELDS["destino_mercado"])),
        # ultimo_cambio_estado_at: None hasta que crf21_ultimo_cambio_estado_at exista en Dataverse.
        ultimo_cambio_estado_at=_parse_datetime(row.get(PALLET_FIELDS["ultimo_cambio_estado_at"])),
    )


def _row_to_camara_mantencion(row: dict, lote_id: Any = None) -> CamaraMantencionRecord:
    return CamaraMantencionRecord(
        id=row.get(CAMARA_MANTENCION_FIELDS["id"]),
        lote_id=lote_id or row.get(CAMARA_MANTENCION_FIELDS["lote_id_value"]),
        camara_numero=_str(row.get(CAMARA_MANTENCION_FIELDS["camara_numero"])),
        fecha_ingreso=_parse_date(row.get(CAMARA_MANTENCION_FIELDS["fecha_ingreso"])),
        hora_ingreso=_str(row.get(CAMARA_MANTENCION_FIELDS["hora_ingreso"])),
        fecha_salida=_parse_date(row.get(CAMARA_MANTENCION_FIELDS["fecha_salida"])),
        hora_salida=_str(row.get(CAMARA_MANTENCION_FIELDS["hora_salida"])),
        temperatura_camara=_parse_decimal(row.get(CAMARA_MANTENCION_FIELDS["temperatura_camara"])),
        humedad_relativa=_parse_decimal(row.get(CAMARA_MANTENCION_FIELDS["humedad_relativa"])),
        observaciones=_str(row.get(CAMARA_MANTENCION_FIELDS["observaciones"])),
        operator_code=_str(row.get(CAMARA_MANTENCION_FIELDS["operator_code"])),
        source_system="dataverse",
        rol=_str(row.get(CAMARA_MANTENCION_FIELDS["rol"])),
    )


def _row_to_desverdizado(row: dict, lote_id: Any = None) -> DesverdizadoRecord:
    return DesverdizadoRecord(
        id=row.get(DESVERDIZADO_FIELDS["id"]),
        lote_id=lote_id or row.get(DESVERDIZADO_FIELDS["lote_id_value"]),
        numero_camara=_str(row.get(DESVERDIZADO_FIELDS["numero_camara"])),
        fecha_ingreso=_parse_date(row.get(DESVERDIZADO_FIELDS["fecha_ingreso"])),
        hora_ingreso=_str(row.get(DESVERDIZADO_FIELDS["hora_ingreso"])),
        fecha_salida=_parse_date(row.get(DESVERDIZADO_FIELDS["fecha_salida"])),
        hora_salida=_str(row.get(DESVERDIZADO_FIELDS["hora_salida"])),
        horas_desverdizado=_parse_int(row.get(DESVERDIZADO_FIELDS["horas_desverdizado"])),
        kilos_enviados_terreno=_parse_decimal(row.get(DESVERDIZADO_FIELDS["kilos_enviados_terreno"])),
        kilos_recepcionados=_parse_decimal(row.get(DESVERDIZADO_FIELDS["kilos_recepcionados"])),
        kilos_procesados=_parse_decimal(row.get(DESVERDIZADO_FIELDS["kilos_procesados"])),
        kilos_bruto_salida=_parse_decimal(row.get(DESVERDIZADO_FIELDS["kilos_bruto_salida"])),
        kilos_neto_salida=_parse_decimal(row.get(DESVERDIZADO_FIELDS["kilos_neto_salida"])),
        color_salida=_str(row.get(DESVERDIZADO_FIELDS["color_salida"])),
        proceso=_str(row.get(DESVERDIZADO_FIELDS["proceso"])),
        operator_code=_str(row.get(DESVERDIZADO_FIELDS["operator_code"])),
        source_system="dataverse",
        rol=_str(row.get(DESVERDIZADO_FIELDS["rol"])),
    )


def _row_to_calidad_desverdizado(row: dict, lote_id: Any = None) -> CalidadDesverdizadoRecord:
    return CalidadDesverdizadoRecord(
        id=row.get(CALIDAD_DESVERDIZADO_FIELDS["id"]),
        lote_id=lote_id or row.get(CALIDAD_DESVERDIZADO_FIELDS["lote_id_value"]),
        fecha=_parse_date(row.get(CALIDAD_DESVERDIZADO_FIELDS["fecha"])),
        hora=_str(row.get(CALIDAD_DESVERDIZADO_FIELDS["hora"])),
        temperatura_fruta=_parse_decimal(row.get(CALIDAD_DESVERDIZADO_FIELDS["temperatura_fruta"])),
        color_evaluado=_str(row.get(CALIDAD_DESVERDIZADO_FIELDS["color_evaluado"])),
        estado_visual=_str(row.get(CALIDAD_DESVERDIZADO_FIELDS["estado_visual"])),
        presencia_defectos=row.get(CALIDAD_DESVERDIZADO_FIELDS["presencia_defectos"]),
        aprobado=row.get(CALIDAD_DESVERDIZADO_FIELDS["aprobado"]),
        observaciones=_str(row.get(CALIDAD_DESVERDIZADO_FIELDS["observaciones"])),
        operator_code=_str(row.get(CALIDAD_DESVERDIZADO_FIELDS["operator_code"])),
        source_system="dataverse",
        rol=_str(row.get(CALIDAD_DESVERDIZADO_FIELDS["rol"])),
    )


def _row_to_ingreso_packing(row: dict, lote_id: Any = None) -> IngresoAPackingRecord:
    return IngresoAPackingRecord(
        id=row.get(INGRESO_PACKING_FIELDS["id"]),
        lote_id=lote_id or row.get(INGRESO_PACKING_FIELDS["lote_id_value"]),
        fecha_ingreso=_parse_date(row.get(INGRESO_PACKING_FIELDS["fecha_ingreso"])),
        hora_ingreso=_str(row.get(INGRESO_PACKING_FIELDS["hora_ingreso"])),
        kilos_bruto_ingreso_packing=_parse_decimal(row.get(INGRESO_PACKING_FIELDS["kilos_bruto_ingreso_packing"])),
        kilos_neto_ingreso_packing=_parse_decimal(row.get(INGRESO_PACKING_FIELDS["kilos_neto_ingreso_packing"])),
        via_desverdizado=bool(row.get(INGRESO_PACKING_FIELDS["via_desverdizado"])),
        observaciones=_str(row.get(INGRESO_PACKING_FIELDS["observaciones"])),
        operator_code=_str(row.get(INGRESO_PACKING_FIELDS["operator_code"])),
        source_system="dataverse",
        rol=_str(row.get(INGRESO_PACKING_FIELDS["rol"])),
    )


def _row_to_registro_packing(row: dict, lote_id: Any = None) -> RegistroPackingRecord:
    return RegistroPackingRecord(
        id=row.get(REGISTRO_PACKING_FIELDS["id"]),
        lote_id=lote_id or row.get(REGISTRO_PACKING_FIELDS["lote_id_value"]),
        fecha=_parse_date(row.get(REGISTRO_PACKING_FIELDS["fecha"])),
        hora_inicio=_str(row.get(REGISTRO_PACKING_FIELDS["hora_inicio"])),
        linea_proceso=_str(row.get(REGISTRO_PACKING_FIELDS["linea_proceso"])),
        categoria_calidad=_str(row.get(REGISTRO_PACKING_FIELDS["categoria_calidad"])),
        calibre=_str(row.get(REGISTRO_PACKING_FIELDS["calibre"])),
        tipo_envase=_str(row.get(REGISTRO_PACKING_FIELDS["tipo_envase"])),
        cantidad_cajas_producidas=row.get(REGISTRO_PACKING_FIELDS["cantidad_cajas_producidas"]),
        peso_promedio_caja_kg=_parse_decimal(row.get(REGISTRO_PACKING_FIELDS["peso_promedio_caja_kg"])),
        merma_seleccion_pct=_parse_decimal(row.get(REGISTRO_PACKING_FIELDS["merma_seleccion_pct"])),
        operator_code=_str(row.get(REGISTRO_PACKING_FIELDS["operator_code"])),
        source_system="dataverse",
        rol=_str(row.get(REGISTRO_PACKING_FIELDS["rol"])),
    )


def _row_to_control_proceso(row: dict, lote_id: Any = None) -> ControlProcesoPackingRecord:
    def _f(k): return row.get(CONTROL_PROCESO_PACKING_FIELDS[k])
    return ControlProcesoPackingRecord(
        id=_f("id"),
        lote_id=lote_id or _f("lote_id_value"),
        fecha=_parse_date(_f("fecha")),
        hora=_str(_f("hora")),
        n_bins_procesados=_f("n_bins_procesados"),
        temp_agua_tina=_parse_decimal(_f("temp_agua_tina")),
        ph_agua=_parse_decimal(_f("ph_agua")),
        recambio_agua=_f("recambio_agua"),
        rendimiento_lote_pct=_parse_decimal(_f("rendimiento_lote_pct")),
        observaciones_generales=_str(_f("observaciones_generales")),
        velocidad_volcador=_parse_decimal(_f("velocidad_volcador")),
        obs_volcador=_str(_f("obs_volcador")),
        cloro_libre_ppm=_parse_decimal(_f("cloro_libre_ppm")),
        tiempo_inmersion_seg=_f("tiempo_inmersion_seg"),
        temp_aire_secado=_parse_decimal(_f("temp_aire_secado")),
        velocidad_ventiladores=_parse_decimal(_f("velocidad_ventiladores")),
        fruta_sale_seca=_f("fruta_sale_seca"),
        tipo_cera=_str(_f("tipo_cera")),
        dosis_cera_ml_min=_parse_decimal(_f("dosis_cera_ml_min")),
        temp_cera=_parse_decimal(_f("temp_cera")),
        cobertura_uniforme=_f("cobertura_uniforme"),
        n_operarios_seleccion=_f("n_operarios_seleccion"),
        fruta_dano_condicion_kg=_parse_decimal(_f("fruta_dano_condicion_kg")),
        fruta_dano_calidad_kg=_parse_decimal(_f("fruta_dano_calidad_kg")),
        fruta_pudricion_kg=_parse_decimal(_f("fruta_pudricion_kg")),
        merma_total_seleccion_kg=_parse_decimal(_f("merma_total_seleccion_kg")),
        equipo_calibrador=_str(_f("equipo_calibrador")),
        calibre_predominante=_str(_f("calibre_predominante")),
        pct_calibre_export=_parse_decimal(_f("pct_calibre_export")),
        pct_calibres_menores=_parse_decimal(_f("pct_calibres_menores")),
        tipo_caja=_str(_f("tipo_caja")),
        peso_promedio_caja_kg=_parse_decimal(_f("peso_promedio_caja_kg")),
        n_cajas_producidas=_f("n_cajas_producidas"),
        operator_code=_str(_f("operator_code")),
        source_system="dataverse",
        rol=_str(_f("rol")),
    )


def _row_to_calidad_pallet(row: dict, pallet_id: Any = None) -> CalidadPalletRecord:
    return CalidadPalletRecord(
        id=row.get(CALIDAD_PALLET_FIELDS["id"]),
        pallet_id=pallet_id or row.get(CALIDAD_PALLET_FIELDS["pallet_id_value"]),
        fecha=_parse_date(row.get(CALIDAD_PALLET_FIELDS["fecha"])),
        hora=_str(row.get(CALIDAD_PALLET_FIELDS["hora"])),
        temperatura_fruta=_parse_decimal(row.get(CALIDAD_PALLET_FIELDS["temperatura_fruta"])),
        peso_caja_muestra=_parse_decimal(row.get(CALIDAD_PALLET_FIELDS["peso_caja_muestra"])),
        estado_visual_fruta=_str(row.get(CALIDAD_PALLET_FIELDS["estado_visual_fruta"])),
        presencia_defectos=row.get(CALIDAD_PALLET_FIELDS["presencia_defectos"]),
        aprobado=row.get(CALIDAD_PALLET_FIELDS["aprobado"]),
        observaciones=_str(row.get(CALIDAD_PALLET_FIELDS["observaciones"])),
        operator_code=_str(row.get(CALIDAD_PALLET_FIELDS["operator_code"])),
        source_system="dataverse",
        rol=_str(row.get(CALIDAD_PALLET_FIELDS["rol"])),
    )


def _row_to_calidad_pallet_muestra(row: dict, pallet_id: Any = None) -> CalidadPalletMuestraRecord:
    raw_numero = row.get(CALIDAD_PALLET_MUESTRA_FIELDS["numero_muestra"])
    raw_n = row.get(CALIDAD_PALLET_MUESTRA_FIELDS["n_frutos"])
    return CalidadPalletMuestraRecord(
        id=row.get(CALIDAD_PALLET_MUESTRA_FIELDS["id"]),
        pallet_id=pallet_id or row.get(CALIDAD_PALLET_MUESTRA_FIELDS["pallet_id_value"]),
        numero_muestra=int(raw_numero) if raw_numero is not None else None,
        temperatura_fruta=_parse_decimal(row.get(CALIDAD_PALLET_MUESTRA_FIELDS["temperatura_fruta"])),
        peso_caja_muestra=_parse_decimal(row.get(CALIDAD_PALLET_MUESTRA_FIELDS["peso_caja_muestra"])),
        n_frutos=int(raw_n) if raw_n is not None else None,
        aprobado=row.get(CALIDAD_PALLET_MUESTRA_FIELDS["aprobado"]),
        observaciones=_str(row.get(CALIDAD_PALLET_MUESTRA_FIELDS["observaciones"])),
        operator_code=_str(row.get(CALIDAD_PALLET_MUESTRA_FIELDS["operator_code"])),
        source_system="dataverse",
        rol=_str(row.get(CALIDAD_PALLET_MUESTRA_FIELDS["rol"])),
    )


def _row_to_camara_frio(row: dict, pallet_id: Any = None) -> CamaraFrioRecord:
    return CamaraFrioRecord(
        id=row.get(CAMARA_FRIO_FIELDS["id"]),
        pallet_id=pallet_id or row.get(CAMARA_FRIO_FIELDS["pallet_id_value"]),
        camara_numero=_str(row.get(CAMARA_FRIO_FIELDS["camara_numero"])),
        temperatura_camara=_parse_decimal(row.get(CAMARA_FRIO_FIELDS["temperatura_camara"])),
        humedad_relativa=_parse_decimal(row.get(CAMARA_FRIO_FIELDS["humedad_relativa"])),
        fecha_ingreso=_parse_date(row.get(CAMARA_FRIO_FIELDS["fecha_ingreso"])),
        hora_ingreso=_str(row.get(CAMARA_FRIO_FIELDS["hora_ingreso"])),
        fecha_salida=_parse_date(row.get(CAMARA_FRIO_FIELDS["fecha_salida"])),
        hora_salida=_str(row.get(CAMARA_FRIO_FIELDS["hora_salida"])),
        destino_despacho=_str(row.get(CAMARA_FRIO_FIELDS["destino_despacho"])),
        operator_code=_str(row.get(CAMARA_FRIO_FIELDS["operator_code"])),
        source_system="dataverse",
        rol=_str(row.get(CAMARA_FRIO_FIELDS["rol"])),
    )


def _row_to_medicion_temperatura(row: dict, pallet_id: Any = None) -> MedicionTemperaturaSalidaRecord:
    return MedicionTemperaturaSalidaRecord(
        id=row.get(MEDICION_TEMPERATURA_FIELDS["id"]),
        pallet_id=pallet_id or row.get(MEDICION_TEMPERATURA_FIELDS["pallet_id_value"]),
        fecha=_parse_date(row.get(MEDICION_TEMPERATURA_FIELDS["fecha"])),
        hora=_str(row.get(MEDICION_TEMPERATURA_FIELDS["hora"])),
        temperatura_pallet=_parse_decimal(row.get(MEDICION_TEMPERATURA_FIELDS["temperatura_pallet"])),
        punto_medicion=_str(row.get(MEDICION_TEMPERATURA_FIELDS["punto_medicion"])),
        dentro_rango=row.get(MEDICION_TEMPERATURA_FIELDS["dentro_rango"]),
        observaciones=_str(row.get(MEDICION_TEMPERATURA_FIELDS["observaciones"])),
        operator_code=_str(row.get(MEDICION_TEMPERATURA_FIELDS["operator_code"])),
        source_system="dataverse",
        rol=_str(row.get(MEDICION_TEMPERATURA_FIELDS["rol"])),
    )


# ---------------------------------------------------------------------------
# Selects reutilizables
# ---------------------------------------------------------------------------

_BIN_SELECT = [BIN_FIELDS[k] for k in (
    "id", "id_bin", "bin_code", "operator_code", "source_system",
    "source_event_id", "nombre_productor", "tipo_cultivo", "variedad_fruta",
    "numero_cuartel", "nombre_cuartel", "sector",
    "kilos_bruto_ingreso", "kilos_neto_ingreso", "codigo_productor", "color",
    "fecha_cosecha",
)]
_LOTE_SELECT = [LOTE_FIELDS[k] for k in (
    "id", "id_lote_planta", "lote_code", "operator_code", "source_system",
    "source_event_id", "cantidad_bins", "kilos_bruto_conformacion",
    "kilos_neto_conformacion", "requiere_desverdizado",
    "disponibilidad_camara_desverdizado", "etapa_actual", "codigo_productor",
    "fecha_conformacion", "ultimo_cambio_estado_at",
)]
_BIN_LOTE_SELECT = [BIN_LOTE_FIELDS[k] for k in ("id", "bin_id_value", "lote_id_value")]
_PALLET_SELECT = [PALLET_FIELDS[k] for k in (
    "id", "id_pallet", "pallet_code", "operator_code",
    "fecha", "tipo_caja", "cajas_por_pallet", "peso_total_kg", "destino_mercado",
    # ultimo_cambio_estado_at excluido por la misma razon que en _LOTE_SELECT.
)]


# ---------------------------------------------------------------------------
# BinRepository
# ---------------------------------------------------------------------------

class DataverseBinRepository(BinRepository):

    def __init__(self, client) -> None:
        self._client = client

    def find_by_code(self, temporada: str, bin_code: str) -> Optional[BinRecord]:
        from django.core.cache import caches
        _cache = caches["dataverse"]
        _key = f"bin_by_code:{bin_code}"
        cached = _cache.get(_key)
        if cached is not None:
            return cached

        # temporada no existe en Dataverse; filtramos solo por bin_code
        f = f"{BIN_FIELDS['bin_code']} eq '{bin_code}'"
        result = self._client.list_rows(
            ENTITY_SET_BIN,
            select=_BIN_SELECT,
            filter_expr=f,
            top=1,
        )
        rows = (result or {}).get("value", [])
        record = _row_to_bin(rows[0]) if rows else None
        if record:
            _cache.set(_key, record, timeout=30)
        return record

    def create(
        self,
        temporada: str,
        bin_code: str,
        *,
        operator_code: str = "",
        source_system: str = "dataverse",
        source_event_id: str = "",
        extra: Optional[dict] = None,
    ) -> BinRecord:
        body: dict = {
            BIN_FIELDS["bin_code"]:        bin_code,
            BIN_FIELDS["operator_code"]:   operator_code,
            BIN_FIELDS["source_system"]:   source_system,
            BIN_FIELDS["source_event_id"]: source_event_id,
        }
        _extra_map = {
            "codigo_productor":   BIN_FIELDS["codigo_productor"],
            "nombre_productor":   BIN_FIELDS["nombre_productor"],
            "tipo_cultivo":       BIN_FIELDS["tipo_cultivo"],
            "variedad_fruta":     BIN_FIELDS["variedad_fruta"],
            "numero_cuartel":     BIN_FIELDS["numero_cuartel"],
            "nombre_cuartel":     BIN_FIELDS["nombre_cuartel"],
            "predio":             BIN_FIELDS["predio"],
            "sector":             BIN_FIELDS["sector"],
            "lote_productor":     BIN_FIELDS["lote_productor"],
            "fecha_cosecha":      BIN_FIELDS["fecha_cosecha"],
            "color":              BIN_FIELDS["color"],
            "estado_fisico":      BIN_FIELDS["estado_fisico"],
            "a_o_r":              BIN_FIELDS["a_o_r"],
            "hora_recepcion":     BIN_FIELDS["hora_recepcion"],
            "kilos_bruto_ingreso":BIN_FIELDS["kilos_bruto_ingreso"],
            "kilos_neto_ingreso": BIN_FIELDS["kilos_neto_ingreso"],
            "n_cajas_campo":      BIN_FIELDS["n_cajas_campo"],
            "observaciones":      BIN_FIELDS["observaciones"],
            "n_guia":             BIN_FIELDS["n_guia"],
            "transporte":         BIN_FIELDS["transporte"],
            "capataz":            BIN_FIELDS["capataz"],
            "codigo_contratista": BIN_FIELDS["codigo_contratista"],
            "nombre_contratista": BIN_FIELDS["nombre_contratista"],
        }
        for domain_key, dv_field in _extra_map.items():
            v = (extra or {}).get(domain_key)
            if v not in (None, ""):
                if domain_key == "a_o_r":
                    v = AOR_DV.get(v, v)
                body[dv_field] = v

        row = self._client.create_row(ENTITY_SET_BIN, body) or {}
        return BinRecord(
            id=row.get(BIN_FIELDS["id"]),
            temporada=temporada,
            bin_code=bin_code,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
        )

    def filter_by_codes(self, temporada: str, bin_codes: list[str]) -> list[BinRecord]:
        if not bin_codes:
            return []
        _CHUNK = 20
        records = []
        for i in range(0, len(bin_codes), _CHUNK):
            chunk = bin_codes[i:i + _CHUNK]
            codes_filter = " or ".join(
                f"{BIN_FIELDS['bin_code']} eq '{c}'" for c in chunk
            )
            result = self._client.list_rows(
                ENTITY_SET_BIN,
                select=_BIN_SELECT,
                filter_expr=f"({codes_filter})",
                top=len(chunk) + 10,
            )
            records.extend(_row_to_bin(r) for r in (result or {}).get("value", []))
        return records

    def list_by_lote(self, lote_id: Any) -> list[BinRecord]:
        """
        Obtiene los bins de un lote consultando primero la tabla de union
        crf21_bin_lote_plantas por lote, luego resolviendo los bins por sus IDs.

        Estrategia de dos pasos:
          1. crf21_bin_lote_plantas filtrado por _crf21_lote_planta_id_value = lote_id
          2. crf21_bins filtrado por los bin_ids obtenidos
        """
        # Paso 1: obtener bin_ids asociados al lote.
        # SIN $select para que Dataverse incluya siempre los campos _*_value.
        f = f"{BIN_LOTE_FIELDS['lote_id_value']} eq {lote_id}"
        result = self._client.list_rows(
            ENTITY_SET_BIN_LOTE,
            filter_expr=f,
            top=9999,
        )
        bin_ids = [
            r.get(BIN_LOTE_FIELDS["bin_id_value"])
            for r in (result or {}).get("value", [])
            if r.get(BIN_LOTE_FIELDS["bin_id_value"])
        ]
        if not bin_ids:
            return []

        # Paso 2: obtener los bins por sus IDs
        ids_filter = " or ".join(
            f"{BIN_FIELDS['id']} eq {bid}" for bid in bin_ids
        )
        result2 = self._client.list_rows(
            ENTITY_SET_BIN,
            select=_BIN_SELECT,
            filter_expr=f"({ids_filter})",
            top=len(bin_ids) + 10,
        )
        return [_row_to_bin(r) for r in (result2 or {}).get("value", [])]

    def first_bin_by_lotes(self, lote_ids: list) -> dict:
        """
        Retorna {lote_id: BinRecord} con el primer bin de cada lote indicado.
        Hace dos queries (BIN_LOTE + BIN) independientemente del numero de lotes.

        Nota: NO se usa $select en la query al join table porque Dataverse no garantiza
        devolver campos _*_value cuando solo esos se piden en $select.
        Sin $select, Dataverse devuelve todas las columnas incluyendo los _*_value.
        """
        if not lote_ids:
            return {}

        from django.core.cache import caches
        _cache = caches["dataverse"]
        _key = "first_bin_by_lotes:" + ":".join(sorted(str(i) for i in lote_ids))
        cached = _cache.get(_key)
        if cached is not None:
            return cached

        _log = logging.getLogger(__name__)
        _log.debug("first_bin_by_lotes: buscando primer bin para %d lotes: %s",
                   len(lote_ids), lote_ids)

        # Paso 1: obtener todas las asociaciones bin-lote para los lotes dados.
        # SIN $select para que Dataverse incluya siempre los campos _*_value.
        ids_filter = " or ".join(
            f"{BIN_LOTE_FIELDS['lote_id_value']} eq {lid}" for lid in lote_ids
        )
        result = self._client.list_rows(
            ENTITY_SET_BIN_LOTE,
            filter_expr=f"({ids_filter})",
            top=len(lote_ids) * 500,
        )
        rows = (result or {}).get("value", [])
        _log.debug("first_bin_by_lotes: paso1 encontro %d filas en join table", len(rows))

        if rows:
            _log.debug("first_bin_by_lotes: sample row keys: %s", list(rows[0].keys())[:15])

        # Para cada lote, tomar solo el primer bin_id encontrado
        lote_to_bin: dict = {}
        for r in rows:
            lid = r.get(BIN_LOTE_FIELDS["lote_id_value"])
            bid = r.get(BIN_LOTE_FIELDS["bin_id_value"])
            if lid and bid and lid not in lote_to_bin:
                lote_to_bin[lid] = bid

        _log.debug("first_bin_by_lotes: lote_to_bin tiene %d entradas", len(lote_to_bin))
        if not lote_to_bin:
            _log.warning(
                "first_bin_by_lotes: no se encontraron join records para lotes %s. "
                "Revisar que la tabla %s tenga registros y que los lote_ids sean correctos.",
                lote_ids, ENTITY_SET_BIN_LOTE,
            )
            return {}

        # Paso 2: obtener los bins en batch
        bin_ids = list(lote_to_bin.values())
        bins_filter = " or ".join(f"{BIN_FIELDS['id']} eq {bid}" for bid in bin_ids)
        result2 = self._client.list_rows(
            ENTITY_SET_BIN,
            select=_BIN_SELECT,
            filter_expr=f"({bins_filter})",
            top=len(bin_ids) + 10,
        )
        bin_by_id = {
            r.get(BIN_FIELDS["id"]): _row_to_bin(r)
            for r in (result2 or {}).get("value", [])
            if r.get(BIN_FIELDS["id"])
        }
        _log.debug("first_bin_by_lotes: paso2 encontro %d bins", len(bin_by_id))

        resultado = {
            lid: bin_by_id[bid]
            for lid, bid in lote_to_bin.items()
            if bid in bin_by_id
        }
        _log.debug("first_bin_by_lotes: resultado final tiene %d entradas", len(resultado))
        _cache.set(_key, resultado, timeout=60)
        return resultado

    def all_bins_by_lotes(self, lote_ids: list) -> dict:
        """
        Retorna {lote_id: [BinRecord, ...]} con TODOS los bins de cada lote.
        Hace dos queries (BIN_LOTE + BIN) independientemente del numero de lotes.
        Orden dentro de cada lote: createdon asc (el orden de ingreso de bins).
        """
        if not lote_ids:
            return {}

        from django.core.cache import caches
        _cache = caches["dataverse"]
        _key = "all_bins_by_lotes:" + ":".join(sorted(str(i) for i in lote_ids))
        cached = _cache.get(_key)
        if cached is not None:
            return cached

        _log = logging.getLogger(__name__)

        # Paso 1: obtener TODAS las asociaciones bin-lote para los lotes dados.
        ids_filter = " or ".join(
            f"{BIN_LOTE_FIELDS['lote_id_value']} eq {lid}" for lid in lote_ids
        )
        result = self._client.list_rows(
            ENTITY_SET_BIN_LOTE,
            filter_expr=f"({ids_filter})",
            top=len(lote_ids) * 500,
        )
        rows = (result or {}).get("value", [])
        _log.debug("all_bins_by_lotes: paso1 encontro %d filas en join table", len(rows))

        # Para cada lote, recopilar TODOS los bin_ids (en orden de llegada)
        lote_to_bin_ids: dict = {}
        for r in rows:
            lid = r.get(BIN_LOTE_FIELDS["lote_id_value"])
            bid = r.get(BIN_LOTE_FIELDS["bin_id_value"])
            if lid and bid:
                lst = lote_to_bin_ids.setdefault(lid, [])
                if bid not in lst:
                    lst.append(bid)

        if not lote_to_bin_ids:
            _cache.set(_key, {}, timeout=60)
            return {}

        # Paso 2: obtener los bins en batch (deduplicado, por chunks)
        all_bin_ids = list({bid for bids in lote_to_bin_ids.values() for bid in bids})
        _CHUNK = 50
        bin_by_id: dict = {}
        for i in range(0, len(all_bin_ids), _CHUNK):
            chunk = all_bin_ids[i : i + _CHUNK]
            bins_filter = " or ".join(f"{BIN_FIELDS['id']} eq {bid}" for bid in chunk)
            result2 = self._client.list_rows(
                ENTITY_SET_BIN,
                select=_BIN_SELECT,
                filter_expr=f"({bins_filter})",
                top=len(chunk) + 10,
            )
            for r in (result2 or {}).get("value", []):
                bid = r.get(BIN_FIELDS["id"])
                if bid:
                    bin_by_id[bid] = _row_to_bin(r)

        _log.debug("all_bins_by_lotes: paso2 encontro %d bins distintos", len(bin_by_id))

        resultado = {
            lid: [bin_by_id[bid] for bid in bids if bid in bin_by_id]
            for lid, bids in lote_to_bin_ids.items()
        }
        _cache.set(_key, resultado, timeout=60)
        return resultado

    def update(self, bin_id: Any, fields: dict) -> BinRecord:
        _updatable = {
            "numero_cuartel":      BIN_FIELDS["numero_cuartel"],
            "hora_recepcion":      BIN_FIELDS["hora_recepcion"],
            "kilos_bruto_ingreso": BIN_FIELDS["kilos_bruto_ingreso"],
            "kilos_neto_ingreso":  BIN_FIELDS["kilos_neto_ingreso"],
            "a_o_r":               BIN_FIELDS["a_o_r"],
            "observaciones":       BIN_FIELDS["observaciones"],
        }
        body = {}
        for domain_key, dv_field in _updatable.items():
            if domain_key not in fields:
                continue
            v = fields[domain_key]
            if domain_key == "a_o_r" and isinstance(v, str):
                v = AOR_DV.get(v, v)
            body[dv_field] = v
        if body:
            row = self._client.update_row(
                ENTITY_SET_BIN, str(bin_id), body, return_representation=True
            )
            if row:
                return _row_to_bin(row)
        # Fallback a GET (body vacío o sin cambios)
        result = self._client.list_rows(
            ENTITY_SET_BIN,
            select=_BIN_SELECT,
            filter_expr=f"{BIN_FIELDS['id']} eq {bin_id}",
            top=1,
        )
        rows = (result or {}).get("value", [])
        return _row_to_bin(rows[0]) if rows else BinRecord(id=bin_id, temporada="", bin_code="")

    def delete(self, bin_id: Any) -> None:
        self._client.delete_row(ENTITY_SET_BIN, str(bin_id))


# ---------------------------------------------------------------------------
# LoteRepository
# ---------------------------------------------------------------------------

class DataverseLoteRepository(LoteRepository):

    def __init__(self, client) -> None:
        self._client = client

    def find_by_id(self, lote_id: Any) -> Optional[LoteRecord]:
        result = self._client.list_rows(
            ENTITY_SET_LOTE,
            select=_LOTE_SELECT,
            filter_expr=f"{LOTE_FIELDS['id']} eq {lote_id}",
            top=1,
        )
        rows = (result or {}).get("value", [])
        return _row_to_lote(rows[0]) if rows else None

    def find_by_code(self, temporada: str, lote_code: str) -> Optional[LoteRecord]:
        from django.core.cache import caches
        _cache = caches["dataverse"]
        _key = f"lote_by_code:{lote_code}"
        cached = _cache.get(_key)
        if cached is not None:
            return cached

        # lote_code se almacena en crf21_id_lote_planta
        f = f"{LOTE_FIELDS['lote_code']} eq '{lote_code}'"
        result = self._client.list_rows(
            ENTITY_SET_LOTE,
            select=_LOTE_SELECT,
            filter_expr=f,
            orderby="createdon desc",
            top=1,
        )
        rows = (result or {}).get("value", [])
        if not rows:
            return None
        record = _row_to_lote(rows[0])
        record.temporada = temporada
        _cache.set(_key, record, timeout=30)
        return record

    def create(
        self,
        temporada: str,
        lote_code: str,
        *,
        operator_code: str = "",
        source_system: str = "dataverse",
        source_event_id: str = "",
        extra: Optional[dict] = None,
    ) -> LoteRecord:
        body: dict = {
            LOTE_FIELDS["lote_code"]:       lote_code,
            LOTE_FIELDS["operator_code"]:   operator_code,
            LOTE_FIELDS["source_system"]:   source_system,
            LOTE_FIELDS["source_event_id"]: source_event_id,
            LOTE_FIELDS["cantidad_bins"]:   0,
        }
        extra = extra or {}
        if extra.get("fecha_conformacion"):
            body[LOTE_FIELDS["fecha_conformacion"]] = str(extra["fecha_conformacion"])
        if extra.get("etapa_actual"):
            body[LOTE_FIELDS["etapa_actual"]] = str(extra["etapa_actual"])
        if extra.get("ultimo_cambio_estado_at"):
            _ts = extra["ultimo_cambio_estado_at"]
            body[LOTE_FIELDS["ultimo_cambio_estado_at"]] = (
                _ts.isoformat() if hasattr(_ts, "isoformat") else str(_ts)
            )

        row = self._client.create_row(ENTITY_SET_LOTE, body) or {}
        record = LoteRecord(
            id=row.get(LOTE_FIELDS["id"]),
            temporada=temporada,
            lote_code=lote_code,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
            estado="abierto",
            temporada_codigo="",
            correlativo_temporada=None,
            etapa_actual=extra.get("etapa_actual"),
            fecha_conformacion=extra.get("fecha_conformacion"),
            ultimo_cambio_estado_at=extra.get("ultimo_cambio_estado_at"),
        )
        # Warm the cache immediately so find_by_code returns this record on the
        # very next request, bypassing Dataverse eventual-consistency delay
        # (newly-created rows are not always queryable via OData for 1-3 seconds).
        try:
            from django.core.cache import caches
            caches["dataverse"].set(f"lote_by_code:{lote_code}", record, timeout=30)
        except Exception:
            pass
        return record

    def filter_by_codes(self, temporada: str, lote_codes: list[str]) -> list[LoteRecord]:
        if not lote_codes:
            return []
        _CHUNK = 20
        records = []
        for i in range(0, len(lote_codes), _CHUNK):
            chunk = lote_codes[i:i + _CHUNK]
            codes_filter = " or ".join(
                f"{LOTE_FIELDS['lote_code']} eq '{c}'" for c in chunk
            )
            result = self._client.list_rows(
                ENTITY_SET_LOTE,
                select=_LOTE_SELECT,
                filter_expr=f"({codes_filter})",
                top=len(chunk) + 10,
            )
            records.extend(_row_to_lote(r) for r in (result or {}).get("value", []))
        for r in records:
            r.temporada = temporada
        return records

    def update(self, lote_id: Any, fields: dict) -> LoteRecord:
        # Mapear campos del dominio a campos Dataverse (solo los que existen)
        _updatable = {
            "cantidad_bins":                        LOTE_FIELDS["cantidad_bins"],
            "kilos_bruto_conformacion":             LOTE_FIELDS["kilos_bruto_conformacion"],
            "kilos_neto_conformacion":              LOTE_FIELDS["kilos_neto_conformacion"],
            "requiere_desverdizado":                LOTE_FIELDS["requiere_desverdizado"],
            "disponibilidad_camara_desverdizado":   LOTE_FIELDS["disponibilidad_camara_desverdizado"],
            "operator_code":                        LOTE_FIELDS["operator_code"],
            # etapa_actual: campo disponible desde 2026-03-31
            "etapa_actual":                         LOTE_FIELDS["etapa_actual"],
            # codigo_productor: campo crf21_codigo_productor agregado 2026-04-04
            "codigo_productor":                     LOTE_FIELDS["codigo_productor"],
            "fecha_conformacion":                   LOTE_FIELDS["fecha_conformacion"],
            "ultimo_cambio_estado_at":              LOTE_FIELDS["ultimo_cambio_estado_at"],
        }
        body = {}
        for domain_key, dv_field in _updatable.items():
            if domain_key not in fields:
                continue
            v = fields[domain_key]
            if domain_key == "disponibilidad_camara_desverdizado" and isinstance(v, str):
                v = True if v == "disponible" else False
            elif domain_key == "fecha_conformacion" and v is not None:
                v = str(v)
            elif domain_key == "ultimo_cambio_estado_at" and v is not None:
                v = v.isoformat() if hasattr(v, "isoformat") else str(v)
            body[dv_field] = v
        # Campos no soportados en Dataverse: estado, temporada_codigo,
        # correlativo_temporada — se ignoran silenciosamente.
        if body:
            row = self._client.update_row(
                ENTITY_SET_LOTE, str(lote_id), body, return_representation=True
            )
            # Invalidar cachés de list_recent para que el cambio de etapa_actual
            # sea visible de inmediato sin esperar el TTL de 30s.
            # Se invalidan todos los límites conocidos (dashboard=50, desverdizado=200).
            try:
                from django.core.cache import caches
                _dv_cache = caches["dataverse"]
                _dv_cache.delete("lotes_list_recent:50")
                _dv_cache.delete("lotes_list_recent:200")
            except Exception:
                pass
            if row:
                record = _row_to_lote(row)
                # Actualizar lote_by_code cache para que find_by_code subsiguiente
                # obtenga el estado real (cantidad_bins actualizado, etc.) y no
                # reintente un PATCH sin cambios que fuerza el fallback GET.
                try:
                    if record.lote_code:
                        _dv_cache.set(f"lote_by_code:{record.lote_code}", record, timeout=30)
                except Exception:
                    pass
                return record

        # Fallback a GET (body vacío o PATCH sin cambios → 204)
        result = self._client.list_rows(
            ENTITY_SET_LOTE,
            select=_LOTE_SELECT,
            filter_expr=f"{LOTE_FIELDS['id']} eq {lote_id}",
            top=1,
        )
        rows = (result or {}).get("value", [])
        if not rows:
            return LoteRecord(id=lote_id, temporada="", lote_code="")
        record = _row_to_lote(rows[0])
        # Calentar cache para que la siguiente find_by_code no reintente un GET redundante.
        try:
            from django.core.cache import caches
            if record.lote_code:
                caches["dataverse"].set(f"lote_by_code:{record.lote_code}", record, timeout=30)
        except Exception:
            pass
        return record

    def list_recent(self, limit: int = 50) -> list[LoteRecord]:
        """
        Retorna los lotes mas recientes ordenados por fecha de creacion descendente.
        Usado por DashboardView en modo Dataverse para mostrar KPIs reales.
        temporada no existe en Dataverse: se retorna temporada="" en todos los records.
        """
        from django.core.cache import caches
        _cache = caches["dataverse"]
        _key = f"lotes_list_recent:{limit}"
        cached = _cache.get(_key)
        if cached is not None:
            return cached
        result = self._client.list_rows(
            ENTITY_SET_LOTE,
            select=_LOTE_SELECT,
            orderby="createdon desc",
            top=limit,
        )
        records = [_row_to_lote(r) for r in (result or {}).get("value", [])]
        _cache.set(_key, records, timeout=30)
        return records

    def count_bins_today(self) -> int:
        """
        Retorna la suma de crf21_cantidad_bins para lotes creados hoy (UTC).
        Filtra por createdon en Dataverse en vez de sumar lotes recientes.
        Sin cache: dato en tiempo real para el dashboard.
        """
        import datetime as _dt
        today = _dt.date.today()
        tomorrow = today + _dt.timedelta(days=1)
        filter_expr = (
            f"createdon ge {today.isoformat()}T00:00:00Z "
            f"and createdon lt {tomorrow.isoformat()}T00:00:00Z"
        )
        result = self._client.list_rows(
            ENTITY_SET_LOTE,
            select=[LOTE_FIELDS["cantidad_bins"]],
            filter_expr=filter_expr,
            top=500,
        )
        rows = (result or {}).get("value", [])
        cantidad_field = LOTE_FIELDS["cantidad_bins"]
        return sum(int(r.get(cantidad_field) or 0) for r in rows)


# ---------------------------------------------------------------------------
# PalletRepository
# ---------------------------------------------------------------------------

class DataversePalletRepository(PalletRepository):

    def __init__(self, client) -> None:
        self._client = client

    def find_by_code(self, temporada: str, pallet_code: str) -> Optional[PalletRecord]:
        f = f"{PALLET_FIELDS['pallet_code']} eq '{pallet_code}'"
        result = self._client.list_rows(
            ENTITY_SET_PALLET,
            select=_PALLET_SELECT,
            filter_expr=f,
            orderby="createdon desc",
            top=1,
        )
        rows = (result or {}).get("value", [])
        if not rows:
            return None
        record = _row_to_pallet(rows[0])
        record.temporada = temporada
        return record

    def list_recent(self, limit: int = 30) -> list[PalletRecord]:
        """Retorna los pallets mas recientes ordenados por fecha de creacion descendente."""
        from django.core.cache import caches
        _cache = caches["dataverse"]
        _key = f"pallets_list_recent:{limit}"
        cached = _cache.get(_key)
        if cached is not None:
            return cached
        result = self._client.list_rows(
            ENTITY_SET_PALLET,
            select=_PALLET_SELECT,
            orderby="createdon desc",
            top=limit,
        )
        records = [_row_to_pallet(r) for r in (result or {}).get("value", [])]
        _cache.set(_key, records, timeout=30)
        return records

    def get_or_create(
        self,
        temporada: str,
        pallet_code: str,
        *,
        operator_code: str = "",
        source_system: str = "dataverse",
        source_event_id: str = "",
        extra: Optional[dict] = None,
    ) -> tuple[PalletRecord, bool]:
        existing = self.find_by_code(temporada, pallet_code)
        if existing:
            return existing, False
        body: dict = {
            PALLET_FIELDS["pallet_code"]:   pallet_code,
            PALLET_FIELDS["operator_code"]: operator_code,
        }
        extra = extra or {}
        # ultimo_cambio_estado_at omitido: OData metadata propagation delay en Dataverse.
        for domain_key in ("fecha", "tipo_caja", "cajas_por_pallet", "peso_total_kg",
                           "destino_mercado"):
            v = extra.get(domain_key)
            if v not in (None, ""):
                body[PALLET_FIELDS[domain_key]] = v
        row = self._client.create_row(ENTITY_SET_PALLET, body) or {}
        return PalletRecord(
            id=row.get(PALLET_FIELDS["id"]),
            temporada=temporada,
            pallet_code=pallet_code,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
        ), True


# ---------------------------------------------------------------------------
# BinLoteRepository
# ---------------------------------------------------------------------------

class DataverseBinLoteRepository(BinLoteRepository):

    def __init__(self, client) -> None:
        self._client = client

    def create(
        self,
        bin_id: Any,
        lote_id: Any,
        *,
        operator_code: str = "",
        source_system: str = "dataverse",
        source_event_id: str = "",
    ) -> BinLoteRecord:
        body = {
            f"{BIN_LOTE_FIELDS['bin_id']}@odata.bind":  odata_bind(ENTITY_SET_BIN, str(bin_id)),
            f"{BIN_LOTE_FIELDS['lote_id']}@odata.bind": odata_bind(ENTITY_SET_LOTE, str(lote_id)),
        }
        row = self._client.create_row(ENTITY_SET_BIN_LOTE, body) or {}
        return BinLoteRecord(
            id=row.get(BIN_LOTE_FIELDS["id"]),
            bin_id=bin_id,
            lote_id=lote_id,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
        )

    def find_existing_assignments(self, bin_ids: list[Any]) -> list[BinAssignmentConflict]:
        if not bin_ids:
            return []
        ids_filter = " or ".join(
            f"{BIN_LOTE_FIELDS['bin_id_value']} eq {guid}" for guid in bin_ids
        )
        result = self._client.list_rows(
            ENTITY_SET_BIN_LOTE,
            select=[BIN_LOTE_FIELDS["id"],
                    BIN_LOTE_FIELDS["bin_id_value"],
                    BIN_LOTE_FIELDS["lote_id_value"]],
            filter_expr=f"({ids_filter})",
            top=len(bin_ids) + 10,
        )
        conflicts = []
        for row in (result or {}).get("value", []):
            conflicts.append(BinAssignmentConflict(
                bin_code=_str(row.get(BIN_LOTE_FIELDS["bin_id_value"])),
                lote_code=_str(row.get(BIN_LOTE_FIELDS["lote_id_value"])),
            ))
        return conflicts

    def list_by_lote(self, lote_id: Any) -> list[BinLoteRecord]:
        """Retorna todos los registros de la tabla union bin-lote para un lote dado."""
        f = f"{BIN_LOTE_FIELDS['lote_id_value']} eq {lote_id}"
        result = self._client.list_rows(
            ENTITY_SET_BIN_LOTE,
            select=_BIN_LOTE_SELECT,
            filter_expr=f,
            top=9999,
        )
        records = []
        for row in (result or {}).get("value", []):
            records.append(BinLoteRecord(
                id=row.get(BIN_LOTE_FIELDS["id"]),
                bin_id=row.get(BIN_LOTE_FIELDS["bin_id_value"]),
                lote_id=lote_id,
            ))
        return records

    def find_by_bin_and_lote(self, bin_id: Any, lote_id: Any) -> Optional[BinLoteRecord]:
        """Retorna el registro BinLote para el par (bin_id, lote_id), o None."""
        f = (
            f"{BIN_LOTE_FIELDS['bin_id_value']} eq {bin_id} and "
            f"{BIN_LOTE_FIELDS['lote_id_value']} eq {lote_id}"
        )
        result = self._client.list_rows(
            ENTITY_SET_BIN_LOTE,
            filter_expr=f,
            top=1,
        )
        rows = (result or {}).get("value", [])
        if not rows:
            return None
        row = rows[0]
        return BinLoteRecord(
            id=row.get(BIN_LOTE_FIELDS["id"]),
            bin_id=bin_id,
            lote_id=lote_id,
        )

    def delete(self, bin_lote_id: Any) -> None:
        self._client.delete_row(ENTITY_SET_BIN_LOTE, str(bin_lote_id))


# ---------------------------------------------------------------------------
# PalletLoteRepository
# ---------------------------------------------------------------------------

class DataversePalletLoteRepository(PalletLoteRepository):

    def __init__(self, client) -> None:
        self._client = client

    def find_by_lote(self, lote_id: Any) -> Optional[PalletLoteRecord]:
        f = f"{PALLET_LOTE_FIELDS['lote_id_value']} eq {lote_id}"
        result = self._client.list_rows(
            ENTITY_SET_PALLET_LOTE,
            select=[PALLET_LOTE_FIELDS["id"],
                    PALLET_LOTE_FIELDS["pallet_id_value"],
                    PALLET_LOTE_FIELDS["lote_id_value"]],
            filter_expr=f,
            orderby="createdon desc",
            top=1,
        )
        rows = (result or {}).get("value", [])
        if not rows:
            return None
        row = rows[0]
        return PalletLoteRecord(
            id=row.get(PALLET_LOTE_FIELDS["id"]),
            pallet_id=row.get(PALLET_LOTE_FIELDS["pallet_id_value"]),
            lote_id=lote_id,
        )

    def find_by_pallet(self, pallet_id: Any) -> Optional[PalletLoteRecord]:
        """
        Retorna la asociacion lote-pallet dado un pallet_id.
        Usado para actualizar etapa_actual del lote en operaciones pallet-nivel
        (calidad_pallet, camara_frio, medicion_temperatura).
        """
        f = f"{PALLET_LOTE_FIELDS['pallet_id_value']} eq {pallet_id}"
        result = self._client.list_rows(
            ENTITY_SET_PALLET_LOTE,
            select=[PALLET_LOTE_FIELDS["id"],
                    PALLET_LOTE_FIELDS["pallet_id_value"],
                    PALLET_LOTE_FIELDS["lote_id_value"]],
            filter_expr=f,
            orderby="createdon desc",
            top=1,
        )
        rows = (result or {}).get("value", [])
        if not rows:
            return None
        row = rows[0]
        return PalletLoteRecord(
            id=row.get(PALLET_LOTE_FIELDS["id"]),
            pallet_id=pallet_id,
            lote_id=row.get(PALLET_LOTE_FIELDS["lote_id_value"]),
        )

    def get_or_create(
        self,
        pallet_id: Any,
        lote_id: Any,
        *,
        operator_code: str = "",
        source_system: str = "dataverse",
        source_event_id: str = "",
    ) -> tuple[PalletLoteRecord, bool]:
        f = (
            f"{PALLET_LOTE_FIELDS['pallet_id_value']} eq {pallet_id}"
            f" and {PALLET_LOTE_FIELDS['lote_id_value']} eq {lote_id}"
        )
        result = self._client.list_rows(
            ENTITY_SET_PALLET_LOTE,
            select=[PALLET_LOTE_FIELDS["id"]],
            filter_expr=f,
            top=1,
        )
        rows = (result or {}).get("value", [])
        if rows:
            return PalletLoteRecord(
                id=rows[0].get(PALLET_LOTE_FIELDS["id"]),
                pallet_id=pallet_id,
                lote_id=lote_id,
            ), False

        body = {
            f"{PALLET_LOTE_FIELDS['pallet_id']}@odata.bind": odata_bind(ENTITY_SET_PALLET, str(pallet_id)),
            f"{PALLET_LOTE_FIELDS['lote_id']}@odata.bind":   odata_bind(ENTITY_SET_LOTE, str(lote_id)),
        }
        row = self._client.create_row(ENTITY_SET_PALLET_LOTE, body) or {}
        return PalletLoteRecord(
            id=row.get(PALLET_LOTE_FIELDS["id"]),
            pallet_id=pallet_id,
            lote_id=lote_id,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
        ), True


# ---------------------------------------------------------------------------
# RegistroEtapaRepository — no-op (no existe tabla en Dataverse)
# ---------------------------------------------------------------------------

class DataverseRegistroEtapaRepository(RegistroEtapaRepository):
    """
    No existe tabla registro_etapas en Dataverse (validado 2026-03-29).
    Los eventos de traza se registran solo en log local. Los casos de uso
    funcionan correctamente: el registro de eventos es informacional y no
    bloquea la logica de negocio.
    """

    def create(
        self,
        *,
        temporada: str,
        event_key: str,
        tipo_evento: str,
        bin_id: Optional[Any] = None,
        lote_id: Optional[Any] = None,
        pallet_id: Optional[Any] = None,
        operator_code: str = "",
        source_system: str = "dataverse",
        source_event_id: str = "",
        payload: Optional[dict] = None,
        notes: str = "",
    ) -> RegistroEtapaRecord:
        logger.info(
            "dataverse:registro_etapa [%s] temporada=%s bin=%s lote=%s pallet=%s payload=%s",
            event_key, temporada, bin_id, lote_id, pallet_id, payload,
        )
        return RegistroEtapaRecord(
            id=None,
            temporada=temporada,
            event_key=event_key,
            tipo_evento=tipo_evento,
            bin_id=bin_id,
            lote_id=lote_id,
            pallet_id=pallet_id,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
            payload=payload or {},
            notes=notes,
        )

    def get_or_create(
        self,
        *,
        event_key: str,
        temporada: str,
        tipo_evento: str,
        bin_id: Optional[Any] = None,
        lote_id: Optional[Any] = None,
        pallet_id: Optional[Any] = None,
        operator_code: str = "",
        source_system: str = "dataverse",
        source_event_id: str = "",
        payload: Optional[dict] = None,
    ) -> tuple[RegistroEtapaRecord, bool]:
        record = self.create(
            temporada=temporada,
            event_key=event_key,
            tipo_evento=tipo_evento,
            bin_id=bin_id,
            lote_id=lote_id,
            pallet_id=pallet_id,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
            payload=payload,
        )
        return record, True

    def list_recent(self, limit: int = 100) -> list[RegistroEtapaRecord]:
        # Sin tabla en Dataverse: retorna lista vacia (no es informacion critica).
        return []


# ---------------------------------------------------------------------------
# SequenceCounterRepository — conteo de registros existentes en Dataverse
# ---------------------------------------------------------------------------

class DataverseSequenceCounterRepository(SequenceCounterRepository):
    """
    Genera correlativos contando registros existentes en Dataverse.
    No es atomico — race conditions posibles bajo alta concurrencia.
    Aceptable para la escala del MVP.
    """

    def __init__(self, client) -> None:
        self._client = client

    def get_next(self, entity_name: str, dimension: str) -> int:
        count = self._count(entity_name, dimension)
        return count + 1

    def current_value(self, entity_name: str, dimension: str) -> int:
        return self._count(entity_name, dimension)

    def _count(self, entity_name: str, dimension: str) -> int:
        try:
            if entity_name == "bin":
                return self._count_bins(dimension)
            if entity_name == "lote":
                return self._count_lotes(dimension)
            if entity_name == "pallet":
                return self._count_pallets(dimension)
        except Exception as exc:
            logger.warning("DataverseSequenceCounter._count(%s, %s) error: %s", entity_name, dimension, exc)
        return 0

    def _count_bins(self, dimension: str) -> int:
        """dimension = 'cod_prod|cultivo|variedad|cuartel|fecha_str'"""
        parts = dimension.split("|")
        prefix = "-".join(parts) + "-"
        result = self._client.list_rows(
            ENTITY_SET_BIN,
            select=[BIN_FIELDS["bin_code"]],
            filter_expr=f"startswith({BIN_FIELDS['bin_code']},'{prefix}')",
            top=9999,
        )
        return len((result or {}).get("value", []))

    def _count_lotes(self, dimension: str) -> int:
        """dimension = temporada_codigo like '2025-2026'"""
        try:
            start_year, end_year = dimension.split("-")
            start = f"{start_year}-10-01T00:00:00Z"
            end   = f"{end_year}-09-30T23:59:59Z"
        except ValueError:
            return 0
        result = self._client.list_rows(
            ENTITY_SET_LOTE,
            select=[LOTE_FIELDS["id"]],
            filter_expr=(
                f"{LOTE_FIELDS['created_at']} ge {start}"
                f" and {LOTE_FIELDS['created_at']} le {end}"
            ),
            top=9999,
        )
        return len((result or {}).get("value", []))

    def _count_pallets(self, dimension: str) -> int:
        """dimension = YYYYMMDD"""
        try:
            d = datetime.date(int(dimension[:4]), int(dimension[4:6]), int(dimension[6:8]))
        except (ValueError, IndexError):
            return 0
        start = f"{d.isoformat()}T00:00:00Z"
        next_d = d + datetime.timedelta(days=1)
        end   = f"{next_d.isoformat()}T00:00:00Z"
        result = self._client.list_rows(
            ENTITY_SET_PALLET,
            select=[PALLET_FIELDS["id"]],
            filter_expr=f"{PALLET_FIELDS['created_at']} ge {start} and {PALLET_FIELDS['created_at']} lt {end}",
            top=9999,
        )
        return len((result or {}).get("value", []))


# ---------------------------------------------------------------------------
# CamaraMantencionRepository
# ---------------------------------------------------------------------------

class DataverseCamaraMantencionRepository(CamaraMantencionRepository):

    def __init__(self, client) -> None:
        self._client = client

    def find_by_lote(self, lote_id: Any) -> Optional[CamaraMantencionRecord]:
        f = f"{CAMARA_MANTENCION_FIELDS['lote_id_value']} eq {lote_id}"
        result = self._client.list_rows(
            ENTITY_SET_CAMARA_MANTENCION,
            select=[CAMARA_MANTENCION_FIELDS[k] for k in (
                "id", "lote_id_value", "camara_numero", "fecha_ingreso",
                "hora_ingreso", "temperatura_camara", "humedad_relativa",
                "observaciones", "operator_code",
            )],
            filter_expr=f,
            top=1,
        )
        rows = (result or {}).get("value", [])
        return _row_to_camara_mantencion(rows[0], lote_id) if rows else None

    def create(
        self,
        lote_id: Any,
        *,
        operator_code: str = "",
        source_system: str = "dataverse",
        extra: Optional[dict] = None,
    ) -> CamaraMantencionRecord:
        body: dict = {
            f"{CAMARA_MANTENCION_FIELDS['lote_id']}@odata.bind": odata_bind(ENTITY_SET_LOTE, str(lote_id)),
            CAMARA_MANTENCION_FIELDS["operator_code"]: operator_code,
        }
        _extra_map = {
            "camara_numero":      CAMARA_MANTENCION_FIELDS["camara_numero"],
            "fecha_ingreso":      CAMARA_MANTENCION_FIELDS["fecha_ingreso"],
            "hora_ingreso":       CAMARA_MANTENCION_FIELDS["hora_ingreso"],
            "temperatura_camara": CAMARA_MANTENCION_FIELDS["temperatura_camara"],
            "humedad_relativa":   CAMARA_MANTENCION_FIELDS["humedad_relativa"],
            "observaciones":      CAMARA_MANTENCION_FIELDS["observaciones"],
        }
        for domain_key, dv_field in _extra_map.items():
            v = (extra or {}).get(domain_key)
            if v not in (None, ""):
                if domain_key in {"temperatura_fruta", "peso_caja_muestra"}:
                    v = float(v)
                body[dv_field] = v

        row = self._client.create_row(ENTITY_SET_CAMARA_MANTENCION, body) or {}
        return CamaraMantencionRecord(
            id=row.get(CAMARA_MANTENCION_FIELDS["id"]),
            lote_id=lote_id,
            operator_code=operator_code,
            source_system=source_system,
        )

    def update(self, record_id: Any, fields: dict) -> CamaraMantencionRecord:
        _updatable = {
            "camara_numero":      CAMARA_MANTENCION_FIELDS["camara_numero"],
            "fecha_salida":       CAMARA_MANTENCION_FIELDS["fecha_salida"],
            "hora_salida":        CAMARA_MANTENCION_FIELDS["hora_salida"],
            "temperatura_camara": CAMARA_MANTENCION_FIELDS["temperatura_camara"],
            "humedad_relativa":   CAMARA_MANTENCION_FIELDS["humedad_relativa"],
            "observaciones":      CAMARA_MANTENCION_FIELDS["observaciones"],
        }
        body = {dv_field: fields[k] for k, dv_field in _updatable.items() if k in fields}
        if body:
            self._client.update_row(ENTITY_SET_CAMARA_MANTENCION, str(record_id), body)
        return CamaraMantencionRecord(id=record_id, lote_id=None)


# ---------------------------------------------------------------------------
# DesverdizadoRepository
# ---------------------------------------------------------------------------

class DataverseDesverdizadoRepository(DesverdizadoRepository):

    def __init__(self, client) -> None:
        self._client = client

    def find_by_lote(self, lote_id: Any) -> Optional[DesverdizadoRecord]:
        f = f"{DESVERDIZADO_FIELDS['lote_id_value']} eq {lote_id}"
        result = self._client.list_rows(
            ENTITY_SET_DESVERDIZADO,
            select=[DESVERDIZADO_FIELDS[k] for k in (
                "id", "lote_id_value", "numero_camara", "fecha_ingreso", "hora_ingreso",
                "fecha_salida", "hora_salida", "horas_desverdizado",
                "kilos_enviados_terreno", "kilos_recepcionados",
                "kilos_bruto_salida", "kilos_neto_salida",
                "color_salida", "proceso", "operator_code",
            )],
            filter_expr=f,
            top=1,
        )
        rows = (result or {}).get("value", [])
        return _row_to_desverdizado(rows[0], lote_id) if rows else None

    def list_by_lotes(self, lote_ids: list) -> dict:
        """Batch fetch: retorna {lote_id: DesverdizadoRecord} en chunks de 20 GUIDs."""
        if not lote_ids:
            return {}
        _CHUNK = 20
        _select = [DESVERDIZADO_FIELDS[k] for k in (
            "id", "lote_id_value", "numero_camara", "fecha_ingreso", "hora_ingreso",
            "fecha_salida", "hora_salida", "horas_desverdizado",
            "kilos_enviados_terreno", "kilos_recepcionados",
            "kilos_bruto_salida", "kilos_neto_salida",
            "color_salida", "proceso", "operator_code",
        )]
        resultado: dict = {}
        lote_id_field = DESVERDIZADO_FIELDS["lote_id_value"]
        for i in range(0, len(lote_ids), _CHUNK):
            chunk = lote_ids[i:i + _CHUNK]
            ids_filter = " or ".join(f"{lote_id_field} eq {lid}" for lid in chunk)
            try:
                result = self._client.list_rows(
                    ENTITY_SET_DESVERDIZADO,
                    select=_select,
                    filter_expr=f"({ids_filter})",
                    top=len(chunk) + 5,
                )
                for row in (result or {}).get("value", []):
                    lid = row.get(lote_id_field)
                    if lid and lid not in resultado:
                        resultado[lid] = _row_to_desverdizado(row, lid)
            except Exception:
                logger.warning("list_by_lotes desverdizado chunk %d falló", i // _CHUNK)
        return resultado

    def create(
        self,
        lote_id: Any,
        *,
        operator_code: str = "",
        source_system: str = "dataverse",
        extra: Optional[dict] = None,
    ) -> DesverdizadoRecord:
        body: dict = {
            f"{DESVERDIZADO_FIELDS['lote_id']}@odata.bind": odata_bind(ENTITY_SET_LOTE, str(lote_id)),
            DESVERDIZADO_FIELDS["operator_code"]: operator_code,
        }
        _extra_map = {
            "numero_camara":          DESVERDIZADO_FIELDS["numero_camara"],
            "fecha_ingreso":          DESVERDIZADO_FIELDS["fecha_ingreso"],
            "hora_ingreso":           DESVERDIZADO_FIELDS["hora_ingreso"],
            "horas_desverdizado":     DESVERDIZADO_FIELDS["horas_desverdizado"],
            "color_salida":           DESVERDIZADO_FIELDS["color_salida"],
            "proceso":                DESVERDIZADO_FIELDS["proceso"],
            "kilos_enviados_terreno": DESVERDIZADO_FIELDS["kilos_enviados_terreno"],
            "kilos_recepcionados":    DESVERDIZADO_FIELDS["kilos_recepcionados"],
            "kilos_procesados":       DESVERDIZADO_FIELDS["kilos_procesados"],
            "kilos_bruto_salida":     DESVERDIZADO_FIELDS["kilos_bruto_salida"],
            "kilos_neto_salida":      DESVERDIZADO_FIELDS["kilos_neto_salida"],
            "fecha_proceso":          DESVERDIZADO_FIELDS["fecha_proceso"],
            "sector":                 DESVERDIZADO_FIELDS["sector"],
            "cuartel":                DESVERDIZADO_FIELDS["cuartel"],
        }
        for domain_key, dv_field in _extra_map.items():
            v = (extra or {}).get(domain_key)
            if v not in (None, ""):
                body[dv_field] = v

        row = self._client.create_row(ENTITY_SET_DESVERDIZADO, body) or {}
        return DesverdizadoRecord(
            id=row.get(DESVERDIZADO_FIELDS["id"]),
            lote_id=lote_id,
            operator_code=operator_code,
            source_system=source_system,
        )

    def update(self, record_id: Any, fields: dict) -> DesverdizadoRecord:
        _updatable = {
            "fecha_salida":       DESVERDIZADO_FIELDS["fecha_salida"],
            "hora_salida":        DESVERDIZADO_FIELDS["hora_salida"],
            "kilos_bruto_salida": DESVERDIZADO_FIELDS["kilos_bruto_salida"],
            "kilos_neto_salida":  DESVERDIZADO_FIELDS["kilos_neto_salida"],
            "color_salida":       DESVERDIZADO_FIELDS["color_salida"],
        }
        body = {dv_field: fields[k] for k, dv_field in _updatable.items() if k in fields}
        if body:
            self._client.update_row(ENTITY_SET_DESVERDIZADO, str(record_id), body)
        return DesverdizadoRecord(id=record_id, lote_id=None)


# ---------------------------------------------------------------------------
# CalidadDesverdizadoRepository
# ---------------------------------------------------------------------------

class DataverseCalidadDesverdizadoRepository(CalidadDesverdizadoRepository):

    def __init__(self, client) -> None:
        self._client = client

    def create(
        self,
        lote_id: Any,
        *,
        operator_code: str = "",
        source_system: str = "dataverse",
        extra: Optional[dict] = None,
    ) -> CalidadDesverdizadoRecord:
        body: dict = {
            f"{CALIDAD_DESVERDIZADO_FIELDS['lote_id']}@odata.bind": odata_bind(ENTITY_SET_LOTE, str(lote_id)),
            CALIDAD_DESVERDIZADO_FIELDS["operator_code"]: operator_code,
        }
        _extra_map = {
            "fecha":                CALIDAD_DESVERDIZADO_FIELDS["fecha"],
            "hora":                 CALIDAD_DESVERDIZADO_FIELDS["hora"],
            "temperatura_fruta":    CALIDAD_DESVERDIZADO_FIELDS["temperatura_fruta"],
            "color_evaluado":       CALIDAD_DESVERDIZADO_FIELDS["color_evaluado"],
            "estado_visual":        CALIDAD_DESVERDIZADO_FIELDS["estado_visual"],
            "presencia_defectos":   CALIDAD_DESVERDIZADO_FIELDS["presencia_defectos"],
            "descripcion_defectos": CALIDAD_DESVERDIZADO_FIELDS["descripcion_defectos"],
            "aprobado":             CALIDAD_DESVERDIZADO_FIELDS["aprobado"],
            "observaciones":        CALIDAD_DESVERDIZADO_FIELDS["observaciones"],
        }
        for domain_key, dv_field in _extra_map.items():
            v = (extra or {}).get(domain_key)
            if v not in (None, ""):
                body[dv_field] = v

        row = self._client.create_row(ENTITY_SET_CALIDAD_DESVERDIZADO, body) or {}
        aprobado = (extra or {}).get("aprobado")
        return CalidadDesverdizadoRecord(
            id=row.get(CALIDAD_DESVERDIZADO_FIELDS["id"]),
            lote_id=lote_id,
            aprobado=aprobado,
            operator_code=operator_code,
            source_system=source_system,
        )

    def list_by_lote(self, lote_id: Any) -> list[CalidadDesverdizadoRecord]:
        f = f"{CALIDAD_DESVERDIZADO_FIELDS['lote_id_value']} eq {lote_id}"
        result = self._client.list_rows(
            ENTITY_SET_CALIDAD_DESVERDIZADO,
            select=[CALIDAD_DESVERDIZADO_FIELDS[k] for k in (
                "id", "lote_id_value", "fecha", "hora", "temperatura_fruta",
                "color_evaluado", "aprobado", "observaciones", "operator_code",
            )],
            filter_expr=f,
            orderby="createdon desc",
            top=100,
        )
        return [_row_to_calidad_desverdizado(r, lote_id) for r in (result or {}).get("value", [])]


# ---------------------------------------------------------------------------
# IngresoAPackingRepository
# ---------------------------------------------------------------------------

class DataverseIngresoAPackingRepository(IngresoAPackingRepository):

    def __init__(self, client) -> None:
        self._client = client

    def find_by_lote(self, lote_id: Any) -> Optional[IngresoAPackingRecord]:
        f = f"{INGRESO_PACKING_FIELDS['lote_id_value']} eq {lote_id}"
        result = self._client.list_rows(
            ENTITY_SET_INGRESO_PACKING,
            select=[INGRESO_PACKING_FIELDS[k] for k in (
                "id", "lote_id_value", "fecha_ingreso", "hora_ingreso",
                "kilos_bruto_ingreso_packing", "kilos_neto_ingreso_packing",
                "via_desverdizado", "observaciones", "operator_code",
            )],
            filter_expr=f,
            top=1,
        )
        rows = (result or {}).get("value", [])
        return _row_to_ingreso_packing(rows[0], lote_id) if rows else None

    def list_by_lotes(self, lote_ids: list) -> dict:
        """Batch fetch: retorna {lote_id: IngresoAPackingRecord} en chunks de 20 GUIDs."""
        if not lote_ids:
            return {}
        _CHUNK = 20
        _select = [INGRESO_PACKING_FIELDS[k] for k in (
            "id", "lote_id_value", "fecha_ingreso", "hora_ingreso",
            "kilos_bruto_ingreso_packing", "kilos_neto_ingreso_packing",
            "via_desverdizado", "observaciones", "operator_code",
        )]
        resultado: dict = {}
        lote_id_field = INGRESO_PACKING_FIELDS["lote_id_value"]
        for i in range(0, len(lote_ids), _CHUNK):
            chunk = lote_ids[i:i + _CHUNK]
            ids_filter = " or ".join(f"{lote_id_field} eq {lid}" for lid in chunk)
            try:
                result = self._client.list_rows(
                    ENTITY_SET_INGRESO_PACKING,
                    select=_select,
                    filter_expr=f"({ids_filter})",
                    top=len(chunk) + 5,
                )
                for row in (result or {}).get("value", []):
                    lid = row.get(lote_id_field)
                    if lid and lid not in resultado:
                        resultado[lid] = _row_to_ingreso_packing(row, lid)
            except Exception:
                logger.warning("list_by_lotes ingresos_packing chunk %d falló", i // _CHUNK)
        return resultado

    def create(
        self,
        lote_id: Any,
        *,
        operator_code: str = "",
        source_system: str = "dataverse",
        extra: Optional[dict] = None,
    ) -> IngresoAPackingRecord:
        body: dict = {
            f"{INGRESO_PACKING_FIELDS['lote_id']}@odata.bind": odata_bind(ENTITY_SET_LOTE, str(lote_id)),
            INGRESO_PACKING_FIELDS["operator_code"]: operator_code,
        }
        _extra_map = {
            "fecha_ingreso":              INGRESO_PACKING_FIELDS["fecha_ingreso"],
            "hora_ingreso":               INGRESO_PACKING_FIELDS["hora_ingreso"],
            "kilos_bruto_ingreso_packing":INGRESO_PACKING_FIELDS["kilos_bruto_ingreso_packing"],
            "kilos_neto_ingreso_packing": INGRESO_PACKING_FIELDS["kilos_neto_ingreso_packing"],
            "via_desverdizado":           INGRESO_PACKING_FIELDS["via_desverdizado"],
            "observaciones":              INGRESO_PACKING_FIELDS["observaciones"],
        }
        for domain_key, dv_field in _extra_map.items():
            v = (extra or {}).get(domain_key)
            if v not in (None, ""):
                body[dv_field] = v

        row = self._client.create_row(ENTITY_SET_INGRESO_PACKING, body) or {}
        via_desv = (extra or {}).get("via_desverdizado", False)
        return IngresoAPackingRecord(
            id=row.get(INGRESO_PACKING_FIELDS["id"]),
            lote_id=lote_id,
            via_desverdizado=bool(via_desv),
            operator_code=operator_code,
            source_system=source_system,
        )


# ---------------------------------------------------------------------------
# RegistroPackingRepository
# ---------------------------------------------------------------------------

class DataverseRegistroPackingRepository(RegistroPackingRepository):

    def __init__(self, client) -> None:
        self._client = client

    def create(
        self,
        lote_id: Any,
        *,
        operator_code: str = "",
        source_system: str = "dataverse",
        extra: Optional[dict] = None,
    ) -> RegistroPackingRecord:
        body: dict = {
            f"{REGISTRO_PACKING_FIELDS['lote_id']}@odata.bind": odata_bind(ENTITY_SET_LOTE, str(lote_id)),
            REGISTRO_PACKING_FIELDS["operator_code"]: operator_code,
        }
        _extra_map = {
            "fecha":                  REGISTRO_PACKING_FIELDS["fecha"],
            "hora_inicio":            REGISTRO_PACKING_FIELDS["hora_inicio"],
            "linea_proceso":          REGISTRO_PACKING_FIELDS["linea_proceso"],
            "categoria_calidad":      REGISTRO_PACKING_FIELDS["categoria_calidad"],
            "calibre":                REGISTRO_PACKING_FIELDS["calibre"],
            "tipo_envase":            REGISTRO_PACKING_FIELDS["tipo_envase"],
            "cantidad_cajas_producidas": REGISTRO_PACKING_FIELDS["cantidad_cajas_producidas"],
            "peso_promedio_caja_kg":  REGISTRO_PACKING_FIELDS["peso_promedio_caja_kg"],
            "merma_seleccion_pct":    REGISTRO_PACKING_FIELDS["merma_seleccion_pct"],
        }
        for domain_key, dv_field in _extra_map.items():
            v = (extra or {}).get(domain_key)
            if v not in (None, ""):
                body[dv_field] = v

        row = self._client.create_row(ENTITY_SET_REGISTRO_PACKING, body) or {}
        return RegistroPackingRecord(
            id=row.get(REGISTRO_PACKING_FIELDS["id"]),
            lote_id=lote_id,
            operator_code=operator_code,
            source_system=source_system,
        )

    def list_by_lote(self, lote_id: Any) -> list[RegistroPackingRecord]:
        f = f"{REGISTRO_PACKING_FIELDS['lote_id_value']} eq {lote_id}"
        result = self._client.list_rows(
            ENTITY_SET_REGISTRO_PACKING,
            select=[REGISTRO_PACKING_FIELDS[k] for k in (
                "id", "lote_id_value", "fecha", "hora_inicio",
                "linea_proceso", "categoria_calidad", "calibre", "tipo_envase",
                "cantidad_cajas_producidas", "peso_promedio_caja_kg",
                "merma_seleccion_pct", "operator_code",
            )],
            filter_expr=f,
            orderby="createdon desc",
            top=200,
        )
        return [_row_to_registro_packing(r, lote_id) for r in (result or {}).get("value", [])]


# ---------------------------------------------------------------------------
# ControlProcesoPackingRepository
# ---------------------------------------------------------------------------

class DataverseControlProcesoPackingRepository(ControlProcesoPackingRepository):

    def __init__(self, client) -> None:
        self._client = client

    def create(
        self,
        lote_id: Any,
        *,
        operator_code: str = "",
        source_system: str = "dataverse",
        extra: Optional[dict] = None,
    ) -> ControlProcesoPackingRecord:
        body: dict = {
            f"{CONTROL_PROCESO_PACKING_FIELDS['lote_id']}@odata.bind": odata_bind(ENTITY_SET_LOTE, str(lote_id)),
            CONTROL_PROCESO_PACKING_FIELDS["operator_code"]: operator_code,
        }
        _extra_map = {k: CONTROL_PROCESO_PACKING_FIELDS[k] for k in (
            "fecha", "hora", "n_bins_procesados", "temp_agua_tina", "ph_agua",
            "recambio_agua", "rendimiento_lote_pct", "observaciones_generales",
            "velocidad_volcador", "obs_volcador", "cloro_libre_ppm",
            "tiempo_inmersion_seg", "temp_aire_secado", "velocidad_ventiladores",
            "fruta_sale_seca", "tipo_cera", "dosis_cera_ml_min", "temp_cera",
            "cobertura_uniforme", "n_operarios_seleccion", "fruta_dano_condicion_kg",
            "fruta_dano_calidad_kg", "fruta_pudricion_kg", "merma_total_seleccion_kg",
            "equipo_calibrador", "calibre_predominante", "pct_calibre_export",
            "pct_calibres_menores", "tipo_caja", "peso_promedio_caja_kg",
            "n_cajas_producidas", "rol",
        )}
        for domain_key, dv_field in _extra_map.items():
            v = (extra or {}).get(domain_key)
            if v not in (None, ""):
                body[dv_field] = v

        row = self._client.create_row(ENTITY_SET_CONTROL_PROCESO_PACKING, body) or {}
        return ControlProcesoPackingRecord(
            id=row.get(CONTROL_PROCESO_PACKING_FIELDS["id"]),
            lote_id=lote_id,
            operator_code=operator_code,
            source_system=source_system,
        )

    def list_by_lote(self, lote_id: Any) -> list[ControlProcesoPackingRecord]:
        f = f"{CONTROL_PROCESO_PACKING_FIELDS['lote_id_value']} eq {lote_id}"
        result = self._client.list_rows(
            ENTITY_SET_CONTROL_PROCESO_PACKING,
            select=[CONTROL_PROCESO_PACKING_FIELDS[k] for k in (
                "id", "lote_id_value", "fecha", "hora", "n_bins_procesados",
                "temp_agua_tina", "ph_agua", "recambio_agua",
                "rendimiento_lote_pct", "observaciones_generales",
                "velocidad_volcador", "obs_volcador", "cloro_libre_ppm",
                "tiempo_inmersion_seg", "temp_aire_secado", "velocidad_ventiladores",
                "fruta_sale_seca", "tipo_cera", "dosis_cera_ml_min", "temp_cera",
                "cobertura_uniforme", "n_operarios_seleccion", "fruta_dano_condicion_kg",
                "fruta_dano_calidad_kg", "fruta_pudricion_kg", "merma_total_seleccion_kg",
                "equipo_calibrador", "calibre_predominante", "pct_calibre_export",
                "pct_calibres_menores", "tipo_caja", "peso_promedio_caja_kg",
                "n_cajas_producidas", "operator_code", "rol",
            )],
            filter_expr=f,
            orderby="createdon desc",
            top=200,
        )
        return [_row_to_control_proceso(r, lote_id) for r in (result or {}).get("value", [])]


# ---------------------------------------------------------------------------
# CalidadPalletRepository
# ---------------------------------------------------------------------------

class DataverseCalidadPalletRepository(CalidadPalletRepository):

    def __init__(self, client) -> None:
        self._client = client

    def create(
        self,
        pallet_id: Any,
        *,
        operator_code: str = "",
        source_system: str = "dataverse",
        extra: Optional[dict] = None,
    ) -> CalidadPalletRecord:
        body: dict = {
            f"{CALIDAD_PALLET_FIELDS['pallet_id']}@odata.bind": odata_bind(ENTITY_SET_PALLET, str(pallet_id)),
            CALIDAD_PALLET_FIELDS["operator_code"]: operator_code,
        }
        _extra_map = {
            "fecha":                CALIDAD_PALLET_FIELDS["fecha"],
            "hora":                 CALIDAD_PALLET_FIELDS["hora"],
            "temperatura_fruta":    CALIDAD_PALLET_FIELDS["temperatura_fruta"],
            "peso_caja_muestra":    CALIDAD_PALLET_FIELDS["peso_caja_muestra"],
            "estado_embalaje":      CALIDAD_PALLET_FIELDS["estado_embalaje"],
            "estado_visual_fruta":  CALIDAD_PALLET_FIELDS["estado_visual_fruta"],
            "presencia_defectos":   CALIDAD_PALLET_FIELDS["presencia_defectos"],
            "descripcion_defectos": CALIDAD_PALLET_FIELDS["descripcion_defectos"],
            "aprobado":             CALIDAD_PALLET_FIELDS["aprobado"],
            "observaciones":        CALIDAD_PALLET_FIELDS["observaciones"],
        }
        for domain_key, dv_field in _extra_map.items():
            v = (extra or {}).get(domain_key)
            if v not in (None, ""):
                body[dv_field] = v

        row = self._client.create_row(ENTITY_SET_CALIDAD_PALLET, body) or {}
        aprobado = (extra or {}).get("aprobado")
        return CalidadPalletRecord(
            id=row.get(CALIDAD_PALLET_FIELDS["id"]),
            pallet_id=pallet_id,
            aprobado=aprobado,
            operator_code=operator_code,
            source_system=source_system,
        )

    def list_by_pallet(self, pallet_id: Any) -> list[CalidadPalletRecord]:
        f = f"{CALIDAD_PALLET_FIELDS['pallet_id_value']} eq {pallet_id}"
        result = self._client.list_rows(
            ENTITY_SET_CALIDAD_PALLET,
            select=[CALIDAD_PALLET_FIELDS[k] for k in (
                "id", "pallet_id_value", "fecha", "hora",
                "temperatura_fruta", "peso_caja_muestra", "estado_visual_fruta",
                "presencia_defectos", "aprobado", "observaciones", "operator_code",
            )],
            filter_expr=f,
            orderby="createdon desc",
            top=100,
        )
        return [_row_to_calidad_pallet(r, pallet_id) for r in (result or {}).get("value", [])]


# ---------------------------------------------------------------------------
# CalidadPalletMuestraRepository
# ---------------------------------------------------------------------------

class DataverseCalidadPalletMuestraRepository(CalidadPalletMuestraRepository):

    def __init__(self, client) -> None:
        self._client = client

    def create(
        self,
        pallet_id: Any,
        *,
        operator_code: str = "",
        source_system: str = "dataverse",
        extra: Optional[dict] = None,
    ) -> CalidadPalletMuestraRecord:
        body: dict = {
            f"{CALIDAD_PALLET_MUESTRA_FIELDS['pallet_id']}@odata.bind": odata_bind(ENTITY_SET_PALLET, str(pallet_id)),
            CALIDAD_PALLET_MUESTRA_FIELDS["operator_code"]: operator_code,
        }
        _extra_map = {
            "numero_muestra":    CALIDAD_PALLET_MUESTRA_FIELDS["numero_muestra"],
            "temperatura_fruta": CALIDAD_PALLET_MUESTRA_FIELDS["temperatura_fruta"],
            "peso_caja_muestra": CALIDAD_PALLET_MUESTRA_FIELDS["peso_caja_muestra"],
            "n_frutos":          CALIDAD_PALLET_MUESTRA_FIELDS["n_frutos"],
            "aprobado":          CALIDAD_PALLET_MUESTRA_FIELDS["aprobado"],
            "observaciones":     CALIDAD_PALLET_MUESTRA_FIELDS["observaciones"],
            "rol":               CALIDAD_PALLET_MUESTRA_FIELDS["rol"],
        }
        for domain_key, dv_field in _extra_map.items():
            v = (extra or {}).get(domain_key)
            if v not in (None, ""):
                body[dv_field] = v

        row = self._client.create_row(ENTITY_SET_CALIDAD_PALLET_MUESTRA, body) or {}
        extra = extra or {}
        return CalidadPalletMuestraRecord(
            id=row.get(CALIDAD_PALLET_MUESTRA_FIELDS["id"]),
            pallet_id=pallet_id,
            numero_muestra=extra.get("numero_muestra"),
            aprobado=extra.get("aprobado"),
            operator_code=operator_code,
            source_system=source_system,
        )

    def list_by_pallet(self, pallet_id: Any) -> list[CalidadPalletMuestraRecord]:
        f = f"{CALIDAD_PALLET_MUESTRA_FIELDS['pallet_id_value']} eq {pallet_id}"
        result = self._client.list_rows(
            ENTITY_SET_CALIDAD_PALLET_MUESTRA,
            select=[CALIDAD_PALLET_MUESTRA_FIELDS[k] for k in (
                "id", "pallet_id_value", "numero_muestra",
                "temperatura_fruta", "peso_caja_muestra", "n_frutos",
                "aprobado", "observaciones", "operator_code",
            )],
            filter_expr=f,
            orderby="crf21_numero_muestra asc",
            top=100,
        )
        return [_row_to_calidad_pallet_muestra(r, pallet_id) for r in (result or {}).get("value", [])]


# ---------------------------------------------------------------------------
# CamaraFrioRepository
# ---------------------------------------------------------------------------

class DataverseCamaraFrioRepository(CamaraFrioRepository):

    def __init__(self, client) -> None:
        self._client = client

    def find_by_pallet(self, pallet_id: Any) -> Optional[CamaraFrioRecord]:
        f = f"{CAMARA_FRIO_FIELDS['pallet_id_value']} eq {pallet_id}"
        result = self._client.list_rows(
            ENTITY_SET_CAMARA_FRIO,
            select=[CAMARA_FRIO_FIELDS[k] for k in (
                "id", "pallet_id_value", "camara_numero", "temperatura_camara",
                "humedad_relativa", "fecha_ingreso", "hora_ingreso",
                "fecha_salida", "hora_salida", "destino_despacho", "operator_code",
            )],
            filter_expr=f,
            top=1,
        )
        rows = (result or {}).get("value", [])
        return _row_to_camara_frio(rows[0], pallet_id) if rows else None

    def create(
        self,
        pallet_id: Any,
        *,
        operator_code: str = "",
        source_system: str = "dataverse",
        extra: Optional[dict] = None,
    ) -> CamaraFrioRecord:
        body: dict = {
            f"{CAMARA_FRIO_FIELDS['pallet_id']}@odata.bind": odata_bind(ENTITY_SET_PALLET, str(pallet_id)),
            CAMARA_FRIO_FIELDS["operator_code"]: operator_code,
        }
        _extra_map = {
            "camara_numero":      CAMARA_FRIO_FIELDS["camara_numero"],
            "temperatura_camara": CAMARA_FRIO_FIELDS["temperatura_camara"],
            "humedad_relativa":   CAMARA_FRIO_FIELDS["humedad_relativa"],
            "fecha_ingreso":      CAMARA_FRIO_FIELDS["fecha_ingreso"],
            "hora_ingreso":       CAMARA_FRIO_FIELDS["hora_ingreso"],
            "destino_despacho":   CAMARA_FRIO_FIELDS["destino_despacho"],
        }
        for domain_key, dv_field in _extra_map.items():
            v = (extra or {}).get(domain_key)
            if v not in (None, ""):
                body[dv_field] = v

        row = self._client.create_row(ENTITY_SET_CAMARA_FRIO, body) or {}
        return CamaraFrioRecord(
            id=row.get(CAMARA_FRIO_FIELDS["id"]),
            pallet_id=pallet_id,
            operator_code=operator_code,
            source_system=source_system,
        )

    def update(self, record_id: Any, fields: dict) -> CamaraFrioRecord:
        _updatable = {
            "fecha_salida":       CAMARA_FRIO_FIELDS["fecha_salida"],
            "hora_salida":        CAMARA_FRIO_FIELDS["hora_salida"],
            "temperatura_camara": CAMARA_FRIO_FIELDS["temperatura_camara"],
            "humedad_relativa":   CAMARA_FRIO_FIELDS["humedad_relativa"],
            "destino_despacho":   CAMARA_FRIO_FIELDS["destino_despacho"],
        }
        body = {dv_field: fields[k] for k, dv_field in _updatable.items() if k in fields}
        if body:
            self._client.update_row(ENTITY_SET_CAMARA_FRIO, str(record_id), body)
        return CamaraFrioRecord(id=record_id, pallet_id=None)


# ---------------------------------------------------------------------------
# MedicionTemperaturaSalidaRepository
# ---------------------------------------------------------------------------

class DataverseMedicionTemperaturaSalidaRepository(MedicionTemperaturaSalidaRepository):

    def __init__(self, client) -> None:
        self._client = client

    def create(
        self,
        pallet_id: Any,
        *,
        operator_code: str = "",
        source_system: str = "dataverse",
        extra: Optional[dict] = None,
    ) -> MedicionTemperaturaSalidaRecord:
        body: dict = {
            f"{MEDICION_TEMPERATURA_FIELDS['pallet_id']}@odata.bind": odata_bind(ENTITY_SET_PALLET, str(pallet_id)),
            MEDICION_TEMPERATURA_FIELDS["operator_code"]: operator_code,
        }
        _extra_map = {
            "fecha":              MEDICION_TEMPERATURA_FIELDS["fecha"],
            "hora":               MEDICION_TEMPERATURA_FIELDS["hora"],
            "temperatura_pallet": MEDICION_TEMPERATURA_FIELDS["temperatura_pallet"],
            "punto_medicion":     MEDICION_TEMPERATURA_FIELDS["punto_medicion"],
            "dentro_rango":       MEDICION_TEMPERATURA_FIELDS["dentro_rango"],
            "observaciones":      MEDICION_TEMPERATURA_FIELDS["observaciones"],
        }
        for domain_key, dv_field in _extra_map.items():
            v = (extra or {}).get(domain_key)
            if v not in (None, ""):
                body[dv_field] = v

        row = self._client.create_row(ENTITY_SET_MEDICION_TEMPERATURA, body) or {}
        dentro_rango = (extra or {}).get("dentro_rango")
        return MedicionTemperaturaSalidaRecord(
            id=row.get(MEDICION_TEMPERATURA_FIELDS["id"]),
            pallet_id=pallet_id,
            dentro_rango=dentro_rango,
            operator_code=operator_code,
            source_system=source_system,
        )

    def list_by_pallet(self, pallet_id: Any) -> list[MedicionTemperaturaSalidaRecord]:
        f = f"{MEDICION_TEMPERATURA_FIELDS['pallet_id_value']} eq {pallet_id}"
        result = self._client.list_rows(
            ENTITY_SET_MEDICION_TEMPERATURA,
            select=[MEDICION_TEMPERATURA_FIELDS[k] for k in (
                "id", "pallet_id_value", "fecha", "hora",
                "temperatura_pallet", "punto_medicion", "dentro_rango",
                "observaciones", "operator_code",
            )],
            filter_expr=f,
            orderby="createdon desc",
            top=100,
        )
        return [_row_to_medicion_temperatura(r, pallet_id) for r in (result or {}).get("value", [])]


# ---------------------------------------------------------------------------
# Resolver de etapa actual — fuente principal: campo persistido en Dataverse
# ---------------------------------------------------------------------------

def resolve_etapa_lote(lote, repos=None) -> str:
    """
    Retorna la etapa actual del lote como string display-friendly.

    Estrategia:
      1. Si el lote tiene etapa_actual persistida (no null), la retorna directamente.
         Este es el camino feliz para todos los lotes creados desde 2026-03-31.
      2. Si etapa_actual es null (registros anteriores a la integracion) y repos
         esta disponible, deriva la etapa consultando tablas de etapas en orden
         inverso (mas avanzada primero). Esto es costoso en Dataverse (multiples
         API calls) y NO debe usarse para listados bulk.
      3. Si repos es None o falla la derivacion, retorna 'Recepcion' como fallback
         conservador (los lotes sin etapa eran mayormente de recepcion).

    IMPORTANTE: para listados bulk (dashboard, consulta), llamar sin repos o con
    repos=None para evitar N*K llamadas a Dataverse.
    Para vista de detalle de un solo lote, pasar repos para derivacion completa.

    Args:
        lote: LoteRecord (Dataverse) o instancia ORM Lote (SQLite).
        repos: Repositories opcional para derivacion completa de fallback.

    Returns:
        str con la etapa (ej. "Recepcion", "Pesaje", "Desverdizado", etc.)
    """
    # Lote Dataverse con etapa_actual persistida
    etapa_persistida = getattr(lote, "etapa_actual", None)
    if etapa_persistida:
        return etapa_persistida

    # Fallback conservador sin repos (uso en bulk listings)
    if repos is None:
        return "Recepcion"

    # Derivacion completa para registros antiguos (uso en detalle individual)
    try:
        lote_id = lote.id
        # Orden inverso: etapa mas avanzada primero
        pl = repos.pallet_lotes.find_by_lote(lote_id)
        if pl:
            # Si hay pallet, verificar si tiene camara_frio
            try:
                cf = repos.camara_frios.find_by_pallet(pl.pallet_id)
                if cf:
                    return "Camara Frio"
            except Exception:
                pass
            return "Paletizado"

        ip = repos.ingresos_packing.find_by_lote(lote_id)
        if ip:
            # puede tener registros packing tambien
            return "Ingreso Packing"

        desv = repos.desverdizados.find_by_lote(lote_id)
        if desv:
            return "Desverdizado"

        cm = repos.camara_mantencions.find_by_lote(lote_id)
        if cm:
            return "Mantencion"

        # Sin registros de etapas avanzadas: Pesaje o Recepcion
        cantidad_bins = getattr(lote, "cantidad_bins", 0)
        if cantidad_bins and int(cantidad_bins) > 0:
            return "Pesaje"

        return "Recepcion"
    except Exception as exc:
        logger.debug("resolve_etapa_lote fallback error para lote %s: %s", getattr(lote, "id", "?"), exc)
        return "Recepcion"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Dataverse repositories — Planillas de Control de Calidad
# ---------------------------------------------------------------------------

def _parse_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_json_parse(value) -> list:
    """Deserializa JSON string a lista, con fallback a []."""
    import json
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except Exception:
        return []


def _row_to_planilla_desv_calibre(row: dict, lote_id: Any = None) -> PlanillaDesverdizadoCalibreRecord:
    import json
    grupos_raw = row.get(PLANILLA_DESV_CALIBRE_FIELDS["calibres_grupos"]) or "[]"
    return PlanillaDesverdizadoCalibreRecord(
        id=row.get(PLANILLA_DESV_CALIBRE_FIELDS["id"]),
        lote_id=lote_id or row.get(PLANILLA_DESV_CALIBRE_FIELDS["lote_id_value"]),
        supervisor=_str(row.get(PLANILLA_DESV_CALIBRE_FIELDS["supervisor"])),
        productor=_str(row.get(PLANILLA_DESV_CALIBRE_FIELDS["productor"])),
        variedad=_str(row.get(PLANILLA_DESV_CALIBRE_FIELDS["variedad"])),
        trazabilidad=_str(row.get(PLANILLA_DESV_CALIBRE_FIELDS["trazabilidad"])),
        cod_sdp=_str(row.get(PLANILLA_DESV_CALIBRE_FIELDS["cod_sdp"])),
        fecha_cosecha=_parse_date(row.get(PLANILLA_DESV_CALIBRE_FIELDS["fecha_cosecha"])),
        fecha_despacho=_parse_date(row.get(PLANILLA_DESV_CALIBRE_FIELDS["fecha_despacho"])),
        cuartel=_str(row.get(PLANILLA_DESV_CALIBRE_FIELDS["cuartel"])),
        sector=_str(row.get(PLANILLA_DESV_CALIBRE_FIELDS["sector"])),
        oleocelosis=_parse_int(row.get(PLANILLA_DESV_CALIBRE_FIELDS["oleocelosis"])),
        heridas_abiertas=_parse_int(row.get(PLANILLA_DESV_CALIBRE_FIELDS["heridas_abiertas"])),
        rugoso=_parse_int(row.get(PLANILLA_DESV_CALIBRE_FIELDS["rugoso"])),
        deforme=_parse_int(row.get(PLANILLA_DESV_CALIBRE_FIELDS["deforme"])),
        golpe_sol=_parse_int(row.get(PLANILLA_DESV_CALIBRE_FIELDS["golpe_sol"])),
        verdes=_parse_int(row.get(PLANILLA_DESV_CALIBRE_FIELDS["verdes"])),
        pre_calibre_defecto=_parse_int(row.get(PLANILLA_DESV_CALIBRE_FIELDS["pre_calibre_defecto"])),
        palo_largo=_parse_int(row.get(PLANILLA_DESV_CALIBRE_FIELDS["palo_largo"])),
        calibres_grupos_json=grupos_raw if isinstance(grupos_raw, str) else json.dumps(grupos_raw),
        observaciones=_str(row.get(PLANILLA_DESV_CALIBRE_FIELDS["observaciones"])),
        operator_code=_str(row.get(PLANILLA_DESV_CALIBRE_FIELDS["operator_code"])),
        source_system="dataverse",
    )


def _row_to_planilla_desv_semillas(row: dict, lote_id: Any = None) -> PlanillaDesverdizadoSemillasRecord:
    import json
    frutas_raw = row.get(PLANILLA_DESV_SEMILLAS_FIELDS["frutas_data"]) or "[]"
    return PlanillaDesverdizadoSemillasRecord(
        id=row.get(PLANILLA_DESV_SEMILLAS_FIELDS["id"]),
        lote_id=lote_id or row.get(PLANILLA_DESV_SEMILLAS_FIELDS["lote_id_value"]),
        fecha=_parse_date(row.get(PLANILLA_DESV_SEMILLAS_FIELDS["fecha"])),
        supervisor=_str(row.get(PLANILLA_DESV_SEMILLAS_FIELDS["supervisor"])),
        productor=_str(row.get(PLANILLA_DESV_SEMILLAS_FIELDS["productor"])),
        variedad=_str(row.get(PLANILLA_DESV_SEMILLAS_FIELDS["variedad"])),
        cuartel=_str(row.get(PLANILLA_DESV_SEMILLAS_FIELDS["cuartel"])),
        sector=_str(row.get(PLANILLA_DESV_SEMILLAS_FIELDS["sector"])),
        trazabilidad=_str(row.get(PLANILLA_DESV_SEMILLAS_FIELDS["trazabilidad"])),
        cod_sdp=_str(row.get(PLANILLA_DESV_SEMILLAS_FIELDS["cod_sdp"])),
        color=_str(row.get(PLANILLA_DESV_SEMILLAS_FIELDS["color"])),
        frutas_data_json=frutas_raw if isinstance(frutas_raw, str) else json.dumps(frutas_raw),
        total_frutos_muestra=_parse_int(row.get(PLANILLA_DESV_SEMILLAS_FIELDS["total_frutos_muestra"])),
        total_frutos_con_semillas=_parse_int(row.get(PLANILLA_DESV_SEMILLAS_FIELDS["total_frutos_con_semillas"])),
        total_semillas=_parse_int(row.get(PLANILLA_DESV_SEMILLAS_FIELDS["total_semillas"])),
        pct_frutos_con_semillas=_parse_decimal(row.get(PLANILLA_DESV_SEMILLAS_FIELDS["pct_frutos_con_semillas"])),
        promedio_semillas=_parse_decimal(row.get(PLANILLA_DESV_SEMILLAS_FIELDS["promedio_semillas"])),
        operator_code=_str(row.get(PLANILLA_DESV_SEMILLAS_FIELDS["operator_code"])),
        source_system="dataverse",
    )


def _row_to_planilla_calidad_packing(row: dict, pallet_id: Any = None) -> PlanillaCalidadPackingRecord:
    F = PLANILLA_CALIDAD_PACKING_FIELDS
    return PlanillaCalidadPackingRecord(
        id=row.get(F["id"]),
        pallet_id=pallet_id or row.get(F["pallet_id_value"]),
        productor=_str(row.get(F["productor"])),
        trazabilidad=_str(row.get(F["trazabilidad"])),
        cod_sdp=_str(row.get(F["cod_sdp"])),
        cuartel=_str(row.get(F["cuartel"])),
        sector=_str(row.get(F["sector"])),
        nombre_control=_str(row.get(F["nombre_control"])),
        n_cuadrilla=_str(row.get(F["n_cuadrilla"])),
        supervisor=_str(row.get(F["supervisor"])),
        fecha_despacho=_parse_date(row.get(F["fecha_despacho"])),
        fecha_cosecha=_parse_date(row.get(F["fecha_cosecha"])),
        numero_hoja=_parse_int(row.get(F["numero_hoja"])) or 1,
        tipo_fruta=_str(row.get(F["tipo_fruta"])),
        variedad=_str(row.get(F["variedad"])),
        temperatura=_parse_decimal(row.get(F["temperatura"])),
        humedad=_parse_decimal(row.get(F["humedad"])),
        horas_cosecha=_str(row.get(F["horas_cosecha"])),
        color=_str(row.get(F["color"])),
        n_frutos_muestreados=_parse_int(row.get(F["n_frutos_muestreados"])),
        brix=_parse_decimal(row.get(F["brix"])),
        pre_calibre=_parse_int(row.get(F["pre_calibre"])),
        sobre_calibre=_parse_int(row.get(F["sobre_calibre"])),
        color_contrario_evaluado=_parse_int(row.get(F["color_contrario_evaluado"])),
        cantidad_frutos=_parse_int(row.get(F["cantidad_frutos"])),
        ausencia_roseta=_parse_int(row.get(F["ausencia_roseta"])),
        deformes=_parse_int(row.get(F["deformes"])),
        frutos_con_semilla=_parse_int(row.get(F["frutos_con_semilla"])),
        n_semillas=_parse_int(row.get(F["n_semillas"])),
        fumagina=_parse_int(row.get(F["fumagina"])),
        h_cicatrizadas=_parse_int(row.get(F["h_cicatrizadas"])),
        manchas=_parse_int(row.get(F["manchas"])),
        peduculo_largo=_parse_int(row.get(F["peduculo_largo"])),
        residuos=_parse_int(row.get(F["residuos"])),
        rugosos=_parse_int(row.get(F["rugosos"])),
        russet_leve_claros=_parse_int(row.get(F["russet_leve_claros"])),
        russet_moderados_claros=_parse_int(row.get(F["russet_moderados_claros"])),
        russet_severos_oscuros=_parse_int(row.get(F["russet_severos_oscuros"])),
        creasing_leve=_parse_int(row.get(F["creasing_leve"])),
        creasing_mod_sev=_parse_int(row.get(F["creasing_mod_sev"])),
        dano_frio_granulados=_parse_int(row.get(F["dano_frio_granulados"])),
        bufado=_parse_int(row.get(F["bufado"])),
        deshidratacion_roseta=_parse_int(row.get(F["deshidratacion_roseta"])),
        golpe_sol=_parse_int(row.get(F["golpe_sol"])),
        h_abiertas_superior=_parse_int(row.get(F["h_abiertas_superior"])),
        h_abiertas_inferior=_parse_int(row.get(F["h_abiertas_inferior"])),
        acostillado=_parse_int(row.get(F["acostillado"])),
        machucon=_parse_int(row.get(F["machucon"])),
        blandos=_parse_int(row.get(F["blandos"])),
        oleocelosis=_parse_int(row.get(F["oleocelosis"])),
        ombligo_rasgado=_parse_int(row.get(F["ombligo_rasgado"])),
        colapso_corteza=_parse_int(row.get(F["colapso_corteza"])),
        pudricion=_parse_int(row.get(F["pudricion"])),
        dano_arana_leve=_parse_int(row.get(F["dano_arana_leve"])),
        dano_arana_moderado=_parse_int(row.get(F["dano_arana_moderado"])),
        dano_arana_severo=_parse_int(row.get(F["dano_arana_severo"])),
        dano_mecanico=_parse_int(row.get(F["dano_mecanico"])),
        otros_condicion=_str(row.get(F["otros_condicion"])),
        total_defectos_pct=_parse_decimal(row.get(F["total_defectos_pct"])),
        operator_code=_str(row.get(F["operator_code"])),
        source_system="dataverse",
    )


def _row_to_planilla_calidad_camara(row: dict, pallet_id: Any = None) -> PlanillaCalidadCamaraRecord:
    import json
    F = PLANILLA_CALIDAD_CAMARA_FIELDS
    meds_raw = row.get(F["mediciones"]) or "[]"
    return PlanillaCalidadCamaraRecord(
        id=row.get(F["id"]),
        pallet_id=pallet_id or row.get(F["pallet_id_value"]),
        fecha_control=_parse_date(row.get(F["fecha_control"])),
        tipo_proceso=_str(row.get(F["tipo_proceso"])),
        zona_planta=_str(row.get(F["zona_planta"])),
        tunel_camara=_str(row.get(F["tunel_camara"])),
        capacidad_maxima=_str(row.get(F["capacidad_maxima"])),
        temperatura_equipos=_str(row.get(F["temperatura_equipos"])),
        codigo_envases=_str(row.get(F["codigo_envases"])),
        cantidad_pallets=_parse_int(row.get(F["cantidad_pallets"])),
        especie=_str(row.get(F["especie"])),
        variedad=_str(row.get(F["variedad"])),
        fecha_embalaje=_parse_date(row.get(F["fecha_embalaje"])),
        estiba=_str(row.get(F["estiba"])),
        tipo_inversion=_str(row.get(F["tipo_inversion"])),
        mediciones_json=meds_raw if isinstance(meds_raw, str) else json.dumps(meds_raw),
        temp_pulpa_ext_inicio=_parse_decimal(row.get(F["temp_pulpa_ext_inicio"])),
        temp_pulpa_ext_termino=_parse_decimal(row.get(F["temp_pulpa_ext_termino"])),
        temp_pulpa_int_inicio=_parse_decimal(row.get(F["temp_pulpa_int_inicio"])),
        temp_pulpa_int_termino=_parse_decimal(row.get(F["temp_pulpa_int_termino"])),
        temp_ambiente_inicio=_parse_decimal(row.get(F["temp_ambiente_inicio"])),
        temp_ambiente_termino=_parse_decimal(row.get(F["temp_ambiente_termino"])),
        tiempo_carga_inicio=_str(row.get(F["tiempo_carga_inicio"])),
        tiempo_carga_termino=_str(row.get(F["tiempo_carga_termino"])),
        tiempo_descarga_inicio=_str(row.get(F["tiempo_descarga_inicio"])),
        tiempo_descarga_termino=_str(row.get(F["tiempo_descarga_termino"])),
        tiempo_enfriado_inicio=_str(row.get(F["tiempo_enfriado_inicio"])),
        tiempo_enfriado_termino=_str(row.get(F["tiempo_enfriado_termino"])),
        observaciones=_str(row.get(F["observaciones"])),
        nombre_control=_str(row.get(F["nombre_control"])),
        operator_code=_str(row.get(F["operator_code"])),
        source_system="dataverse",
    )


class DataversePlanillaDesverdizadoCalibreRepository(PlanillaDesverdizadoCalibreRepository):

    def __init__(self, client) -> None:
        self._client = client

    def create(self, lote_id: Any, *, operator_code: str = "",
               source_system: str = "dataverse", extra: Optional[dict] = None,
               ) -> PlanillaDesverdizadoCalibreRecord:
        import json
        F = PLANILLA_DESV_CALIBRE_FIELDS
        body: dict = {
            f"{F['lote_id']}@odata.bind": odata_bind(ENTITY_SET_LOTE, str(lote_id)),
            F["operator_code"]: operator_code,
        }
        _scalar_keys = [
            "supervisor", "productor", "variedad", "trazabilidad", "cod_sdp",
            "fecha_cosecha", "fecha_despacho", "cuartel", "sector",
            "oleocelosis", "heridas_abiertas", "rugoso", "deforme", "golpe_sol",
            "verdes", "pre_calibre_defecto", "palo_largo", "observaciones", "rol",
        ]
        for k in _scalar_keys:
            v = (extra or {}).get(k)
            if v not in (None, ""):
                body[F[k]] = str(v) if isinstance(v, (type(None),)) else v
        # JSON field
        grupos = (extra or {}).get("calibres_grupos")
        if grupos is not None:
            body[F["calibres_grupos"]] = json.dumps(grupos, ensure_ascii=False) if not isinstance(grupos, str) else grupos
        row = self._client.create_row(ENTITY_SET_PLANILLA_DESV_CALIBRE, body) or {}
        return PlanillaDesverdizadoCalibreRecord(
            id=row.get(F["id"]),
            lote_id=lote_id,
            operator_code=operator_code,
            source_system=source_system,
        )

    def list_by_lote(self, lote_id: Any) -> list[PlanillaDesverdizadoCalibreRecord]:
        F = PLANILLA_DESV_CALIBRE_FIELDS
        filt = f"{F['lote_id_value']} eq {lote_id}"
        result = self._client.list_rows(
            ENTITY_SET_PLANILLA_DESV_CALIBRE,
            select=[F[k] for k in ("id", "supervisor", "productor", "variedad",
                                   "fecha_cosecha", "fecha_despacho", "calibres_grupos",
                                   "oleocelosis", "heridas_abiertas", "rugoso", "deforme",
                                   "golpe_sol", "verdes", "observaciones", "operator_code")],
            filter_expr=filt,
            top=50,
        )
        return [_row_to_planilla_desv_calibre(r, lote_id) for r in (result or {}).get("value", [])]


class DataversePlanillaDesverdizadoSemillasRepository(PlanillaDesverdizadoSemillasRepository):

    def __init__(self, client) -> None:
        self._client = client

    def create(self, lote_id: Any, *, operator_code: str = "",
               source_system: str = "dataverse", extra: Optional[dict] = None,
               ) -> PlanillaDesverdizadoSemillasRecord:
        import json
        F = PLANILLA_DESV_SEMILLAS_FIELDS
        body: dict = {
            f"{F['lote_id']}@odata.bind": odata_bind(ENTITY_SET_LOTE, str(lote_id)),
            F["operator_code"]: operator_code,
        }
        _scalar_keys = [
            "fecha", "supervisor", "productor", "variedad", "cuartel", "sector",
            "trazabilidad", "cod_sdp", "color",
            "total_frutos_muestra", "total_frutos_con_semillas", "total_semillas",
            "pct_frutos_con_semillas", "promedio_semillas", "rol",
        ]
        for k in _scalar_keys:
            v = (extra or {}).get(k)
            if v not in (None, ""):
                body[F[k]] = v
        # JSON field
        frutas = (extra or {}).get("frutas_data")
        if frutas is not None:
            body[F["frutas_data"]] = json.dumps(frutas, ensure_ascii=False) if not isinstance(frutas, str) else frutas
        row = self._client.create_row(ENTITY_SET_PLANILLA_DESV_SEMILLAS, body) or {}
        return PlanillaDesverdizadoSemillasRecord(
            id=row.get(F["id"]),
            lote_id=lote_id,
            operator_code=operator_code,
            source_system=source_system,
        )

    def list_by_lote(self, lote_id: Any) -> list[PlanillaDesverdizadoSemillasRecord]:
        F = PLANILLA_DESV_SEMILLAS_FIELDS
        filt = f"{F['lote_id_value']} eq {lote_id}"
        result = self._client.list_rows(
            ENTITY_SET_PLANILLA_DESV_SEMILLAS,
            select=[F[k] for k in ("id", "fecha", "variedad", "frutas_data",
                                   "total_frutos_muestra", "total_semillas",
                                   "pct_frutos_con_semillas", "operator_code")],
            filter_expr=filt,
            top=50,
        )
        return [_row_to_planilla_desv_semillas(r, lote_id) for r in (result or {}).get("value", [])]


class DataversePlanillaCalidadPackingRepository(PlanillaCalidadPackingRepository):

    def __init__(self, client) -> None:
        self._client = client

    def create(self, pallet_id: Any, *, operator_code: str = "",
               source_system: str = "dataverse", extra: Optional[dict] = None,
               ) -> PlanillaCalidadPackingRecord:
        F = PLANILLA_CALIDAD_PACKING_FIELDS
        body: dict = {
            f"{F['pallet_id']}@odata.bind": odata_bind(ENTITY_SET_PALLET, str(pallet_id)),
            F["operator_code"]: operator_code,
        }
        _scalar_keys = [
            "productor", "trazabilidad", "cod_sdp", "cuartel", "sector",
            "nombre_control", "n_cuadrilla", "supervisor",
            "fecha_despacho", "fecha_cosecha", "numero_hoja", "tipo_fruta", "variedad",
            "temperatura", "humedad", "horas_cosecha", "color",
            "n_frutos_muestreados", "brix", "pre_calibre", "sobre_calibre",
            "color_contrario_evaluado", "cantidad_frutos", "ausencia_roseta", "deformes",
            "frutos_con_semilla", "n_semillas", "fumagina", "h_cicatrizadas", "manchas",
            "peduculo_largo", "residuos", "rugosos",
            "russet_leve_claros", "russet_moderados_claros", "russet_severos_oscuros",
            "creasing_leve", "creasing_mod_sev", "dano_frio_granulados", "bufado",
            "deshidratacion_roseta", "golpe_sol", "h_abiertas_superior", "h_abiertas_inferior",
            "acostillado", "machucon", "blandos", "oleocelosis", "ombligo_rasgado",
            "colapso_corteza", "pudricion",
            "dano_arana_leve", "dano_arana_moderado", "dano_arana_severo",
            "dano_mecanico", "otros_condicion", "total_defectos_pct", "rol",
        ]
        for k in _scalar_keys:
            v = (extra or {}).get(k)
            if v not in (None, ""):
                body[F[k]] = v
        row = self._client.create_row(ENTITY_SET_PLANILLA_CALIDAD_PACKING, body) or {}
        return PlanillaCalidadPackingRecord(
            id=row.get(F["id"]),
            pallet_id=pallet_id,
            operator_code=operator_code,
            source_system=source_system,
        )

    def list_by_pallet(self, pallet_id: Any) -> list[PlanillaCalidadPackingRecord]:
        F = PLANILLA_CALIDAD_PACKING_FIELDS
        filt = f"{F['pallet_id_value']} eq {pallet_id}"
        result = self._client.list_rows(
            ENTITY_SET_PLANILLA_CALIDAD_PACKING,
            select=[F[k] for k in ("id", "variedad", "numero_hoja", "brix",
                                   "total_defectos_pct", "operator_code")],
            filter_expr=filt,
            top=50,
        )
        return [_row_to_planilla_calidad_packing(r, pallet_id) for r in (result or {}).get("value", [])]


class DataversePlanillaCalidadCamaraRepository(PlanillaCalidadCamaraRepository):

    def __init__(self, client) -> None:
        self._client = client

    def create(self, pallet_id: Any, *, operator_code: str = "",
               source_system: str = "dataverse", extra: Optional[dict] = None,
               ) -> PlanillaCalidadCamaraRecord:
        import json
        F = PLANILLA_CALIDAD_CAMARA_FIELDS
        body: dict = {F["operator_code"]: operator_code}
        if pallet_id:
            body[f"{F['pallet_id']}@odata.bind"] = odata_bind(ENTITY_SET_PALLET, str(pallet_id))
        _scalar_keys = [
            "fecha_control", "tipo_proceso", "zona_planta", "tunel_camara",
            "capacidad_maxima", "temperatura_equipos", "codigo_envases", "cantidad_pallets",
            "especie", "variedad", "fecha_embalaje", "estiba", "tipo_inversion",
            "temp_pulpa_ext_inicio", "temp_pulpa_ext_termino",
            "temp_pulpa_int_inicio", "temp_pulpa_int_termino",
            "temp_ambiente_inicio", "temp_ambiente_termino",
            "tiempo_carga_inicio", "tiempo_carga_termino",
            "tiempo_descarga_inicio", "tiempo_descarga_termino",
            "tiempo_enfriado_inicio", "tiempo_enfriado_termino",
            "observaciones", "nombre_control", "rol",
        ]
        for k in _scalar_keys:
            v = (extra or {}).get(k)
            if v not in (None, ""):
                body[F[k]] = v
        # JSON field
        meds = (extra or {}).get("mediciones")
        if meds is not None:
            body[F["mediciones"]] = json.dumps(meds, ensure_ascii=False) if not isinstance(meds, str) else meds
        row = self._client.create_row(ENTITY_SET_PLANILLA_CALIDAD_CAMARA, body) or {}
        return PlanillaCalidadCamaraRecord(
            id=row.get(F["id"]),
            pallet_id=pallet_id,
            operator_code=operator_code,
            source_system=source_system,
        )

    def list_by_pallet(self, pallet_id: Any) -> list[PlanillaCalidadCamaraRecord]:
        F = PLANILLA_CALIDAD_CAMARA_FIELDS
        filt = f"{F['pallet_id_value']} eq {pallet_id}"
        result = self._client.list_rows(
            ENTITY_SET_PLANILLA_CALIDAD_CAMARA,
            select=[F[k] for k in ("id", "fecha_control", "tipo_proceso",
                                   "tunel_camara", "mediciones",
                                   "nombre_control", "operator_code")],
            filter_expr=filt,
            top=50,
        )
        return [_row_to_planilla_calidad_camara(r, pallet_id) for r in (result or {}).get("value", [])]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_dataverse_repositories() -> Repositories:
    from infrastructure.dataverse.client import DataverseClient
    client = DataverseClient()
    return Repositories(
        bins=DataverseBinRepository(client),
        lotes=DataverseLoteRepository(client),
        pallets=DataversePalletRepository(client),
        bin_lotes=DataverseBinLoteRepository(client),
        pallet_lotes=DataversePalletLoteRepository(client),
        registros=DataverseRegistroEtapaRepository(),
        sequences=DataverseSequenceCounterRepository(client),
        camara_mantencions=DataverseCamaraMantencionRepository(client),
        desverdizados=DataverseDesverdizadoRepository(client),
        calidad_desverdizados=DataverseCalidadDesverdizadoRepository(client),
        ingresos_packing=DataverseIngresoAPackingRepository(client),
        registros_packing=DataverseRegistroPackingRepository(client),
        control_proceso_packings=DataverseControlProcesoPackingRepository(client),
        calidad_pallets=DataverseCalidadPalletRepository(client),
        calidad_pallet_muestras=DataverseCalidadPalletMuestraRepository(client),
        camara_frios=DataverseCamaraFrioRepository(client),
        mediciones_temperatura=DataverseMedicionTemperaturaSalidaRepository(client),
        planillas_desv_calibres=DataversePlanillaDesverdizadoCalibreRepository(client),
        planillas_desv_semillas=DataversePlanillaDesverdizadoSemillasRepository(client),
        planillas_calidad_packing=DataversePlanillaCalidadPackingRepository(client),
        planillas_calidad_camara=DataversePlanillaCalidadCamaraRepository(client),
    )
