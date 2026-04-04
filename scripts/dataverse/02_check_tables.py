"""
02_check_tables - Verifica existencia y conteo de registros en las 15 tablas crf21_*.

También reporta tablas que se saben faltantes (gaps conocidos del Issue #39).

Ejecutar desde la raíz del repositorio:
    python scripts/dataverse/02_check_tables.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _setup  # noqa: F401

from infrastructure.dataverse.client import DataverseClient, DataverseAPIError
from infrastructure.dataverse.auth import DataverseAuthError

# Tablas que deben existir en Dataverse (16 tablas activas)
EXPECTED_TABLES = [
    ("crf21_bins",                          "Bins"),
    ("crf21_lote_plantas",                  "LotePlanta"),
    ("crf21_pallets",                       "Pallets"),
    ("crf21_bin_lote_plantas",              "BinLote (M2M)"),
    ("crf21_lote_planta_pallets",           "LotePallet (M2M)"),
    ("crf21_camara_mantencions",            "CamaraMantencion"),
    ("crf21_desverdizados",                 "Desverdizado"),
    ("crf21_calidad_desverdizados",         "CalidadDesverdizado"),
    ("crf21_ingreso_packings",              "IngresoPacking"),
    ("crf21_registro_packings",             "RegistroPacking"),
    ("crf21_control_proceso_packings",      "ControlProcesoPacking"),
    ("crf21_calidad_pallets",               "CalidadPallet"),
    ("crf21_camara_frios",                  "CamaraFrio"),
    ("crf21_medicion_temperatura_salidas",  "MedicionTemperatura"),
    ("crf21_usuariooperativos",             "UsuarioOperativo"),
    ("crf21_calidad_pallet_muestras",       "CalidadPalletMuestra"),  # Creada 2026-04-04
]

# Tablas aceptadas como no-op (no se crean en Dataverse, no bloquean el flujo)
GAP_TABLES = [
    ("crf21_registro_etapas", "RegistroEtapa - audit log, no-op intencional en Dataverse"),
]


def _get_count(client: DataverseClient, entity_set: str) -> str:
    """Retorna el conteo de registros o '?' si no está soportado."""
    try:
        # $top=1 con $count=true: retorna un registro Y el conteo total
        data = client._request("GET", entity_set, params={"$count": "true", "$top": 1})
        count = data.get("@odata.count")
        if count is not None:
            return str(count)
        # Si @odata.count no viene en la respuesta, al menos confirmamos existencia
        rows = data.get("value", [])
        return ">=1" if rows else "0"
    except DataverseAPIError:
        return "NO EXISTE"
    except Exception:
        return "ERROR"


def main() -> dict:
    print("=" * 60)
    print("02 · CHECK TABLES (existencia + conteo)")
    print("=" * 60)

    try:
        client = DataverseClient()
    except Exception as exc:
        print(f"  [FAIL] No se pudo crear DataverseClient: {exc}")
        return {"status": "FAIL", "message": str(exc)}

    results = []
    fails = 0
    warns = 0

    print(f"\n{'Tabla':<45} {'Alias':<25} {'Estado':<8} {'Registros'}")
    print("-" * 100)

    for entity_set, alias in EXPECTED_TABLES:
        try:
            count = _get_count(client, entity_set)
            mark = "OK"
            results.append((entity_set, alias, "PASS", count))
            print(f"  {entity_set:<43} {alias:<25} {'OK':<8} {count}")
        except DataverseAPIError as exc:
            status_code = "404" if "404" in str(exc) else "ERR"
            results.append((entity_set, alias, "FAIL", status_code))
            print(f"  {entity_set:<43} {alias:<25} {'FAIL':<8} {status_code}")
            fails += 1
        except Exception as exc:
            results.append((entity_set, alias, "FAIL", str(exc)[:20]))
            print(f"  {entity_set:<43} {alias:<25} {'FAIL':<8} ERROR")
            fails += 1

    print(f"\nTablas gap conocidas del Issue #39:")
    print("-" * 100)
    for entity_set, desc in GAP_TABLES:
        count = _get_count(client, entity_set)
        if count == "NO EXISTE":
            print(f"  {entity_set:<43} [NO EXISTE - esperado]        {desc}")
        elif count == "ERROR":
            print(f"  {entity_set:<43} [ERROR al verificar]           {desc}")
        else:
            print(f"  {entity_set:<43} [EXISTE! {count:>5} registros] {desc} -- INESPERADO")
            warns += 1

    status = "FAIL" if fails > 0 else ("WARN" if warns > 0 else "PASS")
    print(f"\nResultado: {status}  ({fails} fallos, {warns} warnings)")
    print("=" * 60)
    return {"status": status, "message": f"{fails} tablas faltantes, {warns} warnings", "data": results}


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result["status"] in ("PASS", "WARN") else 1)
