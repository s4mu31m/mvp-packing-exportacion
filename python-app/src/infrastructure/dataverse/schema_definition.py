"""
Definicion del esquema Dataverse requerido para el funcionamiento completo de la app.

Esta es la FUENTE UNICA DE VERDAD para:
  - El management command ``dataverse_ensure_schema`` (verifica y crea tablas/campos).
  - La suite de smoke tests ``test_schema_validation.py``.

Las entidades marcadas con ``is_new=True`` son las 4 planillas de control de calidad
agregadas en el commit 896f419. Pueden no existir aun en el entorno Dataverse.

Los campos de lectura OData (prefijados con ``_``, ej: ``_crf21_pallet_id_value``)
NO son Attributes reales de Dataverse y estan excluidos de esta definicion.

Nomenclatura Dataverse:
  - ``logical_name``: nombre logico de la entidad (ej: ``crf21_planilla_desv_calibre``).
  - ``entity_set_name``: nombre del entity set OData (ej: ``crf21_planilla_desv_calibres``).
  - ``schema_name``: SchemaName PascalCase requerido por la Metadata API.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


FieldType = Literal["String", "Memo", "Integer", "Decimal", "Boolean", "DateTime", "Lookup"]


@dataclass
class FieldSpec:
    logical_name: str
    schema_name: str
    display_label: str
    field_type: FieldType
    # Para String
    max_length: int = 500
    # Para Memo
    max_length_memo: int = 4000
    # Para Decimal
    precision: int = 2
    min_value_decimal: float = -999999.0
    max_value_decimal: float = 999999.0
    # Para Integer
    min_value_int: int = 0
    max_value_int: int = 9999999
    # Para Lookup
    lookup_target_entity: str = ""          # logical_name de la entidad referenciada
    lookup_relationship_schema: str = ""    # SchemaName de la relacion


@dataclass
class EntitySpec:
    logical_name: str
    entity_set_name: str
    schema_name: str
    display_label: str
    display_collection_label: str
    fields: list[FieldSpec] = field(default_factory=list)
    is_new: bool = False    # True → puede no existir aun en Dataverse


# ---------------------------------------------------------------------------
# Helpers para construir FieldSpec de forma concisa
# ---------------------------------------------------------------------------

def _str(logical: str, label: str, max_length: int = 500) -> FieldSpec:
    schema = "crf21_" + logical.removeprefix("crf21_").replace("_", "_").capitalize()
    # Reconstruimos el schema_name de forma simple
    parts = logical.removeprefix("crf21_").split("_")
    schema = "crf21_" + "".join(p.capitalize() for p in parts)
    return FieldSpec(logical, schema, label, "String", max_length=max_length)


def _memo(logical: str, label: str, max_length: int = 4000) -> FieldSpec:
    parts = logical.removeprefix("crf21_").split("_")
    schema = "crf21_" + "".join(p.capitalize() for p in parts)
    return FieldSpec(logical, schema, label, "Memo", max_length_memo=max_length)


def _dec(logical: str, label: str, precision: int = 2,
         min_val: float = -999999.0, max_val: float = 999999.0) -> FieldSpec:
    parts = logical.removeprefix("crf21_").split("_")
    schema = "crf21_" + "".join(p.capitalize() for p in parts)
    return FieldSpec(logical, schema, label, "Decimal", precision=precision,
                     min_value_decimal=min_val, max_value_decimal=max_val)


def _int(logical: str, label: str, min_val: int = 0, max_val: int = 9999999) -> FieldSpec:
    parts = logical.removeprefix("crf21_").split("_")
    schema = "crf21_" + "".join(p.capitalize() for p in parts)
    return FieldSpec(logical, schema, label, "Integer",
                     min_value_int=min_val, max_value_int=max_val)


def _bool(logical: str, label: str) -> FieldSpec:
    parts = logical.removeprefix("crf21_").split("_")
    schema = "crf21_" + "".join(p.capitalize() for p in parts)
    return FieldSpec(logical, schema, label, "Boolean")


def _dt(logical: str, label: str) -> FieldSpec:
    parts = logical.removeprefix("crf21_").split("_")
    schema = "crf21_" + "".join(p.capitalize() for p in parts)
    return FieldSpec(logical, schema, label, "DateTime")


def _lookup(logical: str, label: str, target_entity: str, relationship_schema: str) -> FieldSpec:
    parts = logical.removeprefix("crf21_").split("_")
    schema = "crf21_" + "".join(p.capitalize() for p in parts)
    return FieldSpec(logical, schema, label, "Lookup",
                     lookup_target_entity=target_entity,
                     lookup_relationship_schema=relationship_schema)


# ---------------------------------------------------------------------------
# Campos comunes reutilizables
# ---------------------------------------------------------------------------

def _common_control_fields() -> list[FieldSpec]:
    """Campos de control presentes en la mayoria de entidades operativas."""
    return [
        _str("crf21_rol", "Rol", max_length=100),
        _str("crf21_operator_code", "Codigo Operador", max_length=50),
        _str("crf21_source_system", "Sistema Origen", max_length=100),
        _str("crf21_source_event_id", "ID Evento Origen", max_length=200),
    ]


# ---------------------------------------------------------------------------
# REQUIRED_SCHEMA: las 20 entidades Dataverse necesarias
# ---------------------------------------------------------------------------

REQUIRED_SCHEMA: list[EntitySpec] = [

    # -----------------------------------------------------------------------
    # 1. crf21_bin — Bins operativos
    # -----------------------------------------------------------------------
    EntitySpec(
        logical_name="crf21_bin",
        entity_set_name="crf21_bins",
        schema_name="crf21_bin",
        display_label="Bin",
        display_collection_label="Bins",
        fields=[
            _str("crf21_id_bin", "ID Bin", max_length=100),
            _str("crf21_bin_code", "Codigo Bin", max_length=100),
            _dt("crf21_fecha_cosecha", "Fecha Cosecha"),
            _str("crf21_codigo_productor", "Codigo Productor", max_length=100),
            _str("crf21_nombre_productor", "Nombre Productor", max_length=200),
            _str("crf21_tipo_cultivo", "Tipo Cultivo", max_length=100),
            _str("crf21_variedad_fruta", "Variedad Fruta", max_length=100),
            _str("crf21_color", "Color", max_length=50),
            _dec("crf21_kilos_bruto_ingreso", "Kilos Bruto Ingreso", min_val=0, max_val=99999),
            _dec("crf21_kilos_neto_ingreso", "Kilos Neto Ingreso", min_val=0, max_val=99999),
            _str("crf21_numero_cuartel", "Numero Cuartel", max_length=100),
            _str("crf21_nombre_cuartel", "Nombre Cuartel", max_length=200),
            _str("crf21_sector", "Sector", max_length=100),
            _str("crf21_hora_recepcion", "Hora Recepcion", max_length=10),
            _memo("crf21_observaciones", "Observaciones"),
            *_common_control_fields(),
        ],
    ),

    # -----------------------------------------------------------------------
    # 2. crf21_lote_planta — Lotes de planta
    # -----------------------------------------------------------------------
    EntitySpec(
        logical_name="crf21_lote_planta",
        entity_set_name="crf21_lote_plantas",
        schema_name="crf21_lote_planta",
        display_label="Lote Planta",
        display_collection_label="Lotes Planta",
        fields=[
            _str("crf21_id_lote_planta", "ID Lote Planta", max_length=100),
            _int("crf21_cantidad_bins", "Cantidad Bins", min_val=0, max_val=9999),
            _dec("crf21_kilos_bruto_conformacion", "Kilos Bruto Conformacion", min_val=0, max_val=999999),
            _dec("crf21_kilos_neto_conformacion", "Kilos Neto Conformacion", min_val=0, max_val=999999),
            _bool("crf21_requiere_desverdizado", "Requiere Desverdizado"),
            _str("crf21_disponibilidad_camara_desverdizado", "Disponibilidad Camara Desverdizado", max_length=50),
            _str("crf21_etapa_actual", "Etapa Actual", max_length=100),
            _str("crf21_codigo_productor", "Codigo Productor", max_length=100),
            *_common_control_fields(),
        ],
    ),

    # -----------------------------------------------------------------------
    # 3. crf21_pallet — Pallets
    # -----------------------------------------------------------------------
    EntitySpec(
        logical_name="crf21_pallet",
        entity_set_name="crf21_pallets",
        schema_name="crf21_pallet",
        display_label="Pallet",
        display_collection_label="Pallets",
        fields=[
            _str("crf21_id_pallet", "ID Pallet", max_length=100),
            _str("crf21_fecha", "Fecha", max_length=20),
            _str("crf21_hora", "Hora", max_length=10),
            _str("crf21_tipo_caja", "Tipo Caja", max_length=100),
            _int("crf21_cajas_por_pallet", "Cajas por Pallet", min_val=0, max_val=9999),
            _dec("crf21_peso_total_kg", "Peso Total Kg", min_val=0, max_val=999999),
            _str("crf21_destino_mercado", "Destino Mercado", max_length=100),
            *_common_control_fields(),
        ],
    ),

    # -----------------------------------------------------------------------
    # 4. crf21_bin_lote_planta — Junction bins ↔ lotes
    # -----------------------------------------------------------------------
    EntitySpec(
        logical_name="crf21_bin_lote_planta",
        entity_set_name="crf21_bin_lote_plantas",
        schema_name="crf21_bin_lote_planta",
        display_label="Bin Lote Planta",
        display_collection_label="Bin Lote Plantas",
        fields=[
            _lookup("crf21_bin_id", "Bin", "crf21_bin", "crf21_bin_bin_lote_plantas"),
            _lookup("crf21_lote_planta_id", "Lote Planta", "crf21_lote_planta",
                    "crf21_lote_planta_bin_lote_plantas"),
        ],
    ),

    # -----------------------------------------------------------------------
    # 5. crf21_lote_planta_pallet — Junction lotes ↔ pallets
    # -----------------------------------------------------------------------
    EntitySpec(
        logical_name="crf21_lote_planta_pallet",
        entity_set_name="crf21_lote_planta_pallets",
        schema_name="crf21_lote_planta_pallet",
        display_label="Lote Planta Pallet",
        display_collection_label="Lote Planta Pallets",
        fields=[
            _lookup("crf21_pallet_id", "Pallet", "crf21_pallet",
                    "crf21_pallet_lote_planta_pallets"),
            _lookup("crf21_lote_planta_id", "Lote Planta", "crf21_lote_planta",
                    "crf21_lote_planta_lote_planta_pallets"),
        ],
    ),

    # -----------------------------------------------------------------------
    # 6. crf21_camara_mantencion — Camara mantencion
    # -----------------------------------------------------------------------
    EntitySpec(
        logical_name="crf21_camara_mantencion",
        entity_set_name="crf21_camara_mantencions",
        schema_name="crf21_camara_mantencion",
        display_label="Camara Mantencion",
        display_collection_label="Camara Mantenciones",
        fields=[
            _lookup("crf21_lote_planta_id", "Lote Planta", "crf21_lote_planta",
                    "crf21_lote_planta_camara_mantencions"),
            _str("crf21_camara_numero", "Numero Camara", max_length=50),
            _str("crf21_fecha_ingreso", "Fecha Ingreso", max_length=20),
            _str("crf21_hora_ingreso", "Hora Ingreso", max_length=10),
            _str("crf21_fecha_salida", "Fecha Salida", max_length=20),
            _str("crf21_hora_salida", "Hora Salida", max_length=10),
            _dec("crf21_temperatura_camara", "Temperatura Camara"),
            _dec("crf21_humedad_relativa", "Humedad Relativa", min_val=0, max_val=100),
            _memo("crf21_observaciones", "Observaciones"),
            *_common_control_fields(),
        ],
    ),

    # -----------------------------------------------------------------------
    # 7. crf21_desverdizado — Proceso de desverdizado
    # -----------------------------------------------------------------------
    EntitySpec(
        logical_name="crf21_desverdizado",
        entity_set_name="crf21_desverdizados",
        schema_name="crf21_desverdizado",
        display_label="Desverdizado",
        display_collection_label="Desverdizados",
        fields=[
            _lookup("crf21_lote_planta_id", "Lote Planta", "crf21_lote_planta",
                    "crf21_lote_planta_desverdizados"),
            _str("crf21_fecha_ingreso", "Fecha Ingreso", max_length=20),
            _str("crf21_hora_ingreso", "Hora Ingreso", max_length=10),
            _str("crf21_color_salida", "Color Salida", max_length=50),
            _str("crf21_proceso", "Proceso (horas desverdizado)", max_length=200),
            _dec("crf21_kilos_neto_salida", "Kilos Neto Salida", min_val=0, max_val=999999),
            _dec("crf21_kilos_bruto_salida", "Kilos Bruto Salida", min_val=0, max_val=999999),
            *_common_control_fields(),
        ],
    ),

    # -----------------------------------------------------------------------
    # 8. crf21_calidad_desverdizado — Calidad en desverdizado
    # -----------------------------------------------------------------------
    EntitySpec(
        logical_name="crf21_calidad_desverdizado",
        entity_set_name="crf21_calidad_desverdizados",
        schema_name="crf21_calidad_desverdizado",
        display_label="Calidad Desverdizado",
        display_collection_label="Calidad Desverdizados",
        fields=[
            _lookup("crf21_lote_planta_id", "Lote Planta", "crf21_lote_planta",
                    "crf21_lote_planta_calidad_desverdizados"),
            _str("crf21_fecha", "Fecha", max_length=20),
            _str("crf21_hora", "Hora", max_length=10),
            _dec("crf21_temperatura_fruta", "Temperatura Fruta"),
            _str("crf21_color_evaluado", "Color Evaluado", max_length=50),
            _str("crf21_estado_visual", "Estado Visual", max_length=100),
            _bool("crf21_presencia_defectos", "Presencia Defectos"),
            _bool("crf21_aprobado", "Aprobado"),
            _memo("crf21_observaciones", "Observaciones"),
            *_common_control_fields(),
        ],
    ),

    # -----------------------------------------------------------------------
    # 9. crf21_ingreso_packing — Ingreso a packing
    # -----------------------------------------------------------------------
    EntitySpec(
        logical_name="crf21_ingreso_packing",
        entity_set_name="crf21_ingreso_packings",
        schema_name="crf21_ingreso_packing",
        display_label="Ingreso Packing",
        display_collection_label="Ingresos Packing",
        fields=[
            _lookup("crf21_lote_planta_id", "Lote Planta", "crf21_lote_planta",
                    "crf21_lote_planta_ingreso_packings"),
            _str("crf21_fecha_ingreso", "Fecha Ingreso", max_length=20),
            _str("crf21_hora_ingreso", "Hora Ingreso", max_length=10),
            _dec("crf21_kilos_bruto_ingreso_packing", "Kilos Bruto Ingreso Packing",
                 min_val=0, max_val=999999),
            _dec("crf21_kilos_neto_ingreso_packing", "Kilos Neto Ingreso Packing",
                 min_val=0, max_val=999999),
            _bool("crf21_via_desverdizado", "Via Desverdizado"),
            _memo("crf21_observaciones", "Observaciones"),
            *_common_control_fields(),
        ],
    ),

    # -----------------------------------------------------------------------
    # 10. crf21_registro_packing — Registro proceso packing
    # -----------------------------------------------------------------------
    EntitySpec(
        logical_name="crf21_registro_packing",
        entity_set_name="crf21_registro_packings",
        schema_name="crf21_registro_packing",
        display_label="Registro Packing",
        display_collection_label="Registros Packing",
        fields=[
            _lookup("crf21_lote_planta_id", "Lote Planta", "crf21_lote_planta",
                    "crf21_lote_planta_registro_packings"),
            _str("crf21_fecha", "Fecha", max_length=20),
            _str("crf21_hora_inicio", "Hora Inicio", max_length=10),
            _str("crf21_linea_proceso", "Linea Proceso", max_length=50),
            _str("crf21_categoria_calidad", "Categoria Calidad", max_length=50),
            _str("crf21_calibre", "Calibre", max_length=50),
            _str("crf21_tipo_envase", "Tipo Envase", max_length=100),
            _int("crf21_cantidad_cajas_producidas", "Cantidad Cajas Producidas",
                 min_val=0, max_val=999999),
            _dec("crf21_merma_seleccion_pct", "Merma Seleccion Pct", min_val=0, max_val=100),
            *_common_control_fields(),
        ],
    ),

    # -----------------------------------------------------------------------
    # 11. crf21_control_proceso_packing — Control del proceso de packing
    # -----------------------------------------------------------------------
    EntitySpec(
        logical_name="crf21_control_proceso_packing",
        entity_set_name="crf21_control_proceso_packings",
        schema_name="crf21_control_proceso_packing",
        display_label="Control Proceso Packing",
        display_collection_label="Control Proceso Packings",
        fields=[
            _lookup("crf21_lote_planta_id", "Lote Planta", "crf21_lote_planta",
                    "crf21_lote_planta_control_proceso_packings"),
            _str("crf21_fecha", "Fecha", max_length=20),
            _str("crf21_hora", "Hora", max_length=10),
            _int("crf21_n_bins_procesados", "N Bins Procesados", min_val=0, max_val=9999),
            _dec("crf21_temp_agua_tina", "Temperatura Agua Tina"),
            _dec("crf21_ph_agua", "pH Agua", precision=1, min_val=0, max_val=14),
            _bool("crf21_recambio_agua", "Recambio Agua"),
            _dec("crf21_rendimiento_lote_pct", "Rendimiento Lote Pct", min_val=0, max_val=100),
            _memo("crf21_observaciones_generales", "Observaciones Generales"),
            *_common_control_fields(),
        ],
    ),

    # -----------------------------------------------------------------------
    # 12. crf21_calidad_pallet — Calidad del pallet
    # -----------------------------------------------------------------------
    EntitySpec(
        logical_name="crf21_calidad_pallet",
        entity_set_name="crf21_calidad_pallets",
        schema_name="crf21_calidad_pallet",
        display_label="Calidad Pallet",
        display_collection_label="Calidad Pallets",
        fields=[
            _lookup("crf21_pallet_id", "Pallet", "crf21_pallet",
                    "crf21_pallet_calidad_pallets"),
            _str("crf21_fecha", "Fecha", max_length=20),
            _str("crf21_hora", "Hora", max_length=10),
            _dec("crf21_temperatura_fruta", "Temperatura Fruta"),
            _dec("crf21_peso_caja_muestra", "Peso Caja Muestra", precision=3,
                 min_val=0, max_val=99999),
            _str("crf21_estado_visual_fruta", "Estado Visual Fruta", max_length=100),
            _bool("crf21_aprobado", "Aprobado"),
            _memo("crf21_observaciones", "Observaciones"),
            *_common_control_fields(),
        ],
    ),

    # -----------------------------------------------------------------------
    # 13. crf21_calidad_pallet_muestra — Muestras individuales de calidad pallet
    # -----------------------------------------------------------------------
    EntitySpec(
        logical_name="crf21_calidad_pallet_muestra",
        entity_set_name="crf21_calidad_pallet_muestras",
        schema_name="crf21_calidad_pallet_muestra",
        display_label="Calidad Pallet Muestra",
        display_collection_label="Calidad Pallet Muestras",
        fields=[
            _lookup("crf21_pallet_id", "Pallet", "crf21_pallet",
                    "crf21_pallet_calidad_pallet_muestras"),
            _int("crf21_numero_muestra", "Numero Muestra", min_val=1, max_val=10),
            _dec("crf21_temperatura_fruta", "Temperatura Fruta"),
            _dec("crf21_peso_caja_muestra", "Peso Caja Muestra", precision=3,
                 min_val=0, max_val=99999),
            _int("crf21_n_frutos", "N Frutos", min_val=0, max_val=9999),
            _bool("crf21_aprobado", "Aprobado"),
            _memo("crf21_observaciones", "Observaciones"),
            *_common_control_fields(),
        ],
    ),

    # -----------------------------------------------------------------------
    # 14. crf21_camara_frio — Ingreso a camara de frio
    # -----------------------------------------------------------------------
    EntitySpec(
        logical_name="crf21_camara_frio",
        entity_set_name="crf21_camara_frios",
        schema_name="crf21_camara_frio",
        display_label="Camara Frio",
        display_collection_label="Camara Frios",
        fields=[
            _lookup("crf21_pallet_id", "Pallet", "crf21_pallet",
                    "crf21_pallet_camara_frios"),
            _str("crf21_camara_numero", "Numero Camara", max_length=50),
            _dec("crf21_temperatura_camara", "Temperatura Camara"),
            _dec("crf21_humedad_relativa", "Humedad Relativa", min_val=0, max_val=100),
            _str("crf21_fecha_ingreso", "Fecha Ingreso", max_length=20),
            _str("crf21_hora_ingreso", "Hora Ingreso", max_length=10),
            _str("crf21_destino_despacho", "Destino Despacho", max_length=200),
            *_common_control_fields(),
        ],
    ),

    # -----------------------------------------------------------------------
    # 15. crf21_medicion_temperatura_salida — Medicion temperatura salida
    # -----------------------------------------------------------------------
    EntitySpec(
        logical_name="crf21_medicion_temperatura_salida",
        entity_set_name="crf21_medicion_temperatura_salidas",
        schema_name="crf21_medicion_temperatura_salida",
        display_label="Medicion Temperatura Salida",
        display_collection_label="Mediciones Temperatura Salida",
        fields=[
            _lookup("crf21_pallet_id", "Pallet", "crf21_pallet",
                    "crf21_pallet_medicion_temperatura_salidas"),
            _str("crf21_fecha", "Fecha", max_length=20),
            _str("crf21_hora", "Hora", max_length=10),
            _dec("crf21_temperatura_pallet", "Temperatura Pallet"),
            _str("crf21_punto_medicion", "Punto Medicion", max_length=100),
            _bool("crf21_dentro_rango", "Dentro Rango"),
            _memo("crf21_observaciones", "Observaciones"),
            *_common_control_fields(),
        ],
    ),

    # -----------------------------------------------------------------------
    # 16. crf21_usuariooperativo — Usuarios operativos
    # -----------------------------------------------------------------------
    EntitySpec(
        logical_name="crf21_usuariooperativo",
        entity_set_name="crf21_usuariooperativos",
        schema_name="crf21_usuariooperativo",
        display_label="Usuario Operativo",
        display_collection_label="Usuarios Operativos",
        fields=[
            _str("crf21_usernamelogin", "Username Login", max_length=150),
            _str("crf21_nombrecompleto", "Nombre Completo", max_length=200),
            _str("crf21_correo", "Correo", max_length=254),
            _str("crf21_rol", "Rol", max_length=100),
            _bool("crf21_activo", "Activo"),
            _bool("crf21_bloqueado", "Bloqueado"),
            _str("crf21_codigooperador", "Codigo Operador", max_length=50),
        ],
    ),

    # -----------------------------------------------------------------------
    # 17. crf21_planilla_desv_calibre — Planilla calibres desverdizado [NUEVA]
    # -----------------------------------------------------------------------
    EntitySpec(
        logical_name="crf21_planilla_desv_calibre",
        entity_set_name="crf21_planilla_desv_calibres",
        schema_name="crf21_planilla_desv_calibre",
        display_label="Planilla Desverdizado Calibre",
        display_collection_label="Planillas Desverdizado Calibres",
        is_new=True,
        fields=[
            _lookup("crf21_lote_planta_id", "Lote Planta", "crf21_lote_planta",
                    "crf21_lote_planta_planilla_desv_calibres"),
            _str("crf21_supervisor", "Supervisor", max_length=200),
            _str("crf21_productor", "Productor", max_length=200),
            _str("crf21_variedad", "Variedad", max_length=100),
            _str("crf21_trazabilidad", "Trazabilidad", max_length=200),
            _str("crf21_cod_sdp", "Codigo SDP", max_length=100),
            _str("crf21_fecha_cosecha", "Fecha Cosecha", max_length=20),
            _str("crf21_fecha_despacho", "Fecha Despacho", max_length=20),
            _str("crf21_cuartel", "Cuartel", max_length=100),
            _str("crf21_sector", "Sector", max_length=100),
            # Defectos (%)
            _dec("crf21_oleocelosis", "Oleocelosis", min_val=0, max_val=100),
            _dec("crf21_heridas_abiertas", "Heridas Abiertas", min_val=0, max_val=100),
            _dec("crf21_rugoso", "Rugoso", min_val=0, max_val=100),
            _dec("crf21_deforme", "Deforme", min_val=0, max_val=100),
            _dec("crf21_golpe_sol", "Golpe Sol", min_val=0, max_val=100),
            _dec("crf21_verdes", "Verdes", min_val=0, max_val=100),
            _dec("crf21_pre_calibre_defecto", "Pre Calibre Defecto", min_val=0, max_val=100),
            _dec("crf21_palo_largo", "Palo Largo", min_val=0, max_val=100),
            # Datos de calibres en JSON
            _memo("crf21_calibres_grupos", "Calibres Grupos (JSON)", max_length=8000),
            _memo("crf21_observaciones", "Observaciones"),
            *_common_control_fields(),
        ],
    ),

    # -----------------------------------------------------------------------
    # 18. crf21_planilla_desv_semillas — Planilla semillas desverdizado [NUEVA]
    # Nota: el logical_name termina en 's' segun el PK crf21_planilla_desv_semillasid
    # -----------------------------------------------------------------------
    EntitySpec(
        logical_name="crf21_planilla_desv_semillas",
        entity_set_name="crf21_planilla_desv_semillas",
        schema_name="crf21_planilla_desv_semillas",
        display_label="Planilla Desverdizado Semillas",
        display_collection_label="Planillas Desverdizado Semillas",
        is_new=True,
        fields=[
            _lookup("crf21_lote_planta_id", "Lote Planta", "crf21_lote_planta",
                    "crf21_lote_planta_planilla_desv_semillas"),
            _str("crf21_fecha", "Fecha", max_length=20),
            _str("crf21_supervisor", "Supervisor", max_length=200),
            _str("crf21_productor", "Productor", max_length=200),
            _str("crf21_variedad", "Variedad", max_length=100),
            _str("crf21_cuartel", "Cuartel", max_length=100),
            _str("crf21_sector", "Sector", max_length=100),
            _str("crf21_trazabilidad", "Trazabilidad", max_length=200),
            _str("crf21_cod_sdp", "Codigo SDP", max_length=100),
            _str("crf21_color", "Color", max_length=50),
            # 50 frutos como JSON
            _memo("crf21_frutas_data", "Frutas Data (JSON)", max_length=8000),
            # Estadisticas calculadas
            _int("crf21_total_frutos_muestra", "Total Frutos Muestra", min_val=0, max_val=9999),
            _int("crf21_total_frutos_con_semillas", "Total Frutos Con Semillas",
                 min_val=0, max_val=9999),
            _int("crf21_total_semillas", "Total Semillas", min_val=0, max_val=99999),
            _dec("crf21_pct_frutos_con_semillas", "Pct Frutos Con Semillas",
                 min_val=0, max_val=100),
            _dec("crf21_promedio_semillas", "Promedio Semillas", min_val=0, max_val=999),
            *_common_control_fields(),
        ],
    ),

    # -----------------------------------------------------------------------
    # 19. crf21_planilla_calidad_packing — Planilla calidad packing [NUEVA]
    # -----------------------------------------------------------------------
    EntitySpec(
        logical_name="crf21_planilla_calidad_packing",
        entity_set_name="crf21_planilla_calidad_packings",
        schema_name="crf21_planilla_calidad_packing",
        display_label="Planilla Calidad Packing",
        display_collection_label="Planillas Calidad Packing",
        is_new=True,
        fields=[
            _lookup("crf21_pallet_id", "Pallet", "crf21_pallet",
                    "crf21_pallet_planilla_calidad_packings"),
            # Identificacion
            _str("crf21_productor", "Productor", max_length=200),
            _str("crf21_trazabilidad", "Trazabilidad", max_length=200),
            _str("crf21_cod_sdp", "Codigo SDP", max_length=100),
            _str("crf21_cuartel", "Cuartel", max_length=100),
            _str("crf21_sector", "Sector", max_length=100),
            _str("crf21_nombre_control", "Nombre Control", max_length=200),
            _str("crf21_n_cuadrilla", "N Cuadrilla", max_length=50),
            _str("crf21_supervisor", "Supervisor", max_length=200),
            _str("crf21_fecha_despacho", "Fecha Despacho", max_length=20),
            _str("crf21_fecha_cosecha", "Fecha Cosecha", max_length=20),
            _str("crf21_numero_hoja", "Numero Hoja", max_length=50),
            _str("crf21_tipo_fruta", "Tipo Fruta", max_length=100),
            _str("crf21_variedad", "Variedad", max_length=100),
            _dec("crf21_temperatura", "Temperatura"),
            _dec("crf21_humedad", "Humedad", min_val=0, max_val=100),
            _dec("crf21_horas_cosecha", "Horas Cosecha", min_val=0, max_val=999),
            _str("crf21_color", "Color", max_length=50),
            _int("crf21_n_frutos_muestreados", "N Frutos Muestreados", min_val=0, max_val=9999),
            _dec("crf21_brix", "Brix", precision=1, min_val=0, max_val=50),
            # Calibre
            _dec("crf21_pre_calibre", "Pre Calibre", min_val=0, max_val=100),
            _dec("crf21_sobre_calibre", "Sobre Calibre", min_val=0, max_val=100),
            # Defectos de calidad (conteo frutos)
            _int("crf21_color_contrario_evaluado", "Color Contrario Evaluado",
                 min_val=0, max_val=9999),
            _int("crf21_cantidad_frutos", "Cantidad Frutos", min_val=0, max_val=9999),
            _int("crf21_ausencia_roseta", "Ausencia Roseta", min_val=0, max_val=9999),
            _int("crf21_deformes", "Deformes", min_val=0, max_val=9999),
            _int("crf21_frutos_con_semilla", "Frutos Con Semilla", min_val=0, max_val=9999),
            _int("crf21_n_semillas", "N Semillas", min_val=0, max_val=99999),
            _int("crf21_fumagina", "Fumagina", min_val=0, max_val=9999),
            _int("crf21_h_cicatrizadas", "Heridas Cicatrizadas", min_val=0, max_val=9999),
            _int("crf21_manchas", "Manchas", min_val=0, max_val=9999),
            _int("crf21_peduculo_largo", "Peduculo Largo", min_val=0, max_val=9999),
            _int("crf21_residuos", "Residuos", min_val=0, max_val=9999),
            _int("crf21_rugosos", "Rugosos", min_val=0, max_val=9999),
            # Defectos Russet
            _int("crf21_russet_leve_claros", "Russet Leve Claros", min_val=0, max_val=9999),
            _int("crf21_russet_moderados_claros", "Russet Moderados Claros",
                 min_val=0, max_val=9999),
            _int("crf21_russet_severos_oscuros", "Russet Severos Oscuros",
                 min_val=0, max_val=9999),
            # Defectos Creasing
            _int("crf21_creasing_leve", "Creasing Leve", min_val=0, max_val=9999),
            _int("crf21_creasing_mod_sev", "Creasing Mod-Sev", min_val=0, max_val=9999),
            # Defectos condicion
            _int("crf21_dano_frio_granulados", "Dano Frio Granulados", min_val=0, max_val=9999),
            _int("crf21_bufado", "Bufado", min_val=0, max_val=9999),
            _int("crf21_deshidratacion_roseta", "Deshidratacion Roseta", min_val=0, max_val=9999),
            _int("crf21_golpe_sol", "Golpe Sol", min_val=0, max_val=9999),
            _int("crf21_h_abiertas_superior", "Heridas Abiertas Superior",
                 min_val=0, max_val=9999),
            _int("crf21_h_abiertas_inferior", "Heridas Abiertas Inferior",
                 min_val=0, max_val=9999),
            _int("crf21_acostillado", "Acostillado", min_val=0, max_val=9999),
            _int("crf21_machucon", "Machucon", min_val=0, max_val=9999),
            _int("crf21_blandos", "Blandos", min_val=0, max_val=9999),
            _int("crf21_oleocelosis", "Oleocelosis", min_val=0, max_val=9999),
            _int("crf21_ombligo_rasgado", "Ombligo Rasgado", min_val=0, max_val=9999),
            _int("crf21_colapso_corteza", "Colapso Corteza", min_val=0, max_val=9999),
            _int("crf21_pudricion", "Pudricion", min_val=0, max_val=9999),
            # Araña
            _int("crf21_dano_arana_leve", "Dano Arana Leve", min_val=0, max_val=9999),
            _int("crf21_dano_arana_moderado", "Dano Arana Moderado", min_val=0, max_val=9999),
            _int("crf21_dano_arana_severo", "Dano Arana Severo", min_val=0, max_val=9999),
            _int("crf21_dano_mecanico", "Dano Mecanico", min_val=0, max_val=9999),
            _memo("crf21_otros_condicion", "Otros Condicion"),
            # Resumen
            _dec("crf21_total_defectos_pct", "Total Defectos Pct", min_val=0, max_val=100),
            *_common_control_fields(),
        ],
    ),

    # -----------------------------------------------------------------------
    # 20. crf21_planilla_calidad_camara — Planilla calidad camara frio [NUEVA]
    # -----------------------------------------------------------------------
    EntitySpec(
        logical_name="crf21_planilla_calidad_camara",
        entity_set_name="crf21_planilla_calidad_camaras",
        schema_name="crf21_planilla_calidad_camara",
        display_label="Planilla Calidad Camara",
        display_collection_label="Planillas Calidad Camara",
        is_new=True,
        fields=[
            _lookup("crf21_pallet_id", "Pallet", "crf21_pallet",
                    "crf21_pallet_planilla_calidad_camaras"),
            _str("crf21_fecha_control", "Fecha Control", max_length=20),
            _str("crf21_tipo_proceso", "Tipo Proceso", max_length=100),
            _str("crf21_zona_planta", "Zona Planta", max_length=100),
            _str("crf21_tunel_camara", "Tunel Camara", max_length=50),
            _int("crf21_capacidad_maxima", "Capacidad Maxima Pallets", min_val=0, max_val=9999),
            _dec("crf21_temperatura_equipos", "Temperatura Equipos"),
            _str("crf21_codigo_envases", "Codigo Envases", max_length=200),
            _int("crf21_cantidad_pallets", "Cantidad Pallets", min_val=0, max_val=9999),
            _str("crf21_especie", "Especie", max_length=100),
            _str("crf21_variedad", "Variedad", max_length=100),
            _str("crf21_fecha_embalaje", "Fecha Embalaje", max_length=20),
            _str("crf21_estiba", "Estiba", max_length=100),
            _str("crf21_tipo_inversion", "Tipo Inversion", max_length=100),
            # Mediciones horarias en JSON
            _memo("crf21_mediciones", "Mediciones (JSON)", max_length=8000),
            # Temperaturas
            _dec("crf21_temp_pulpa_ext_inicio", "Temp Pulpa Ext Inicio"),
            _dec("crf21_temp_pulpa_ext_termino", "Temp Pulpa Ext Termino"),
            _dec("crf21_temp_pulpa_int_inicio", "Temp Pulpa Int Inicio"),
            _dec("crf21_temp_pulpa_int_termino", "Temp Pulpa Int Termino"),
            _dec("crf21_temp_ambiente_inicio", "Temp Ambiente Inicio"),
            _dec("crf21_temp_ambiente_termino", "Temp Ambiente Termino"),
            # Tiempos
            _str("crf21_tiempo_carga_inicio", "Tiempo Carga Inicio", max_length=10),
            _str("crf21_tiempo_carga_termino", "Tiempo Carga Termino", max_length=10),
            _str("crf21_tiempo_descarga_inicio", "Tiempo Descarga Inicio", max_length=10),
            _str("crf21_tiempo_descarga_termino", "Tiempo Descarga Termino", max_length=10),
            _str("crf21_tiempo_enfriado_inicio", "Tiempo Enfriado Inicio", max_length=10),
            _str("crf21_tiempo_enfriado_termino", "Tiempo Enfriado Termino", max_length=10),
            _memo("crf21_observaciones", "Observaciones"),
            _str("crf21_nombre_control", "Nombre Control", max_length=200),
            *_common_control_fields(),
        ],
    ),
]

# Indice para lookup rapido por entity_set_name
ENTITY_SET_INDEX: dict[str, EntitySpec] = {
    spec.entity_set_name: spec for spec in REQUIRED_SCHEMA
}

# Indice por logical_name
LOGICAL_NAME_INDEX: dict[str, EntitySpec] = {
    spec.logical_name: spec for spec in REQUIRED_SCHEMA
}

# Las 4 entidades nuevas (planillas)
NEW_ENTITIES: list[EntitySpec] = [spec for spec in REQUIRED_SCHEMA if spec.is_new]
