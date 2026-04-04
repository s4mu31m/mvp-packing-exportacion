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
        variedad_fruta=_str(row.get(BIN_FIELDS["variedad_fruta"])),
        kilos_bruto_ingreso=_parse_decimal(row.get(BIN_FIELDS["kilos_bruto_ingreso"])),
        kilos_neto_ingreso=_parse_decimal(row.get(BIN_FIELDS["kilos_neto_ingreso"])),
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
        cantidad_bins=int(row.get(LOTE_FIELDS["cantidad_bins"]) or 0),
        kilos_bruto_conformacion=_parse_decimal(row.get(LOTE_FIELDS["kilos_bruto_conformacion"])),
        kilos_neto_conformacion=_parse_decimal(row.get(LOTE_FIELDS["kilos_neto_conformacion"])),
        requiere_desverdizado=bool(row.get(LOTE_FIELDS["requiere_desverdizado"])),
        disponibilidad_camara_desverdizado=_str(row.get(LOTE_FIELDS["disponibilidad_camara_desverdizado"])) or None,
        # estado, temporada_codigo, correlativo_temporada no existen en Dataverse.
        # etapa_actual se lee desde crf21_etapa_actual; None si no ha sido escrito aún.
        estado="abierto",
        temporada_codigo="",
        correlativo_temporada=None,
        etapa_actual=_str(row.get(LOTE_FIELDS["etapa_actual"])) or None,
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
        fecha_ingreso=_parse_date(row.get(DESVERDIZADO_FIELDS["fecha_ingreso"])),
        hora_ingreso=_str(row.get(DESVERDIZADO_FIELDS["hora_ingreso"])),
        fecha_salida=_parse_date(row.get(DESVERDIZADO_FIELDS["fecha_salida"])),
        hora_salida=_str(row.get(DESVERDIZADO_FIELDS["hora_salida"])),
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
    return ControlProcesoPackingRecord(
        id=row.get(CONTROL_PROCESO_PACKING_FIELDS["id"]),
        lote_id=lote_id or row.get(CONTROL_PROCESO_PACKING_FIELDS["lote_id_value"]),
        fecha=_parse_date(row.get(CONTROL_PROCESO_PACKING_FIELDS["fecha"])),
        hora=_str(row.get(CONTROL_PROCESO_PACKING_FIELDS["hora"])),
        n_bins_procesados=row.get(CONTROL_PROCESO_PACKING_FIELDS["n_bins_procesados"]),
        temp_agua_tina=_parse_decimal(row.get(CONTROL_PROCESO_PACKING_FIELDS["temp_agua_tina"])),
        ph_agua=_parse_decimal(row.get(CONTROL_PROCESO_PACKING_FIELDS["ph_agua"])),
        recambio_agua=row.get(CONTROL_PROCESO_PACKING_FIELDS["recambio_agua"]),
        rendimiento_lote_pct=_parse_decimal(row.get(CONTROL_PROCESO_PACKING_FIELDS["rendimiento_lote_pct"])),
        observaciones_generales=_str(row.get(CONTROL_PROCESO_PACKING_FIELDS["observaciones_generales"])),
        operator_code=_str(row.get(CONTROL_PROCESO_PACKING_FIELDS["operator_code"])),
        source_system="dataverse",
        rol=_str(row.get(CONTROL_PROCESO_PACKING_FIELDS["rol"])),
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
    raw_n = row.get(CALIDAD_PALLET_MUESTRA_FIELDS["n_frutos"])
    return CalidadPalletMuestraRecord(
        id=row.get(CALIDAD_PALLET_MUESTRA_FIELDS["id"]),
        pallet_id=pallet_id or row.get(CALIDAD_PALLET_MUESTRA_FIELDS["pallet_id_value"]),
        numero_muestra=int(raw_n) if raw_n is not None else None,
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
    "source_event_id", "variedad_fruta", "kilos_bruto_ingreso", "kilos_neto_ingreso",
)]
_LOTE_SELECT = [LOTE_FIELDS[k] for k in (
    "id", "id_lote_planta", "lote_code", "operator_code", "source_system",
    "source_event_id", "cantidad_bins", "kilos_bruto_conformacion",
    "kilos_neto_conformacion", "requiere_desverdizado",
    "disponibilidad_camara_desverdizado", "etapa_actual",
)]
_BIN_LOTE_SELECT = [BIN_LOTE_FIELDS[k] for k in ("id", "bin_id_value", "lote_id_value")]


