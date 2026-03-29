"""
Mapa de entidades y campos entre el dominio Python y Dataverse Web API (OData v4).

IMPORTANTE — Convenciones y supuestos:
  - El prefijo de publisher usado es ``CaliPro_`` (configurado en Power Platform).
  - Los nombres aqui son supuestos razonables basados en la especificacion 03.4.
    Deben validarse contra el esquema real del ambiente Dataverse una vez que
    el equipo de Power Platform entregue el modelo de datos definitivo.
  - Si los nombres reales difieren, basta con actualizar las constantes de este
    modulo; la logica de repositorios y casos de uso no cambia.
  - El campo ``temporada`` existe en Django pero NO en Dataverse. Las consultas
    por temporada se construyen en el backend con filtros de rango de fechas
    sobre fecha_cosecha en Bin (ver seccion 6 de 03.4).

Referencia: https://learn.microsoft.com/es-es/power-apps/developer/data-platform/webapi/overview
"""

# ---------------------------------------------------------------------------
# Entity set names  (URL path segment en /api/data/v9.2/<EntitySetName>)
# ---------------------------------------------------------------------------

ENTITY_SET_BIN                     = "CaliPro_bins"
ENTITY_SET_LOTE_PLANTA             = "CaliPro_loteplantas"
ENTITY_SET_PALLET                  = "CaliPro_pallets"
ENTITY_SET_BIN_LOTE_PLANTA         = "CaliPro_binloteplantas"
ENTITY_SET_PALLET_LOTE_PLANTA      = "CaliPro_palletloteplantas"
ENTITY_SET_REGISTRO_ETAPA          = "CaliPro_registroetapas"
ENTITY_SET_CAMARA_MANTENCION       = "CaliPro_camaramantencions"
ENTITY_SET_DESVERDIZADO            = "CaliPro_desverdizados"
ENTITY_SET_CALIDAD_DESVERDIZADO    = "CaliPro_calidaddesverdizados"
ENTITY_SET_INGRESO_PACKING         = "CaliPro_ingresopacking"
ENTITY_SET_REGISTRO_PACKING        = "CaliPro_registropacking"
ENTITY_SET_CONTROL_PROCESO_PACKING = "CaliPro_controlprocesopacking"
ENTITY_SET_CALIDAD_PALLET          = "CaliPro_calidadpallets"
ENTITY_SET_CAMARA_FRIO             = "CaliPro_camarafrios"
ENTITY_SET_MEDICION_TEMPERATURA    = "CaliPro_mediciontemperaturas"

# Aliases mantenidos para compatibilidad con codigo anterior que usaba CaliPro_lotes
ENTITY_SET_LOTE            = ENTITY_SET_LOTE_PLANTA
ENTITY_SET_BIN_LOTE        = ENTITY_SET_BIN_LOTE_PLANTA
ENTITY_SET_PALLET_LOTE     = ENTITY_SET_PALLET_LOTE_PLANTA

# ---------------------------------------------------------------------------
# Logical names  (para EntityDefinitions y metadatos)
# ---------------------------------------------------------------------------

LOGICAL_NAME_BIN                     = "CaliPro_bin"
LOGICAL_NAME_LOTE_PLANTA             = "CaliPro_loteplanta"
LOGICAL_NAME_PALLET                  = "CaliPro_pallet"
LOGICAL_NAME_BIN_LOTE_PLANTA         = "CaliPro_binloteplanta"
LOGICAL_NAME_PALLET_LOTE_PLANTA      = "CaliPro_palletloteplanta"
LOGICAL_NAME_REGISTRO_ETAPA          = "CaliPro_registroetapa"
LOGICAL_NAME_CAMARA_MANTENCION       = "CaliPro_camaramantencion"
LOGICAL_NAME_DESVERDIZADO            = "CaliPro_desverdizado"
LOGICAL_NAME_CALIDAD_DESVERDIZADO    = "CaliPro_calidaddesverdizado"
LOGICAL_NAME_INGRESO_PACKING         = "CaliPro_ingresoapacking"
LOGICAL_NAME_REGISTRO_PACKING        = "CaliPro_registropacking"
LOGICAL_NAME_CONTROL_PROCESO_PACKING = "CaliPro_controlprocesopacking"
LOGICAL_NAME_CALIDAD_PALLET          = "CaliPro_calidadpallet"
LOGICAL_NAME_CAMARA_FRIO             = "CaliPro_camarafrio"
LOGICAL_NAME_MEDICION_TEMPERATURA    = "CaliPro_mediciontemperaturasal"

