"""
Implementaciones SQLite (Django ORM) de los repositorios de dominio.

Cada clase envuelve las operaciones del ORM de Django y convierte los objetos
del modelo a record types del dominio. Esto permite que los casos de uso sean
agnósticos al mecanismo de persistencia.

Las importaciones de operaciones.models se hacen dentro de los métodos para
evitar problemas de orden de inicialización del registro de apps de Django.
"""
from __future__ import annotations

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
)


# ---------------------------------------------------------------------------
# Helpers: model instance → record type
# ---------------------------------------------------------------------------

def _bin_to_record(obj) -> BinRecord:
    return BinRecord(
        id=obj.id,
        temporada=obj.temporada,
        bin_code=obj.bin_code,
        operator_code=obj.operator_code,
        source_system=obj.source_system,
        source_event_id=obj.source_event_id,
        dataverse_id=obj.dataverse_id,
        is_active=obj.is_active,
    )


def _lote_to_record(obj) -> LoteRecord:
    return LoteRecord(
        id=obj.id,
        temporada=obj.temporada,
        lote_code=obj.lote_code,
        operator_code=obj.operator_code,
        source_system=obj.source_system,
        source_event_id=obj.source_event_id,
        dataverse_id=obj.dataverse_id,
        is_active=obj.is_active,
    )


def _pallet_to_record(obj) -> PalletRecord:
    return PalletRecord(
        id=obj.id,
        temporada=obj.temporada,
        pallet_code=obj.pallet_code,
        operator_code=obj.operator_code,
        source_system=obj.source_system,
        source_event_id=obj.source_event_id,
        dataverse_id=obj.dataverse_id,
        is_active=obj.is_active,
    )


def _bin_lote_to_record(obj) -> BinLoteRecord:
    return BinLoteRecord(
        id=obj.id,
        bin_id=obj.bin_id,
        lote_id=obj.lote_id,
        operator_code=obj.operator_code,
        source_system=obj.source_system,
        source_event_id=obj.source_event_id,
    )


def _pallet_lote_to_record(obj) -> PalletLoteRecord:
    return PalletLoteRecord(
        id=obj.id,
        pallet_id=obj.pallet_id,
        lote_id=obj.lote_id,
        operator_code=obj.operator_code,
        source_system=obj.source_system,
        source_event_id=obj.source_event_id,
    )


def _registro_to_record(obj) -> RegistroEtapaRecord:
    return RegistroEtapaRecord(
        id=obj.id,
        temporada=obj.temporada,
        event_key=obj.event_key,
        tipo_evento=obj.tipo_evento,
        bin_id=obj.bin_id,
        lote_id=obj.lote_id,
        pallet_id=obj.pallet_id,
        operator_code=obj.operator_code,
        source_system=obj.source_system,
        source_event_id=obj.source_event_id,
        payload=obj.payload or {},
        notes=obj.notes or "",
    )


# ---------------------------------------------------------------------------
# Concrete repositories
# ---------------------------------------------------------------------------

class SqliteBinRepository(BinRepository):

    def find_by_code(self, temporada: str, bin_code: str) -> Optional[BinRecord]:
        from operaciones.models import Bin
        obj = Bin.objects.filter(temporada=temporada, bin_code=bin_code).first()
        return _bin_to_record(obj) if obj else None

    def create(
        self,
        temporada: str,
        bin_code: str,
        *,
        operator_code: str = "",
        source_system: str = "local",
        source_event_id: str = "",
    ) -> BinRecord:
        from operaciones.models import Bin
        obj = Bin.objects.create(
            temporada=temporada,
            bin_code=bin_code,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
        )
        return _bin_to_record(obj)

    def filter_by_codes(self, temporada: str, bin_codes: list[str]) -> list[BinRecord]:
        from operaciones.models import Bin
        objs = list(Bin.objects.filter(temporada=temporada, bin_code__in=bin_codes))
        return [_bin_to_record(obj) for obj in objs]


class SqliteLoteRepository(LoteRepository):

    def find_by_code(self, temporada: str, lote_code: str) -> Optional[LoteRecord]:
        from operaciones.models import Lote
        obj = Lote.objects.filter(temporada=temporada, lote_code=lote_code).first()
        return _lote_to_record(obj) if obj else None

    def create(
        self,
        temporada: str,
        lote_code: str,
        *,
        operator_code: str = "",
        source_system: str = "local",
        source_event_id: str = "",
    ) -> LoteRecord:
        from operaciones.models import Lote
        obj = Lote.objects.create(
            temporada=temporada,
            lote_code=lote_code,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
        )
        return _lote_to_record(obj)

    def filter_by_codes(self, temporada: str, lote_codes: list[str]) -> list[LoteRecord]:
        from operaciones.models import Lote
        objs = list(Lote.objects.filter(temporada=temporada, lote_code__in=lote_codes))
        return [_lote_to_record(obj) for obj in objs]


