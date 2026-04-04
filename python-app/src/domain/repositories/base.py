"""
Capa de dominio: tipos de registro (records) e interfaces abstractas de repositorios.

Los record types son simples dataclasses que representan entidades del dominio sin
dependencia del mecanismo de persistencia (ORM Django ni Dataverse Web API).
Los repositorios abstractos definen el contrato que deben cumplir las implementaciones
concretas (SQLite / Dataverse), permitiendo que los casos de uso sean agnosticos al backend.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Record types — entidades base
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
    # Campos extendidos (nullable para compatibilidad con registros anteriores)
    id_bin: str = ""
    fecha_cosecha: Optional[date] = None
    variedad_fruta: str = ""
    color: str = ""
    kilos_bruto_ingreso: Optional[Decimal] = None
    kilos_neto_ingreso: Optional[Decimal] = None


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
    # Campos extendidos
    id_lote_planta: str = ""
    fecha_conformacion: Optional[date] = None
    cantidad_bins: int = 0
    kilos_bruto_conformacion: Optional[Decimal] = None
    kilos_neto_conformacion: Optional[Decimal] = None
    requiere_desverdizado: bool = False
    disponibilidad_camara_desverdizado: Optional[str] = None
    # Generacion dinamica de codigo y estado
    estado: str = "abierto"
    temporada_codigo: str = ""
    correlativo_temporada: Optional[int] = None
    # etapa_actual: persiste la etapa de proceso en Dataverse.
    # En SQLite este campo no existe en el modelo; se deriva en vista via _etapa_lote().
    # En Dataverse se lee desde crf21_etapa_actual; puede ser None para
    # registros anteriores al 2026-03-31 (usar derive_etapa_lote() como fallback).
    etapa_actual: Optional[str] = None


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
    # Campos extendidos
    id_pallet: str = ""
    fecha: Optional[date] = None
    tipo_caja: str = ""
    cajas_por_pallet: Optional[int] = None
    peso_total_kg: Optional[Decimal] = None
    destino_mercado: str = ""


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
    """Representa un bin que ya esta asignado a otro lote (violacion de regla de negocio)."""
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
# Record types — nuevas entidades del flujo operativo
# ---------------------------------------------------------------------------

@dataclass
class CamaraMantencionRecord:
    id: Any
    lote_id: Any
    camara_numero: str = ""
    fecha_ingreso: Optional[date] = None
    hora_ingreso: str = ""
    fecha_salida: Optional[date] = None
    hora_salida: str = ""
    temperatura_camara: Optional[Decimal] = None
    humedad_relativa: Optional[Decimal] = None
    observaciones: str = ""
    operator_code: str = ""
    source_system: str = "local"
    rol: str = ""


@dataclass
class DesverdizadoRecord:
    id: Any
    lote_id: Any
    fecha_ingreso: Optional[date] = None
    hora_ingreso: str = ""
    fecha_salida: Optional[date] = None
    hora_salida: str = ""
    kilos_enviados_terreno: Optional[Decimal] = None
    kilos_recepcionados: Optional[Decimal] = None
    kilos_procesados: Optional[Decimal] = None
    kilos_bruto_salida: Optional[Decimal] = None
    kilos_neto_salida: Optional[Decimal] = None
    color_salida: str = ""
    proceso: str = ""
    operator_code: str = ""
    source_system: str = "local"
    rol: str = ""


@dataclass
class CalidadDesverdizadoRecord:
    id: Any
    lote_id: Any
    fecha: Optional[date] = None
    hora: str = ""
    temperatura_fruta: Optional[Decimal] = None
    color_evaluado: str = ""
    estado_visual: str = ""
    presencia_defectos: Optional[bool] = None
    aprobado: Optional[bool] = None
    observaciones: str = ""
    operator_code: str = ""
    source_system: str = "local"
    rol: str = ""


@dataclass
class IngresoAPackingRecord:
    id: Any
    lote_id: Any
    fecha_ingreso: Optional[date] = None
    hora_ingreso: str = ""
    kilos_bruto_ingreso_packing: Optional[Decimal] = None
    kilos_neto_ingreso_packing: Optional[Decimal] = None
    via_desverdizado: bool = False
    observaciones: str = ""
    operator_code: str = ""
    source_system: str = "local"
    rol: str = ""


@dataclass
class RegistroPackingRecord:
    id: Any
    lote_id: Any
    fecha: Optional[date] = None
    hora_inicio: str = ""
    linea_proceso: str = ""
    categoria_calidad: str = ""
    calibre: str = ""
    tipo_envase: str = ""
    cantidad_cajas_producidas: Optional[int] = None
    peso_promedio_caja_kg: Optional[Decimal] = None
    merma_seleccion_pct: Optional[Decimal] = None
    operator_code: str = ""
    source_system: str = "local"
    rol: str = ""


@dataclass
class ControlProcesoPackingRecord:
    id: Any
    lote_id: Any
    fecha: Optional[date] = None
    hora: str = ""
    n_bins_procesados: Optional[int] = None
    temp_agua_tina: Optional[Decimal] = None
    ph_agua: Optional[Decimal] = None
    recambio_agua: Optional[bool] = None
    rendimiento_lote_pct: Optional[Decimal] = None
    observaciones_generales: str = ""
    operator_code: str = ""
    source_system: str = "local"
    rol: str = ""


@dataclass
class CalidadPalletRecord:
    id: Any
    pallet_id: Any
    fecha: Optional[date] = None
    hora: str = ""
    temperatura_fruta: Optional[Decimal] = None
    peso_caja_muestra: Optional[Decimal] = None
    estado_visual_fruta: str = ""
    presencia_defectos: Optional[bool] = None
    aprobado: Optional[bool] = None
    observaciones: str = ""
    operator_code: str = ""
    source_system: str = "local"
    rol: str = ""


@dataclass
class CalidadPalletMuestraRecord:
    id: Any
    pallet_id: Any
    numero_muestra: Optional[int] = None
    temperatura_fruta: Optional[Decimal] = None
    peso_caja_muestra: Optional[Decimal] = None
    n_frutos: Optional[int] = None
    aprobado: Optional[bool] = None
    observaciones: str = ""
    operator_code: str = ""
    source_system: str = "local"
    rol: str = ""


@dataclass
class CamaraFrioRecord:
    id: Any
    pallet_id: Any
    camara_numero: str = ""
    temperatura_camara: Optional[Decimal] = None
    humedad_relativa: Optional[Decimal] = None
    fecha_ingreso: Optional[date] = None
    hora_ingreso: str = ""
    fecha_salida: Optional[date] = None
    hora_salida: str = ""
    destino_despacho: str = ""
    operator_code: str = ""
    source_system: str = "local"
    rol: str = ""


@dataclass
class SequenceCounterRecord:
    id: Any
    entity_name: str
    dimension: str
    last_value: int


@dataclass
class MedicionTemperaturaSalidaRecord:
    id: Any
    pallet_id: Any
    fecha: Optional[date] = None
    hora: str = ""
    temperatura_pallet: Optional[Decimal] = None
    punto_medicion: str = ""
    dentro_rango: Optional[bool] = None
    observaciones: str = ""
    operator_code: str = ""
    source_system: str = "local"
    rol: str = ""


# ---------------------------------------------------------------------------
# Repository abstract base classes — entidades base
# ---------------------------------------------------------------------------

class BinRepository(ABC):

    @abstractmethod
    def find_by_code(self, temporada: str, bin_code: str) -> Optional[BinRecord]:
        """Busca un bin por temporada y codigo. Retorna None si no existe."""

    @abstractmethod
    def create(
        self,
        temporada: str,
        bin_code: str,
        *,
        operator_code: str = "",
        source_system: str = "local",
        source_event_id: str = "",
        extra: Optional[dict] = None,
    ) -> BinRecord:
        """Crea un nuevo bin y retorna el record creado."""

    @abstractmethod
    def filter_by_codes(self, temporada: str, bin_codes: list[str]) -> list[BinRecord]:
        """Retorna los bins que existen para la temporada y los codigos dados."""

    def list_by_lote(self, lote_id: Any) -> list[BinRecord]:
        """
        Retorna los bins asociados a un lote.
        Implementacion por defecto: lista vacia (compatibilidad con SQLite que
        accede a esta relacion via ORM directo). Dataverse sobreescribe este metodo.
        """
        return []


class LoteRepository(ABC):

    @abstractmethod
    def find_by_code(self, temporada: str, lote_code: str) -> Optional[LoteRecord]:
        """Busca un lote por temporada y codigo. Retorna None si no existe."""

    @abstractmethod
    def create(
        self,
        temporada: str,
        lote_code: str,
        *,
        operator_code: str = "",
        source_system: str = "local",
        source_event_id: str = "",
        extra: Optional[dict] = None,
    ) -> LoteRecord:
        """Crea un nuevo lote y retorna el record creado."""

    @abstractmethod
    def filter_by_codes(self, temporada: str, lote_codes: list[str]) -> list[LoteRecord]:
        """Retorna los lotes que existen para la temporada y los codigos dados."""

    @abstractmethod
    def update(self, lote_id: Any, fields: dict) -> LoteRecord:
        """Actualiza campos del lote. Retorna el record actualizado."""

    def list_recent(self, limit: int = 50) -> list[LoteRecord]:
        """
        Retorna los lotes mas recientes (ordenados por fecha de creacion descendente).
        Implementacion por defecto: lista vacia. Dataverse sobreescribe para
        proveer datos reales al dashboard cuando PERSISTENCE_BACKEND=dataverse.
        SQLite accede a lotes via ORM directo en las vistas.
        """
        return []


class PalletRepository(ABC):

    @abstractmethod
    def find_by_code(self, temporada: str, pallet_code: str) -> Optional[PalletRecord]:
        """Busca un pallet por temporada y codigo. Retorna None si no existe."""

    @abstractmethod
    def get_or_create(
        self,
        temporada: str,
        pallet_code: str,
        *,
        operator_code: str = "",
        source_system: str = "local",
        source_event_id: str = "",
        extra: Optional[dict] = None,
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
        """Crea la asociacion bin-lote."""

    @abstractmethod
    def find_existing_assignments(self, bin_ids: list[Any]) -> list[BinAssignmentConflict]:
        """Retorna bins de la lista que ya estan asignados a algun lote."""

    def list_by_lote(self, lote_id: Any) -> list[BinLoteRecord]:
        """
        Retorna todos los registros bin-lote de un lote dado.
        Implementacion por defecto: lista vacia. Dataverse sobreescribe.
        SQLite usa ORM directo via lote.bin_lotes.all().
        """
        return []


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
        """Obtiene o crea la asociacion pallet-lote. Retorna (record, created)."""

    @abstractmethod
    def find_by_lote(self, lote_id: Any) -> Optional[PalletLoteRecord]:
        """Retorna la asignacion de pallet para un lote, o None si no tiene."""

    def find_by_pallet(self, pallet_id: Any) -> Optional[PalletLoteRecord]:
        """
        Retorna la asociacion lote-pallet dado un pallet_id, o None.
        Implementacion por defecto: None (SQLite accede via ORM directo).
        Dataverse sobreescribe para actualizar etapa_actual del lote cuando
        operaciones pallet-nivel (calidad_pallet, camara_frio) necesitan el lote_id.
        """
        return None


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
        """Lista los registros de etapa mas recientes."""


# ---------------------------------------------------------------------------
# Repository abstract base classes — nuevas entidades del flujo
# ---------------------------------------------------------------------------

class CamaraMantencionRepository(ABC):

    @abstractmethod
    def find_by_lote(self, lote_id: Any) -> Optional[CamaraMantencionRecord]:
        """Retorna el registro de camara de mantencion del lote, o None."""

    @abstractmethod
    def create(self, lote_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> CamaraMantencionRecord:
        """Crea el registro de camara de mantencion."""

    @abstractmethod
    def update(self, record_id: Any, fields: dict) -> CamaraMantencionRecord:
        """Actualiza campos del registro."""


class DesverdizadoRepository(ABC):

    @abstractmethod
    def find_by_lote(self, lote_id: Any) -> Optional[DesverdizadoRecord]:
        """Retorna el registro de desverdizado del lote, o None."""

    @abstractmethod
    def create(self, lote_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> DesverdizadoRecord:
        """Crea el registro de desverdizado."""

    @abstractmethod
    def update(self, record_id: Any, fields: dict) -> DesverdizadoRecord:
        """Actualiza campos del registro."""


class CalidadDesverdizadoRepository(ABC):

    @abstractmethod
    def create(self, lote_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> CalidadDesverdizadoRecord:
        """Crea un registro de calidad post-desverdizado."""

    @abstractmethod
    def list_by_lote(self, lote_id: Any) -> list[CalidadDesverdizadoRecord]:
        """Lista los registros de calidad de un lote."""


class IngresoAPackingRepository(ABC):

    @abstractmethod
    def find_by_lote(self, lote_id: Any) -> Optional[IngresoAPackingRecord]:
        """Retorna el registro de ingreso a packing del lote, o None."""

    @abstractmethod
    def create(self, lote_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> IngresoAPackingRecord:
        """Crea el registro de ingreso a packing."""


class RegistroPackingRepository(ABC):

    @abstractmethod
    def create(self, lote_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> RegistroPackingRecord:
        """Crea un registro de packing."""

    @abstractmethod
    def list_by_lote(self, lote_id: Any) -> list[RegistroPackingRecord]:
        """Lista los registros de packing de un lote."""


class ControlProcesoPackingRepository(ABC):

    @abstractmethod
    def create(self, lote_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> ControlProcesoPackingRecord:
        """Crea un registro de control de proceso packing."""

    @abstractmethod
    def list_by_lote(self, lote_id: Any) -> list[ControlProcesoPackingRecord]:
        """Lista los registros de control de proceso de un lote."""


class CalidadPalletRepository(ABC):

    @abstractmethod
    def create(self, pallet_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> CalidadPalletRecord:
        """Crea un registro de calidad de pallet."""

    @abstractmethod
    def list_by_pallet(self, pallet_id: Any) -> list[CalidadPalletRecord]:
        """Lista los registros de calidad de un pallet."""


class CalidadPalletMuestraRepository(ABC):

    @abstractmethod
    def create(self, pallet_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> CalidadPalletMuestraRecord:
        """Crea un registro de muestra individual de calidad para un pallet."""

    @abstractmethod
    def list_by_pallet(self, pallet_id: Any) -> list[CalidadPalletMuestraRecord]:
        """Lista las muestras de calidad de un pallet."""


class CamaraFrioRepository(ABC):

    @abstractmethod
    def find_by_pallet(self, pallet_id: Any) -> Optional[CamaraFrioRecord]:
        """Retorna el registro de camara de frio del pallet, o None."""

    @abstractmethod
    def create(self, pallet_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> CamaraFrioRecord:
        """Crea el registro de camara de frio."""

    @abstractmethod
    def update(self, record_id: Any, fields: dict) -> CamaraFrioRecord:
        """Actualiza campos del registro (ej: fecha_salida)."""


class MedicionTemperaturaSalidaRepository(ABC):

    @abstractmethod
    def create(self, pallet_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> MedicionTemperaturaSalidaRecord:
        """Crea una medicion de temperatura al salir."""

    @abstractmethod
    def list_by_pallet(self, pallet_id: Any) -> list[MedicionTemperaturaSalidaRecord]:
        """Lista las mediciones de temperatura de un pallet."""


class SequenceCounterRepository(ABC):

    @abstractmethod
    def get_next(self, entity_name: str, dimension: str) -> int:
        """
        Obtiene el siguiente correlativo para la entidad y dimension dadas.
        Operacion atomica: incrementa last_value y retorna el nuevo valor.
        """

    @abstractmethod
    def current_value(self, entity_name: str, dimension: str) -> int:
        """Retorna el ultimo valor asignado (0 si no existe)."""


# ---------------------------------------------------------------------------
# Container
# ---------------------------------------------------------------------------

@dataclass
class Repositories:
    """Agrupa todos los repositorios disponibles para un ciclo de ejecucion."""
    bins: BinRepository
    lotes: LoteRepository
    pallets: PalletRepository
    bin_lotes: BinLoteRepository
    pallet_lotes: PalletLoteRepository
    registros: RegistroEtapaRepository
    # Nuevas entidades del flujo operativo
    camara_mantencions: CamaraMantencionRepository
    desverdizados: DesverdizadoRepository
    calidad_desverdizados: CalidadDesverdizadoRepository
    ingresos_packing: IngresoAPackingRepository
    registros_packing: RegistroPackingRepository
    control_proceso_packings: ControlProcesoPackingRepository
    calidad_pallets: CalidadPalletRepository
    calidad_pallet_muestras: CalidadPalletMuestraRepository
    camara_frios: CamaraFrioRepository
    mediciones_temperatura: MedicionTemperaturaSalidaRepository
    # Gestion de correlativos
    sequences: SequenceCounterRepository
