"""
Mapa de entidades y campos entre el dominio Python y Dataverse Web API (OData v4).

Los nombres aqui reflejan el esquema REAL del ambiente Dataverse validado
el 2026-03-29 via endpoint /api/dataverse/check_tables/. El prefijo del
publisher es ``crf21_`` (no ``CaliPro_`` como se supuso antes de la validacion).

Notas de adaptacion backend → Dataverse:
  - ``temporada`` no existe como campo en ninguna tabla Dataverse.
    Se deriva de fechas o se ignora al persistir; los repositorios filtran
    por rango de fechas cuando sea necesario.
  - ``lote_code`` no existe; se mapea a ``crf21_id_lote_planta``.
  - ``pallet_code`` no existe; se mapea a ``crf21_id_pallet``.
  - ``estado``, ``temporada_codigo``, ``correlativo_temporada`` no existen
    en ``crf21_lote_plantas``; se manejan solo en SQLite.
  - No existe tabla ``registro_etapas``; los eventos de traza se registran
    solo en SQLite (DataverseRegistroEtapaRepository es no-op con log local).
  - ``SequenceCounter`` no tiene tabla Dataverse; el correlativo se determina
    contando registros existentes via OData filter.

Referencia: https://learn.microsoft.com/es-es/power-apps/developer/data-platform/webapi/overview
"""

# ---------------------------------------------------------------------------
# Entity set names  (URL path segment en /api/data/v9.2/<EntitySetName>)
# Validados el 2026-03-29 via check_tables endpoint.
# ---------------------------------------------------------------------------

ENTITY_SET_BIN                     = "crf21_bins"
ENTITY_SET_LOTE_PLANTA             = "crf21_lote_plantas"
ENTITY_SET_PALLET                  = "crf21_pallets"
ENTITY_SET_BIN_LOTE_PLANTA         = "crf21_bin_lote_plantas"
ENTITY_SET_PALLET_LOTE_PLANTA      = "crf21_lote_planta_pallets"
ENTITY_SET_CAMARA_MANTENCION       = "crf21_camara_mantencions"
ENTITY_SET_DESVERDIZADO            = "crf21_desverdizados"
ENTITY_SET_CALIDAD_DESVERDIZADO    = "crf21_calidad_desverdizados"
ENTITY_SET_INGRESO_PACKING         = "crf21_ingreso_packings"
ENTITY_SET_REGISTRO_PACKING        = "crf21_registro_packings"
ENTITY_SET_CONTROL_PROCESO_PACKING = "crf21_control_proceso_packings"
ENTITY_SET_CALIDAD_PALLET          = "crf21_calidad_pallets"
ENTITY_SET_CAMARA_FRIO             = "crf21_camara_frios"
ENTITY_SET_MEDICION_TEMPERATURA    = "crf21_medicion_temperatura_salidas"
ENTITY_SET_USUARIO_OPERATIVO       = "crf21_usuariooperativos"
ENTITY_SET_CALIDAD_PALLET_MUESTRA  = "crf21_calidad_pallet_muestras"

# Aliases para compatibilidad con codigo que usa nombres genéricos
ENTITY_SET_LOTE        = ENTITY_SET_LOTE_PLANTA
ENTITY_SET_BIN_LOTE    = ENTITY_SET_BIN_LOTE_PLANTA
ENTITY_SET_PALLET_LOTE = ENTITY_SET_PALLET_LOTE_PLANTA

# NOTA: No existe tabla registro_etapas en Dataverse.
# DataverseRegistroEtapaRepository es no-op (registra solo en log local).
ENTITY_SET_REGISTRO_ETAPA = None

# ---------------------------------------------------------------------------
# Logical names  (para EntityDefinitions y metadatos)
# ---------------------------------------------------------------------------

