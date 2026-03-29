"""
Implementaciones Dataverse de los repositorios de dominio.

Cada repositorio usa DataverseClient para realizar operaciones OData v4 contra
el ambiente configurado en las variables de entorno DATAVERSE_*.

SUPUESTOS DE ESQUEMA:
  Los nombres de entity set y campos están definidos en infrastructure/dataverse/mapping.py.
  Deben validarse contra el modelo real de Dataverse antes de usar en producción.
  Ver: docs/arquitectura/preinicio-mvp.md sección "Estrategia de indexación e integración".

TRANSACCIONES:
  Dataverse Web API no soporta transacciones ACID equivalentes a las de una base
  de datos relacional. En caso de error parcial durante operaciones multi-paso, se
  deben implementar compensaciones manuales o usar $batch con rollback semántico.
  Para el MVP esto es una brecha conocida; se documenta en TECHNICAL_CHANGES.md.
"""
from __future__ import annotations

import json
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
    # Nuevas entidades
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
    ENTITY_SET_REGISTRO_ETAPA,
    BIN_FIELDS,
    LOTE_FIELDS,
    PALLET_FIELDS,
    REGISTRO_ETAPA_FIELDS,
    odata_bind,
)


# ---------------------------------------------------------------------------
# Helpers: OData row → record type
# ---------------------------------------------------------------------------

def _row_to_bin(row: dict) -> BinRecord:
    return BinRecord(
        id=row.get(BIN_FIELDS["id"]),
        temporada=row.get(BIN_FIELDS["temporada"], ""),
        bin_code=row.get(BIN_FIELDS["bin_code"], ""),
        operator_code=row.get(BIN_FIELDS["operator_code"], ""),
        source_system=row.get(BIN_FIELDS["source_system"], "dataverse"),
        source_event_id=row.get(BIN_FIELDS["source_event_id"], ""),
        is_active=row.get(BIN_FIELDS["is_active"], True),
    )


def _row_to_lote(row: dict) -> LoteRecord:
    return LoteRecord(
        id=row.get(LOTE_FIELDS["id"]),
        temporada=row.get(LOTE_FIELDS["temporada"], ""),
        lote_code=row.get(LOTE_FIELDS["lote_code"], ""),
        operator_code=row.get(LOTE_FIELDS["operator_code"], ""),
        source_system=row.get(LOTE_FIELDS["source_system"], "dataverse"),
        source_event_id=row.get(LOTE_FIELDS["source_event_id"], ""),
        is_active=row.get(LOTE_FIELDS["is_active"], True),
    )


def _row_to_pallet(row: dict) -> PalletRecord:
    return PalletRecord(
        id=row.get(PALLET_FIELDS["id"]),
        temporada=row.get(PALLET_FIELDS["temporada"], ""),
        pallet_code=row.get(PALLET_FIELDS["pallet_code"], ""),
        operator_code=row.get(PALLET_FIELDS["operator_code"], ""),
        source_system=row.get(PALLET_FIELDS["source_system"], "dataverse"),
        source_event_id=row.get(PALLET_FIELDS["source_event_id"], ""),
        is_active=row.get(PALLET_FIELDS["is_active"], True),
    )


def _row_to_registro(row: dict) -> RegistroEtapaRecord:
    payload_raw = row.get(REGISTRO_ETAPA_FIELDS["payload"], "{}")
    try:
        payload = json.loads(payload_raw) if isinstance(payload_raw, str) else (payload_raw or {})
    except (ValueError, TypeError):
        payload = {}
    return RegistroEtapaRecord(
        id=row.get(REGISTRO_ETAPA_FIELDS["id"]),
        temporada=row.get(REGISTRO_ETAPA_FIELDS["temporada"], ""),
        event_key=row.get(REGISTRO_ETAPA_FIELDS["event_key"], ""),
        tipo_evento=row.get(REGISTRO_ETAPA_FIELDS["tipo_evento"], ""),
        operator_code=row.get(REGISTRO_ETAPA_FIELDS["operator_code"], ""),
        source_system=row.get(REGISTRO_ETAPA_FIELDS["source_system"], "dataverse"),
        source_event_id=row.get(REGISTRO_ETAPA_FIELDS["source_event_id"], ""),
        payload=payload,
        notes=row.get(REGISTRO_ETAPA_FIELDS["notes"], ""),
    )


# ---------------------------------------------------------------------------
# Concrete Dataverse repositories
# ---------------------------------------------------------------------------

