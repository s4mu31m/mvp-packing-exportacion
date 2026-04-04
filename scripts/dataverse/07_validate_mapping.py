"""
07_validate_mapping — Valida que los campos declarados en mapping.py existen
en el schema real de Dataverse.

Para cada entidad llama a:
    GET /api/data/v9.2/EntityDefinitions(LogicalName='{name}')/Attributes?$select=LogicalName

y cruza contra los valores (nombres de campo Dataverse) de los field maps.

Ejecutar desde la raíz del repositorio:
    python scripts/dataverse/07_validate_mapping.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _setup  # noqa: F401

from infrastructure.dataverse.client import DataverseClient, DataverseAPIError
import infrastructure.dataverse.mapping as mapping

# Campos de sistema OData — siempre existen, no están en EntityDefinitions/Attributes
SYSTEM_FIELDS = {"createdon", "modifiedon", "@odata.etag"}

# Pares (logical_name, field_map, alias)
ENTITY_FIELD_MAPS = [
    (mapping.LOGICAL_NAME_BIN,                     mapping.BIN_FIELDS,                     "Bin"),
    (mapping.LOGICAL_NAME_LOTE_PLANTA,              mapping.LOTE_PLANTA_FIELDS,             "LotePlanta"),
    (mapping.LOGICAL_NAME_PALLET,                   mapping.PALLET_FIELDS,                  "Pallet"),
    (mapping.LOGICAL_NAME_BIN_LOTE_PLANTA,          mapping.BIN_LOTE_FIELDS,                "BinLote"),
    (mapping.LOGICAL_NAME_PALLET_LOTE_PLANTA,       mapping.PALLET_LOTE_FIELDS,             "PalletLote"),
    (mapping.LOGICAL_NAME_CAMARA_MANTENCION,        mapping.CAMARA_MANTENCION_FIELDS,       "CamaraMantencion"),
    (mapping.LOGICAL_NAME_DESVERDIZADO,             mapping.DESVERDIZADO_FIELDS,            "Desverdizado"),
    (mapping.LOGICAL_NAME_CALIDAD_DESVERDIZADO,     mapping.CALIDAD_DESVERDIZADO_FIELDS,    "CalidadDesverdizado"),
    (mapping.LOGICAL_NAME_INGRESO_PACKING,          mapping.INGRESO_PACKING_FIELDS,         "IngresoPacking"),
    (mapping.LOGICAL_NAME_REGISTRO_PACKING,         mapping.REGISTRO_PACKING_FIELDS,        "RegistroPacking"),
    (mapping.LOGICAL_NAME_CONTROL_PROCESO_PACKING,  mapping.CONTROL_PROCESO_PACKING_FIELDS, "ControlProcesoPacking"),
    (mapping.LOGICAL_NAME_CALIDAD_PALLET,           mapping.CALIDAD_PALLET_FIELDS,          "CalidadPallet"),
    (mapping.LOGICAL_NAME_CAMARA_FRIO,              mapping.CAMARA_FRIO_FIELDS,             "CamaraFrio"),
    (mapping.LOGICAL_NAME_MEDICION_TEMPERATURA,     mapping.MEDICION_TEMPERATURA_FIELDS,    "MedicionTemperatura"),
    (mapping.LOGICAL_NAME_USUARIO_OPERATIVO,        mapping.USUARIO_OPERATIVO_FIELDS,       "UsuarioOperativo"),
]


def _get_entity_attributes(client: DataverseClient, logical_name: str) -> set[str]:
    """Retorna el conjunto de LogicalName de todos los atributos de la entidad."""
    path = f"EntityDefinitions(LogicalName='{logical_name}')/Attributes"
    params = {"$select": "LogicalName", "$top": 300}
    data = client._request("GET", path, params=params)
    return {attr["LogicalName"] for attr in data.get("value", [])}


def main() -> dict:
    print("=" * 60)
    print("07 · VALIDATE FIELD MAPPING (mapping.py vs schema real)")
    print("=" * 60)
    print("  Campos de sistema (createdon, modifiedon) se omiten.")
    print("  Campos de navegación (_*_value) se omiten (son anotaciones OData).")

    try:
        client = DataverseClient()
    except Exception as exc:
        print(f"  [FAIL] No se pudo crear DataverseClient: {exc}")
        return {"status": "FAIL", "message": str(exc)}

    total_missing = 0
    total_entities = 0
    entities_with_issues = []

    for logical_name, field_map, alias in ENTITY_FIELD_MAPS:
        total_entities += 1
        try:
            actual_fields = _get_entity_attributes(client, logical_name)
        except DataverseAPIError as exc:
            if "404" in str(exc):
                print(f"\n  {alias} ({logical_name}): [FAIL] Entidad no encontrada en Dataverse")
                entities_with_issues.append((alias, ["Entidad no existe"]))
                total_missing += 1
            else:
                print(f"\n  {alias} ({logical_name}): [ERROR] {exc}")
                entities_with_issues.append((alias, [str(exc)]))
            continue

        # Campos declarados en mapping.py para esta entidad
        # Filtrar: excluir campos de sistema y anotaciones de navegación (_*_value)
        declared_dv_fields = [
            dv_field
            for dv_field in field_map.values()
            if dv_field not in SYSTEM_FIELDS and not dv_field.startswith("_")
        ]

        missing = [f for f in declared_dv_fields if f not in actual_fields]
        status = "PASS" if not missing else "WARN"
        mark = "[OK]" if not missing else "[WARN]"

        print(f"\n  {mark} {alias} ({logical_name})")
        print(f"    Campos declarados en mapping.py: {len(declared_dv_fields)}")
        print(f"    Campos en schema real:           {len(actual_fields)}")

        if missing:
            print(f"    Campos AUSENTES en Dataverse ({len(missing)}):")
            for f in missing:
                print(f"      — {f}")
            total_missing += len(missing)
            entities_with_issues.append((alias, missing))
        else:
            print(f"    Todos los campos presentes OK")

    print()
    if not entities_with_issues:
        print("  Resultado global: PASS — todos los campos del mapping existen en Dataverse")
        status = "PASS"
    else:
        print(f"  Resultado global: WARN — {total_missing} campos ausentes en {len(entities_with_issues)} entidades")
        status = "WARN"

    print(f"\nResultado: {status}")
    print("=" * 60)
    return {
        "status": status,
        "message": f"{total_missing} campos ausentes en {len(entities_with_issues)} entidades",
        "data": entities_with_issues,
    }


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result["status"] in ("PASS", "WARN") else 1)
