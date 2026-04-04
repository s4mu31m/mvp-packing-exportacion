"""
08_check_aor_optionset — Descubre los valores enteros del OptionSet crf21_a_o_r.

Llama a la Metadata API de Dataverse para obtener las opciones del campo
crf21_a_o_r en la entidad crf21_bin e imprime el Value (int) y Label de cada
opción.  Ejecutar una vez para saber qué enteros mapear en AOR_DV.

Ejecutar desde la raíz del repositorio:
    python scripts/dataverse/08_check_aor_optionset.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _setup  # noqa: F401

from infrastructure.dataverse.client import DataverseClient, DataverseAPIError


def main() -> None:
    print("=" * 60)
    print("08 · CHECK OPTIONSET VALUES — crf21_a_o_r (crf21_bin)")
    print("=" * 60)

    try:
        client = DataverseClient()
    except Exception as exc:
        print(f"  [FAIL] No se pudo crear DataverseClient: {exc}")
        sys.exit(1)

    path = (
        "EntityDefinitions(LogicalName='crf21_bin')"
        "/Attributes(LogicalName='crf21_a_o_r')"
        "/Microsoft.Dynamics.CRM.PicklistAttributeMetadata"
        "/OptionSet"
    )
    params = {}

    try:
        data = client._request("GET", path, params=params)
    except DataverseAPIError as exc:
        print(f"  [ERROR] {exc}")
        sys.exit(1)

    option_set = data
    options = option_set.get("Options", [])

    if not options:
        print("  [WARN] No se encontraron opciones — verifica que el campo sea de tipo Choice/OptionSet.")
        sys.exit(1)

    print(f"\n  Campo: crf21_a_o_r")
    print(f"  Tipo OptionSet: {option_set.get('OptionSetType', '?')}")
    print(f"\n  Opciones ({len(options)}):")
    for opt in options:
        value = opt.get("Value")
        label_obj = opt.get("Label", {})
        # Intentar obtener etiqueta en español o el primero disponible
        localized = label_obj.get("LocalizedLabels", [])
        label = next(
            (l["Label"] for l in localized if l.get("LanguageCode") in (3082, 1034)),
            localized[0]["Label"] if localized else "?",
        )
        print(f"    Value={value}  Label='{label}'")

    print()
    print("  Copia estos valores en AOR_DV dentro de mapping.py:")
    print("  AOR_DV = {")
    for opt in options:
        value = opt.get("Value")
        localized = opt.get("Label", {}).get("LocalizedLabels", [])
        label = next(
            (l["Label"] for l in localized if l.get("LanguageCode") in (3082, 1034)),
            localized[0]["Label"] if localized else "?",
        )
        print(f'      "{label.lower()}": {value},')
    print("  }")
    print("=" * 60)


if __name__ == "__main__":
    main()