LOGICAL_NAME_BIN                     = "crf21_bin"
LOGICAL_NAME_LOTE_PLANTA             = "crf21_lote_planta"
LOGICAL_NAME_PALLET                  = "crf21_pallet"
LOGICAL_NAME_BIN_LOTE_PLANTA         = "crf21_bin_lote_planta"
LOGICAL_NAME_PALLET_LOTE_PLANTA      = "crf21_lote_planta_pallet"
LOGICAL_NAME_CAMARA_MANTENCION       = "crf21_camara_mantencion"
LOGICAL_NAME_DESVERDIZADO            = "crf21_desverdizado"
LOGICAL_NAME_CALIDAD_DESVERDIZADO    = "crf21_calidad_desverdizado"
LOGICAL_NAME_INGRESO_PACKING         = "crf21_ingreso_packing"
LOGICAL_NAME_REGISTRO_PACKING        = "crf21_registro_packing"
LOGICAL_NAME_CONTROL_PROCESO_PACKING = "crf21_control_proceso_packing"
LOGICAL_NAME_CALIDAD_PALLET          = "crf21_calidad_pallet"
LOGICAL_NAME_CAMARA_FRIO             = "crf21_camara_frio"
LOGICAL_NAME_MEDICION_TEMPERATURA    = "crf21_medicion_temperatura_salida"
LOGICAL_NAME_USUARIO_OPERATIVO       = "crf21_usuariooperativo"
LOGICAL_NAME_CALIDAD_PALLET_MUESTRA  = "crf21_calidad_pallet_muestra"

LOGICAL_NAME_LOTE        = LOGICAL_NAME_LOTE_PLANTA
LOGICAL_NAME_BIN_LOTE    = LOGICAL_NAME_BIN_LOTE_PLANTA
LOGICAL_NAME_PALLET_LOTE = LOGICAL_NAME_PALLET_LOTE_PLANTA

# ---------------------------------------------------------------------------
# Field maps  dominio → Dataverse OData field name
# Validados el 2026-03-29 via sample records del endpoint check_tables.
# ---------------------------------------------------------------------------

BIN_FIELDS = {
    # Identificadores
    "id":                   "crf21_binid",
    "id_bin":               "crf21_id_bin",
    "bin_code":             "crf21_bin_code",          # Alternate key
    "contador_incremental": "crf21_contador_incremental",
    # Datos agronómicos
    "fecha_cosecha":        "crf21_fecha_cosecha",
    "codigo_productor":     "crf21_codigo_productor",
    "nombre_productor":     "crf21_nombre_productor",
    "tipo_cultivo":         "crf21_tipo_cultivo",
    "variedad_fruta":       "crf21_variedad_fruta",
    "numero_cuartel":       "crf21_numero_cuartel",
    "nombre_cuartel":       "crf21_nombre_cuartel",
    "predio":               "crf21_predio",
    "sector":               "crf21_sector",
    "lote_productor":       "crf21_lote_productor",
    "color":                "crf21_color",
    "estado_fisico":        "crf21_estado_fisico",
    "a_o_r":                "crf21_a_o_r",
    "hora_recepcion":       "crf21_hora_recepcion",
    "kilos_bruto_ingreso":  "crf21_kilos_bruto_ingreso",
    "kilos_neto_ingreso":   "crf21_kilos_neto_ingreso",
    "n_cajas_campo":        "crf21_n_cajas_campo",
    "observaciones":        "crf21_observaciones",
    # Trazabilidad de transporte
    "n_guia":               "crf21_n_guia",
    "transporte":           "crf21_transporte",
    "capataz":              "crf21_capataz",
    "codigo_contratista":   "crf21_codigo_contratista",
    "nombre_contratista":   "crf21_nombre_contratista",
    # Control
    "rol":                  "crf21_rol",
    "operator_code":        "crf21_operator_code",
    "source_system":        "crf21_source_system",
    "source_event_id":      "crf21_source_event_id",
    "created_at":           "createdon",
    "updated_at":           "modifiedon",
}

LOTE_PLANTA_FIELDS = {
    # Identificadores
    "id":                                   "crf21_lote_plantaid",
    "id_lote_planta":                       "crf21_id_lote_planta",
    # lote_code → crf21_id_lote_planta (mejor campo disponible en Dataverse)
    "lote_code":                            "crf21_id_lote_planta",
    "contador_incremental":                 "crf21_contador_incremental",
    # Datos operativos
    "fecha_conformacion":                   "crf21_fecha_conformacion",
    "cantidad_bins":                        "crf21_cantidad_bins",
    "kilos_bruto_conformacion":             "crf21_kilos_bruto_conformacion",
    "kilos_neto_conformacion":              "crf21_kilos_neto_conformacion",
    "requiere_desverdizado":                "crf21_requiere_desverdizado",
    "disponibilidad_camara_desverdizado":   "crf21_disponibilidad_camara_desverdizado",
    # Control
    "rol":                                  "crf21_rol",
    "operator_code":                        "crf21_operator_code",
    "source_system":                        "crf21_source_system",
    "source_event_id":                      "crf21_source_event_id",
    "created_at":                           "createdon",
    "updated_at":                           "modifiedon",
    # etapa_actual: campo que registra la etapa de proceso en la que se encuentra el lote.
    # Valores posibles: "Recepcion", "Pesaje", "Mantencion", "Desverdizado",
    # "Ingreso Packing", "Packing / Proceso", "Paletizado",
    # "Calidad Pallet", "Camara Frio", "Temperatura Salida".
    # Registros anteriores al 2026-03-31 tienen este campo en null;
    # el backend aplica derive_etapa_lote() como fallback.
    "etapa_actual":                         "crf21_etapa_actual",
    # Nota: temporada, estado, temporada_codigo, correlativo_temporada NO existen
    # en Dataverse. Se gestionan solo en SQLite.
}