# ---------------------------------------------------------------------------
# BinRepository
# ---------------------------------------------------------------------------

class DataverseBinRepository(BinRepository):

    def __init__(self, client) -> None:
        self._client = client

    def find_by_code(self, temporada: str, bin_code: str) -> Optional[BinRecord]:
        # temporada no existe en Dataverse; filtramos solo por bin_code
        f = f"{BIN_FIELDS['bin_code']} eq '{bin_code}'"
        result = self._client.list_rows(
            ENTITY_SET_BIN,
            select=_BIN_SELECT,
            filter_expr=f,
            top=1,
        )
        rows = (result or {}).get("value", [])
        return _row_to_bin(rows[0]) if rows else None

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
        codes_filter = " or ".join(
            f"{BIN_FIELDS['bin_code']} eq '{c}'" for c in bin_codes
        )
        result = self._client.list_rows(
            ENTITY_SET_BIN,
            select=_BIN_SELECT,
            filter_expr=f"({codes_filter})",
            top=len(bin_codes) + 10,
        )
        return [_row_to_bin(r) for r in (result or {}).get("value", [])]

    def list_by_lote(self, lote_id: Any) -> list[BinRecord]:
        """
        Obtiene los bins de un lote consultando primero la tabla de union
        crf21_bin_lote_plantas por lote, luego resolviendo los bins por sus IDs.

        Estrategia de dos pasos:
          1. crf21_bin_lote_plantas filtrado por _crf21_lote_planta_id_value = lote_id
          2. crf21_bins filtrado por los bin_ids obtenidos
        """
        # Paso 1: obtener bin_ids asociados al lote
        f = f"{BIN_LOTE_FIELDS['lote_id_value']} eq {lote_id}"
        result = self._client.list_rows(
            ENTITY_SET_BIN_LOTE,
            select=[BIN_LOTE_FIELDS["bin_id_value"]],
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


# ---------------------------------------------------------------------------
# LoteRepository
# ---------------------------------------------------------------------------

class DataverseLoteRepository(LoteRepository):

    def __init__(self, client) -> None:
        self._client = client

    def find_by_code(self, temporada: str, lote_code: str) -> Optional[LoteRecord]:
        # lote_code se almacena en crf21_id_lote_planta
        f = f"{LOTE_FIELDS['lote_code']} eq '{lote_code}'"
        result = self._client.list_rows(
            ENTITY_SET_LOTE,
            select=_LOTE_SELECT,
            filter_expr=f,
            top=1,
        )
        rows = (result or {}).get("value", [])
        if not rows:
            return None
        record = _row_to_lote(rows[0])
        record.temporada = temporada
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

        row = self._client.create_row(ENTITY_SET_LOTE, body) or {}
        return LoteRecord(
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
        )

    def filter_by_codes(self, temporada: str, lote_codes: list[str]) -> list[LoteRecord]:
        if not lote_codes:
            return []
        codes_filter = " or ".join(
            f"{LOTE_FIELDS['lote_code']} eq '{c}'" for c in lote_codes
        )
        result = self._client.list_rows(
            ENTITY_SET_LOTE,
            select=_LOTE_SELECT,
            filter_expr=f"({codes_filter})",
            top=len(lote_codes) + 10,
        )
        records = [_row_to_lote(r) for r in (result or {}).get("value", [])]
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
        }
        body = {
            dv_field: fields[domain_key]
            for domain_key, dv_field in _updatable.items()
            if domain_key in fields
        }
        # Campos no soportados en Dataverse: estado, temporada_codigo,
        # correlativo_temporada — se ignoran silenciosamente.
        if body:
            self._client.update_row(ENTITY_SET_LOTE, str(lote_id), body)

        # Recuperar registro actualizado
        result = self._client.list_rows(
            ENTITY_SET_LOTE,
            select=_LOTE_SELECT,
            filter_expr=f"{LOTE_FIELDS['id']} eq {lote_id}",
            top=1,
        )
        rows = (result or {}).get("value", [])
        return _row_to_lote(rows[0]) if rows else LoteRecord(
            id=lote_id, temporada="", lote_code="",
        )

    def list_recent(self, limit: int = 50) -> list[LoteRecord]:
        """
        Retorna los lotes mas recientes ordenados por fecha de creacion descendente.
        Usado por DashboardView en modo Dataverse para mostrar KPIs reales.
        temporada no existe en Dataverse: se retorna temporada="" en todos los records.
        """
        result = self._client.list_rows(
            ENTITY_SET_LOTE,
            select=_LOTE_SELECT,
            orderby="createdon desc",
            top=limit,
        )
        return [_row_to_lote(r) for r in (result or {}).get("value", [])]


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
            select=[PALLET_FIELDS[k] for k in ("id", "id_pallet", "pallet_code", "operator_code", "fecha")],
            filter_expr=f,
            top=1,
        )
        rows = (result or {}).get("value", [])
        if not rows:
            return None
        record = _row_to_pallet(rows[0])
        record.temporada = temporada
        return record

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
        for domain_key in ("fecha", "tipo_caja", "cajas_por_pallet", "peso_total_kg", "destino_mercado"):
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
                f"{LOTE_FIELDS['fecha_conformacion']} ge {start}"
                f" and {LOTE_FIELDS['fecha_conformacion']} le {end}"
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
            filter_expr=f"{PALLET_FIELDS['fecha']} ge {start} and {PALLET_FIELDS['fecha']} lt {end}",
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
                "id", "lote_id_value", "fecha_ingreso", "hora_ingreso",
                "fecha_salida", "hora_salida", "kilos_enviados_terreno",
                "kilos_recepcionados", "kilos_bruto_salida", "kilos_neto_salida",
                "color_salida", "proceso", "operator_code",
            )],
            filter_expr=f,
            top=1,
        )
        rows = (result or {}).get("value", [])
        return _row_to_desverdizado(rows[0], lote_id) if rows else None

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
            "fecha_ingreso":          DESVERDIZADO_FIELDS["fecha_ingreso"],
            "hora_ingreso":           DESVERDIZADO_FIELDS["hora_ingreso"],
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
                "linea_proceso", "categoria_calidad", "calibre",
                "cantidad_cajas_producidas", "operator_code",
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
        _extra_map = {
            "fecha":                  CONTROL_PROCESO_PACKING_FIELDS["fecha"],
            "hora":                   CONTROL_PROCESO_PACKING_FIELDS["hora"],
            "n_bins_procesados":      CONTROL_PROCESO_PACKING_FIELDS["n_bins_procesados"],
            "temp_agua_tina":         CONTROL_PROCESO_PACKING_FIELDS["temp_agua_tina"],
            "ph_agua":                CONTROL_PROCESO_PACKING_FIELDS["ph_agua"],
            "recambio_agua":          CONTROL_PROCESO_PACKING_FIELDS["recambio_agua"],
            "rendimiento_lote_pct":   CONTROL_PROCESO_PACKING_FIELDS["rendimiento_lote_pct"],
            "observaciones_generales":CONTROL_PROCESO_PACKING_FIELDS["observaciones_generales"],
        }
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
                "id", "lote_id_value", "fecha", "hora",
                "n_bins_procesados", "temp_agua_tina", "ph_agua", "operator_code",
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
                "temperatura_fruta", "aprobado", "observaciones", "operator_code",
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
    )
