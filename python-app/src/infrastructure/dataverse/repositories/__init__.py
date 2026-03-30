"""
Implementaciones Dataverse de los repositorios de dominio.

Cada repositorio usa DataverseClient para realizar operaciones OData v4 contra
el ambiente configurado en las variables de entorno DATAVERSE_*.

ADAPTACIONES BACKEND → DATAVERSE (schema real validado 2026-03-29):
  - Los nombres de tabla y campo provienen del esquema real (prefijo crf21_).
  - ``temporada`` no existe en Dataverse; se filtra por rango de fechas cuando
    sea necesario, o se ignora si el filtro por codigo es suficientemente
    selectivo.
  - ``lote_code`` se almacena en ``crf21_id_lote_planta``.
  - ``pallet_code`` se almacena en ``crf21_id_pallet``.
  - ``estado``, ``temporada_codigo``, ``correlativo_temporada`` no existen en
    Dataverse; el LoteRecord devuelto los rellena con valores por defecto.
  - No existe tabla registro_etapas; DataverseRegistroEtapaRepository es no-op
    (registra en log local sin persistir en Dataverse).
  - DataverseSequenceCounterRepository genera correlativos contando registros
    existentes en Dataverse — no requiere tabla dedicada. No es atomico, pero
    es aceptable para la escala del MVP.

TRANSACCIONES:
  Dataverse Web API no soporta transacciones ACID. En error parcial en
  operaciones multi-paso se requieren compensaciones manuales. Brecha conocida.
"""
from __future__ import annotations

import datetime
import json
import logging
from typing import Any, Optional