# Alias para codigo que usa LOTE_FIELDS
LOTE_FIELDS = LOTE_PLANTA_FIELDS

PALLET_FIELDS = {
    # Identificadores
    "id":               "crf21_palletid",
    "id_pallet":        "crf21_id_pallet",
    # pallet_code → crf21_id_pallet (mejor campo disponible en Dataverse)
    "pallet_code":      "crf21_id_pallet",
    "contador_incremental": "crf21_contador_incremental",
    # Datos operativos
    "fecha":            "crf21_fecha",
    "hora":             "crf21_hora",
    "tipo_caja":        "crf21_tipo_caja",
    "cajas_por_pallet": "crf21_cajas_por_pallet",
    "peso_total_kg":    "crf21_peso_total_kg",
    "destino_mercado":  "crf21_destino_mercado",
    # Control
    "rol":              "crf21_rol",
    "operator_code":    "crf21_operator_code",
    "created_at":       "createdon",
    "updated_at":       "modifiedon",
    # Nota: temporada no existe en Dataverse.
}

BIN_LOTE_FIELDS = {
    # Identificadores
    "id":            "crf21_bin_lote_plantaid",
    # Lookups — campo de escritura (@odata.bind) vs lectura (_*_value)
    "bin_id":        "crf21_bin_id",              # escritura: crf21_bin_id@odata.bind
    "lote_id":       "crf21_lote_planta_id",      # escritura: crf21_lote_planta_id@odata.bind
    "bin_id_value":  "_crf21_bin_id_value",        # lectura
    "lote_id_value": "_crf21_lote_planta_id_value", # lectura
    # Nota: operator_code, source_system, source_event_id no existen en esta tabla.
}

PALLET_LOTE_FIELDS = {
    # Identificadores
    "id":            "crf21_lote_planta_palletid",
    # Lookups
    "pallet_id":        "crf21_pallet_id",            # escritura
    "lote_id":          "crf21_lote_planta_id",       # escritura
    "pallet_id_value":  "_crf21_pallet_id_value",     # lectura
    "lote_id_value":    "_crf21_lote_planta_id_value", # lectura
    # Nota: operator_code no existe en esta tabla.
}

CAMARA_MANTENCION_FIELDS = {
    "id":                   "crf21_camara_mantencionid",
    "lote_id":              "crf21_lote_planta_id",
    "lote_id_value":        "_crf21_lote_planta_id_value",
    "camara_numero":        "crf21_camara_numero",
    "fecha_ingreso":        "crf21_fecha_ingreso",
    "hora_ingreso":         "crf21_hora_ingreso",
    "fecha_salida":         "crf21_fecha_salida",
    "hora_salida":          "crf21_hora_salida",
    "temperatura_camara":   "crf21_temperatura_camara",
    "humedad_relativa":     "crf21_humedad_relativa",
    "observaciones":        "crf21_observaciones",
    "rol":                  "crf21_rol",
    "operator_code":        "crf21_operator_code",
    "created_at":           "createdon",
    "updated_at":           "modifiedon",
}

DESVERDIZADO_FIELDS = {
    "id":                       "crf21_desverdizadoid",
    "lote_id":                  "crf21_lote_planta_id",
    "lote_id_value":            "_crf21_lote_planta_id_value",
    "fecha_ingreso":            "crf21_fecha_ingreso",
    "hora_ingreso":             "crf21_hora_ingreso",
    "fecha_salida":             "crf21_fecha_salida",
    "hora_salida":              "crf21_hora_salida",
    "kilos_enviados_terreno":   "crf21_kilos_enviados_terreno",
    "kilos_recepcionados":      "crf21_kilos_recepcionados",
    "kilos_procesados":         "crf21_kilos_procesados",
    "kilos_bruto_salida":       "crf21_kilos_bruto_salida",
    "kilos_neto_salida":        "crf21_kilos_neto_salida",
    "color_salida":             "crf21_color_salida",
    "proceso":                  "crf21_proceso",
    "fecha_proceso":            "crf21_fecha_proceso",
    "sector":                   "crf21_sector",
    "cuartel":                  "crf21_cuartel",
    "rol":                      "crf21_rol",
    "operator_code":            "crf21_operator_code",
    "created_at":               "createdon",
    "updated_at":               "modifiedon",
}