class DataverseBinRepository(BinRepository):

    def __init__(self, client) -> None:
        self._client = client

    def find_by_code(self, temporada: str, bin_code: str) -> Optional[BinRecord]:
        f = (
            f"{BIN_FIELDS['temporada']} eq '{temporada}'"
            f" and {BIN_FIELDS['bin_code']} eq '{bin_code}'"
        )
        result = self._client.list_rows(
            ENTITY_SET_BIN,
            select=[BIN_FIELDS[k] for k in ("id", "temporada", "bin_code", "operator_code",
                                              "source_system", "source_event_id", "is_active")],
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
    ) -> BinRecord:
        body = {
            BIN_FIELDS["temporada"]:       temporada,
            BIN_FIELDS["bin_code"]:        bin_code,
            BIN_FIELDS["operator_code"]:   operator_code,
            BIN_FIELDS["source_system"]:   source_system,
            BIN_FIELDS["source_event_id"]: source_event_id,
            BIN_FIELDS["is_active"]:       True,
        }
        row = self._client.create_row(ENTITY_SET_BIN, body)
        return _row_to_bin(row or {})

    def filter_by_codes(self, temporada: str, bin_codes: list[str]) -> list[BinRecord]:
        if not bin_codes:
            return []
        codes_filter = " or ".join(
            f"{BIN_FIELDS['bin_code']} eq '{c}'" for c in bin_codes
        )
        f = f"{BIN_FIELDS['temporada']} eq '{temporada}' and ({codes_filter})"
        result = self._client.list_rows(
            ENTITY_SET_BIN,
            select=[BIN_FIELDS[k] for k in ("id", "temporada", "bin_code", "operator_code",
                                              "source_system", "source_event_id", "is_active")],
            filter_expr=f,
            top=len(bin_codes) + 10,
        )
        return [_row_to_bin(r) for r in (result or {}).get("value", [])]


class DataverseLoteRepository(LoteRepository):

    def __init__(self, client) -> None:
        self._client = client

    def find_by_code(self, temporada: str, lote_code: str) -> Optional[LoteRecord]:
        f = (
            f"{LOTE_FIELDS['temporada']} eq '{temporada}'"
            f" and {LOTE_FIELDS['lote_code']} eq '{lote_code}'"
        )
        result = self._client.list_rows(
            ENTITY_SET_LOTE,
            select=[LOTE_FIELDS[k] for k in ("id", "temporada", "lote_code", "operator_code",
                                               "source_system", "source_event_id", "is_active")],
            filter_expr=f,
            top=1,
        )
        rows = (result or {}).get("value", [])
        return _row_to_lote(rows[0]) if rows else None

    def create(
        self,
        temporada: str,
        lote_code: str,
        *,
        operator_code: str = "",
        source_system: str = "dataverse",
        source_event_id: str = "",
    ) -> LoteRecord:
        body = {
            LOTE_FIELDS["temporada"]:       temporada,
            LOTE_FIELDS["lote_code"]:       lote_code,
            LOTE_FIELDS["operator_code"]:   operator_code,
            LOTE_FIELDS["source_system"]:   source_system,
            LOTE_FIELDS["source_event_id"]: source_event_id,
            LOTE_FIELDS["is_active"]:       True,
        }
        row = self._client.create_row(ENTITY_SET_LOTE, body)
        return _row_to_lote(row or {})

    def filter_by_codes(self, temporada: str, lote_codes: list[str]) -> list[LoteRecord]:
        if not lote_codes:
            return []
        codes_filter = " or ".join(
            f"{LOTE_FIELDS['lote_code']} eq '{c}'" for c in lote_codes
        )
        f = f"{LOTE_FIELDS['temporada']} eq '{temporada}' and ({codes_filter})"
        result = self._client.list_rows(
            ENTITY_SET_LOTE,
            select=[LOTE_FIELDS[k] for k in ("id", "temporada", "lote_code", "operator_code",
                                               "source_system", "source_event_id", "is_active")],
            filter_expr=f,
            top=len(lote_codes) + 10,
        )
        return [_row_to_lote(r) for r in (result or {}).get("value", [])]