from domain.repositories.base import (
    BinAssignmentConflict,
    BinLoteRecord,
    BinRecord,
    BinLoteRepository,
    BinRepository,
    LoteRecord,
    LoteRepository,
    PalletLoteRecord,
    PalletLoteRepository,
    PalletRecord,
    PalletRepository,
    Repositories,
    RegistroEtapaRecord,
    RegistroEtapaRepository,
    SequenceCounterRecord,
    SequenceCounterRepository,
    CamaraMantencionRecord,
    CamaraMantencionRepository,
    DesverdizadoRecord,
    DesverdizadoRepository,
    CalidadDesverdizadoRecord,
    CalidadDesverdizadoRepository,
    IngresoAPackingRecord,
    IngresoAPackingRepository,
    RegistroPackingRecord,
    RegistroPackingRepository,
    ControlProcesoPackingRecord,
    ControlProcesoPackingRepository,
    CalidadPalletRecord,
    CalidadPalletRepository,
    CamaraFrioRecord,
    CamaraFrioRepository,
    MedicionTemperaturaSalidaRecord,
    MedicionTemperaturaSalidaRepository,
)
from infrastructure.dataverse.mapping import (
    ENTITY_SET_BIN,
    ENTITY_SET_BIN_LOTE,
    ENTITY_SET_LOTE,
    ENTITY_SET_PALLET,
    ENTITY_SET_PALLET_LOTE,
    BIN_FIELDS,
    BIN_LOTE_FIELDS,
    LOTE_PLANTA_FIELDS,
    LOTE_FIELDS,
    PALLET_FIELDS,
    PALLET_LOTE_FIELDS,
    odata_bind,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers: OData row → record type
# ---------------------------------------------------------------------------

def _row_to_bin(row: dict) -> BinRecord:
    return BinRecord(
        id=row.get(BIN_FIELDS["id"]),
        temporada="",                               # no existe en Dataverse
        bin_code=row.get(BIN_FIELDS["bin_code"], ""),
        operator_code=row.get(BIN_FIELDS["operator_code"], ""),
        source_system=row.get(BIN_FIELDS["source_system"], "dataverse"),
        source_event_id=row.get(BIN_FIELDS["source_event_id"], ""),
        is_active=row.get("statecode", 0) == 0,
        id_bin=row.get(BIN_FIELDS["id_bin"], ""),
        variedad_fruta=row.get(BIN_FIELDS["variedad_fruta"], ""),
    )


def _row_to_lote(row: dict) -> LoteRecord:
    return LoteRecord(
        id=row.get(LOTE_FIELDS["id"]),
        temporada="",                               # no existe en Dataverse
        lote_code=row.get(LOTE_FIELDS["lote_code"], ""),
        operator_code=row.get(LOTE_FIELDS["operator_code"], ""),
        source_system=row.get(LOTE_FIELDS["source_system"], "dataverse"),
        source_event_id=row.get(LOTE_FIELDS["source_event_id"], ""),
        is_active=row.get("statecode", 0) == 0,
        id_lote_planta=row.get(LOTE_FIELDS["id_lote_planta"], ""),
        cantidad_bins=row.get(LOTE_FIELDS["cantidad_bins"], 0) or 0,
        # estado, temporada_codigo, correlativo_temporada no existen en Dataverse
        estado="abierto",
        temporada_codigo="",
        correlativo_temporada=None,
    )


def _row_to_pallet(row: dict) -> PalletRecord:
    return PalletRecord(
        id=row.get(PALLET_FIELDS["id"]),
        temporada="",                               # no existe en Dataverse
        pallet_code=row.get(PALLET_FIELDS["pallet_code"], ""),
        operator_code=row.get(PALLET_FIELDS["operator_code"], ""),
        source_system="dataverse",
        source_event_id="",
        is_active=row.get("statecode", 0) == 0,
        id_pallet=row.get(PALLET_FIELDS["id_pallet"], ""),
    )


# ---------------------------------------------------------------------------
# BinRepository
# ---------------------------------------------------------------------------

class DataverseBinRepository(BinRepository):

    def __init__(self, client) -> None:
        self._client = client

    def find_by_code(self, temporada: str, bin_code: str) -> Optional[BinRecord]:
        # temporada no existe en Dataverse; filtramos solo por bin_code
        f = f"{BIN_FIELDS['bin_code']} eq '{bin_code}'"
        result = self._client.list_rows(
            ENTITY_SET_BIN,
            select=[BIN_FIELDS[k] for k in (
                "id", "id_bin", "bin_code", "operator_code",
                "source_system", "source_event_id", "variedad_fruta",
            )],
            filter_expr=f,
            top=1,
        )
        rows = (result or {}).get("value", [])
        return _row_to_bin(rows[0]) if rows else None

    def create(
        self,
        temporada: str,
        bin_code: str,
        *,
        operator_code: str = "",
        source_system: str = "dataverse",
        source_event_id: str = "",
        extra: Optional[dict] = None,
    ) -> BinRecord:
        body: dict = {
            BIN_FIELDS["bin_code"]:        bin_code,
            BIN_FIELDS["operator_code"]:   operator_code,
            BIN_FIELDS["source_system"]:   source_system,
            BIN_FIELDS["source_event_id"]: source_event_id,
        }
        # Mapear campos extra conocidos al esquema Dataverse
        extra = extra or {}
        _extra_map = {
            "codigo_productor":  BIN_FIELDS["codigo_productor"],
            "nombre_productor":  BIN_FIELDS["nombre_productor"],
            "tipo_cultivo":      BIN_FIELDS["tipo_cultivo"],
            "variedad_fruta":    BIN_FIELDS["variedad_fruta"],
            "numero_cuartel":    BIN_FIELDS["numero_cuartel"],
            "nombre_cuartel":    BIN_FIELDS["nombre_cuartel"],
            "predio":            BIN_FIELDS["predio"],
            "sector":            BIN_FIELDS["sector"],
            "lote_productor":    BIN_FIELDS["lote_productor"],
            "color":             BIN_FIELDS["color"],
            "estado_fisico":     BIN_FIELDS["estado_fisico"],
            "a_o_r":             BIN_FIELDS["a_o_r"],
            "hora_recepcion":    BIN_FIELDS["hora_recepcion"],
            "kilos_bruto_ingreso": BIN_FIELDS["kilos_bruto_ingreso"],
            "kilos_neto_ingreso":  BIN_FIELDS["kilos_neto_ingreso"],
            "n_cajas_campo":     BIN_FIELDS["n_cajas_campo"],
            "observaciones":     BIN_FIELDS["observaciones"],
            "n_guia":            BIN_FIELDS["n_guia"],
            "transporte":        BIN_FIELDS["transporte"],
            "capataz":           BIN_FIELDS["capataz"],
            "codigo_contratista": BIN_FIELDS["codigo_contratista"],
            "nombre_contratista": BIN_FIELDS["nombre_contratista"],
        }
        for domain_key, dv_field in _extra_map.items():
            if domain_key in extra and extra[domain_key] not in (None, ""):
                body[dv_field] = extra[domain_key]

        row = self._client.create_row(ENTITY_SET_BIN, body) or {}
        return BinRecord(
            id=row.get(BIN_FIELDS["id"]),
            temporada=temporada,
            bin_code=bin_code,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
        )

    def filter_by_codes(self, temporada: str, bin_codes: list[str]) -> list[BinRecord]:
        if not bin_codes:
            return []
        codes_filter = " or ".join(
            f"{BIN_FIELDS['bin_code']} eq '{c}'" for c in bin_codes
        )
        result = self._client.list_rows(
            ENTITY_SET_BIN,
            select=[BIN_FIELDS[k] for k in (
                "id", "id_bin", "bin_code", "operator_code",
                "source_system", "source_event_id", "variedad_fruta",
            )],
            filter_expr=f"({codes_filter})",
            top=len(bin_codes) + 10,
        )
        return [_row_to_bin(r) for r in (result or {}).get("value", [])]


# ---------------------------------------------------------------------------
# LoteRepository
# ---------------------------------------------------------------------------

class DataverseLoteRepository(LoteRepository):

    def __init__(self, client) -> None:
        self._client = client

    def find_by_code(self, temporada: str, lote_code: str) -> Optional[LoteRecord]:
        # lote_code se almacena en crf21_id_lote_planta
        f = f"{LOTE_FIELDS['lote_code']} eq '{lote_code}'"
        result = self._client.list_rows(
            ENTITY_SET_LOTE,
            select=[LOTE_FIELDS[k] for k in (
                "id", "id_lote_planta", "lote_code", "operator_code",
                "source_system", "source_event_id", "cantidad_bins",
            )],
            filter_expr=f,
            top=1,
        )
        rows = (result or {}).get("value", [])
        if not rows:
            return None
        record = _row_to_lote(rows[0])
        record.temporada = temporada
        return record

    def create(
        self,
        temporada: str,
        lote_code: str,
        *,
        operator_code: str = "",
        source_system: str = "dataverse",
        source_event_id: str = "",
        extra: Optional[dict] = None,
    ) -> LoteRecord:
        body: dict = {
            LOTE_FIELDS["lote_code"]:       lote_code,
            LOTE_FIELDS["operator_code"]:   operator_code,
            LOTE_FIELDS["source_system"]:   source_system,
            LOTE_FIELDS["source_event_id"]: source_event_id,
            LOTE_FIELDS["cantidad_bins"]:   0,
        }
        extra = extra or {}
        if "fecha_conformacion" in extra and extra["fecha_conformacion"]:
            body[LOTE_FIELDS["fecha_conformacion"]] = str(extra["fecha_conformacion"])

        row = self._client.create_row(ENTITY_SET_LOTE, body) or {}
        return LoteRecord(
            id=row.get(LOTE_FIELDS["id"]),
            temporada=temporada,
            lote_code=lote_code,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
            estado="abierto",
            temporada_codigo="",
            correlativo_temporada=None,
        )

    def filter_by_codes(self, temporada: str, lote_codes: list[str]) -> list[LoteRecord]:
        if not lote_codes:
            return []
        codes_filter = " or ".join(
            f"{LOTE_FIELDS['lote_code']} eq '{c}'" for c in lote_codes
        )
        result = self._client.list_rows(
            ENTITY_SET_LOTE,
            select=[LOTE_FIELDS[k] for k in (
                "id", "id_lote_planta", "lote_code", "operator_code",
                "source_system", "source_event_id", "cantidad_bins",
            )],
            filter_expr=f"({codes_filter})",
            top=len(lote_codes) + 10,
        )
        records = [_row_to_lote(r) for r in (result or {}).get("value", [])]
        for r in records:
            r.temporada = temporada
        return records

    def update(self, lote_id: Any, fields: dict) -> LoteRecord:
        # Mapear campos del dominio a campos Dataverse (solo los que existen)
        _updatable = {
            "cantidad_bins":            LOTE_FIELDS["cantidad_bins"],
            "kilos_bruto_conformacion": LOTE_FIELDS["kilos_bruto_conformacion"],
            "kilos_neto_conformacion":  LOTE_FIELDS["kilos_neto_conformacion"],
            "requiere_desverdizado":    LOTE_FIELDS["requiere_desverdizado"],
            "disponibilidad_camara_desverdizado": LOTE_FIELDS["disponibilidad_camara_desverdizado"],
            "operator_code":            LOTE_FIELDS["operator_code"],
        }
        body = {
            dv_field: fields[domain_key]
            for domain_key, dv_field in _updatable.items()
            if domain_key in fields
        }
        # Campos no soportados en Dataverse: estado, temporada_codigo,
        # correlativo_temporada — se ignoran silenciosamente.
        if body:
            self._client.update_row(ENTITY_SET_LOTE, str(lote_id), body)

        # Recuperar registro actualizado
        result = self._client.list_rows(
            ENTITY_SET_LOTE,
            select=[LOTE_FIELDS[k] for k in (
                "id", "id_lote_planta", "lote_code", "operator_code",
                "source_system", "source_event_id", "cantidad_bins",
            )],
            filter_expr=f"{LOTE_FIELDS['id']} eq {lote_id}",
            top=1,
        )
        rows = (result or {}).get("value", [])
        return _row_to_lote(rows[0]) if rows else LoteRecord(
            id=lote_id, temporada="", lote_code="",
        )


# ---------------------------------------------------------------------------
# PalletRepository
# ---------------------------------------------------------------------------

class DataversePalletRepository(PalletRepository):

    def __init__(self, client) -> None:
        self._client = client

    def find_by_code(self, temporada: str, pallet_code: str) -> Optional[PalletRecord]:
        f = f"{PALLET_FIELDS['pallet_code']} eq '{pallet_code}'"
        result = self._client.list_rows(
            ENTITY_SET_PALLET,
            select=[PALLET_FIELDS[k] for k in (
                "id", "id_pallet", "pallet_code", "operator_code", "fecha",
            )],
            filter_expr=f,
            top=1,
        )
        rows = (result or {}).get("value", [])
        if not rows:
            return None
        record = _row_to_pallet(rows[0])
        record.temporada = temporada
        return record

    def get_or_create(
        self,
        temporada: str,
        pallet_code: str,
        *,
        operator_code: str = "",
        source_system: str = "dataverse",
        source_event_id: str = "",
        extra: Optional[dict] = None,
    ) -> tuple[PalletRecord, bool]:
        existing = self.find_by_code(temporada, pallet_code)
        if existing:
            return existing, False
        body: dict = {
            PALLET_FIELDS["pallet_code"]:   pallet_code,
            PALLET_FIELDS["operator_code"]: operator_code,
        }
        extra = extra or {}
        for domain_key in ("fecha", "tipo_caja", "cajas_por_pallet", "peso_total_kg", "destino_mercado"):
            if domain_key in extra and extra[domain_key] not in (None, ""):
                body[PALLET_FIELDS[domain_key]] = extra[domain_key]
        row = self._client.create_row(ENTITY_SET_PALLET, body) or {}
        return PalletRecord(
            id=row.get(PALLET_FIELDS["id"]),
            temporada=temporada,
            pallet_code=pallet_code,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
        ), True


# ---------------------------------------------------------------------------
# BinLoteRepository
# ---------------------------------------------------------------------------

class DataverseBinLoteRepository(BinLoteRepository):

    def __init__(self, client) -> None:
        self._client = client

    def create(
        self,
        bin_id: Any,
        lote_id: Any,
        *,
        operator_code: str = "",
        source_system: str = "dataverse",
        source_event_id: str = "",
    ) -> BinLoteRecord:
        body = {
            f"{BIN_LOTE_FIELDS['bin_id']}@odata.bind":  odata_bind(ENTITY_SET_BIN, str(bin_id)),
            f"{BIN_LOTE_FIELDS['lote_id']}@odata.bind": odata_bind(ENTITY_SET_LOTE, str(lote_id)),
        }
        row = self._client.create_row(ENTITY_SET_BIN_LOTE, body) or {}
        return BinLoteRecord(
            id=row.get(BIN_LOTE_FIELDS["id"]),
            bin_id=bin_id,
            lote_id=lote_id,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
        )

    def find_existing_assignments(self, bin_ids: list[Any]) -> list[BinAssignmentConflict]:
        if not bin_ids:
            return []
        ids_filter = " or ".join(
            f"{BIN_LOTE_FIELDS['bin_id_value']} eq {guid}" for guid in bin_ids
        )
        result = self._client.list_rows(
            ENTITY_SET_BIN_LOTE,
            select=[BIN_LOTE_FIELDS["id"],
                    BIN_LOTE_FIELDS["bin_id_value"],
                    BIN_LOTE_FIELDS["lote_id_value"]],
            filter_expr=f"({ids_filter})",
            top=len(bin_ids) + 10,
        )
        conflicts = []
        for row in (result or {}).get("value", []):
            conflicts.append(BinAssignmentConflict(
                bin_code=str(row.get(BIN_LOTE_FIELDS["bin_id_value"], "")),
                lote_code=str(row.get(BIN_LOTE_FIELDS["lote_id_value"], "")),
            ))
        return conflicts


# ---------------------------------------------------------------------------
# PalletLoteRepository
# ---------------------------------------------------------------------------

class DataversePalletLoteRepository(PalletLoteRepository):

    def __init__(self, client) -> None:
        self._client = client

    def find_by_lote(self, lote_id: Any) -> Optional[PalletLoteRecord]:
        f = f"{PALLET_LOTE_FIELDS['lote_id_value']} eq {lote_id}"
        result = self._client.list_rows(
            ENTITY_SET_PALLET_LOTE,
            select=[PALLET_LOTE_FIELDS["id"],
                    PALLET_LOTE_FIELDS["pallet_id_value"],
                    PALLET_LOTE_FIELDS["lote_id_value"]],
            filter_expr=f,
            top=1,
        )
        rows = (result or {}).get("value", [])
        if not rows:
            return None
        row = rows[0]
        return PalletLoteRecord(
            id=row.get(PALLET_LOTE_FIELDS["id"]),
            pallet_id=row.get(PALLET_LOTE_FIELDS["pallet_id_value"]),
            lote_id=lote_id,
        )

    def get_or_create(
        self,
        pallet_id: Any,
        lote_id: Any,
        *,
        operator_code: str = "",
        source_system: str = "dataverse",
        source_event_id: str = "",
    ) -> tuple[PalletLoteRecord, bool]:
        f = (
            f"{PALLET_LOTE_FIELDS['pallet_id_value']} eq {pallet_id}"
            f" and {PALLET_LOTE_FIELDS['lote_id_value']} eq {lote_id}"
        )
        result = self._client.list_rows(
            ENTITY_SET_PALLET_LOTE,
            select=[PALLET_LOTE_FIELDS["id"]],
            filter_expr=f,
            top=1,
        )
        rows = (result or {}).get("value", [])
        if rows:
            return PalletLoteRecord(
                id=rows[0].get(PALLET_LOTE_FIELDS["id"]),
                pallet_id=pallet_id,
                lote_id=lote_id,
            ), False

        body = {
            f"{PALLET_LOTE_FIELDS['pallet_id']}@odata.bind": odata_bind(ENTITY_SET_PALLET, str(pallet_id)),
            f"{PALLET_LOTE_FIELDS['lote_id']}@odata.bind":   odata_bind(ENTITY_SET_LOTE, str(lote_id)),
        }
        row = self._client.create_row(ENTITY_SET_PALLET_LOTE, body) or {}
        return PalletLoteRecord(
            id=row.get(PALLET_LOTE_FIELDS["id"]),
            pallet_id=pallet_id,
            lote_id=lote_id,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
        ), True


# ---------------------------------------------------------------------------
# RegistroEtapaRepository — no-op (no existe tabla en Dataverse)
# ---------------------------------------------------------------------------

class DataverseRegistroEtapaRepository(RegistroEtapaRepository):
    """
    No existe tabla registro_etapas en Dataverse (validado 2026-03-29).
    Los eventos de traza se registran solo en log local. Los casos de uso
    funcionan correctamente: el registro de eventos es informacional y no
    bloquea la logica de negocio.
    """

    def create(
        self,
        *,
        temporada: str,
        event_key: str,
        tipo_evento: str,
        bin_id: Optional[Any] = None,
        lote_id: Optional[Any] = None,
        pallet_id: Optional[Any] = None,
        operator_code: str = "",
        source_system: str = "dataverse",
        source_event_id: str = "",
        payload: Optional[dict] = None,
        notes: str = "",
    ) -> RegistroEtapaRecord:
        logger.info(
            "dataverse:registro_etapa [%s] temporada=%s bin=%s lote=%s pallet=%s payload=%s",
            event_key, temporada, bin_id, lote_id, pallet_id, payload,
        )
        return RegistroEtapaRecord(
            id=None,
            temporada=temporada,
            event_key=event_key,
            tipo_evento=tipo_evento,
            bin_id=bin_id,
            lote_id=lote_id,
            pallet_id=pallet_id,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
            payload=payload or {},
            notes=notes,
        )

    def get_or_create(
        self,
        *,
        event_key: str,
        temporada: str,
        tipo_evento: str,
        bin_id: Optional[Any] = None,
        lote_id: Optional[Any] = None,
        pallet_id: Optional[Any] = None,
        operator_code: str = "",
        source_system: str = "dataverse",
        source_event_id: str = "",
        payload: Optional[dict] = None,
    ) -> tuple[RegistroEtapaRecord, bool]:
        record = self.create(
            temporada=temporada,
            event_key=event_key,
            tipo_evento=tipo_evento,
            bin_id=bin_id,
            lote_id=lote_id,
            pallet_id=pallet_id,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
            payload=payload,
        )
        return record, True

    def list_recent(self, limit: int = 100) -> list[RegistroEtapaRecord]:
        return []


# ---------------------------------------------------------------------------
# SequenceCounterRepository — conteo de registros existentes en Dataverse
# ---------------------------------------------------------------------------

class DataverseSequenceCounterRepository(SequenceCounterRepository):
    """
    Genera correlativos contando registros existentes en Dataverse.
    No es atomico — race conditions posibles bajo alta concurrencia.
    Aceptable para la escala del MVP.

    Estrategias por entidad:
      bin    — cuenta bins con bin_code que empiece por el prefijo de la dimension
      lote   — cuenta lotes en el rango de fechas de la temporada
      pallet — cuenta pallets con fecha en el dia de la dimension
    """

    def __init__(self, client) -> None:
        self._client = client

    def get_next(self, entity_name: str, dimension: str) -> int:
        count = self._count(entity_name, dimension)
        return count + 1

    def current_value(self, entity_name: str, dimension: str) -> int:
        return self._count(entity_name, dimension)

    def _count(self, entity_name: str, dimension: str) -> int:
        try:
            if entity_name == "bin":
                return self._count_bins(dimension)
            if entity_name == "lote":
                return self._count_lotes(dimension)
            if entity_name == "pallet":
                return self._count_pallets(dimension)
        except Exception as exc:
            logger.warning("DataverseSequenceCounter._count(%s, %s) error: %s", entity_name, dimension, exc)
        return 0

    def _count_bins(self, dimension: str) -> int:
        """dimension = 'cod_prod|cultivo|variedad|cuartel|fecha_str'"""
        parts = dimension.split("|")
        prefix = "-".join(parts) + "-"
        result = self._client.list_rows(
            "crf21_bins",
            select=["crf21_bin_code"],
            filter_expr=f"startswith(crf21_bin_code,'{prefix}')",
            top=9999,
        )
        return len((result or {}).get("value", []))

    def _count_lotes(self, dimension: str) -> int:
        """dimension = temporada_codigo like '2025-2026'"""
        try:
            start_year, end_year = dimension.split("-")
            start = f"{start_year}-10-01T00:00:00Z"
            end   = f"{end_year}-09-30T23:59:59Z"
        except ValueError:
            return 0
        result = self._client.list_rows(
            "crf21_lote_plantas",
            select=["crf21_lote_plantaid"],
            filter_expr=(
                f"crf21_fecha_conformacion ge {start}"
                f" and crf21_fecha_conformacion le {end}"
            ),
            top=9999,
        )
        return len((result or {}).get("value", []))

    def _count_pallets(self, dimension: str) -> int:
        """dimension = YYYYMMDD"""
        try:
            d = datetime.date(int(dimension[:4]), int(dimension[4:6]), int(dimension[6:8]))
        except (ValueError, IndexError):
            return 0
        start = f"{d.isoformat()}T00:00:00Z"
        next_d = d + datetime.timedelta(days=1)
        end   = f"{next_d.isoformat()}T00:00:00Z"
        result = self._client.list_rows(
            "crf21_pallets",
            select=["crf21_palletid"],
            filter_expr=f"crf21_fecha ge {start} and crf21_fecha lt {end}",
            top=9999,
        )
        return len((result or {}).get("value", []))


# ---------------------------------------------------------------------------
# Stub implementations para nuevas entidades (pendientes de uso en Dataverse)
# ---------------------------------------------------------------------------

class _DataverseStubMixin:
    _entity_name: str = "entidad"

    def _not_implemented(self, method: str):
        raise NotImplementedError(
            f"DataverseRepository para {self._entity_name}.{method} "
            "no esta implementado aun. Valide el esquema con el equipo de "
            "Power Platform y complete la implementacion OData en este modulo."
        )


class DataverseCamaraMantencionRepository(_DataverseStubMixin, CamaraMantencionRepository):
    _entity_name = "CamaraMantencion"

    def __init__(self, client) -> None:
        self._client = client

    def find_by_lote(self, lote_id: Any): self._not_implemented("find_by_lote")
    def create(self, lote_id, **kw): self._not_implemented("create")
    def update(self, record_id, fields): self._not_implemented("update")


class DataverseDesverdizadoRepository(_DataverseStubMixin, DesverdizadoRepository):
    _entity_name = "Desverdizado"

    def __init__(self, client) -> None:
        self._client = client

    def find_by_lote(self, lote_id: Any): self._not_implemented("find_by_lote")
    def create(self, lote_id, **kw): self._not_implemented("create")
    def update(self, record_id, fields): self._not_implemented("update")


class DataverseCalidadDesverdizadoRepository(_DataverseStubMixin, CalidadDesverdizadoRepository):
    _entity_name = "CalidadDesverdizado"

    def __init__(self, client) -> None:
        self._client = client

    def create(self, lote_id, **kw): self._not_implemented("create")
    def list_by_lote(self, lote_id): self._not_implemented("list_by_lote")


class DataverseIngresoAPackingRepository(_DataverseStubMixin, IngresoAPackingRepository):
    _entity_name = "IngresoAPacking"

    def __init__(self, client) -> None:
        self._client = client

    def find_by_lote(self, lote_id: Any): self._not_implemented("find_by_lote")
    def create(self, lote_id, **kw): self._not_implemented("create")


class DataverseRegistroPackingRepository(_DataverseStubMixin, RegistroPackingRepository):
    _entity_name = "RegistroPacking"

    def __init__(self, client) -> None:
        self._client = client

    def create(self, lote_id, **kw): self._not_implemented("create")
    def list_by_lote(self, lote_id): self._not_implemented("list_by_lote")


class DataverseControlProcesoPackingRepository(_DataverseStubMixin, ControlProcesoPackingRepository):
    _entity_name = "ControlProcesoPacking"

    def __init__(self, client) -> None:
        self._client = client

    def create(self, lote_id, **kw): self._not_implemented("create")
    def list_by_lote(self, lote_id): self._not_implemented("list_by_lote")


class DataverseCalidadPalletRepository(_DataverseStubMixin, CalidadPalletRepository):
    _entity_name = "CalidadPallet"

    def __init__(self, client) -> None:
        self._client = client

    def create(self, pallet_id, **kw): self._not_implemented("create")
    def list_by_pallet(self, pallet_id): self._not_implemented("list_by_pallet")


class DataverseCamaraFrioRepository(_DataverseStubMixin, CamaraFrioRepository):
    _entity_name = "CamaraFrio"

    def __init__(self, client) -> None:
        self._client = client

    def find_by_pallet(self, pallet_id: Any): self._not_implemented("find_by_pallet")
    def create(self, pallet_id, **kw): self._not_implemented("create")
    def update(self, record_id, fields): self._not_implemented("update")


class DataverseMedicionTemperaturaSalidaRepository(_DataverseStubMixin, MedicionTemperaturaSalidaRepository):
    _entity_name = "MedicionTemperaturaSalida"

    def __init__(self, client) -> None:
        self._client = client

    def create(self, pallet_id, **kw): self._not_implemented("create")
    def list_by_pallet(self, pallet_id): self._not_implemented("list_by_pallet")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_dataverse_repositories() -> Repositories:
    from infrastructure.dataverse.client import DataverseClient
    client = DataverseClient()
    return Repositories(
        bins=DataverseBinRepository(client),
        lotes=DataverseLoteRepository(client),
        pallets=DataversePalletRepository(client),
        bin_lotes=DataverseBinLoteRepository(client),
        pallet_lotes=DataversePalletLoteRepository(client),
        registros=DataverseRegistroEtapaRepository(),
        sequences=DataverseSequenceCounterRepository(client),
        camara_mantencions=DataverseCamaraMantencionRepository(client),
        desverdizados=DataverseDesverdizadoRepository(client),
        calidad_desverdizados=DataverseCalidadDesverdizadoRepository(client),
        ingresos_packing=DataverseIngresoAPackingRepository(client),
        registros_packing=DataverseRegistroPackingRepository(client),
        control_proceso_packings=DataverseControlProcesoPackingRepository(client),
        calidad_pallets=DataverseCalidadPalletRepository(client),
        camara_frios=DataverseCamaraFrioRepository(client),
        mediciones_temperatura=DataverseMedicionTemperaturaSalidaRepository(client),
    )
