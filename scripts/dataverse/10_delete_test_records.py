"""
10_delete_test_records.py

Elimina de Dataverse todos los registros con source_system='test' y sus
registros relacionados (en cascada manual).

Solo crf21_bins y crf21_lote_plantas tienen el campo source_system.
Las tablas hijas se identifican por FK desde los registros raíz.

Orden de eliminación (hijos primero):
  calidad_pallet_muestras, calidad_pallets, camara_frios, medicion_temperatura_salidas
  → lote_planta_pallets → pallets
  → camara_mantencions, desverdizados, calidad_desverdizados,
    ingreso_packings, registro_packings, control_proceso_packings
  → bin_lote_plantas
  → lote_plantas → bins

Uso:
    python scripts/dataverse/10_delete_test_records.py            # dry-run
    python scripts/dataverse/10_delete_test_records.py --confirm  # elimina realmente
"""
from __future__ import annotations
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _setup  # noqa: F401

from infrastructure.dataverse.client import DataverseClient, DataverseAPIError

SOURCE_SYSTEM_FIELD = "crf21_source_system"
OPERATOR_CODE_FIELD = "crf21_operator_code"
TEST_OPERATOR_CODES = ("OP-001", "OP-TEST")
MAX_ROWS = 5000  # techo por consulta; suficiente para datos de test


# ── helpers ───────────────────────────────────────────────────────────────────

def _list_rows(client, entity_set, *, select, filter_expr):
    result = client.list_rows(entity_set, select=select, filter_expr=filter_expr, top=MAX_ROWS)
    return (result or {}).get("value", [])


def _ids_by_fk(client, entity_set, pk_field, fk_field, fk_value):
    """Retorna lista de PKs de entity_set donde fk_field eq fk_value."""
    rows = _list_rows(
        client, entity_set,
        select=[pk_field],
        filter_expr=f"{fk_field} eq {fk_value}",
    )
    return [r[pk_field] for r in rows if r.get(pk_field)]


def _delete_batch(client, entity_set, ids, label, dry_run):
    """Elimina una lista de registros. Deduplica antes de actuar."""
    unique_ids = list(dict.fromkeys(ids))  # dedup preservando orden
    if not unique_ids:
        return 0
    if dry_run:
        print(f"    [dry]  {len(unique_ids):>4}  {label}")
        return len(unique_ids)
    deleted = 0
    for rid in unique_ids:
        try:
            client._request("DELETE", f"{entity_set}({rid})")
            deleted += 1
        except DataverseAPIError as exc:
            msg = str(exc)
            if "404" in msg or "0x80040217" in msg or "does not exist" in msg.lower():
                pass  # ya eliminado (doble referencia deduplicada tarde)
            else:
                print(f"    [WARN]  {label} {rid}: {exc}")
    print(f"    OK  {deleted}/{len(unique_ids)}  {label}")
    return deleted


# ── main ──────────────────────────────────────────────────────────────────────

