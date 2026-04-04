"""
05_query_pallets — Consulta los últimos 10 pallets en Dataverse.

Ejecutar desde la raíz del repositorio:
    python scripts/dataverse/05_query_pallets.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _setup  # noqa: F401

from infrastructure.dataverse.client import DataverseClient, DataverseAPIError
from infrastructure.dataverse.mapping import ENTITY_SET_PALLET

SELECT_FIELDS = [
    "crf21_id_pallet",
    "crf21_fecha",
    "crf21_tipo_caja",
    "crf21_cajas_por_pallet",
    "crf21_peso_total_kg",
    "crf21_destino_mercado",
    "createdon",
]


def main() -> dict:
    print("=" * 60)
    print("05 · QUERY PALLETS (últimos 10, orden desc por createdon)")
    print("=" * 60)

    try:
        client = DataverseClient()
        data = client.list_rows(
            ENTITY_SET_PALLET,
            select=SELECT_FIELDS,
            top=10,
            orderby="createdon desc",
        )
        rows = data.get("value", [])

        if not rows:
            print("\n  [WARN] No se encontraron registros en crf21_pallets")
            print("\nResultado: WARN")
            print("=" * 60)
            return {"status": "WARN", "message": "Tabla vacía", "data": []}

        print(f"\n  Total registros retornados: {len(rows)}")
        print()
        print(f"  {'pallet_code':<20} {'fecha':<12} {'tipo_caja':<12} {'cajas':<6} {'kg_total':<10} {'destino':<15} {'created'}")
        print("  " + "-" * 100)
        for row in rows:
            code = row.get("crf21_id_pallet", "—")
            fecha = str(row.get("crf21_fecha", "—"))[:10]
            tipo = str(row.get("crf21_tipo_caja", "—"))[:12]
            cajas = str(row.get("crf21_cajas_por_pallet", "—"))
            kg = str(row.get("crf21_peso_total_kg", "—"))
            destino = str(row.get("crf21_destino_mercado", "—"))[:15]
            created = str(row.get("createdon", "—"))[:19]
            print(f"  {code:<20} {fecha:<12} {tipo:<12} {cajas:<6} {kg:<10} {destino:<15} {created}")

        print(f"\nResultado: PASS")
        print("=" * 60)
        return {"status": "PASS", "message": f"{len(rows)} pallets encontrados", "data": rows}

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
