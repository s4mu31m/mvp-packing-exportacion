"""
Helpers compartidos para tests del flujo operativo.
Crean objetos en DB con valores mínimos válidos.
"""
from operaciones.models import Bin, Lote, Pallet, BinLote, PalletLote, DisponibilidadCamara


def make_bin(temporada="2026", bin_code="BIN-001", **kwargs):
    return Bin.objects.create(
        temporada=temporada,
        bin_code=bin_code,
        operator_code=kwargs.pop("operator_code", "OP-TEST"),
        source_system=kwargs.pop("source_system", "test"),
        **kwargs,
    )


def make_lote(temporada="2026", lote_code="LOT-001", **kwargs):
    return Lote.objects.create(
        temporada=temporada,
        lote_code=lote_code,
        operator_code=kwargs.pop("operator_code", "OP-TEST"),
        source_system=kwargs.pop("source_system", "test"),
        **kwargs,
    )


def make_lote_con_desverdizado(temporada="2026", lote_code="LOT-001", disponible=True):
    """Crea un lote configurado para el flujo de desverdizado."""
    disponibilidad = (
        DisponibilidadCamara.DISPONIBLE if disponible
        else DisponibilidadCamara.NO_DISPONIBLE
    )
    return make_lote(
        temporada=temporada,
        lote_code=lote_code,
        requiere_desverdizado=True,
        disponibilidad_camara_desverdizado=disponibilidad,
    )


def make_pallet(temporada="2026", pallet_code="PAL-001", **kwargs):
    return Pallet.objects.create(
        temporada=temporada,
        pallet_code=pallet_code,
        operator_code=kwargs.pop("operator_code", "OP-TEST"),
        source_system=kwargs.pop("source_system", "test"),
        **kwargs,
    )


def base_payload(temporada="2026", **kwargs):
    return {
        "temporada": temporada,
        "operator_code": "OP-TEST",
        "source_system": "test",
        "nombre_cuartel": "Cuartel Test",
        "codigo_sag_csg": "CSG-TEST",
        "codigo_sag_csp": "CSP-TEST",
        "codigo_sdp": "SDP-TEST",
        "lote_productor": "Lote-Test",
        **kwargs,
    }