# Aliases para compatibilidad
LOGICAL_NAME_LOTE       = LOGICAL_NAME_LOTE_PLANTA
LOGICAL_NAME_BIN_LOTE   = LOGICAL_NAME_BIN_LOTE_PLANTA
LOGICAL_NAME_PALLET_LOTE = LOGICAL_NAME_PALLET_LOTE_PLANTA

# ---------------------------------------------------------------------------
# Field maps  dominio → Dataverse OData field name
# ---------------------------------------------------------------------------

BIN_FIELDS = {
    "id":                   "CaliPro_binid",
    "id_bin":               "CaliPro_idbin",
    "bin_code":             "CaliPro_bincode",       # Alternate key recomendada
    "contador_incremental": "CaliPro_contadorincremental",
    "fecha_cosecha":        "CaliPro_fechacosecha",
    "codigo_productor":     "CaliPro_codigoproductor",
    "nombre_productor":     "CaliPro_nombreproductor",
    "variedad_fruta":       "CaliPro_variedadfruta",
    "numero_cuartel":       "CaliPro_numerocuartel",
    "nombre_cuartel":       "CaliPro_nombrecuartel",
    "predio":               "CaliPro_predio",
    "sector":               "CaliPro_sector",
    "lote_productor":       "CaliPro_loteproductor",
    "color":                "CaliPro_color",
    "estado_fisico":        "CaliPro_estadofisico",
    "a_o_r":                "CaliPro_aor",
    "hora_recepcion":       "CaliPro_horarecepcion",
    "kilos_bruto_ingreso":  "CaliPro_kilosbrutoingreso",
    "kilos_neto_ingreso":   "CaliPro_kilosnetoingreso",
    "n_cajas_campo":        "CaliPro_ncajascampo",
    "observaciones":        "CaliPro_observaciones",
    "rol":                  "CaliPro_rol",
    "operator_code":        "CaliPro_operatorcode",
    "source_system":        "CaliPro_sourcesystem",
    "source_event_id":      "CaliPro_sourceeventid",
    "created_at":           "createdon",
    "updated_at":           "modifiedon",
}

LOTE_PLANTA_FIELDS = {
    "id":                                   "CaliPro_loteplaantaid",
    "id_lote_planta":                       "CaliPro_idloteplanta",
    "lote_code":                            "CaliPro_lotecode",      # Alternate key recomendada
    "contador_incremental":                 "CaliPro_contadorincremental",
    "fecha_conformacion":                   "CaliPro_fechaconformacion",
    "cantidad_bins":                        "CaliPro_cantidadbins",
    "kilos_bruto_conformacion":             "CaliPro_kilosbrutoconformacion",
    "kilos_neto_conformacion":              "CaliPro_kilosnetoconformacion",
    "requiere_desverdizado":                "CaliPro_requieredesverdizado",
    "disponibilidad_camara_desverdizado":   "CaliPro_disponibilidadcamara",
    "rol":                                  "CaliPro_rol",
    "operator_code":                        "CaliPro_operatorcode",
    "source_system":                        "CaliPro_sourcesystem",
    "source_event_id":                      "CaliPro_sourceeventid",
    # Campos de compatibilidad Django (no nativos en Dataverse — usar con cautela)
    "temporada":                            "CaliPro_temporada",
    "is_active":                            "CaliPro_isactive",
    "created_at":                           "createdon",
    "updated_at":                           "modifiedon",
}

