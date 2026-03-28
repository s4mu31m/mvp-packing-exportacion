"""
Mapa de entidades y campos entre el dominio Python y Dataverse Web API (OData v4).

IMPORTANTE — Convenciones y supuestos:
  - El prefijo de publisher usado es ``cfn_`` (configurado en Power Platform).
  - Los nombres aquí son supuestos razonables.  Deben validarse contra el esquema
    real del ambiente Dataverse una vez que el equipo de Power Platform entregue
    el modelo de datos definitivo.
  - Si los nombres reales difieren, basta con actualizar las constantes de este
    módulo; la lógica de repositorios y casos de uso no cambia.

Referencia: https://learn.microsoft.com/es-es/power-apps/developer/data-platform/webapi/overview
"""

# ---------------------------------------------------------------------------
# Entity set names  (URL path segment en /api/data/v9.2/<EntitySetName>)
# ---------------------------------------------------------------------------

ENTITY_SET_BIN             = "cfn_bins"
ENTITY_SET_LOTE            = "cfn_lotes"
ENTITY_SET_PALLET          = "cfn_pallets"
ENTITY_SET_BIN_LOTE        = "cfn_binlotes"
ENTITY_SET_PALLET_LOTE     = "cfn_palletlotes"
ENTITY_SET_REGISTRO_ETAPA  = "cfn_registroetapas"

# ---------------------------------------------------------------------------
# Logical names  (para EntityDefinitions y metadatos)
# ---------------------------------------------------------------------------

LOGICAL_NAME_BIN            = "cfn_bin"
LOGICAL_NAME_LOTE           = "cfn_lote"
LOGICAL_NAME_PALLET         = "cfn_pallet"
LOGICAL_NAME_BIN_LOTE       = "cfn_binlote"
LOGICAL_NAME_PALLET_LOTE    = "cfn_palletlote"
LOGICAL_NAME_REGISTRO_ETAPA = "cfn_registroetapa"

# ---------------------------------------------------------------------------
# Field maps  dominio → Dataverse OData field name
# ---------------------------------------------------------------------------

BIN_FIELDS = {
    "id":               "cfn_binid",        # GUID, PK en Dataverse
    "temporada":        "cfn_temporada",
    "bin_code":         "cfn_bincode",      # Alternate key recomendada
    "operator_code":    "cfn_operatorcode",
    "source_system":    "cfn_sourcesystem",
    "source_event_id":  "cfn_sourceeventid",
    "is_active":        "cfn_isactive",
    "created_at":       "createdon",
    "updated_at":       "modifiedon",
}

LOTE_FIELDS = {
    "id":               "cfn_loteid",
    "temporada":        "cfn_temporada",
    "lote_code":        "cfn_lotecode",     # Alternate key recomendada
    "operator_code":    "cfn_operatorcode",
    "source_system":    "cfn_sourcesystem",
    "source_event_id":  "cfn_sourceeventid",
    "is_active":        "cfn_isactive",
    "created_at":       "createdon",
    "updated_at":       "modifiedon",
}

PALLET_FIELDS = {
    "id":               "cfn_palletid",
    "temporada":        "cfn_temporada",
    "pallet_code":      "cfn_palletcode",
    "operator_code":    "cfn_operatorcode",
    "source_system":    "cfn_sourcesystem",
    "source_event_id":  "cfn_sourceeventid",
    "is_active":        "cfn_isactive",
    "created_at":       "createdon",
    "updated_at":       "modifiedon",
}

BIN_LOTE_FIELDS = {
    "id":               "cfn_binloteid",
    "bin_id":           "cfn_bin",          # Lookup a cfn_bin (se envía como @odata.bind)
    "lote_id":          "cfn_lote",         # Lookup a cfn_lote
    "operator_code":    "cfn_operatorcode",
    "source_system":    "cfn_sourcesystem",
    "source_event_id":  "cfn_sourceeventid",
}

PALLET_LOTE_FIELDS = {
    "id":               "cfn_palletloteid",
    "pallet_id":        "cfn_pallet",       # Lookup a cfn_pallet
    "lote_id":          "cfn_lote",         # Lookup a cfn_lote
    "operator_code":    "cfn_operatorcode",
    "source_system":    "cfn_sourcesystem",
    "source_event_id":  "cfn_sourceeventid",
}

REGISTRO_ETAPA_FIELDS = {
    "id":               "cfn_registroetapaid",
    "temporada":        "cfn_temporada",
    "event_key":        "cfn_eventkey",     # Clave idempotente (unique)
    "tipo_evento":      "cfn_tipoevento",
    "bin_id":           "cfn_bin",          # Lookup a cfn_bin
    "lote_id":          "cfn_lote",         # Lookup a cfn_lote
    "pallet_id":        "cfn_pallet",       # Lookup a cfn_pallet
    "operator_code":    "cfn_operatorcode",
    "source_system":    "cfn_sourcesystem",
    "source_event_id":  "cfn_sourceeventid",
    "occurred_at":      "cfn_occurredat",
    "payload":          "cfn_payload",      # JSON serializado como texto multilínea
    "notes":            "cfn_notes",
    "created_at":       "createdon",
    "updated_at":       "modifiedon",
}

# ---------------------------------------------------------------------------
# Alternate key names  (para upsert / búsqueda por clave de negocio)
# ---------------------------------------------------------------------------

BIN_ALTERNATE_KEY  = "cfn_bincode"
LOTE_ALTERNATE_KEY = "cfn_lotecode"

# ---------------------------------------------------------------------------
# Helpers de construcción OData
# ---------------------------------------------------------------------------

def odata_bind(entity_set: str, guid: str) -> str:
    """Construye el valor @odata.bind para un lookup field."""
    return f"/{entity_set}({guid})"


def select_fields(field_map: dict, keys: list[str]) -> str:
    """Construye el string $select a partir de claves del dominio."""
    return ",".join(field_map[k] for k in keys if k in field_map)