class DataversePalletRepository(PalletRepository):

    def __init__(self, client) -> None:
        self._client = client

    def find_by_code(self, temporada: str, pallet_code: str) -> Optional[PalletRecord]:
        from infrastructure.dataverse.mapping import PALLET_FIELDS
        f = (
            f"{PALLET_FIELDS['temporada']} eq '{temporada}'"
            f" and {PALLET_FIELDS['pallet_code']} eq '{pallet_code}'"
        )
        result = self._client.list_rows(
            ENTITY_SET_PALLET,
            select=[PALLET_FIELDS[k] for k in ("id", "temporada", "pallet_code",
                                                 "operator_code", "source_system",
                                                 "source_event_id", "is_active")],
            filter_expr=f,
            top=1,
        )
        rows = (result or {}).get("value", [])
        return _row_to_pallet(rows[0]) if rows else None

    def get_or_create(
        self,
        temporada: str,
        pallet_code: str,
        *,
        operator_code: str = "",
        source_system: str = "dataverse",
        source_event_id: str = "",
    ) -> tuple[PalletRecord, bool]:
        from infrastructure.dataverse.mapping import PALLET_FIELDS
        existing = self.find_by_code(temporada, pallet_code)
        if existing:
            return existing, False
        body = {
            PALLET_FIELDS["temporada"]:       temporada,
            PALLET_FIELDS["pallet_code"]:     pallet_code,
            PALLET_FIELDS["operator_code"]:   operator_code,
            PALLET_FIELDS["source_system"]:   source_system,
            PALLET_FIELDS["source_event_id"]: source_event_id,
            PALLET_FIELDS["is_active"]:       True,
        }
        row = self._client.create_row(ENTITY_SET_PALLET, body)
        return _row_to_pallet(row or {}), True


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
        from infrastructure.dataverse.mapping import BIN_LOTE_FIELDS
        body = {
            f"{BIN_LOTE_FIELDS['bin_id']}@odata.bind":  odata_bind(ENTITY_SET_BIN, str(bin_id)),
            f"{BIN_LOTE_FIELDS['lote_id']}@odata.bind": odata_bind(ENTITY_SET_LOTE, str(lote_id)),
            BIN_LOTE_FIELDS["operator_code"]:            operator_code,
            BIN_LOTE_FIELDS["source_system"]:            source_system,
            BIN_LOTE_FIELDS["source_event_id"]:          source_event_id,
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
        from infrastructure.dataverse.mapping import BIN_LOTE_FIELDS, BIN_FIELDS, LOTE_FIELDS
        if not bin_ids:
            return []
        # Consulta con expand para obtener bin_code y lote_code en una sola request
        ids_filter = " or ".join(
            f"_{BIN_LOTE_FIELDS['bin_id']}_value eq {guid}" for guid in bin_ids
        )
        result = self._client.list_rows(
            ENTITY_SET_BIN_LOTE,
            select=[BIN_LOTE_FIELDS["id"]],
            filter_expr=ids_filter,
            expand=f"{BIN_LOTE_FIELDS['bin_id']}($select={BIN_FIELDS['bin_code']}),"
                   f"{BIN_LOTE_FIELDS['lote_id']}($select={LOTE_FIELDS['lote_code']})",
            top=len(bin_ids) + 10,
        )
        conflicts = []
        for row in (result or {}).get("value", []):
            bin_row  = row.get(BIN_LOTE_FIELDS["bin_id"]) or {}
            lote_row = row.get(BIN_LOTE_FIELDS["lote_id"]) or {}
            conflicts.append(BinAssignmentConflict(
                bin_code=bin_row.get(BIN_FIELDS["bin_code"], ""),
                lote_code=lote_row.get(LOTE_FIELDS["lote_code"], ""),
            ))
        return conflicts


class DataverseLoteRepositoryExtended(DataverseLoteRepository):
    """Extiende con metodo update para cumplir la interfaz completa de LoteRepository."""

    def update(self, lote_id: Any, fields: dict) -> LoteRecord:
        # Dataverse PATCH — pendiente validacion de esquema real
        raise NotImplementedError(
            "DataverseLoteRepository.update: implementacion OData pendiente de "
            "validacion del esquema real con el equipo de Power Platform."
        )


class DataversePalletLoteRepository(PalletLoteRepository):

    def __init__(self, client) -> None:
        self._client = client

    def find_by_lote(self, lote_id: Any) -> Optional[PalletLoteRecord]:
        from infrastructure.dataverse.mapping import PALLET_LOTE_FIELDS
        f = f"_{PALLET_LOTE_FIELDS['lote_id']}_value eq {lote_id}"
        result = self._client.list_rows(
            ENTITY_SET_PALLET_LOTE,
            select=[PALLET_LOTE_FIELDS["id"]],
            filter_expr=f,
            top=1,
        )
        rows = (result or {}).get("value", [])
        if rows:
            row = rows[0]
            return PalletLoteRecord(
                id=row.get(PALLET_LOTE_FIELDS["id"]),
                pallet_id=row.get(f"_{PALLET_LOTE_FIELDS['pallet_id']}_value"),
                lote_id=lote_id,
            )
        return None

    def get_or_create(
        self,
        pallet_id: Any,
        lote_id: Any,
        *,
        operator_code: str = "",
        source_system: str = "dataverse",
        source_event_id: str = "",
    ) -> tuple[PalletLoteRecord, bool]:
        from infrastructure.dataverse.mapping import PALLET_LOTE_FIELDS
        # Buscar registro existente
        f = (
            f"_{PALLET_LOTE_FIELDS['pallet_id']}_value eq {pallet_id}"
            f" and _{PALLET_LOTE_FIELDS['lote_id']}_value eq {lote_id}"
        )
        result = self._client.list_rows(
            ENTITY_SET_PALLET_LOTE,
            select=[PALLET_LOTE_FIELDS["id"]],
            filter_expr=f,
            top=1,
        )
        rows = (result or {}).get("value", [])
        if rows:
            row = rows[0]
            return PalletLoteRecord(
                id=row.get(PALLET_LOTE_FIELDS["id"]),
                pallet_id=pallet_id,
                lote_id=lote_id,
            ), False

        body = {
            f"{PALLET_LOTE_FIELDS['pallet_id']}@odata.bind": odata_bind(ENTITY_SET_PALLET, str(pallet_id)),
            f"{PALLET_LOTE_FIELDS['lote_id']}@odata.bind":   odata_bind(ENTITY_SET_LOTE, str(lote_id)),
            PALLET_LOTE_FIELDS["operator_code"]:              operator_code,
            PALLET_LOTE_FIELDS["source_system"]:              source_system,
            PALLET_LOTE_FIELDS["source_event_id"]:            source_event_id,
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


class DataverseRegistroEtapaRepository(RegistroEtapaRepository):

    def __init__(self, client) -> None:
        self._client = client

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
        body: dict = {
            REGISTRO_ETAPA_FIELDS["temporada"]:       temporada,
            REGISTRO_ETAPA_FIELDS["event_key"]:       event_key,
            REGISTRO_ETAPA_FIELDS["tipo_evento"]:     tipo_evento,
            REGISTRO_ETAPA_FIELDS["operator_code"]:   operator_code,
            REGISTRO_ETAPA_FIELDS["source_system"]:   source_system,
            REGISTRO_ETAPA_FIELDS["source_event_id"]: source_event_id,
            REGISTRO_ETAPA_FIELDS["payload"]:         json.dumps(payload or {}),
            REGISTRO_ETAPA_FIELDS["notes"]:           notes,
        }
        if bin_id:
            body[f"{REGISTRO_ETAPA_FIELDS['bin_id']}@odata.bind"] = odata_bind(ENTITY_SET_BIN, str(bin_id))
        if lote_id:
            body[f"{REGISTRO_ETAPA_FIELDS['lote_id']}@odata.bind"] = odata_bind(ENTITY_SET_LOTE, str(lote_id))
        if pallet_id:
            body[f"{REGISTRO_ETAPA_FIELDS['pallet_id']}@odata.bind"] = odata_bind(ENTITY_SET_PALLET, str(pallet_id))

        row = self._client.create_row(ENTITY_SET_REGISTRO_ETAPA, body) or {}
        return _row_to_registro({**body, REGISTRO_ETAPA_FIELDS["id"]: row.get(REGISTRO_ETAPA_FIELDS["id"])})

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
        # Buscar por event_key (clave idempotente)
        f = f"{REGISTRO_ETAPA_FIELDS['event_key']} eq '{event_key}'"
        result = self._client.list_rows(
            ENTITY_SET_REGISTRO_ETAPA,
            select=[REGISTRO_ETAPA_FIELDS[k] for k in
                    ("id", "temporada", "event_key", "tipo_evento",
                     "operator_code", "source_system", "source_event_id",
                     "payload", "notes")],
            filter_expr=f,
            top=1,
        )
        rows = (result or {}).get("value", [])
        if rows:
            return _row_to_registro(rows[0]), False

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
        result = self._client.list_rows(
            ENTITY_SET_REGISTRO_ETAPA,
            select=[REGISTRO_ETAPA_FIELDS[k] for k in
                    ("id", "temporada", "event_key", "tipo_evento",
                     "operator_code", "source_system", "source_event_id",
                     "payload", "notes")],
            orderby=f"{REGISTRO_ETAPA_FIELDS['created_at']} desc",
            top=limit,
        )
        return [_row_to_registro(r) for r in (result or {}).get("value", [])]


# ---------------------------------------------------------------------------
# Stub implementations para nuevas entidades
# Las implementaciones completas OData estan pendientes de validacion del
# esquema real en el ambiente Dataverse.  Los stubs elevan NotImplementedError
# con un mensaje claro para facilitar el diagnostico durante el desarrollo.
# ---------------------------------------------------------------------------

class _DataverseStubMixin:
    """Helper para generar NotImplementedError descriptivo."""
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
        lotes=DataverseLoteRepositoryExtended(client),
        pallets=DataversePalletRepository(client),
        bin_lotes=DataverseBinLoteRepository(client),
        pallet_lotes=DataversePalletLoteRepository(client),
        registros=DataverseRegistroEtapaRepository(client),
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