def main(dry_run: bool) -> dict:
    mode = "DRY-RUN (solo lectura)" if dry_run else "ELIMINACIÓN REAL — IRREVERSIBLE"
    print("=" * 68)
    print(f"  10 · ELIMINAR REGISTROS DE TEST  —  {mode}")
    print("=" * 68)

    client = DataverseClient()

    # ── Fase 1: Descubrir raíces con source_system='test' ─────────────────
    print("\n[1/4]  Buscando bins con source_system='test' y lotes de prueba...")

    test_bins = _list_rows(
        client, "crf21_bins",
        select=["crf21_binid", "crf21_bin_code", SOURCE_SYSTEM_FIELD],
        filter_expr=f"{SOURCE_SYSTEM_FIELD} eq 'test'",
    )
    test_lotes = _list_rows(
        client, "crf21_lote_plantas",
        select=["crf21_lote_plantaid", "crf21_id_lote_planta", OPERATOR_CODE_FIELD, SOURCE_SYSTEM_FIELD],
        filter_expr=(
            f"{OPERATOR_CODE_FIELD} eq '{TEST_OPERATOR_CODES[0]}' or "
            f"{OPERATOR_CODE_FIELD} eq '{TEST_OPERATOR_CODES[1]}' or "
            f"{SOURCE_SYSTEM_FIELD} eq 'test' or "
            f"{SOURCE_SYSTEM_FIELD} eq 'e2e_dataverse'"
        ),
    )

    bin_ids  = [r["crf21_binid"]         for r in test_bins  if r.get("crf21_binid")]
    lote_ids = [r["crf21_lote_plantaid"] for r in test_lotes if r.get("crf21_lote_plantaid")]

    print(f"\n  Bins  source_system=test : {len(bin_ids)}")
    for r in test_bins[:15]:
        print(f"    - {r.get('crf21_bin_code', '—'):<40}  {r['crf21_binid']}")
    if len(bin_ids) > 15:
        print(f"    ... y {len(bin_ids) - 15} más")

    print(f"\n  Lotes operator_code in {TEST_OPERATOR_CODES} o source_system=test : {len(lote_ids)}")
    for r in test_lotes[:15]:
        print(f"    - {r.get('crf21_id_lote_planta', '—'):<40}  {r['crf21_lote_plantaid']}")
    if len(lote_ids) > 15:
        print(f"    ... y {len(lote_ids) - 15} más")

    if not bin_ids and not lote_ids:
        print("\n  Sin registros de test. Nada que hacer.")
        return {"status": "WARN", "deleted": 0}

    # ── Fase 2: Rastrear pallets vinculados a lotes de test ───────────────
    print("\n[2/4]  Rastreando pallets vinculados a lotes de test...")

    pallet_lote_pks: list[str] = []    # PKs de crf21_lote_planta_pallets
    pallet_ids_set: set[str] = set()   # GUIDs de pallets a eliminar

    for lote_id in lote_ids:
        rows = _list_rows(
            client, "crf21_lote_planta_pallets",
            select=["crf21_lote_planta_palletid", "_crf21_pallet_id_value"],
            filter_expr=f"_crf21_lote_planta_id_value eq {lote_id}",
        )
        for r in rows:
            pk = r.get("crf21_lote_planta_palletid")
            pid = r.get("_crf21_pallet_id_value")
            if pk:
                pallet_lote_pks.append(pk)
            if pid:
                pallet_ids_set.add(pid)

    pallet_ids = list(pallet_ids_set)
    print(f"  Pallets vinculados : {len(pallet_ids)}")
    print(f"  Lote-pallet links  : {len(pallet_lote_pks)}")

    # ── Fase 3: Confirmación (solo en modo real) ───────────────────────────
    if not dry_run:
        print(f"\n  ¡ADVERTENCIA! Esto eliminará de forma PERMANENTE e IRREVERSIBLE:")
        print(f"    · {len(bin_ids)} bins de test")
        print(f"    · {len(lote_ids)} lotes de test")
        print(f"    · {len(pallet_ids)} pallets relacionados")
        print(f"    · Todos sus registros hijos")
        if "--force" not in sys.argv:
            confirm = input("\n  Escribe 'si' para confirmar: ").strip().lower()
            if confirm != "si":
                print("  Operación cancelada.")
                return {"status": "CANCELLED", "deleted": 0}
        else:
            print("\n  --force: omitiendo confirmación interactiva.")

    # ── Fase 4: Eliminar en orden (hijos primero) ─────────────────────────
    label_phase = "simulación" if dry_run else "ELIMINANDO"
    print(f"\n[3/4]  {label_phase.upper()}...")
    total = 0

    # 4a. Hijos de pallet
    for pid in pallet_ids:
        for es, pk, label in [
            ("crf21_calidad_pallet_muestras",      "crf21_calidad_pallet_muestraid",       "calidad_pallet_muestras"),
            ("crf21_calidad_pallets",               "crf21_calidad_palletid",               "calidad_pallets"),
            ("crf21_camara_frios",                  "crf21_camara_frioid",                  "camara_frios"),
            ("crf21_medicion_temperatura_salidas",  "crf21_medicion_temperatura_salidaid",  "medicion_temperaturas"),
        ]:
            ids = _ids_by_fk(client, es, pk, "_crf21_pallet_id_value", pid)
            total += _delete_batch(client, es, ids, label, dry_run)

    # 4b. Lote-pallet join records
    total += _delete_batch(client, "crf21_lote_planta_pallets", pallet_lote_pks, "lote_planta_pallets", dry_run)

    # 4c. Pallets
    total += _delete_batch(client, "crf21_pallets", pallet_ids, "pallets", dry_run)

    # 4d. Hijos de lote + bin-lote links (vía lote)
    for lid in lote_ids:
        for es, pk, fk, label in [
            ("crf21_camara_mantencions",       "crf21_camara_mantencionid",       "_crf21_lote_planta_id_value", "camara_mantencions"),
            ("crf21_desverdizados",            "crf21_desverdizadoid",            "_crf21_lote_planta_id_value", "desverdizados"),
            ("crf21_calidad_desverdizados",    "crf21_calidad_desverdizadoid",    "_crf21_lote_planta_id_value", "calidad_desverdizados"),
            ("crf21_ingreso_packings",         "crf21_ingreso_packingid",         "_crf21_lote_planta_id_value", "ingreso_packings"),
            ("crf21_registro_packings",        "crf21_registro_packingid",        "_crf21_lote_planta_id_value", "registro_packings"),
            ("crf21_control_proceso_packings", "crf21_control_proceso_packingid", "_crf21_lote_planta_id_value", "control_proceso_packings"),
            ("crf21_bin_lote_plantas",         "crf21_bin_lote_plantaid",         "_crf21_lote_planta_id_value", "bin_lote_plantas(vía lote)"),
        ]:
            ids = _ids_by_fk(client, es, pk, fk, lid)
            total += _delete_batch(client, es, ids, label, dry_run)

    # 4e. Bin-lote links residuales (vía bin, por si el bin no tenía lote de test)
    for bid in bin_ids:
        ids = _ids_by_fk(client, "crf21_bin_lote_plantas", "crf21_bin_lote_plantaid", "_crf21_bin_id_value", bid)
        total += _delete_batch(client, "crf21_bin_lote_plantas", ids, "bin_lote_plantas(vía bin)", dry_run)

    # 4f. Raíces: lotes y bins (al final)
    total += _delete_batch(client, "crf21_lote_plantas", lote_ids, "lote_plantas", dry_run)
    total += _delete_batch(client, "crf21_bins",         bin_ids,  "bins",         dry_run)

    # ── Resultado ─────────────────────────────────────────────────────────
    print(f"\n[4/4]  Resultado:")
    if dry_run:
        print(f"  Registros que se eliminarían : {total}")
        print(f"\n  Para ejecutar la eliminación real:")
        print(f"    python scripts/dataverse/10_delete_test_records.py --confirm")
    else:
        print(f"  Total registros eliminados   : {total}")

    print("=" * 68)
    return {"status": "PASS", "deleted": total}


if __name__ == "__main__":
    is_dry_run = "--confirm" not in sys.argv
    try:
        result = main(dry_run=is_dry_run)
        sys.exit(0 if result["status"] in ("PASS", "WARN") else 1)
    except DataverseAPIError as exc:
        print(f"\n[FAIL] Error de API Dataverse: {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n  Cancelado por el usuario.")
        sys.exit(1)