class SqlitePalletRepository(PalletRepository):

    def find_by_code(self, temporada: str, pallet_code: str) -> Optional[PalletRecord]:
        from operaciones.models import Pallet
        obj = Pallet.objects.filter(temporada=temporada, pallet_code=pallet_code).first()
        return _pallet_to_record(obj) if obj else None

    def get_or_create(
        self,
        temporada: str,
        pallet_code: str,
        *,
        operator_code: str = "",
        source_system: str = "local",
        source_event_id: str = "",
    ) -> tuple[PalletRecord, bool]:
        from operaciones.models import Pallet
        obj, created = Pallet.objects.get_or_create(
            temporada=temporada,
            pallet_code=pallet_code,
            defaults={
                "operator_code": operator_code,
                "source_system": source_system,
                "source_event_id": source_event_id,
            },
        )
        return _pallet_to_record(obj), created


class SqliteBinLoteRepository(BinLoteRepository):

    def create(
        self,
        bin_id: Any,
        lote_id: Any,
        *,
        operator_code: str = "",
        source_system: str = "local",
        source_event_id: str = "",
    ) -> BinLoteRecord:
        from operaciones.models import BinLote
        obj = BinLote.objects.create(
            bin_id=bin_id,
            lote_id=lote_id,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
        )
        return _bin_lote_to_record(obj)

    def find_existing_assignments(self, bin_ids: list[Any]) -> list[BinAssignmentConflict]:
        from operaciones.models import BinLote
        conflicts = BinLote.objects.filter(bin_id__in=bin_ids).select_related("bin", "lote")
        return [
            BinAssignmentConflict(bin_code=c.bin.bin_code, lote_code=c.lote.lote_code)
            for c in conflicts
        ]


class SqlitePalletLoteRepository(PalletLoteRepository):

    def get_or_create(
        self,
        pallet_id: Any,
        lote_id: Any,
        *,
        operator_code: str = "",
        source_system: str = "local",
        source_event_id: str = "",
    ) -> tuple[PalletLoteRecord, bool]:
        from operaciones.models import PalletLote
        obj, created = PalletLote.objects.get_or_create(
            pallet_id=pallet_id,
            lote_id=lote_id,
            defaults={
                "operator_code": operator_code,
                "source_system": source_system,
                "source_event_id": source_event_id,
            },
        )
        return _pallet_lote_to_record(obj), created


class SqliteRegistroEtapaRepository(RegistroEtapaRepository):

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
        source_system: str = "local",
        source_event_id: str = "",
        payload: Optional[dict] = None,
        notes: str = "",
    ) -> RegistroEtapaRecord:
        from operaciones.models import RegistroEtapa
        obj = RegistroEtapa.objects.create(
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
        return _registro_to_record(obj)

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
        source_system: str = "local",
        source_event_id: str = "",
        payload: Optional[dict] = None,
    ) -> tuple[RegistroEtapaRecord, bool]:
        from operaciones.models import RegistroEtapa
        obj, created = RegistroEtapa.objects.get_or_create(
            event_key=event_key,
            defaults={
                "temporada": temporada,
                "tipo_evento": tipo_evento,
                "bin_id": bin_id,
                "lote_id": lote_id,
                "pallet_id": pallet_id,
                "operator_code": operator_code,
                "source_system": source_system,
                "source_event_id": source_event_id,
                "payload": payload or {},
            },
        )
        return _registro_to_record(obj), created

    def list_recent(self, limit: int = 100) -> list[RegistroEtapaRecord]:
        from operaciones.models import RegistroEtapa
        objs = RegistroEtapa.objects.order_by("-created_at")[:limit]
        return [_registro_to_record(obj) for obj in objs]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_sqlite_repositories() -> Repositories:
    return Repositories(
        bins=SqliteBinRepository(),
        lotes=SqliteLoteRepository(),
        pallets=SqlitePalletRepository(),
        bin_lotes=SqliteBinLoteRepository(),
        pallet_lotes=SqlitePalletLoteRepository(),
        registros=SqliteRegistroEtapaRepository(),
    )
