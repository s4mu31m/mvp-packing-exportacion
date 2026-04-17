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
    "codigo_sag_csg":       "crf21_codigo_sag_csg",
    "codigo_sag_csp":       "crf21_codigo_sag_csp",
    "codigo_sdp":           "crf21_codigo_sdp",
    "predio":               "crf21_predio",
    "sector":               "crf21_sector",
    "lote_productor":       "crf21_lote_productor",
    "color":                "crf21_color",
    "estado_fisico":        "crf21_estado_fisico",
    "a_o_r":                "crf21_a_o_r",
    "hora_recepcion":       "crf21_hora_recepcion",
    "kilos_bruto_ingreso":  "crf21_kilos_bruto_ingreso",
    "kilos_neto_ingreso":   "crf21_kilos_neto_ingreso",
    "cantidad_bins_grupo":  "crf21_cantidad_bins_grupo",
    "tara_bin":             "crf21_tara_bin",
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

# OptionSet integer values for crf21_a_o_r (Picklist, validated 2026-04-04)
AOR_DV = {
    "aprobado":  137460000,
    "objetado":  137460001,
    "rechazado": 137460002,
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
    # ultimo_cambio_estado_at: timestamp UTC del ultimo cambio real de etapa operativa.
    # Se escribe en cada use case que transiciona etapa_actual.
    # Columna crf21_ultimo_cambio_estado_at debe existir en crf21_lote_plantas (Power Apps).
    # Registros anteriores al deploy de este campo tienen null; se aplica fallback
    # a fecha_conformacion en vistas y exportaciones.
    "ultimo_cambio_estado_at":              "crf21_ultimo_cambio_estado_at",
    # codigo_productor: copiado desde el primer bin al cerrar el lote (cerrar_lote_recepcion).
    # Campo crf21_codigo_productor agregado a crf21_lote_plantas en Power Apps el 2026-04-04.
    "codigo_productor":                     "crf21_codigo_productor",
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
    # ultimo_cambio_estado_at: timestamp UTC del ultimo cambio real de etapa del pallet.
    # Columna crf21_ultimo_cambio_estado_at debe existir en crf21_pallets (Power Apps).
    "ultimo_cambio_estado_at":  "crf21_ultimo_cambio_estado_at",
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
    "numero_camara":            "crf21_numerocamara",
    "fecha_ingreso":            "crf21_fecha_ingreso",
    "hora_ingreso":             "crf21_hora_ingreso",
    "fecha_salida":             "crf21_fecha_salida",
    "hora_salida":              "crf21_hora_salida",
    "horas_desverdizado":       "crf21_horasdesverdizado",
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
    "rendimiento_lote_pct":      "crf21_rendimiento_lote_pct",
    "observaciones_generales":   "crf21_observaciones_generales",
    "velocidad_volcador":        "crf21_velocidad_volcador",
    "obs_volcador":              "crf21_obs_volcador",
    "cloro_libre_ppm":           "crf21_cloro_libre_ppm",
    "tiempo_inmersion_seg":      "crf21_tiempo_inmersion_seg",
    "temp_aire_secado":          "crf21_temp_aire_secado",
    "velocidad_ventiladores":    "crf21_velocidad_ventiladores",
    "fruta_sale_seca":           "crf21_fruta_sale_seca",
    "tipo_cera":                 "crf21_tipo_cera",
    "dosis_cera_ml_min":         "crf21_dosis_cera_ml_min",
    "temp_cera":                 "crf21_temp_cera",
    "cobertura_uniforme":        "crf21_cobertura_uniforme",
    "n_operarios_seleccion":     "crf21_n_operarios_seleccion",
    "fruta_dano_condicion_kg":   "crf21_fruta_dano_condicion_kg",
    "fruta_dano_calidad_kg":     "crf21_fruta_dano_calidad_kg",
    "fruta_pudricion_kg":        "crf21_fruta_pudricion_kg",
    "merma_total_seleccion_kg":  "crf21_merma_total_seleccion_kg",
    "equipo_calibrador":         "crf21_equipo_calibrador",
    "calibre_predominante":      "crf21_calibre_predominante",
    "pct_calibre_export":        "crf21_pct_calibre_export",
    "pct_calibres_menores":      "crf21_pct_calibres_menores",
    "tipo_caja":                 "crf21_tipo_caja",
    "peso_promedio_caja_kg":     "crf21_peso_promedio_caja_kg",
    "n_cajas_producidas":        "crf21_n_cajas_producidas",
    "rol":                       "crf21_rol",
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
# Planillas de Control de Calidad
# ---------------------------------------------------------------------------

PLANILLA_DESV_CALIBRE_FIELDS = {
    "id":                  "crf21_planilla_desv_calibreid",
    "lote_id":             "crf21_lote_planta_id",
    "lote_id_value":       "_crf21_lote_planta_id_value",
    "supervisor":          "crf21_supervisor",
    "productor":           "crf21_productor",
    "variedad":            "crf21_variedad",
    "trazabilidad":        "crf21_trazabilidad",
    "cod_sdp":             "crf21_cod_sdp",
    "fecha_cosecha":       "crf21_fecha_cosecha",
    "fecha_despacho":      "crf21_fecha_despacho",
    "cuartel":             "crf21_cuartel",
    "sector":              "crf21_sector",
    "oleocelosis":         "crf21_oleocelosis",
    "heridas_abiertas":    "crf21_heridas_abiertas",
    "rugoso":              "crf21_rugoso",
    "deforme":             "crf21_deforme",
    "golpe_sol":           "crf21_golpe_sol",
    "verdes":              "crf21_verdes",
    "pre_calibre_defecto": "crf21_pre_calibre_defecto",
    "palo_largo":          "crf21_palo_largo",
    "calibres_grupos":     "crf21_calibres_grupos",    # Multi-line Text (JSON)
    "observaciones":       "crf21_observaciones",
    "rol":                 "crf21_rol",
    "operator_code":       "crf21_operator_code",
    "created_at":          "createdon",
    "updated_at":          "modifiedon",
}
ENTITY_SET_PLANILLA_DESV_CALIBRE = "crf21_planilla_desv_calibres"

PLANILLA_DESV_SEMILLAS_FIELDS = {
    "id":                           "crf21_planilla_desv_semillasid",
    "lote_id":                      "crf21_lote_planta_id",
    "lote_id_value":                "_crf21_lote_planta_id_value",
    "fecha":                        "crf21_fecha",
    "supervisor":                   "crf21_supervisor",
    "productor":                    "crf21_productor",
    "variedad":                     "crf21_variedad",
    "cuartel":                      "crf21_cuartel",
    "sector":                       "crf21_sector",
    "trazabilidad":                 "crf21_trazabilidad",
    "cod_sdp":                      "crf21_cod_sdp",
    "color":                        "crf21_color",
    "frutas_data":                  "crf21_frutas_data",               # Multi-line Text (JSON)
    "total_frutos_muestra":         "crf21_total_frutos_muestra",
    "total_frutos_con_semillas":    "crf21_total_frutos_con_semillas",
    "total_semillas":               "crf21_total_semillas",
    "pct_frutos_con_semillas":      "crf21_pct_frutos_con_semillas",
    "promedio_semillas":            "crf21_promedio_semillas",
    "rol":                          "crf21_rol",
    "operator_code":                "crf21_operator_code",
    "created_at":                   "createdon",
    "updated_at":                   "modifiedon",
}
ENTITY_SET_PLANILLA_DESV_SEMILLAS = "crf21_planilla_desv_semillas"

PLANILLA_CALIDAD_PACKING_FIELDS = {
    "id":                       "crf21_planilla_calidad_packingid",
    "pallet_id":                "crf21_pallet_id",
    "pallet_id_value":          "_crf21_pallet_id_value",
    "productor":                "crf21_productor",
    "trazabilidad":             "crf21_trazabilidad",
    "cod_sdp":                  "crf21_cod_sdp",
    "cuartel":                  "crf21_cuartel",
    "sector":                   "crf21_sector",
    "nombre_control":           "crf21_nombre_control",
    "n_cuadrilla":              "crf21_n_cuadrilla",
    "supervisor":               "crf21_supervisor",
    "fecha_despacho":           "crf21_fecha_despacho",
    "fecha_cosecha":            "crf21_fecha_cosecha",
    "numero_hoja":              "crf21_numero_hoja",
    "tipo_fruta":               "crf21_tipo_fruta",
    "variedad":                 "crf21_variedad",
    "temperatura":              "crf21_temperatura",
    "humedad":                  "crf21_humedad",
    "horas_cosecha":            "crf21_horas_cosecha",
    "color":                    "crf21_color",
    "n_frutos_muestreados":     "crf21_n_frutos_muestreados",
    "brix":                     "crf21_brix",
    "pre_calibre":              "crf21_pre_calibre",
    "sobre_calibre":            "crf21_sobre_calibre",
    "color_contrario_evaluado": "crf21_color_contrario_evaluado",
    "cantidad_frutos":          "crf21_cantidad_frutos",
    "ausencia_roseta":          "crf21_ausencia_roseta",
    "deformes":                 "crf21_deformes",
    "frutos_con_semilla":       "crf21_frutos_con_semilla",
    "n_semillas":               "crf21_n_semillas",
    "fumagina":                 "crf21_fumagina",
    "h_cicatrizadas":           "crf21_h_cicatrizadas",
    "manchas":                  "crf21_manchas",
    "peduculo_largo":           "crf21_peduculo_largo",
    "residuos":                 "crf21_residuos",
    "rugosos":                  "crf21_rugosos",
    "russet_leve_claros":       "crf21_russet_leve_claros",
    "russet_moderados_claros":  "crf21_russet_moderados_claros",
    "russet_severos_oscuros":   "crf21_russet_severos_oscuros",
    "creasing_leve":            "crf21_creasing_leve",
    "creasing_mod_sev":         "crf21_creasing_mod_sev",
    "dano_frio_granulados":     "crf21_dano_frio_granulados",
    "bufado":                   "crf21_bufado",
    "deshidratacion_roseta":    "crf21_deshidratacion_roseta",
    "golpe_sol":                "crf21_golpe_sol",
    "h_abiertas_superior":      "crf21_h_abiertas_superior",
    "h_abiertas_inferior":      "crf21_h_abiertas_inferior",
    "acostillado":              "crf21_acostillado",
    "machucon":                 "crf21_machucon",
    "blandos":                  "crf21_blandos",
    "oleocelosis":              "crf21_oleocelosis",
    "ombligo_rasgado":          "crf21_ombligo_rasgado",
    "colapso_corteza":          "crf21_colapso_corteza",
    "pudricion":                "crf21_pudricion",
    "dano_arana_leve":          "crf21_dano_arana_leve",
    "dano_arana_moderado":      "crf21_dano_arana_moderado",
    "dano_arana_severo":        "crf21_dano_arana_severo",
    "dano_mecanico":            "crf21_dano_mecanico",
    "otros_condicion":          "crf21_otros_condicion",
    "total_defectos_pct":       "crf21_total_defectos_pct",
    "rol":                      "crf21_rol",
    "operator_code":            "crf21_operator_code",
    "created_at":               "createdon",
    "updated_at":               "modifiedon",
}
ENTITY_SET_PLANILLA_CALIDAD_PACKING = "crf21_planilla_calidad_packings"

PLANILLA_CALIDAD_CAMARA_FIELDS = {
    "id":                      "crf21_planilla_calidad_camaraid",
    "pallet_id":               "crf21_pallet_id",
    "pallet_id_value":         "_crf21_pallet_id_value",
    "fecha_control":           "crf21_fecha_control",
    "tipo_proceso":            "crf21_tipo_proceso",
    "zona_planta":             "crf21_zona_planta",
    "tunel_camara":            "crf21_tunel_camara",
    "capacidad_maxima":        "crf21_capacidad_maxima",
    "temperatura_equipos":     "crf21_temperatura_equipos",
    "codigo_envases":          "crf21_codigo_envases",
    "cantidad_pallets":        "crf21_cantidad_pallets",
    "especie":                 "crf21_especie",
    "variedad":                "crf21_variedad",
    "fecha_embalaje":          "crf21_fecha_embalaje",
    "estiba":                  "crf21_estiba",
    "tipo_inversion":          "crf21_tipo_inversion",
    "mediciones":              "crf21_mediciones",              # Multi-line Text (JSON)
    "temp_pulpa_ext_inicio":   "crf21_temp_pulpa_ext_inicio",
    "temp_pulpa_ext_termino":  "crf21_temp_pulpa_ext_termino",
    "temp_pulpa_int_inicio":   "crf21_temp_pulpa_int_inicio",
    "temp_pulpa_int_termino":  "crf21_temp_pulpa_int_termino",
    "temp_ambiente_inicio":    "crf21_temp_ambiente_inicio",
    "temp_ambiente_termino":   "crf21_temp_ambiente_termino",
    "tiempo_carga_inicio":     "crf21_tiempo_carga_inicio",
    "tiempo_carga_termino":    "crf21_tiempo_carga_termino",
    "tiempo_descarga_inicio":  "crf21_tiempo_descarga_inicio",
    "tiempo_descarga_termino": "crf21_tiempo_descarga_termino",
    "tiempo_enfriado_inicio":  "crf21_tiempo_enfriado_inicio",
    "tiempo_enfriado_termino": "crf21_tiempo_enfriado_termino",
    "observaciones":           "crf21_observaciones",
    "nombre_control":          "crf21_nombre_control",
    "rol":                     "crf21_rol",
    "operator_code":           "crf21_operator_code",
    "created_at":              "createdon",
    "updated_at":              "modifiedon",
}
ENTITY_SET_PLANILLA_CALIDAD_CAMARA = "crf21_planilla_calidad_camaras"


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
