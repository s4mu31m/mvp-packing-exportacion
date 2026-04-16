"""
12_add_campos_lote_planta — Agrega campos faltantes a entidades existentes.

Campos que crea:
  crf21_lote_planta:
    - crf21_ultimo_cambio_estado_at  (DateTime UTC — timestamp de la ultima transicion de etapa)

  crf21_pallet (misma columna):
    - crf21_ultimo_cambio_estado_at  (DateTime UTC)

Ejecutar desde la raiz del repositorio:
    python scripts/dataverse/12_add_campos_lote_planta.py

Requiere que el App Registration tenga rol "System Customizer" o
"System Administrator" en el entorno Dataverse.

Despues de ejecutar este script exitosamente:
    - Re-habilitar el campo en el repositorio Dataverse:
        1. Agregar "ultimo_cambio_estado_at" a _LOTE_SELECT en repositories/__init__.py
        2. Re-agregar el bloque de escritura en create() y update()
    Ver los comentarios "# PENDIENTE: re-habilitar tras ejecutar 12_add_campos_lote_planta.py"
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _setup  # noqa: F401

from infrastructure.dataverse.client import DataverseClient, DataverseAPIError

LOTE_LOGICAL    = "crf21_lote_planta"
PALLET_LOGICAL  = "crf21_pallet"
LABEL_ES        = 3082   # Español


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _label(text: str) -> dict:
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.Label",
        "LocalizedLabels": [{
            "@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
            "Label": text,
            "LanguageCode": LABEL_ES,
        }],
    }


def _req_level(value="None"):
    return {
        "Value": value,
        "CanBeChanged": True,
        "ManagedPropertyLogicalName": "canmodifyrequirementlevelsettings",
    }


def _field_exists(client: DataverseClient, entity_logical: str, field_logical: str) -> bool:
    """Retorna True si el campo ya existe en la entidad."""
    try:
        client._request(
            "GET",
            f"EntityDefinitions(LogicalName='{entity_logical}')"
            f"/Attributes(LogicalName='{field_logical}')",
            params={"$select": "LogicalName"},
        )
        return True
    except DataverseAPIError as exc:
        err = str(exc)
        if "404" in err or "0x80040217" in err or "does not exist" in err.lower():
            return False
        raise


def _add_datetime_field(
    client: DataverseClient,
    entity_logical: str,
    schema_name: str,
    display_name: str,
    description: str,
) -> None:
    """Agrega un campo DateTimeAttributeMetadata con comportamiento UTC."""
    payload = {
        "@odata.type": "Microsoft.Dynamics.CRM.DateTimeAttributeMetadata",
        "SchemaName": schema_name,
        "DisplayName": _label(display_name),
        "Description": _label(description),
        "RequiredLevel": _req_level("None"),
        # UserLocal = almacena en UTC, muestra ajustado al TZ del usuario
        # TimeZoneIndependent = almacena y muestra siempre UTC (mejor para timestamps)
        "DateTimeBehavior": {
            "Value": "TimeZoneIndependent",
        },
        "Format": "DateAndTime",
    }
    base = f"EntityDefinitions(LogicalName='{entity_logical}')/Attributes"
    client._request("POST", base, json=payload)


def _publish(client: DataverseClient, *entities: str) -> None:
    entity_xml = "".join(f"<entity>{e}</entity>" for e in entities)
    xml = f"<importexportxml><entities>{entity_xml}</entities></importexportxml>"
    client._request("POST", "PublishXml", json={"ParameterXml": xml})


# ---------------------------------------------------------------------------
# Procesamiento por entidad
# ---------------------------------------------------------------------------

FIELDS_TO_ADD = {
    LOTE_LOGICAL: [
        {
            "schema_name":  "crf21_ultimo_cambio_estado_at",
            "display_name": "Ultimo Cambio Estado",
            "description":  (
                "Timestamp UTC del ultimo cambio de etapa operativa del lote. "
                "Se actualiza en cada transicion: Recepcion, Desverdizado, "
                "Ingreso Packing, Proceso, Paletizado, Camara Frio, etc."
            ),
        },
    ],
    PALLET_LOGICAL: [
        {
            "schema_name":  "crf21_ultimo_cambio_estado_at",
            "display_name": "Ultimo Cambio Estado",
            "description":  (
                "Timestamp UTC del ultimo cambio de etapa operativa del pallet."
            ),
        },
    ],
}


def process_entity(client: DataverseClient, entity_logical: str) -> list[str]:
    """Agrega campos faltantes a la entidad. Retorna lista de campos creados."""
    created = []
    for field_def in FIELDS_TO_ADD.get(entity_logical, []):
        schema_name = field_def["schema_name"]
        logical_name = schema_name.lower()
        print(f"  Verificando {schema_name} ...", end=" ")

        if _field_exists(client, entity_logical, logical_name):
            print("ya existe, saltando")
            continue

        print("no existe, creando...", end=" ")
        try:
            _add_datetime_field(
                client,
                entity_logical=entity_logical,
                schema_name=schema_name,
                display_name=field_def["display_name"],
                description=field_def["description"],
            )
            print("OK")
            created.append(schema_name)
        except DataverseAPIError as exc:
            if "already exists" in str(exc).lower() or "0x80048418" in str(exc):
                print("ya existia (race condition), saltando")
            else:
                print(f"ERROR: {exc}")
                raise

    return created


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> dict:
    print("=" * 60)
    print("12 · AGREGAR CAMPOS A ENTIDADES EXISTENTES")
    print("=" * 60)

    try:
        client = DataverseClient(timeout=180)
    except Exception as exc:
        print(f"  [FAIL] No se pudo crear DataverseClient: {exc}")
        return {"status": "FAIL", "message": str(exc)}

    all_created: list[str] = []
    entities_modified: list[str] = []

    for entity_logical in [LOTE_LOGICAL, PALLET_LOGICAL]:
        print(f"\n[{entity_logical}]")
        try:
            created = process_entity(client, entity_logical)
            if created:
                all_created.extend(created)
                entities_modified.append(entity_logical)
        except DataverseAPIError as exc:
            print(f"  [FAIL] Error en {entity_logical}: {exc}")
            return {"status": "FAIL", "message": str(exc)}

    if not entities_modified:
        print("\n[INFO] Todos los campos ya existian. Nada que publicar.")
        print("=" * 60)
        return {"status": "PASS", "message": "Campos ya existian"}

    print(f"\nPublicando cambios en: {', '.join(entities_modified)} ...")
    try:
        _publish(client, *entities_modified)
        print("  Publicacion OK")
    except DataverseAPIError as exc:
        print(f"  [WARN] Publicacion fallida: {exc}")
        print("  Publicar manualmente desde Power Apps > Soluciones.")

    print(f"\nResultado: PASS — campos creados: {all_created}")
    print("=" * 60)
    print()
    print("Proximos pasos:")
    print("  1. Re-habilitar ultimo_cambio_estado_at en el repositorio Dataverse:")
    print("     - Agregar 'ultimo_cambio_estado_at' a _LOTE_SELECT")
    print("     - Re-agregar escritura en create() y update()")
    print("  2. Correr 07_validate_mapping.py para verificar que los campos son visibles")
    print("  3. Correr tests: python -m pytest src/operaciones/tests.py -q")
    return {"status": "PASS", "message": f"Campos creados: {all_created}"}


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result["status"] == "PASS" else 1)
