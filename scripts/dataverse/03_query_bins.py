"""
03_query_bins — Consulta los últimos 10 bins en Dataverse.

Ejecutar desde la raíz del repositorio:
    python scripts/dataverse/03_query_bins.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _setup  # noqa: F401

from infrastructure.dataverse.client import DataverseClient, DataverseAPIError
from infrastructure.dataverse.mapping import ENTITY_SET_BIN

# Campos clave a mostrar (nombres Dataverse)
SELECT_FIELDS = [
    "crf21_bin_code",
    "crf21_fecha_cosecha",
    "crf21_codigo_productor",
    "crf21_nombre_productor",
    "crf21_tipo_cultivo",
    "crf21_variedad_fruta",
    "crf21_kilos_neto_ingreso",
    "createdon",
]


def main() -> dict:
    print("=" * 60)
    print("03 · QUERY BINS (últimos 10, orden desc por createdon)")
    print("=" * 60)

    try:
        client = DataverseClient()
        data = client.list_rows(
            ENTITY_SET_BIN,
            select=SELECT_FIELDS,
            top=10,
            orderby="createdon desc",
        )
        rows = data.get("value", [])

        if not rows:
            print("\n  [WARN] No se encontraron registros en crf21_bins")
            print("\nResultado: WARN")
            print("=" * 60)
            return {"status": "WARN", "message": "Tabla vacía", "data": []}

        print(f"\n  Total registros retornados: {len(rows)}")
        print()
        print(f"  {'bin_code':<45} {'fecha_cosecha':<14} {'productor':<10} {'cultivo':<12} {'kg_neto':<10} {'created'}")
        print("  " + "-" * 110)
        for row in rows:
            code = row.get("crf21_bin_code", "—")
            fecha = str(row.get("crf21_fecha_cosecha", "—"))[:10]
            prod = str(row.get("crf21_codigo_productor", "—"))[:10]
            cultivo = str(row.get("crf21_tipo_cultivo", "—"))[:12]
            kg = str(row.get("crf21_kilos_neto_ingreso", "—"))
            created = str(row.get("createdon", "—"))[:19]
            print(f"  {code:<45} {fecha:<14} {prod:<10} {cultivo:<12} {kg:<10} {created}")

        print(f"\nResultado: PASS")
        print("=" * 60)
        return {"status": "PASS", "message": f"{len(rows)} bins encontrados", "data": rows}

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
