"""
11_validate_e2e — Validación end-to-end del layer de repositorios Dataverse.

Prueba las operaciones principales del layer de repos contra Dataverse real,
sin pasar por las vistas ni los casos de uso. Requiere PERSISTENCE_BACKEND=dataverse
y credenciales Dataverse válidas en .env.

Ejecutar desde la raíz del repositorio:
    python scripts/dataverse/11_validate_e2e.py

Retorna exit code 0 si todos los checks pasan (PASS o WARN).
Retorna exit code 1 si algún check falla con FAIL.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _setup  # noqa: F401  — configura Django settings + sys.path

# Agregar PERSISTENCE_BACKEND al settings mínimo
from django.conf import settings as _dj
if not hasattr(_dj, "PERSISTENCE_BACKEND"):
    # settings.configure() ya fue llamado por _setup; agregar atributo extra
    _dj.PERSISTENCE_BACKEND = "dataverse"

from infrastructure.dataverse.repositories import build_dataverse_repositories


# ── Helpers de resultado ──────────────────────────────────────────────────────

def _ok(label: str, detail: str = "") -> dict:
    msg = f"  [PASS] {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return {"status": "PASS", "label": label}


def _warn(label: str, detail: str = "") -> dict:
    msg = f"  [WARN] {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return {"status": "WARN", "label": label}


def _fail(label: str, detail: str = "") -> dict:
    msg = f"  [FAIL] {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return {"status": "FAIL", "label": label}


# ── Checks individuales ───────────────────────────────────────────────────────

def check_lotes_list_recent(repos) -> dict:
    label = "repos.lotes.list_recent(limit=5)"
    try:
        lotes = repos.lotes.list_recent(limit=5)
        if not lotes:
            return _warn(label, "tabla vacía o sin registros activos")
        return _ok(label, f"{len(lotes)} lotes retornados; primero: {lotes[0].lote_code!r}")
    except Exception as exc:
        return _fail(label, str(exc))


def check_lotes_find_by_code(repos) -> dict:
    label = "repos.lotes.find_by_code(temporada, lote_code)"
    try:
        lotes = repos.lotes.list_recent(limit=1)
        if not lotes:
            return _warn(label, "saltado — no hay lotes en Dataverse para testear lookup")
        sample = lotes[0]
        found = repos.lotes.find_by_code(sample.temporada or "", sample.lote_code)
        if found is None:
            return _fail(label, f"find_by_code({sample.lote_code!r}) retornó None inesperadamente")
        return _ok(label, f"encontrado lote {found.lote_code!r} etapa={found.etapa_actual!r}")
    except Exception as exc:
        return _fail(label, str(exc))


def check_pallets_list_recent(repos) -> dict:
    label = "repos.pallets.list_recent(limit=5)"
    try:
        pallets = repos.pallets.list_recent(limit=5)
        if not pallets:
            return _warn(label, "tabla vacía o sin registros activos")
        return _ok(label, f"{len(pallets)} pallets retornados; primero: {pallets[0].pallet_code!r}")
    except Exception as exc:
        return _fail(label, str(exc))


def check_pallets_find_by_code(repos) -> dict:
    label = "repos.pallets.find_by_code(temporada, pallet_code)"
    try:
        pallets = repos.pallets.list_recent(limit=1)
        if not pallets:
            return _warn(label, "saltado — no hay pallets en Dataverse para testear lookup")
        sample = pallets[0]
        found = repos.pallets.find_by_code(sample.temporada or "", sample.pallet_code)
        if found is None:
            return _fail(label, f"find_by_code({sample.pallet_code!r}) retornó None inesperadamente")
        return _ok(label, f"encontrado pallet {found.pallet_code!r}")
    except Exception as exc:
        return _fail(label, str(exc))


def check_ingresos_find_by_lote(repos) -> dict:
    label = "repos.ingresos_packing.find_by_lote(lote_id)"
    try:
        lotes = repos.lotes.list_recent(limit=10)
        if not lotes:
            return _warn(label, "saltado — no hay lotes en Dataverse")
        # Buscar un lote con ingreso (etapa_actual indica progresión avanzada)
        _CON_INGRESO = ("Ingreso Packing", "Packing / Proceso", "Paletizado",
                        "Calidad Pallet", "Camara Frio", "Temperatura Salida")
        candidato = next((l for l in lotes if l.etapa_actual in _CON_INGRESO), lotes[0])
        ingreso = repos.ingresos_packing.find_by_lote(candidato.id)
        if ingreso is None:
            return _warn(
                label,
                f"lote {candidato.lote_code!r} (etapa={candidato.etapa_actual!r}) no tiene ingreso — "
                "WARN esperado si el lote aún no pasó por Ingreso Packing",
            )
        return _ok(label, f"ingreso encontrado para lote {candidato.lote_code!r}")
    except Exception as exc:
        return _fail(label, str(exc))


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> dict:
    print()
    print("=" * 60)
    print("  11 · VALIDATE E2E — Repositorios Dataverse")
    print("=" * 60)
    print()
    print("  Instanciando repositorios Dataverse...")

    try:
        repos = build_dataverse_repositories()
    except Exception as exc:
        print(f"  [FAIL] No se pudo instanciar repositorios: {exc}")
        print()
        print("Resultado: FAIL")
        print("=" * 60)
        return {"status": "FAIL", "message": str(exc)}

    print("  Repositorios OK. Ejecutando checks...\n")

    checks = [
        check_lotes_list_recent(repos),
        check_lotes_find_by_code(repos),
        check_pallets_list_recent(repos),
        check_pallets_find_by_code(repos),
        check_ingresos_find_by_lote(repos),
    ]

    fails  = sum(1 for c in checks if c["status"] == "FAIL")
    warns  = sum(1 for c in checks if c["status"] == "WARN")
    passes = sum(1 for c in checks if c["status"] == "PASS")

    print()
    print(f"  Resumen: {passes} PASS · {warns} WARN · {fails} FAIL  (de {len(checks)} checks)")

    if fails == 0:
        status = "PASS"
        print("\nResultado: PASS")
    else:
        status = "FAIL"
        print("\nResultado: FAIL")
    print("=" * 60)

    return {"status": status, "passes": passes, "warns": warns, "fails": fails}


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result["status"] in ("PASS", "WARN") else 1)
