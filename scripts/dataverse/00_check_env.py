"""
00_check_env — Verifica que las variables de entorno Dataverse estén definidas.

Ejecutar desde la raíz del repositorio:
    python scripts/dataverse/00_check_env.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _setup  # noqa: F401 – configura sys.path, .env, Django settings

REQUIRED = {
    "DATAVERSE_URL":           "URL base de la org (ej. https://org.crm.dynamics.com)",
    "DATAVERSE_TENANT_ID":     "ID del tenant Azure AD (GUID)",
    "DATAVERSE_CLIENT_ID":     "Client ID del App Registration (GUID)",
    "DATAVERSE_CLIENT_SECRET": "Secreto del App Registration",
}

OPTIONAL = {
    "DATAVERSE_API_VERSION": "Versión OData (default: v9.2)",
    "DATAVERSE_TIMEOUT":     "Timeout HTTP en segundos (default: 30)",
}


def main() -> dict:
    print("=" * 60)
    print("00 · CHECK ENV VARS")
    print("=" * 60)

    all_ok = True

    print("\nObligatorias:")
    for key, desc in REQUIRED.items():
        val = os.getenv(key, "")
        if val:
            masked = val[:8] + "***" if len(val) > 8 else "***"
            print(f"  [PASS] {key:<30} = {masked}")
        else:
            print(f"  [FAIL] {key:<30}   — NO DEFINIDA  ({desc})")
            all_ok = False

    print("\nOpcionales:")
    for key, desc in OPTIONAL.items():
        val = os.getenv(key, "")
        label = val if val else "(usando default)"
        print(f"  [INFO] {key:<30} = {label}")

    status = "PASS" if all_ok else "FAIL"
    print(f"\nResultado: {status}")
    print("=" * 60)
    return {"status": status, "message": "Todas las vars presentes" if all_ok else "Faltan vars obligatorias"}


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result["status"] == "PASS" else 1)
