"""
01_whoami — Prueba de autenticación: llama WhoAmI() en Dataverse.

Ejecutar desde la raíz del repositorio:
    python scripts/dataverse/01_whoami.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _setup  # noqa: F401

import json
from infrastructure.dataverse.client import DataverseClient, DataverseAPIError
from infrastructure.dataverse.auth import DataverseAuthError


def main() -> dict:
    print("=" * 60)
    print("01 · WHOAMI (autenticación OAuth2)")
    print("=" * 60)
    try:
        client = DataverseClient()
        result = client.whoami()
        print(f"\n  [PASS] Autenticación exitosa")
        print(f"  BusinessUnitId : {result.get('BusinessUnitId')}")
        print(f"  OrganizationId : {result.get('OrganizationId')}")
        print(f"  UserId         : {result.get('UserId')}")
        print(f"\nResultado: PASS")
        print("=" * 60)
        return {"status": "PASS", "message": "Auth OK", "data": result}
    except DataverseAuthError as exc:
        print(f"\n  [FAIL] Error de autenticación: {exc}")
        print(f"\nResultado: FAIL")
        print("=" * 60)
        return {"status": "FAIL", "message": str(exc)}
    except DataverseAPIError as exc:
        print(f"\n  [FAIL] Error de API: {exc}")
        print(f"\nResultado: FAIL")
        print("=" * 60)
        return {"status": "FAIL", "message": str(exc)}
    except Exception as exc:
        print(f"\n  [FAIL] Error inesperado: {exc}")
        print(f"\nResultado: FAIL")
        print("=" * 60)
        return {"status": "FAIL", "message": str(exc)}


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result["status"] == "PASS" else 1)
