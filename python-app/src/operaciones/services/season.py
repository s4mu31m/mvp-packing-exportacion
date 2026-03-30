"""
Resolucion de temporada operativa.

La temporada corre aproximadamente de octubre a septiembre del año siguiente.
Regla: si mes >= 10  →  {year}-{year+1}
       si mes <  10  →  {year-1}-{year}

Ejemplos:
  oct-2025  →  "2025-2026"
  ene-2026  →  "2025-2026"
  sep-2026  →  "2025-2026"
  oct-2026  →  "2026-2027"
"""
import datetime


def resolve_temporada_codigo(fecha_operativa=None) -> str:
    """
    Devuelve el codigo de temporada ('YYYY-YYYY+1') correspondiente a la fecha dada.
    Si la fecha no se provee, usa la fecha de hoy.
    Si el negocio provee la temporada explicitamente, debe usarse ese valor directamente
    en lugar de llamar esta funcion.
    """
    if fecha_operativa is None:
        fecha_operativa = datetime.date.today()
    elif isinstance(fecha_operativa, str):
        try:
            fecha_operativa = datetime.date.fromisoformat(fecha_operativa)
        except ValueError:
            fecha_operativa = datetime.date.today()

    year = fecha_operativa.year
    month = fecha_operativa.month
    if month >= 10:
        return f"{year}-{year + 1}"
    return f"{year - 1}-{year}"