# Alias para compatibilidad con codigo que usa LOTE_FIELDS
LOTE_FIELDS = LOTE_PLANTA_FIELDS

PALLET_FIELDS = {
    "id":               "CaliPro_palletid",
    "id_pallet":        "CaliPro_idpallet",
    "pallet_code":      "CaliPro_palletcode",
    "contador_incremental": "CaliPro_contadorincremental",
    "fecha":            "CaliPro_fecha",
    "hora":             "CaliPro_hora",
    "tipo_caja":        "CaliPro_tipocaja",
    "cajas_por_pallet": "CaliPro_cajasporpallet",
    "peso_total_kg":    "CaliPro_pesototalkgpallet",
    "destino_mercado":  "CaliPro_destinomercado",
    "rol":              "CaliPro_rol",
    "operator_code":    "CaliPro_operatorcode",
    "source_system":    "CaliPro_sourcesystem",
    "source_event_id":  "CaliPro_sourceeventid",
    # Campos de compatibilidad Django
    "temporada":        "CaliPro_temporada",
    "is_active":        "CaliPro_isactive",
    "created_at":       "createdon",
    "updated_at":       "modifiedon",
}

BIN_LOTE_FIELDS = {
    "id":               "CaliPro_binloteplaantaid",
    "bin_id":           "CaliPro_bin",           # Lookup a CaliPro_bin
    "lote_id":          "CaliPro_loteplanta",    # Lookup a CaliPro_loteplanta
    "operator_code":    "CaliPro_operatorcode",
    "source_system":    "CaliPro_sourcesystem",
    "source_event_id":  "CaliPro_sourceeventid",
}

PALLET_LOTE_FIELDS = {
    "id":               "CaliPro_palletloteplaantaid",
    "pallet_id":        "CaliPro_pallet",        # Lookup a CaliPro_pallet
    "lote_id":          "CaliPro_loteplanta",    # Lookup a CaliPro_loteplanta
    "operator_code":    "CaliPro_operatorcode",
    "source_system":    "CaliPro_sourcesystem",
    "source_event_id":  "CaliPro_sourceeventid",
}

REGISTRO_ETAPA_FIELDS = {
    "id":               "CaliPro_registroetapaid",
    "temporada":        "CaliPro_temporada",
    "event_key":        "CaliPro_eventkey",
    "tipo_evento":      "CaliPro_tipoevento",
    "bin_id":           "CaliPro_bin",
    "lote_id":          "CaliPro_loteplanta",
    "pallet_id":        "CaliPro_pallet",
    "operator_code":    "CaliPro_operatorcode",
    "source_system":    "CaliPro_sourcesystem",
    "source_event_id":  "CaliPro_sourceeventid",
    "occurred_at":      "CaliPro_occurredat",
    "payload":          "CaliPro_payload",
    "notes":            "CaliPro_notes",
    "created_at":       "createdon",
    "updated_at":       "modifiedon",
}

CAMARA_MANTENCION_FIELDS = {
    "id":                   "CaliPro_camaramantencionid",
    "lote_id":              "CaliPro_loteplanta",
    "camara_numero":        "CaliPro_camaranumero",
    "fecha_ingreso":        "CaliPro_fechaingreso",
    "hora_ingreso":         "CaliPro_horaingreso",
    "fecha_salida":         "CaliPro_fechasalida",
    "hora_salida":          "CaliPro_horasalida",
    "temperatura_camara":   "CaliPro_temperaturacamara",
    "humedad_relativa":     "CaliPro_humedadrelativa",
    "observaciones":        "CaliPro_observaciones",
    "rol":                  "CaliPro_rol",
    "operator_code":        "CaliPro_operatorcode",
    "created_at":           "createdon",
    "updated_at":           "modifiedon",
}