CALIDAD_DESVERDIZADO_FIELDS = {
    "id":                   "crf21_calidad_desverdizadoid",
    "lote_id":              "crf21_lote_planta_id",
    "lote_id_value":        "_crf21_lote_planta_id_value",
    "fecha":                "crf21_fecha",
    "hora":                 "crf21_hora",
    "temperatura_fruta":    "crf21_temperatura_fruta",
    "color_evaluado":       "crf21_color_evaluado",
    "estado_visual":        "crf21_estado_visual",
    "presencia_defectos":   "crf21_presencia_defectos",
    "descripcion_defectos": "crf21_descripcion_defectos",
    "aprobado":             "crf21_aprobado",
    "observaciones":        "crf21_observaciones",
    "rol":                  "crf21_rol",
    "operator_code":        "crf21_operator_code",
    "created_at":           "createdon",
    "updated_at":           "modifiedon",
}

INGRESO_PACKING_FIELDS = {
    "id":                           "crf21_ingreso_packingid",
    "lote_id":                      "crf21_lote_planta_id",
    "lote_id_value":                "_crf21_lote_planta_id_value",
    "fecha_ingreso":                "crf21_fecha_ingreso",
    "hora_ingreso":                 "crf21_hora_ingreso",
    "kilos_bruto_ingreso_packing":  "crf21_kilos_bruto_ingreso_packing",
    "kilos_neto_ingreso_packing":   "crf21_kilos_neto_ingreso_packing",
    "via_desverdizado":             "crf21_via_desverdizado",
    "observaciones":                "crf21_observaciones",
    "rol":                          "crf21_rol",
    "operator_code":                "crf21_operator_code",
    "created_at":                   "createdon",
    "updated_at":                   "modifiedon",
}

REGISTRO_PACKING_FIELDS = {
    "id":                       "crf21_registro_packingid",
    "lote_id":                  "crf21_lote_planta_id",
    "lote_id_value":            "_crf21_lote_planta_id_value",
    "fecha":                    "crf21_fecha",
    "hora_inicio":              "crf21_hora_inicio",
    "linea_proceso":            "crf21_linea_proceso",
    "categoria_calidad":        "crf21_categoria_calidad",
    "calibre":                  "crf21_calibre",
    "tipo_envase":              "crf21_tipo_envase",
    "cantidad_cajas_producidas":"crf21_cantidad_cajas_producidas",
    "peso_promedio_caja_kg":    "crf21_peso_promedio_caja_kg",
    "merma_seleccion_pct":      "crf21_merma_seleccion_pct",
    "rol":                      "crf21_rol",
    "operator_code":            "crf21_operator_code",
    "created_at":               "createdon",
    "updated_at":               "modifiedon",
}

CONTROL_PROCESO_PACKING_FIELDS = {
    "id":                       "crf21_control_proceso_packingid",
    "lote_id":                  "crf21_lote_planta_id",
    "lote_id_value":            "_crf21_lote_planta_id_value",
    "fecha":                    "crf21_fecha",
    "hora":                     "crf21_hora",
    "n_bins_procesados":        "crf21_n_bins_procesados",
    "temp_agua_tina":           "crf21_temp_agua_tina",
    "ph_agua":                  "crf21_ph_agua",
    "recambio_agua":            "crf21_recambio_agua",
    "rendimiento_lote_pct":     "crf21_rendimiento_lote_pct",
    "observaciones_generales":  "crf21_observaciones_generales",
    "rol":                      "crf21_rol",
    "operator_code":            "crf21_operator_code",
    "created_at":               "createdon",
    "updated_at":               "modifiedon",
}

