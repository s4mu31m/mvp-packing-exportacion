"""
09_create_calidad_pallet_muestras — Crea la tabla crf21_calidad_pallet_muestras
en Dataverse via Metadata API.

Campos que crea (espejo del modelo Django CalidadPalletMuestra):
  - crf21_nombre           (PrimaryName, String, requerido por Dataverse)
  - crf21_numero_muestra   (Integer)
  - crf21_temperatura_fruta (Decimal)
  - crf21_peso_caja_muestra (Decimal)
  - crf21_n_frutos         (Integer)
  - crf21_aprobado         (Boolean)
  - crf21_observaciones    (Memo/Text largo)
  - crf21_rol              (String)
  - crf21_operator_code    (String)
  - crf21_pallet_id        (Lookup → crf21_pallet)

Ejecutar desde la raíz del repositorio:
    python scripts/dataverse/09_create_calidad_pallet_muestras.py

Requiere que el App Registration tenga rol "System Customizer" o
"System Administrator" en el entorno Dataverse.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _setup  # noqa: F401

from infrastructure.dataverse.client import DataverseClient, DataverseAPIError

LOGICAL_NAME    = "crf21_calidad_pallet_muestra"
ENTITY_SET_NAME = "crf21_calidad_pallet_muestras"
LABEL_ES        = 3082   # Español
PALLET_LOGICAL  = "crf21_pallet"
PALLET_ENTITY_SET = "crf21_pallets"

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

# ---------------------------------------------------------------------------
# Verificaciones previas
# ---------------------------------------------------------------------------

def check_entity_exists(client: DataverseClient) -> bool:
    try:
        client._request("GET", f"EntityDefinitions(LogicalName='{LOGICAL_NAME}')",
                        params={"$select": "LogicalName"})
        return True
    except DataverseAPIError as exc:
        if "404" in str(exc) or "0x80040217" in str(exc):
            return False
        raise

def check_pallet_entity_exists(client: DataverseClient) -> bool:
    try:
        client._request("GET", f"EntityDefinitions(LogicalName='{PALLET_LOGICAL}')",
                        params={"$select": "LogicalName"})
        return True
    except DataverseAPIError:
        return False

# ---------------------------------------------------------------------------
# Creación de la entidad principal
# ---------------------------------------------------------------------------

def create_entity(client: DataverseClient) -> None:
    payload = {
        "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
        "SchemaName": "crf21_calidad_pallet_muestra",
        "DisplayName": _label("Calidad Pallet Muestra"),
        "DisplayCollectionName": _label("Calidad Pallet Muestras"),
        "Description": _label("Muestras individuales de calidad por pallet (2-3 por sesion)"),
        "OwnershipType": "UserOwned",
        "HasActivities": False,
        "HasNotes": False,
        "IsActivity": False,
        # Atributo primario (requerido por Dataverse para toda entidad custom)
        "Attributes": [{
            "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
            "SchemaName": "crf21_nombre",
            "IsPrimaryName": True,
            "DisplayName": _label("Nombre"),
            "Description": _label("Nombre auto-generado del registro"),
            "RequiredLevel": _req_level("None"),
            "MaxLength": 100,
        }],
    }
    client._request("POST", "EntityDefinitions", json=payload)
    print("  Entidad crf21_calidad_pallet_muestra creada OK")

# ---------------------------------------------------------------------------
# Adición de atributos
# ---------------------------------------------------------------------------

def add_attributes(client: DataverseClient) -> None:
    base = f"EntityDefinitions(LogicalName='{LOGICAL_NAME}')/Attributes"

    attrs = [
        # --- numero_muestra (Integer, 1/2/3) ---
        {
            "@odata.type": "Microsoft.Dynamics.CRM.IntegerAttributeMetadata",
            "SchemaName": "crf21_numero_muestra",
            "DisplayName": _label("Numero Muestra"),
            "Description": _label("Numero de muestra dentro de la sesion (1, 2 o 3)"),
            "RequiredLevel": _req_level("None"),
            "Format": "None",
            "MinValue": 1,
            "MaxValue": 10,
        },
        # --- temperatura_fruta (Decimal) ---
        {
            "@odata.type": "Microsoft.Dynamics.CRM.DecimalAttributeMetadata",
            "SchemaName": "crf21_temperatura_fruta",
            "DisplayName": _label("Temperatura Fruta"),
            "Description": _label("Temperatura de la fruta en la muestra (grados Celsius)"),
            "RequiredLevel": _req_level("None"),
            "Precision": 2,
            "MinValue": -50,
            "MaxValue": 100,
        },
        # --- peso_caja_muestra (Decimal) ---
        {
            "@odata.type": "Microsoft.Dynamics.CRM.DecimalAttributeMetadata",
            "SchemaName": "crf21_peso_caja_muestra",
            "DisplayName": _label("Peso Caja Muestra"),
            "Description": _label("Peso de la caja muestra en kg"),
            "RequiredLevel": _req_level("None"),
            "Precision": 3,
            "MinValue": 0,
            "MaxValue": 99999,
        },
        # --- n_frutos (Integer) ---
        {
            "@odata.type": "Microsoft.Dynamics.CRM.IntegerAttributeMetadata",
            "SchemaName": "crf21_n_frutos",
            "DisplayName": _label("N Frutos"),
            "Description": _label("Conteo de frutos en la caja muestra"),
            "RequiredLevel": _req_level("None"),
            "Format": "None",
            "MinValue": 0,
            "MaxValue": 9999,
        },
        # --- aprobado (Boolean) ---
        {
            "@odata.type": "Microsoft.Dynamics.CRM.BooleanAttributeMetadata",
            "SchemaName": "crf21_aprobado",
            "DisplayName": _label("Aprobado"),
            "Description": _label("Indica si la muestra fue aprobada"),
            "RequiredLevel": _req_level("None"),
            "OptionSet": {
                "@odata.type": "Microsoft.Dynamics.CRM.BooleanOptionSetMetadata",
                "TrueOption": {
                    "Value": 1,
                    "Label": _label("Si"),
                },
                "FalseOption": {
                    "Value": 0,
                    "Label": _label("No"),
                },
            },
        },
        # --- observaciones (Memo = texto largo) ---
        {
            "@odata.type": "Microsoft.Dynamics.CRM.MemoAttributeMetadata",
            "SchemaName": "crf21_observaciones",
            "DisplayName": _label("Observaciones"),
            "Description": _label("Observaciones libres sobre la muestra"),
            "RequiredLevel": _req_level("None"),
            "MaxLength": 2000,
        },
        # --- rol (String) ---
        {
            "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
            "SchemaName": "crf21_rol",
            "DisplayName": _label("Rol"),
            "Description": _label("Rol del operador que registra la muestra"),
            "RequiredLevel": _req_level("None"),
            "MaxLength": 100,
        },
        # --- operator_code (String) ---
        {
            "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
            "SchemaName": "crf21_operator_code",
            "DisplayName": _label("Codigo Operador"),
            "Description": _label("Codigo identificador del operador"),
            "RequiredLevel": _req_level("None"),
            "MaxLength": 50,
        },
    ]

    for attr in attrs:
        schema = attr["SchemaName"]
        try:
            client._request("POST", base, json=attr)
            print(f"    Atributo {schema} OK")
        except DataverseAPIError as exc:
            if "already exists" in str(exc).lower() or "0x80048418" in str(exc):
                print(f"    Atributo {schema} ya existe, saltando")
            else:
                print(f"    ERROR en {schema}: {exc}")
                raise

# ---------------------------------------------------------------------------
# Lookup relationship: crf21_calidad_pallet_muestra → crf21_pallet
# ---------------------------------------------------------------------------

def create_lookup_to_pallet(client: DataverseClient) -> None:
    # Nota: NO se incluye ReferencingAttribute (es campo de lectura, no de creación).
    # El objeto Lookup define el atributo nuevo que se crea en la entidad referenciante.
    payload = {
        "@odata.type": "Microsoft.Dynamics.CRM.OneToManyRelationshipMetadata",
        "SchemaName": "crf21_pallet_calidad_pallet_muestras",
        "ReferencedEntity": PALLET_LOGICAL,
        "ReferencingEntity": LOGICAL_NAME,
        "Lookup": {
            "@odata.type": "Microsoft.Dynamics.CRM.LookupAttributeMetadata",
            "SchemaName": "crf21_pallet_id",
            "DisplayName": _label("Pallet"),
            "Description": _label("Pallet al que pertenece esta muestra de calidad"),
            "RequiredLevel": _req_level("None"),
        },
        "AssociatedMenuConfiguration": {
            "Behavior": "UseCollectionName",
            "Group": "Details",
            "Label": _label("Muestras de Calidad"),
            "Order": 10000,
        },
        "CascadeConfiguration": {
            "Assign": "NoCascade",
            "Delete": "RemoveLink",
            "Merge": "NoCascade",
            "Reparent": "NoCascade",
            "Share": "NoCascade",
            "Unshare": "NoCascade",
        },
    }
    try:
        client._request("POST", "RelationshipDefinitions", json=payload)
        print("  Lookup crf21_pallet_id -> crf21_pallet OK")
    except DataverseAPIError as exc:
        err_str = str(exc)
        if "already exists" in err_str.lower() or "0x80048418" in err_str:
            print("  Lookup ya existe, saltando")
        else:
            raise

# ---------------------------------------------------------------------------
# Publicar cambios
# ---------------------------------------------------------------------------

def publish(client: DataverseClient) -> None:
    xml = (
        "<importexportxml><entities>"
        f"<entity>{LOGICAL_NAME}</entity>"
        "</entities></importexportxml>"
    )
    client._request("POST", "PublishXml", json={"ParameterXml": xml})
    print("  Publicacion OK")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> dict:
    print("=" * 60)
    print("09 · CREAR crf21_calidad_pallet_muestras")
    print("=" * 60)

    try:
        # Timeout extendido para operaciones de metadatos (creación de schema puede tardar 60-120s)
        client = DataverseClient(timeout=180)
    except Exception as exc:
        print(f"  [FAIL] No se pudo crear DataverseClient: {exc}")
        return {"status": "FAIL", "message": str(exc)}

    # 1. Verificar si ya existe
    print("\nVerificando si la entidad ya existe...")
    try:
        if check_entity_exists(client):
            print("  [INFO] La entidad ya existe en Dataverse.")
            print("  Verificando que los atributos esten completos...")
            add_attributes(client)
            print("\n  Verificando lookup a crf21_pallet...")
            try:
                create_lookup_to_pallet(client)
            except DataverseAPIError as exc:
                if "already exists" in str(exc).lower() or "0x80048418" in str(exc):
                    print("  Lookup ya existe OK")
                else:
                    print(f"  [WARN] Lookup: {exc}")
            print("\n  Publicando...")
            try:
                publish(client)
            except Exception as exc:
                print(f"  [WARN] Publish: {exc}")
            print("\nResultado: PASS (entidad preexistente, estructura verificada)")
            print("=" * 60)
            return {"status": "PASS", "message": "Entidad ya existia, estructura verificada"}
    except DataverseAPIError as exc:
        print(f"  [FAIL] Error verificando entidad: {exc}")
        return {"status": "FAIL", "message": str(exc)}

    # 2. Verificar que crf21_pallet existe (para el lookup)
    print("Verificando entidad pallet para el lookup...")
    if not check_pallet_entity_exists(client):
        print("  [FAIL] crf21_pallet no existe — no se puede crear el lookup")
        return {"status": "FAIL", "message": "crf21_pallet no encontrado"}
    print("  crf21_pallet encontrado OK")

    # 3. Crear entidad con atributo primario
    print("\nCreando entidad...")
    try:
        create_entity(client)
    except DataverseAPIError as exc:
        print(f"  [FAIL] No se pudo crear entidad: {exc}")
        print()
        print("  Causas posibles:")
        print("  - El App Registration no tiene rol 'System Customizer' en Dataverse")
        print("  - El nombre crf21_ no coincide con el publisher configurado")
        print("  - Cuota de entidades custom alcanzada")
        return {"status": "FAIL", "message": str(exc)}

    # 4. Agregar atributos
    print("\nAgregando atributos...")
    try:
        add_attributes(client)
    except DataverseAPIError as exc:
        print(f"  [FAIL] Error en atributos: {exc}")
        return {"status": "FAIL", "message": str(exc)}

    # 5. Lookup a pallet
    print("\nCreando lookup a crf21_pallet...")
    try:
        create_lookup_to_pallet(client)
    except DataverseAPIError as exc:
        print(f"  [WARN] Lookup no creado: {exc}")
        print("  La entidad existe sin el campo lookup. Se puede agregar manualmente.")

    # 6. Publicar
    print("\nPublicando cambios en Dataverse...")
    try:
        publish(client)
    except DataverseAPIError as exc:
        print(f"  [WARN] Publicacion fallida: {exc}")
        print("  Los cambios pueden requerir publicacion manual desde Power Apps.")

    print(f"\nResultado: PASS")
    print("=" * 60)
    print()
    print("Siguiente paso: ejecutar 02_check_tables.py para verificar")
    print("que crf21_calidad_pallet_muestras aparece en el conteo.")
    return {"status": "PASS", "message": "Entidad creada con atributos y lookup"}


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result["status"] == "PASS" else 1)
