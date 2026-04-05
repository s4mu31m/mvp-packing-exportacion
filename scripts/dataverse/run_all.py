"""
run_all — Ejecuta todos los checks de Dataverse en secuencia y emite un resumen.

Ejecutar desde la raíz del repositorio:
    python scripts/dataverse/run_all.py

El script se detiene ante el primer FAIL de autenticación (01_whoami).
Los demás scripts se ejecutan siempre, incluso si hay WARNings.
"""
import sys
import os
import subprocess
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent

SCRIPTS = [
    ("00_check_env.py",       "Verificar variables de entorno"),
    ("01_whoami.py",          "Probar autenticación OAuth2"),
    ("02_check_tables.py",    "Verificar 15 tablas crf21_*"),
    ("03_query_bins.py",      "Consultar bins"),
    ("04_query_lotes.py",     "Consultar lotes"),
    ("05_query_pallets.py",   "Consultar pallets"),
    ("06_query_usuarios.py",  "Consultar operadores"),
    ("07_validate_mapping.py","Validar field mapping vs schema"),
]

# Scripts opcionales: se ejecutan al final, no bloquean si fallan
OPTIONAL_SCRIPTS = [
    ("11_validate_e2e.py",    "Validación E2E repositorios Dataverse"),
]

# Scripts cuyo fallo detiene la ejecución de los siguientes
BLOCKING = {"00_check_env.py", "01_whoami.py"}


def run_script(script_file: str) -> int:
    """Ejecuta el script como subproceso y retorna el código de salida."""
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script_file)],
        check=False,
    ).returncode


def main():
    print()
    print("=" * 60)
    print("  DATAVERSE DIAGNOSTIC - run_all.py")
    print("=" * 60)
    print()

    summary = []
    blocked = False

    for script_file, description in SCRIPTS + OPTIONAL_SCRIPTS:
        if blocked:
            print(f"  [SKIP] {description} — bloqueado por fallo anterior")
            summary.append((script_file, description, "SKIP"))
            continue

        print(f"\n{'-' * 60}")
        returncode = run_script(script_file)

        if returncode == 0:
            status = "PASS/WARN"
        else:
            status = "FAIL"
            if script_file in BLOCKING:
                blocked = True

        summary.append((script_file, description, status))

    # -- Resumen final ----------------------------------------------------------
    print()
    print("=" * 60)
    print("  RESUMEN")
    print("=" * 60)
    print()

    fails = 0
    for script_file, description, status in summary:
        mark = "OK" if status == "PASS/WARN" else ("!!" if status == "FAIL" else "--")
        print(f"  [{mark}]  {description:<40} {status}")
        if status == "FAIL":
            fails += 1

    print()
    if fails == 0:
        print("  Diagnóstico completado sin fallos críticos.")
        print("  Revisar salida individual para WARNings (tablas vacías, campos ausentes).")
    else:
        print(f"  {fails} script(s) fallaron. Revisar salida arriba para detalles.")
        print("  Próximos pasos:")
        print("    R1 — Si autenticación falla: verificar DATAVERSE_* en .env")
        print("    R2 — Si tablas faltan: crear desde Power Platform Admin")
        print("    R3 — Si campos ausentes: actualizar mapping.py con nombres reales")

    print()
    return fails


if __name__ == "__main__":
    fails = main()
    sys.exit(0 if fails == 0 else 1)