DESVERDIZADO_FIELDS = {
    "id":                       "CaliPro_desverdizadoid",
    "lote_id":                  "CaliPro_loteplanta",
    "fecha_ingreso":            "CaliPro_fechaingreso",
    "hora_ingreso":             "CaliPro_horaingreso",
    "fecha_salida":             "CaliPro_fechasalida",
    "hora_salida":              "CaliPro_horasalida",
    "kilos_enviados_terreno":   "CaliPro_kiloseenviadosterreno",
    "kilos_recepcionados":      "CaliPro_kilosrecepcionados",
    "kilos_procesados":         "CaliPro_kilosprocesados",
    "kilos_bruto_salida":       "CaliPro_kilosbrutosalida",
    "kilos_neto_salida":        "CaliPro_kilosnetosalida",
    "color_salida":             "CaliPro_colorsalida",
    "proceso":                  "CaliPro_proceso",
    "fecha_proceso":            "CaliPro_fechaproceso",
    "sector":                   "CaliPro_sector",
    "cuartel":                  "CaliPro_cuartel",
    "rol":                      "CaliPro_rol",
    "operator_code":            "CaliPro_operatorcode",
    "created_at":               "createdon",
    "updated_at":               "modifiedon",
}

CALIDAD_DESVERDIZADO_FIELDS = {
    "id":                   "CaliPro_calidaddesverdizadoid",
    "lote_id":              "CaliPro_loteplanta",
    "fecha":                "CaliPro_fecha",
    "hora":                 "CaliPro_hora",
    "temperatura_fruta":    "CaliPro_temperaturafruta",
    "color_evaluado":       "CaliPro_colorevaluado",
    "estado_visual":        "CaliPro_estadovisual",
    "presencia_defectos":   "CaliPro_presenciadefectos",
    "descripcion_defectos": "CaliPro_descripciondefectos",
    "aprobado":             "CaliPro_aprobado",
    "observaciones":        "CaliPro_observaciones",
    "rol":                  "CaliPro_rol",
    "operator_code":        "CaliPro_operatorcode",
    "created_at":           "createdon",
    "updated_at":           "modifiedon",
}

INGRESO_PACKING_FIELDS = {
    "id":                           "CaliPro_ingresoapackingid",
    "lote_id":                      "CaliPro_loteplanta",
    "fecha_ingreso":                "CaliPro_fechaingreso",
    "hora_ingreso":                 "CaliPro_horaingreso",
    "kilos_bruto_ingreso_packing":  "CaliPro_kilosbrutoingresspacking",
    "kilos_neto_ingreso_packing":   "CaliPro_kilosnetoingresspacking",
    "via_desverdizado":             "CaliPro_viadesverdizado",
    "observaciones":                "CaliPro_observaciones",
    "rol":                          "CaliPro_rol",
    "operator_code":                "CaliPro_operatorcode",
    "created_at":                   "createdon",
    "updated_at":                   "modifiedon",
}

REGISTRO_PACKING_FIELDS = {
    "id":                       "CaliPro_registropackingid",
    "lote_id":                  "CaliPro_loteplanta",
    "fecha":                    "CaliPro_fecha",
    "hora_inicio":              "CaliPro_horainicio",
    "linea_proceso":            "CaliPro_lineaproceso",
    "categoria_calidad":        "CaliPro_categoriacalidad",
    "calibre":                  "CaliPro_calibre",
    "tipo_envase":              "CaliPro_tipoenvase",
    "cantidad_cajas_producidas":"CaliPro_cantidadcajasproducidas",
    "peso_promedio_caja_kg":    "CaliPro_pesopromedioecaja",
    "merma_seleccion_pct":      "CaliPro_mermaseleccionpct",
    "rol":                      "CaliPro_rol",
    "operator_code":            "CaliPro_operatorcode",
    "created_at":               "createdon",
    "updated_at":               "modifiedon",
}

