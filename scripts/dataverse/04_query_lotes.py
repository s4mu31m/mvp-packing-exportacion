"""
04_query_lotes — Consulta los últimos 10 lotes en Dataverse.

Nota: el campo `estado` no existe en Dataverse (gap conocido Issue #39).
Se muestra `etapa_actual` como proxy del estado actual del lote.

Ejecutar desde la raíz del repositorio:
    python scripts/dataverse/04_query_lotes.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _setup  # noqa: F401

from infrastructure.dataverse.client import DataverseClient, DataverseAPIError
from infrastructure.dataverse.mapping import ENTITY_SET_LOTE

SELECT_FIELDS = [
    "crf21_id_lote_planta",
    "crf21_fecha_conformacion",
    "crf21_cantidad_bins",
    "crf21_kilos_neto_conformacion",
    "crf21_etapa_actual",
    "createdon",
]


def main() -> dict:
    print("=" * 60)
    print("04 · QUERY LOTES (últimos 10, orden desc por createdon)")
    print("=" * 60)
    print("  Nota: campo 'estado' no existe en Dataverse — se muestra etapa_actual")

    try:
        client = DataverseClient()
        data = client.list_rows(
            ENTITY_SET_LOTE,
            select=SELECT_FIELDS,
            top=10,
            orderby="createdon desc",
        )
        rows = data.get("value", [])

        if not rows:
            print("\n  [WARN] No se encontraron registros en crf21_lote_plantas")
            print("\nResultado: WARN")
            print("=" * 60)
            return {"status": "WARN", "message": "Tabla vacía", "data": []}

        print(f"\n  Total registros retornados: {len(rows)}")
        print()
        print(f"  {'lote_code':<20} {'fecha_conf':<12} {'bins':<6} {'kg_neto':<10} {'etapa_actual':<25} {'created'}")
        print("  " + "-" * 95)
        for row in rows:
            code = row.get("crf21_id_lote_planta", "—")
            fecha = str(row.get("crf21_fecha_conformacion", "—"))[:10]
            bins = str(row.get("crf21_cantidad_bins", "—"))
            kg = str(row.get("crf21_kilos_neto_conformacion", "—"))
            etapa = str(row.get("crf21_etapa_actual", "—"))[:25]
            created = str(row.get("createdon", "—"))[:19]
            print(f"  {code:<20} {fecha:<12} {bins:<6} {kg:<10} {etapa:<25} {created}")

        print(f"\nResultado: PASS")
        print("=" * 60)
        return {"status": "PASS", "message": f"{len(rows)} lotes encontrados", "data": rows}

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
