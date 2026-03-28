"""
Capa de dominio: tipos de registro (records) e interfaces abstractas de repositorios.

Los record types son simples dataclasses que representan entidades del dominio sin
dependencia del mecanismo de persistencia (ORM Django ni Dataverse Web API).
Los repositorios abstractos definen el contrato que deben cumplir las implementaciones
concretas (SQLite / Dataverse), permitiendo que los casos de uso sean agnósticos al backend.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Record types
# ---------------------------------------------------------------------------

@dataclass
class BinRecord:
    id: Any
    temporada: str
    bin_code: str
    operator_code: str = ""
    source_system: str = "local"
    source_event_id: str = ""
    dataverse_id: Optional[str] = None
    is_active: bool = True


@dataclass
class LoteRecord:
    id: Any
    temporada: str
    lote_code: str
    operator_code: str = ""
    source_system: str = "local"
    source_event_id: str = ""
    dataverse_id: Optional[str] = None
    is_active: bool = True


@dataclass
class PalletRecord:
    id: Any
    temporada: str
    pallet_code: str
    operator_code: str = ""
    source_system: str = "local"
    source_event_id: str = ""
    dataverse_id: Optional[str] = None
    is_active: bool = True


@dataclass
class BinLoteRecord:
    id: Any
    bin_id: Any
    lote_id: Any
    operator_code: str = ""
    source_system: str = "local"
    source_event_id: str = ""


@dataclass
class BinAssignmentConflict:
    """Representa un bin que ya está asignado a otro lote (violación de regla de negocio)."""
    bin_code: str
    lote_code: str


@dataclass
class PalletLoteRecord:
    id: Any
    pallet_id: Any
    lote_id: Any
    operator_code: str = ""
    source_system: str = "local"
    source_event_id: str = ""


@dataclass
class RegistroEtapaRecord:
    id: Any
    temporada: str
    event_key: str
    tipo_evento: str
    bin_id: Optional[Any] = None
    lote_id: Optional[Any] = None
    pallet_id: Optional[Any] = None
    operator_code: str = ""
    source_system: str = "local"
    source_event_id: str = ""
    payload: dict = field(default_factory=dict)
    notes: str = ""


# ---------------------------------------------------------------------------
# Repository abstract base classes
# ---------------------------------------------------------------------------

class BinRepository(ABC):

    @abstractmethod
    def find_by_code(self, temporada: str, bin_code: str) -> Optional[BinRecord]:
        """Busca un bin por temporada y código. Retorna None si no existe."""

    @abstractmethod
    def create(
        self,
        temporada: str,
        bin_code: str,
        *,
        operator_code: str = "",
        source_system: str = "local",
        source_event_id: str = "",
    ) -> BinRecord:
        """Crea un nuevo bin y retorna el record creado."""

    @abstractmethod
    def filter_by_codes(self, temporada: str, bin_codes: list[str]) -> list[BinRecord]:
        """Retorna los bins que existen para la temporada y los códigos dados."""


class LoteRepository(ABC):

    @abstractmethod
    def find_by_code(self, temporada: str, lote_code: str) -> Optional[LoteRecord]:
        """Busca un lote por temporada y código. Retorna None si no existe."""

    @abstractmethod
    def create(
        self,
        temporada: str,
        lote_code: str,
        *,
        operator_code: str = "",
        source_system: str = "local",
        source_event_id: str = "",
    ) -> LoteRecord:
        """Crea un nuevo lote y retorna el record creado."""

    @abstractmethod
    def filter_by_codes(self, temporada: str, lote_codes: list[str]) -> list[LoteRecord]:
        """Retorna los lotes que existen para la temporada y los códigos dados."""


class PalletRepository(ABC):

    @abstractmethod
    def find_by_code(self, temporada: str, pallet_code: str) -> Optional[PalletRecord]:
        """Busca un pallet por temporada y código. Retorna None si no existe."""

    @abstractmethod
    def get_or_create(
        self,
        temporada: str,
        pallet_code: str,
        *,
        operator_code: str = "",
        source_system: str = "local",
        source_event_id: str = "",
    ) -> tuple[PalletRecord, bool]:
        """Obtiene o crea un pallet. Retorna (record, created)."""


class BinLoteRepository(ABC):

    @abstractmethod
    def create(
        self,
        bin_id: Any,
        lote_id: Any,
        *,
        operator_code: str = "",
        source_system: str = "local",
        source_event_id: str = "",
    ) -> BinLoteRecord:
        """Crea la asociación bin-lote."""

    @abstractmethod
    def find_existing_assignments(self, bin_ids: list[Any]) -> list[BinAssignmentConflict]:
        """Retorna bins de la lista que ya están asignados a algún lote."""


class PalletLoteRepository(ABC):

    @abstractmethod
    def get_or_create(
        self,
        pallet_id: Any,
        lote_id: Any,
        *,
        operator_code: str = "",
        source_system: str = "local",
        source_event_id: str = "",
    ) -> tuple[PalletLoteRecord, bool]:
        """Obtiene o crea la asociación pallet-lote. Retorna (record, created)."""


class RegistroEtapaRepository(ABC):

    @abstractmethod
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
        """Crea un registro de etapa."""

    @abstractmethod
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
        """Obtiene o crea un registro de etapa usando event_key como clave idempotente."""

    @abstractmethod
    def list_recent(self, limit: int = 100) -> list[RegistroEtapaRecord]:
        """Lista los registros de etapa más recientes."""


# ---------------------------------------------------------------------------
# Container
# ---------------------------------------------------------------------------

@dataclass
class Repositories:
    """Agrupa todos los repositorios disponibles para un ciclo de ejecución."""
    bins: BinRepository
    lotes: LoteRepository
    pallets: PalletRepository
    bin_lotes: BinLoteRepository
    pallet_lotes: PalletLoteRepository
    registros: RegistroEtapaRepository
