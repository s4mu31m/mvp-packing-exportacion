"""
Mapa de entidades y campos entre el dominio Python y Dataverse Web API (OData v4).

IMPORTANTE — Convenciones y supuestos:
  - El prefijo de publisher usado es ``cfn_`` (configurado en Power Platform).
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

ENTITY_SET_BIN                     = "cfn_bins"
ENTITY_SET_LOTE_PLANTA             = "cfn_loteplantas"
ENTITY_SET_PALLET                  = "cfn_pallets"
ENTITY_SET_BIN_LOTE_PLANTA         = "cfn_binloteplantas"
ENTITY_SET_PALLET_LOTE_PLANTA      = "cfn_palletloteplantas"
ENTITY_SET_REGISTRO_ETAPA          = "cfn_registroetapas"
ENTITY_SET_CAMARA_MANTENCION       = "cfn_camaramantencions"
ENTITY_SET_DESVERDIZADO            = "cfn_desverdizados"
ENTITY_SET_CALIDAD_DESVERDIZADO    = "cfn_calidaddesverdizados"
ENTITY_SET_INGRESO_PACKING         = "cfn_ingresopacking"
ENTITY_SET_REGISTRO_PACKING        = "cfn_registropacking"
ENTITY_SET_CONTROL_PROCESO_PACKING = "cfn_controlprocesopacking"
ENTITY_SET_CALIDAD_PALLET          = "cfn_calidadpallets"
ENTITY_SET_CAMARA_FRIO             = "cfn_camarafrios"
ENTITY_SET_MEDICION_TEMPERATURA    = "cfn_mediciontemperaturas"

# Aliases mantenidos para compatibilidad con codigo anterior que usaba cfn_lotes
ENTITY_SET_LOTE            = ENTITY_SET_LOTE_PLANTA
ENTITY_SET_BIN_LOTE        = ENTITY_SET_BIN_LOTE_PLANTA
ENTITY_SET_PALLET_LOTE     = ENTITY_SET_PALLET_LOTE_PLANTA

# ---------------------------------------------------------------------------
# Logical names  (para EntityDefinitions y metadatos)
# ---------------------------------------------------------------------------

LOGICAL_NAME_BIN                     = "cfn_bin"
LOGICAL_NAME_LOTE_PLANTA             = "cfn_loteplanta"
LOGICAL_NAME_PALLET                  = "cfn_pallet"
LOGICAL_NAME_BIN_LOTE_PLANTA         = "cfn_binloteplanta"
LOGICAL_NAME_PALLET_LOTE_PLANTA      = "cfn_palletloteplanta"
LOGICAL_NAME_REGISTRO_ETAPA          = "cfn_registroetapa"
LOGICAL_NAME_CAMARA_MANTENCION       = "cfn_camaramantencion"
LOGICAL_NAME_DESVERDIZADO            = "cfn_desverdizado"
LOGICAL_NAME_CALIDAD_DESVERDIZADO    = "cfn_calidaddesverdizado"
LOGICAL_NAME_INGRESO_PACKING         = "cfn_ingresoapacking"
LOGICAL_NAME_REGISTRO_PACKING        = "cfn_registropacking"
LOGICAL_NAME_CONTROL_PROCESO_PACKING = "cfn_controlprocesopacking"
LOGICAL_NAME_CALIDAD_PALLET          = "cfn_calidadpallet"
LOGICAL_NAME_CAMARA_FRIO             = "cfn_camarafrio"
LOGICAL_NAME_MEDICION_TEMPERATURA    = "cfn_mediciontemperaturasal"

# Aliases para compatibilidad
LOGICAL_NAME_LOTE       = LOGICAL_NAME_LOTE_PLANTA
LOGICAL_NAME_BIN_LOTE   = LOGICAL_NAME_BIN_LOTE_PLANTA
LOGICAL_NAME_PALLET_LOTE = LOGICAL_NAME_PALLET_LOTE_PLANTA

# ---------------------------------------------------------------------------
# Field maps  dominio → Dataverse OData field name
# ---------------------------------------------------------------------------

BIN_FIELDS = {
    "id":                   "cfn_binid",
    "id_bin":               "cfn_idbin",
    "bin_code":             "cfn_bincode",       # Alternate key recomendada
    "contador_incremental": "cfn_contadorincremental",
    "fecha_cosecha":        "cfn_fechacosecha",
    "codigo_productor":     "cfn_codigoproductor",
    "nombre_productor":     "cfn_nombreproductor",
    "variedad_fruta":       "cfn_variedadfruta",
    "numero_cuartel":       "cfn_numerocuartel",
    "nombre_cuartel":       "cfn_nombrecuartel",
    "predio":               "cfn_predio",
    "sector":               "cfn_sector",
    "lote_productor":       "cfn_loteproductor",
    "color":                "cfn_color",
    "estado_fisico":        "cfn_estadofisico",
    "a_o_r":                "cfn_aor",
    "hora_recepcion":       "cfn_horarecepcion",
    "kilos_bruto_ingreso":  "cfn_kilosbrutoingreso",
    "kilos_neto_ingreso":   "cfn_kilosnetoingreso",
    "n_cajas_campo":        "cfn_ncajascampo",
    "observaciones":        "cfn_observaciones",
    "rol":                  "cfn_rol",
    "operator_code":        "cfn_operatorcode",
    "source_system":        "cfn_sourcesystem",
    "source_event_id":      "cfn_sourceeventid",
    "created_at":           "createdon",
    "updated_at":           "modifiedon",
}

LOTE_PLANTA_FIELDS = {
    "id":                                   "cfn_loteplaantaid",
    "id_lote_planta":                       "cfn_idloteplanta",
    "lote_code":                            "cfn_lotecode",      # Alternate key recomendada
    "contador_incremental":                 "cfn_contadorincremental",
    "fecha_conformacion":                   "cfn_fechaconformacion",
    "cantidad_bins":                        "cfn_cantidadbins",
    "kilos_bruto_conformacion":             "cfn_kilosbrutoconformacion",
    "kilos_neto_conformacion":              "cfn_kilosnetoconformacion",
    "requiere_desverdizado":                "cfn_requieredesverdizado",
    "disponibilidad_camara_desverdizado":   "cfn_disponibilidadcamara",
    "rol":                                  "cfn_rol",
    "operator_code":                        "cfn_operatorcode",
    "source_system":                        "cfn_sourcesystem",
    "source_event_id":                      "cfn_sourceeventid",
    # Campos de compatibilidad Django (no nativos en Dataverse — usar con cautela)
    "temporada":                            "cfn_temporada",
    "is_active":                            "cfn_isactive",
    "created_at":                           "createdon",
    "updated_at":                           "modifiedon",
}

# Alias para compatibilidad con codigo que usa LOTE_FIELDS
LOTE_FIELDS = LOTE_PLANTA_FIELDS

PALLET_FIELDS = {
    "id":               "cfn_palletid",
    "id_pallet":        "cfn_idpallet",
    "pallet_code":      "cfn_palletcode",
    "contador_incremental": "cfn_contadorincremental",
    "fecha":            "cfn_fecha",
    "hora":             "cfn_hora",
    "tipo_caja":        "cfn_tipocaja",
    "cajas_por_pallet": "cfn_cajasporpallet",
    "peso_total_kg":    "cfn_pesototalkgpallet",
    "destino_mercado":  "cfn_destinomercado",
    "rol":              "cfn_rol",
    "operator_code":    "cfn_operatorcode",
    "source_system":    "cfn_sourcesystem",
    "source_event_id":  "cfn_sourceeventid",
    # Campos de compatibilidad Django
    "temporada":        "cfn_temporada",
    "is_active":        "cfn_isactive",
    "created_at":       "createdon",
    "updated_at":       "modifiedon",
}

BIN_LOTE_FIELDS = {
    "id":               "cfn_binloteplaantaid",
    "bin_id":           "cfn_bin",           # Lookup a cfn_bin
    "lote_id":          "cfn_loteplanta",    # Lookup a cfn_loteplanta
    "operator_code":    "cfn_operatorcode",
    "source_system":    "cfn_sourcesystem",
    "source_event_id":  "cfn_sourceeventid",
}

PALLET_LOTE_FIELDS = {
    "id":               "cfn_palletloteplaantaid",
    "pallet_id":        "cfn_pallet",        # Lookup a cfn_pallet
    "lote_id":          "cfn_loteplanta",    # Lookup a cfn_loteplanta
    "operator_code":    "cfn_operatorcode",
    "source_system":    "cfn_sourcesystem",
    "source_event_id":  "cfn_sourceeventid",
}

REGISTRO_ETAPA_FIELDS = {
    "id":               "cfn_registroetapaid",
    "temporada":        "cfn_temporada",
    "event_key":        "cfn_eventkey",
    "tipo_evento":      "cfn_tipoevento",
    "bin_id":           "cfn_bin",
    "lote_id":          "cfn_loteplanta",
    "pallet_id":        "cfn_pallet",
    "operator_code":    "cfn_operatorcode",
    "source_system":    "cfn_sourcesystem",
    "source_event_id":  "cfn_sourceeventid",
    "occurred_at":      "cfn_occurredat",
    "payload":          "cfn_payload",
    "notes":            "cfn_notes",
    "created_at":       "createdon",
    "updated_at":       "modifiedon",
}

CAMARA_MANTENCION_FIELDS = {
    "id":                   "cfn_camaramantencionid",
    "lote_id":              "cfn_loteplanta",
    "camara_numero":        "cfn_camaranumero",
    "fecha_ingreso":        "cfn_fechaingreso",
    "hora_ingreso":         "cfn_horaingreso",
    "fecha_salida":         "cfn_fechasalida",
    "hora_salida":          "cfn_horasalida",
    "temperatura_camara":   "cfn_temperaturacamara",
    "humedad_relativa":     "cfn_humedadrelativa",
    "observaciones":        "cfn_observaciones",
    "rol":                  "cfn_rol",
    "operator_code":        "cfn_operatorcode",
    "created_at":           "createdon",
    "updated_at":           "modifiedon",
}

DESVERDIZADO_FIELDS = {
    "id":                       "cfn_desverdizadoid",
    "lote_id":                  "cfn_loteplanta",
    "fecha_ingreso":            "cfn_fechaingreso",
    "hora_ingreso":             "cfn_horaingreso",
    "fecha_salida":             "cfn_fechasalida",
    "hora_salida":              "cfn_horasalida",
    "kilos_enviados_terreno":   "cfn_kiloseenviadosterreno",
    "kilos_recepcionados":      "cfn_kilosrecepcionados",
    "kilos_procesados":         "cfn_kilosprocesados",
    "kilos_bruto_salida":       "cfn_kilosbrutosalida",
    "kilos_neto_salida":        "cfn_kilosnetosalida",
    "color_salida":             "cfn_colorsalida",
    "proceso":                  "cfn_proceso",
    "fecha_proceso":            "cfn_fechaproceso",
    "sector":                   "cfn_sector",
    "cuartel":                  "cfn_cuartel",
    "rol":                      "cfn_rol",
    "operator_code":            "cfn_operatorcode",
    "created_at":               "createdon",
    "updated_at":               "modifiedon",
}

CALIDAD_DESVERDIZADO_FIELDS = {
    "id":                   "cfn_calidaddesverdizadoid",
    "lote_id":              "cfn_loteplanta",
    "fecha":                "cfn_fecha",
    "hora":                 "cfn_hora",
    "temperatura_fruta":    "cfn_temperaturafruta",
    "color_evaluado":       "cfn_colorevaluado",
    "estado_visual":        "cfn_estadovisual",
    "presencia_defectos":   "cfn_presenciadefectos",
    "descripcion_defectos": "cfn_descripciondefectos",
    "aprobado":             "cfn_aprobado",
    "observaciones":        "cfn_observaciones",
    "rol":                  "cfn_rol",
    "operator_code":        "cfn_operatorcode",
    "created_at":           "createdon",
    "updated_at":           "modifiedon",
}

INGRESO_PACKING_FIELDS = {
    "id":                           "cfn_ingresoapackingid",
    "lote_id":                      "cfn_loteplanta",
    "fecha_ingreso":                "cfn_fechaingreso",
    "hora_ingreso":                 "cfn_horaingreso",
    "kilos_bruto_ingreso_packing":  "cfn_kilosbrutoingresspacking",
    "kilos_neto_ingreso_packing":   "cfn_kilosnetoingresspacking",
    "via_desverdizado":             "cfn_viadesverdizado",
    "observaciones":                "cfn_observaciones",
    "rol":                          "cfn_rol",
    "operator_code":                "cfn_operatorcode",
    "created_at":                   "createdon",
    "updated_at":                   "modifiedon",
}

REGISTRO_PACKING_FIELDS = {
    "id":                       "cfn_registropackingid",
    "lote_id":                  "cfn_loteplanta",
    "fecha":                    "cfn_fecha",
    "hora_inicio":              "cfn_horainicio",
    "linea_proceso":            "cfn_lineaproceso",
    "categoria_calidad":        "cfn_categoriacalidad",
    "calibre":                  "cfn_calibre",
    "tipo_envase":              "cfn_tipoenvase",
    "cantidad_cajas_producidas":"cfn_cantidadcajasproducidas",
    "peso_promedio_caja_kg":    "cfn_pesopromedioecaja",
    "merma_seleccion_pct":      "cfn_mermaseleccionpct",
    "rol":                      "cfn_rol",
    "operator_code":            "cfn_operatorcode",
    "created_at":               "createdon",
    "updated_at":               "modifiedon",
}

CONTROL_PROCESO_PACKING_FIELDS = {
    "id":                       "cfn_controlprocesopacking",
    "lote_id":                  "cfn_loteplanta",
    "fecha":                    "cfn_fecha",
    "hora":                     "cfn_hora",
    "n_bins_procesados":        "cfn_nbinsprocesados",
    "temp_agua_tina":           "cfn_tempaguatina",
    "ph_agua":                  "cfn_phagua",
    "recambio_agua":            "cfn_recambioagua",
    "rendimiento_lote_pct":     "cfn_rendimientolotepct",
    "observaciones_generales":  "cfn_observacionesgenerales",
    "rol":                      "cfn_rol",
    "operator_code":            "cfn_operatorcode",
    "created_at":               "createdon",
    "updated_at":               "modifiedon",
}

CALIDAD_PALLET_FIELDS = {
    "id":                   "cfn_calidadpalletid",
    "pallet_id":            "cfn_pallet",
    "fecha":                "cfn_fecha",
    "hora":                 "cfn_hora",
    "temperatura_fruta":    "cfn_temperaturafruta",
    "peso_caja_muestra":    "cfn_pesocajamuestra",
    "estado_embalaje":      "cfn_estadoembalaje",
    "estado_visual_fruta":  "cfn_estadovisualfruta",
    "presencia_defectos":   "cfn_presenciadefectos",
    "descripcion_defectos": "cfn_descripciondefectos",
    "aprobado":             "cfn_aprobado",
    "observaciones":        "cfn_observaciones",
    "rol":                  "cfn_rol",
    "operator_code":        "cfn_operatorcode",
    "created_at":           "createdon",
    "updated_at":           "modifiedon",
}

CAMARA_FRIO_FIELDS = {
    "id":                   "cfn_camarafrioid",
    "pallet_id":            "cfn_pallet",
    "camara_numero":        "cfn_camaranumero",
    "temperatura_camara":   "cfn_temperaturacamara",
    "humedad_relativa":     "cfn_humedadrelativa",
    "fecha_ingreso":        "cfn_fechaingreso",
    "hora_ingreso":         "cfn_horaingreso",
    "fecha_salida":         "cfn_fechasalida",
    "hora_salida":          "cfn_horasalida",
    "destino_despacho":     "cfn_destinodespacho",
    "rol":                  "cfn_rol",
    "operator_code":        "cfn_operatorcode",
    "created_at":           "createdon",
    "updated_at":           "modifiedon",
}

MEDICION_TEMPERATURA_FIELDS = {
    "id":                   "cfn_mediciontemperaturasalidaid",
    "pallet_id":            "cfn_pallet",
    "fecha":                "cfn_fecha",
    "hora":                 "cfn_hora",
    "temperatura_pallet":   "cfn_temperaturapallet",
    "punto_medicion":       "cfn_puntomedicion",
    "dentro_rango":         "cfn_dentrorango",
    "observaciones":        "cfn_observaciones",
    "rol":                  "cfn_rol",
    "operator_code":        "cfn_operatorcode",
    "created_at":           "createdon",
    "updated_at":           "modifiedon",
}

# ---------------------------------------------------------------------------
# Alternate key names
# ---------------------------------------------------------------------------

BIN_ALTERNATE_KEY        = "cfn_bincode"
LOTE_PLANTA_ALTERNATE_KEY = "cfn_lotecode"

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
