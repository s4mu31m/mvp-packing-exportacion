"""
Generadores de codigos operacionales para Bin, LotePlanta y Pallet.

Reglas:
- Ningun codigo se digita manualmente. El frontend captura atributos base;
  el backend construye el codigo final.
- Los correlativos se obtienen de sequences.get_next_sequence().
- El formato es estable: si negocio necesita otro formato, se cambia aqui
  sin tocar vistas ni formularios.

Formatos:
  bin_code    → {codigo_productor}-{tipo_cultivo}-{variedad_fruta}-{numero_cuartel}-{DDMMYY}-{correlativo:03d}
                Segun hoja "Codigo de barra" del Excel del cliente.
                Ej: "AG01-LM-Eur-C05-120326-001"

                Campos base requeridos por el frontend:
                  - codigo_productor   (Ej: "AG01")
                  - tipo_cultivo       (Ej: "LM")
                  - variedad_fruta     (Ej: "Eur")
                  - numero_cuartel     (Ej: "C05")
                  - fecha_cosecha      (Ej: "2026-03-12" → "120326" en DDMMYY)
                El correlativo es diario por combinacion de los 5 campos base.

  lote_code   → LP-{temporada_codigo}-{correlativo:06d}
                Ej: "LP-2025-2026-000001"

  pallet_code → PA-{YYYYMMDD}-{correlativo:04d}
                Donde YYYYMMDD es la fecha operativa de hoy.
                Ej: "PA-20260329-0012"
"""
import datetime

from operaciones.services.sequences import get_next_sequence
from operaciones.services.season import resolve_temporada_codigo


def build_bin_code(
    codigo_productor: str = "",
    tipo_cultivo: str = "",
    variedad_fruta: str = "",
    numero_cuartel: str = "",
    fecha_cosecha=None,
    **_kwargs,
) -> str:
    """
    Genera el bin_code segun la hoja "Codigo de barra" del Excel del cliente.

    Formato: {codigo_productor}-{tipo_cultivo}-{variedad_fruta}-{numero_cuartel}-{DDMMYY}-{correlativo:03d}
    Ejemplo: AG01-LM-Eur-C05-120326-001

    El correlativo es diario e independiente por combinacion de los 5 campos base
    (es decir, dos productores distintos tienen correlativos independientes en el mismo dia).

    Si alguno de los campos base esta vacio, se sustituye por un placeholder "XX"
    para evitar codigos con guiones dobles.
    """
    fecha = _parse_date(fecha_cosecha) or datetime.date.today()
    fecha_str = fecha.strftime("%d%m%y")  # DDMMYY segun formato del Excel

    cod_prod  = (codigo_productor or "XX").strip()
    cultivo   = (tipo_cultivo or "XX").strip()
    variedad  = (variedad_fruta or "XX").strip()
    cuartel   = (numero_cuartel or "XX").strip()

    # Dimension incluye todos los campos base para que el correlativo sea
    # independiente por combinacion productor+cultivo+variedad+cuartel+fecha
    dimension = f"{cod_prod}|{cultivo}|{variedad}|{cuartel}|{fecha_str}"
    correlativo = get_next_sequence("bin", dimension)

    return f"{cod_prod}-{cultivo}-{variedad}-{cuartel}-{fecha_str}-{correlativo:03d}"


def build_lote_code(temporada_codigo: str, correlativo: int) -> str:
    """
    Construye el lote_code desde el temporada_codigo y el correlativo de temporada.
    """
    return f"LP-{temporada_codigo}-{correlativo:06d}"


def build_pallet_code(fecha=None) -> str:
    """
    Genera el pallet_code desde la fecha operativa (o hoy).
    Obtiene el correlativo diario desde SequenceCounter.
    """
    fecha = _parse_date(fecha) or datetime.date.today()
    dimension = fecha.strftime("%Y%m%d")
    correlativo = get_next_sequence("pallet", dimension)
    return f"PA-{dimension}-{correlativo:04d}"


def next_lote_correlativo(temporada_codigo: str) -> tuple[str, int]:
    """
    Obtiene el siguiente correlativo de lote para la temporada dada y
    devuelve (lote_code, correlativo).
    """
    correlativo = get_next_sequence("lote", temporada_codigo)
    lote_code = build_lote_code(temporada_codigo, correlativo)
    return lote_code, correlativo


# ---------------------------------------------------------------------------
# Helper interno
# ---------------------------------------------------------------------------

def _parse_date(value) -> datetime.date | None:
    if value is None:
        return None
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return None
    return None
