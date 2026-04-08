from __future__ import annotations

import datetime as dt
import time
from dataclasses import dataclass
from functools import lru_cache
from uuid import uuid4

from domain.repositories.base import Repositories
from operaciones.application.use_cases import (
    agregar_bin_a_lote_abierto,
    cerrar_lote_recepcion,
    cerrar_pallet,
    iniciar_lote_recepcion,
    registrar_camara_mantencion,
    registrar_control_proceso_packing,
    registrar_desverdizado,
    registrar_ingreso_packing,
    registrar_registro_packing,
)


TEMPORADA = str(dt.date.today().year)


@dataclass
class SeededLote:
    temporada: str
    lote_id: object
    lote_code: str
    productor: str
    variedad: str
    tipo_cultivo: str
    color: str
    fecha_cosecha: str
    kilos_bruto: int
    kilos_neto: int
    requiere_desverdizado: bool
    via_desverdizado: bool
    token: str


@dataclass
class SeededPallet:
    temporada: str
    pallet_id: object
    pallet_code: str
    lote: SeededLote


def _assert_ok(result, step: str) -> None:
    if result.ok:
        return
    detail = "; ".join(result.errors or []) if getattr(result, "errors", None) else result.message
    raise AssertionError(f"{step} fallo: {detail}")


def wait_for(description: str, loader, *, timeout: float = 20.0, interval: float = 1.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = loader()
        if value:
            return value
        time.sleep(interval)
    raise AssertionError(f"Timeout esperando {description} en Dataverse")


@lru_cache(maxsize=1)
def dataverse_entity_sets() -> set[str]:
    from infrastructure.dataverse.client import DataverseClient

    doc = DataverseClient()._request("GET", "")
    return {
        row.get("name") or row.get("url")
        for row in (doc or {}).get("value", [])
        if row.get("name") or row.get("url")
    }


def assert_dataverse_entity_set_published(entity_set_name: str) -> None:
    entity_sets = dataverse_entity_sets()
    if entity_set_name in entity_sets:
        return

    related = sorted(
        name for name in entity_sets
        if "camara" in name.lower() or "calidad" in name.lower()
    )
    hint = ", ".join(related) if related else "sin entity sets relacionados visibles"
    raise AssertionError(
        f"Dataverse real no publica el entity set '{entity_set_name}'. "
        f"No se puede validar persistencia de Control Calidad Cámaras hasta provisionarlo. "
        f"Disponibles: {hint}"
    )


def _token(prefix: str) -> str:
    return f"{prefix}-{dt.datetime.now():%m%d%H%M%S}-{uuid4().hex[:6]}".upper()


def _field_data(token: str, *, roja: bool) -> dict:
    cosecha = dt.date.today().isoformat()
    return {
        "codigo_productor": f"PROD-{token}",
        "nombre_productor": f"Productor {token}",
        "tipo_cultivo": "Uva de mesa",
        "variedad_fruta": "Red Globe" if roja else "Thompson Seedless",
        "numero_cuartel": f"C-{token[-2:]}",
        "nombre_cuartel": f"Cuartel {token[-4:]}",
        "predio": f"Predio {token[-4:]}",
        "sector": "Sector Norte",
        "fecha_cosecha": cosecha,
        "color": "5" if roja else "2",
        "a_o_r": "objetado" if roja else "aprobado",
        "hora_recepcion": "08:30",
        "kilos_bruto_ingreso": 610.0 if roja else 520.0,
        "kilos_neto_ingreso": 585.0 if roja else 498.0,
        "observaciones": f"E2E Dataverse {token}",
    }


def seed_closed_lote(
    repos: Repositories,
    *,
    requiere_desverdizado: bool = False,
    disponibilidad: str = "",
    roja: bool = False,
) -> SeededLote:
    token = _token("L")
    data = _field_data(token, roja=roja)
    operator_code = f"E2E-{token[-4:]}"

    start = iniciar_lote_recepcion({
        "temporada": TEMPORADA,
        "operator_code": operator_code,
        "source_system": "e2e_dataverse",
        "source_event_id": f"{token}-START",
    }, repos=repos)
    _assert_ok(start, "iniciar_lote_recepcion")
    lote_code = start.data["lote_code"]

    add_bin = agregar_bin_a_lote_abierto({
        "temporada": TEMPORADA,
        "lote_code": lote_code,
        "operator_code": operator_code,
        "source_system": "e2e_dataverse",
        "source_event_id": f"{token}-BIN-1",
        **data,
    }, repos=repos)
    _assert_ok(add_bin, "agregar_bin_a_lote_abierto")

    close = cerrar_lote_recepcion({
        "temporada": TEMPORADA,
        "lote_code": lote_code,
        "operator_code": operator_code,
        "source_system": "e2e_dataverse",
        "source_event_id": f"{token}-CLOSE",
        "requiere_desverdizado": requiere_desverdizado,
        "disponibilidad_camara_desverdizado": disponibilidad,
        "kilos_bruto_conformacion": float(data["kilos_bruto_ingreso"]),
        "kilos_neto_conformacion": float(data["kilos_neto_ingreso"]),
    }, repos=repos)
    _assert_ok(close, "cerrar_lote_recepcion")

    lote = repos.lotes.find_by_code(TEMPORADA, lote_code)
    if not lote:
        raise AssertionError(f"No se encontro el lote {lote_code} tras cierre en Dataverse")

    return SeededLote(
        temporada=TEMPORADA,
        lote_id=lote.id,
        lote_code=lote_code,
        productor=data["codigo_productor"],
        variedad=data["variedad_fruta"],
        tipo_cultivo=data["tipo_cultivo"],
        color=data["color"],
        fecha_cosecha=data["fecha_cosecha"],
        kilos_bruto=int(float(data["kilos_bruto_ingreso"])),
        kilos_neto=int(float(data["kilos_neto_ingreso"])),
        requiere_desverdizado=requiere_desverdizado,
        via_desverdizado=False,
        token=token,
    )


def seed_lote_with_desverdizado(repos: Repositories) -> SeededLote:
    lote = seed_closed_lote(
        repos,
        requiere_desverdizado=True,
        disponibilidad="no_disponible",
        roja=True,
    )
    operator_code = f"E2E-{lote.token[-4:]}"

    mantencion = registrar_camara_mantencion({
        "temporada": lote.temporada,
        "lote_code": lote.lote_code,
        "operator_code": operator_code,
        "source_system": "e2e_dataverse",
        "source_event_id": f"{lote.token}-MANT",
        "extra": {
            "camara_numero": f"CM-{lote.token[-3:]}",
            "fecha_ingreso": lote.fecha_cosecha,
            "hora_ingreso": "09:15",
            "temperatura_camara": 12.0,
            "humedad_relativa": 85.0,
            "observaciones": f"Mantencion {lote.token}",
        },
    }, repos=repos)
    _assert_ok(mantencion, "registrar_camara_mantencion")

    repos.lotes.update(lote.lote_id, {"disponibilidad_camara_desverdizado": "disponible"})

    desverdizado = registrar_desverdizado({
        "temporada": lote.temporada,
        "lote_code": lote.lote_code,
        "operator_code": operator_code,
        "source_system": "e2e_dataverse",
        "source_event_id": f"{lote.token}-DESV",
        "extra": {
            "fecha_ingreso": lote.fecha_cosecha,
            "hora_ingreso": "10:00",
            "color_salida": "4",
            "horas_desverdizado": 72,
            "kilos_enviados_terreno": float(lote.kilos_neto),
            "kilos_recepcionados": float(lote.kilos_neto - 5),
        },
    }, repos=repos)
    _assert_ok(desverdizado, "registrar_desverdizado")

    lote.via_desverdizado = True
    return lote


def seed_lote_with_ingreso_packing(
    repos: Repositories,
    *,
    via_desverdizado: bool,
) -> SeededLote:
    lote = seed_lote_with_desverdizado(repos) if via_desverdizado else seed_closed_lote(repos)
    operator_code = f"E2E-{lote.token[-4:]}"
    ingreso = registrar_ingreso_packing({
        "temporada": lote.temporada,
        "lote_code": lote.lote_code,
        "operator_code": operator_code,
        "source_system": "e2e_dataverse",
        "source_event_id": f"{lote.token}-ING",
        "extra": {
            "fecha_ingreso": lote.fecha_cosecha,
            "hora_ingreso": "11:00",
            "kilos_bruto_ingreso_packing": float(lote.kilos_bruto),
            "kilos_neto_ingreso_packing": float(lote.kilos_neto - 10),
            "via_desverdizado": via_desverdizado,
            "observaciones": f"Ingreso packing {lote.token}",
        },
    }, repos=repos)
    _assert_ok(ingreso, "registrar_ingreso_packing")
    lote.via_desverdizado = via_desverdizado
    return lote


def seed_lote_in_process(
    repos: Repositories,
    *,
    via_desverdizado: bool,
) -> SeededLote:
    lote = seed_lote_with_ingreso_packing(repos, via_desverdizado=via_desverdizado)
    operator_code = f"E2E-{lote.token[-4:]}"

    proceso = registrar_registro_packing({
        "temporada": lote.temporada,
        "lote_code": lote.lote_code,
        "operator_code": operator_code,
        "source_system": "e2e_dataverse",
        "source_event_id": f"{lote.token}-PROC",
        "extra": {
            "fecha": lote.fecha_cosecha,
            "hora_inicio": "11:30",
            "linea_proceso": "L1",
            "categoria_calidad": "Extra",
            "calibre": "XL",
            "tipo_envase": "Caja 8.2kg",
            "cantidad_cajas_producidas": 60,
            "merma_seleccion_pct": 3.5,
        },
    }, repos=repos)
    _assert_ok(proceso, "registrar_registro_packing")

    control = registrar_control_proceso_packing({
        "temporada": lote.temporada,
        "lote_code": lote.lote_code,
        "operator_code": operator_code,
        "source_system": "e2e_dataverse",
        "source_event_id": f"{lote.token}-CTRL",
        "extra": {
            "fecha": lote.fecha_cosecha,
            "hora": "12:00",
            "n_bins_procesados": 4,
            "temp_agua_tina": 4.5,
            "ph_agua": 6.8,
            "recambio_agua": True,
            "rendimiento_lote_pct": 92.0,
            "observaciones_generales": f"Control proceso {lote.token}",
        },
    }, repos=repos)
    _assert_ok(control, "registrar_control_proceso_packing")
    return lote


def seed_pallet_from_lote(repos: Repositories, lote: SeededLote) -> SeededPallet:
    operator_code = f"E2E-{lote.token[-4:]}"
    close = cerrar_pallet({
        "temporada": lote.temporada,
        "lote_codes": [lote.lote_code],
        "operator_code": operator_code,
        "source_system": "e2e_dataverse",
        "source_event_id": f"{lote.token}-PALLET",
    }, repos=repos)
    _assert_ok(close, "cerrar_pallet")

    pallet_code = close.data["pallet_code"]
    pallet = repos.pallets.find_by_code(lote.temporada, pallet_code)
    if not pallet:
        raise AssertionError(f"No se encontro el pallet {pallet_code} tras cierre en Dataverse")

    return SeededPallet(
        temporada=lote.temporada,
        pallet_id=pallet.id,
        pallet_code=pallet_code,
        lote=lote,
    )
