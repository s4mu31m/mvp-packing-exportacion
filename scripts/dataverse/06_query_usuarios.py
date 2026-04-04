"""
06_query_usuarios — Lista los operadores en Dataverse (sin password hash).

Ejecutar desde la raíz del repositorio:
    python scripts/dataverse/06_query_usuarios.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _setup  # noqa: F401

from infrastructure.dataverse.client import DataverseClient, DataverseAPIError
from infrastructure.dataverse.mapping import ENTITY_SET_USUARIO_OPERATIVO

# Excluimos crf21_passwordhash intencionalmente
SELECT_FIELDS = [
    "crf21_usernamelogin",
    "crf21_nombrecompleto",
    "crf21_correo",
    "crf21_rol",
    "crf21_activo",
    "crf21_bloqueado",
    "crf21_codigooperador",
    "createdon",
]


def main() -> dict:
    print("=" * 60)
    print("06 · QUERY USUARIOS (sin password hash)")
    print("=" * 60)

    try:
        client = DataverseClient()
        data = client.list_rows(
            ENTITY_SET_USUARIO_OPERATIVO,
            select=SELECT_FIELDS,
            top=50,
            orderby="createdon asc",
        )
        rows = data.get("value", [])

        if not rows:
            print("\n  [WARN] No se encontraron operadores en crf21_usuariooperativos")
            print("\nResultado: WARN")
            print("=" * 60)
            return {"status": "WARN", "message": "Sin usuarios", "data": []}

        print(f"\n  Total operadores: {len(rows)}")
        print()
        print(f"  {'username':<20} {'nombre':<25} {'rol':<15} {'activo':<8} {'bloqueado':<10} {'código_op'}")
        print("  " + "-" * 95)
        for row in rows:
            username = row.get("crf21_usernamelogin", "—")
            nombre = str(row.get("crf21_nombrecompleto", "—"))[:25]
            rol = str(row.get("crf21_rol", "—"))[:15]
            activo = "Sí" if row.get("crf21_activo") else "No"
            bloqueado = "Sí" if row.get("crf21_bloqueado") else "No"
            codigo = str(row.get("crf21_codigooperador", "—"))
            print(f"  {username:<20} {nombre:<25} {rol:<15} {activo:<8} {bloqueado:<10} {codigo}")

        print(f"\nResultado: PASS")
        print("=" * 60)
        return {"status": "PASS", "message": f"{len(rows)} usuarios encontrados", "data": rows}

    except DataverseAPIError as exc:
        print(f"\n  [FAIL] {exc}")
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
    sys.exit(0 if result["status"] in ("PASS", "WARN") else 1)