CONTROL_PROCESO_PACKING_FIELDS = {
    "id":                       "CaliPro_controlprocesopacking",
    "lote_id":                  "CaliPro_loteplanta",
    "fecha":                    "CaliPro_fecha",
    "hora":                     "CaliPro_hora",
    "n_bins_procesados":        "CaliPro_nbinsprocesados",
    "temp_agua_tina":           "CaliPro_tempaguatina",
    "ph_agua":                  "CaliPro_phagua",
    "recambio_agua":            "CaliPro_recambioagua",
    "rendimiento_lote_pct":     "CaliPro_rendimientolotepct",
    "observaciones_generales":  "CaliPro_observacionesgenerales",
    "rol":                      "CaliPro_rol",
    "operator_code":            "CaliPro_operatorcode",
    "created_at":               "createdon",
    "updated_at":               "modifiedon",
}

CALIDAD_PALLET_FIELDS = {
    "id":                   "CaliPro_calidadpalletid",
    "pallet_id":            "CaliPro_pallet",
    "fecha":                "CaliPro_fecha",
    "hora":                 "CaliPro_hora",
    "temperatura_fruta":    "CaliPro_temperaturafruta",
    "peso_caja_muestra":    "CaliPro_pesocajamuestra",
    "estado_embalaje":      "CaliPro_estadoembalaje",
    "estado_visual_fruta":  "CaliPro_estadovisualfruta",
    "presencia_defectos":   "CaliPro_presenciadefectos",
    "descripcion_defectos": "CaliPro_descripciondefectos",
    "aprobado":             "CaliPro_aprobado",
    "observaciones":        "CaliPro_observaciones",
    "rol":                  "CaliPro_rol",
    "operator_code":        "CaliPro_operatorcode",
    "created_at":           "createdon",
    "updated_at":           "modifiedon",
}

CAMARA_FRIO_FIELDS = {
    "id":                   "CaliPro_camarafrioid",
    "pallet_id":            "CaliPro_pallet",
    "camara_numero":        "CaliPro_camaranumero",
    "temperatura_camara":   "CaliPro_temperaturacamara",
    "humedad_relativa":     "CaliPro_humedadrelativa",
    "fecha_ingreso":        "CaliPro_fechaingreso",
    "hora_ingreso":         "CaliPro_horaingreso",
    "fecha_salida":         "CaliPro_fechasalida",
    "hora_salida":          "CaliPro_horasalida",
    "destino_despacho":     "CaliPro_destinodespacho",
    "rol":                  "CaliPro_rol",
    "operator_code":        "CaliPro_operatorcode",
    "created_at":           "createdon",
    "updated_at":           "modifiedon",
}

MEDICION_TEMPERATURA_FIELDS = {
    "id":                   "CaliPro_mediciontemperaturasalidaid",
    "pallet_id":            "CaliPro_pallet",
    "fecha":                "CaliPro_fecha",
    "hora":                 "CaliPro_hora",
    "temperatura_pallet":   "CaliPro_temperaturapallet",
    "punto_medicion":       "CaliPro_puntomedicion",
    "dentro_rango":         "CaliPro_dentrorango",
    "observaciones":        "CaliPro_observaciones",
    "rol":                  "CaliPro_rol",
    "operator_code":        "CaliPro_operatorcode",
    "created_at":           "createdon",
    "updated_at":           "modifiedon",
}

# ---------------------------------------------------------------------------
# Alternate key names
# ---------------------------------------------------------------------------

BIN_ALTERNATE_KEY        = "CaliPro_bincode"
LOTE_PLANTA_ALTERNATE_KEY = "CaliPro_lotecode"

# Alias para compatibilidad
LOTE_ALTERNATE_KEY = LOTE_PLANTA_ALTERNATE_KEY

# ---------------------------------------------------------------------------
# Helpers de construccion OData
# ---------------------------------------------------------------------------

def odata_bind(entity_set: str, guid: str) -> str:
    """Construye el valor @odata.bind para un lookup field."""
    return f"/{entity_set}({guid})"


def select_fields(field_map: dict, keys: list[str]) -> str:
    """Construye el string $select a partir de claves del dominio."""
    return ",".join(field_map[k] for k in keys if k in field_map)