CALIDAD_PALLET_FIELDS = {
    "id":                   "crf21_calidad_palletid",
    "pallet_id":            "crf21_pallet_id",
    "pallet_id_value":      "_crf21_pallet_id_value",
    "fecha":                "crf21_fecha",
    "hora":                 "crf21_hora",
    "temperatura_fruta":    "crf21_temperatura_fruta",
    "peso_caja_muestra":    "crf21_peso_caja_muestra",
    "estado_embalaje":      "crf21_estado_embalaje",
    "estado_visual_fruta":  "crf21_estado_visual_fruta",
    "presencia_defectos":   "crf21_presencia_defectos",
    "descripcion_defectos": "crf21_descripcion_defectos",
    "aprobado":             "crf21_aprobado",
    "observaciones":        "crf21_observaciones",
    "rol":                  "crf21_rol",
    "operator_code":        "crf21_operator_code",
    "created_at":           "createdon",
    "updated_at":           "modifiedon",
}

CAMARA_FRIO_FIELDS = {
    "id":                   "crf21_camara_frioid",
    "pallet_id":            "crf21_pallet_id",
    "pallet_id_value":      "_crf21_pallet_id_value",
    "camara_numero":        "crf21_camara_numero",
    "temperatura_camara":   "crf21_temperatura_camara",
    "humedad_relativa":     "crf21_humedad_relativa",
    "fecha_ingreso":        "crf21_fecha_ingreso",
    "hora_ingreso":         "crf21_hora_ingreso",
    "fecha_salida":         "crf21_fecha_salida",
    "hora_salida":          "crf21_hora_salida",
    "destino_despacho":     "crf21_destino_despacho",
    "rol":                  "crf21_rol",
    "operator_code":        "crf21_operator_code",
    "created_at":           "createdon",
    "updated_at":           "modifiedon",
}

MEDICION_TEMPERATURA_FIELDS = {
    "id":                   "crf21_medicion_temperatura_salidaid",
    "pallet_id":            "crf21_pallet_id",
    "pallet_id_value":      "_crf21_pallet_id_value",
    "fecha":                "crf21_fecha",
    "hora":                 "crf21_hora",
    "temperatura_pallet":   "crf21_temperatura_pallet",
    "punto_medicion":       "crf21_punto_medicion",
    "dentro_rango":         "crf21_dentro_rango",
    "observaciones":        "crf21_observaciones",
    "rol":                  "crf21_rol",
    "operator_code":        "crf21_operator_code",
    "created_at":           "createdon",
    "updated_at":           "modifiedon",
}

CALIDAD_PALLET_MUESTRA_FIELDS = {
    # Identificadores
    "id":               "crf21_calidad_pallet_muestraid",
    # Lookup al pallet
    "pallet_id":        "crf21_pallet_id",              # escritura: @odata.bind
    "pallet_id_value":  "_crf21_pallet_id_value",        # lectura
    # Campos operativos (espejo del modelo Django CalidadPalletMuestra)
    "numero_muestra":   "crf21_numero_muestra",
    "temperatura_fruta": "crf21_temperatura_fruta",
    "peso_caja_muestra": "crf21_peso_caja_muestra",
    "n_frutos":         "crf21_n_frutos",
    "aprobado":         "crf21_aprobado",
    "observaciones":    "crf21_observaciones",
    # Control
    "rol":              "crf21_rol",
    "operator_code":    "crf21_operator_code",
    # Sistema (solo lectura)
    "created_at":       "createdon",
    "updated_at":       "modifiedon",
}

# ---------------------------------------------------------------------------
# Helpers de construccion OData
# ---------------------------------------------------------------------------

USUARIO_OPERATIVO_FIELDS = {
    # PK
    "id":             "crf21_usuariooperativoid",
    "dataverse_id":   "crf21_usuariooperativoid",
    # Campos operativos
    "usernamelogin":  "crf21_usernamelogin",
    "nombrecompleto": "crf21_nombrecompleto",
    "correo":         "crf21_correo",
    "passwordhash":   "crf21_passwordhash",
    "rol":            "crf21_rol",
    "activo":         "crf21_activo",
    "bloqueado":      "crf21_bloqueado",
    "codigooperador": "crf21_codigooperador",
    # Campos de sistema (solo lectura)
    "created_at":     "createdon",
    "updated_at":     "modifiedon",
}


def odata_bind(entity_set: str, guid: str) -> str:
    """Construye el valor @odata.bind para un lookup field."""
    return f"/{entity_set}({guid})"


def select_fields(field_map: dict, keys: list[str]) -> str:
    """Construye el string $select a partir de claves del dominio."""
    return ",".join(field_map[k] for k in keys if k in field_map)
