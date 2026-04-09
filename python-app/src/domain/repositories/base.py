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
    nombre_productor: str = ""
    tipo_cultivo: str = ""
    variedad_fruta: str = ""
    numero_cuartel: str = ""
    nombre_cuartel: str = ""
    sector: str = ""
    color: str = ""
    kilos_bruto_ingreso: Optional[Decimal] = None
    kilos_neto_ingreso: Optional[Decimal] = None
    codigo_productor: str = ""


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
    # codigo_productor: derivado del primer bin del lote.
    # En SQLite se puebla al leer el lote (via bin_lotes relation).
    # En Dataverse se lee desde crf21_codigo_productor (campo agregado 2026-04-04).
    # Vacio si el lote no tiene bins o fue creado antes de la migracion.
    codigo_productor: str = ""


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
    numero_camara: str = ""
    fecha_ingreso: Optional[date] = None
    hora_ingreso: str = ""
    fecha_salida: Optional[date] = None
    hora_salida: str = ""
    horas_desverdizado: Optional[int] = None
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
# Record types — Planillas de Control de Calidad
# ---------------------------------------------------------------------------

@dataclass
class PlanillaDesverdizadoCalibreRecord:
    """Planilla CALIDAD DESVERDIZADO — medicion de calibres en terreno."""
    id: Any
    lote_id: Any
    supervisor: str = ""
    productor: str = ""
    variedad: str = ""
    trazabilidad: str = ""
    cod_sdp: str = ""
    fecha_cosecha: Optional[date] = None
    fecha_despacho: Optional[date] = None
    cuartel: str = ""
    sector: str = ""
    oleocelosis: Optional[int] = None
    heridas_abiertas: Optional[int] = None
    rugoso: Optional[int] = None
    deforme: Optional[int] = None
    golpe_sol: Optional[int] = None
    verdes: Optional[int] = None
    pre_calibre_defecto: Optional[int] = None
    palo_largo: Optional[int] = None
    # JSON string: [{"color": str, "calibres": {"1xx":N,...}, "observacion": str}] x3
    calibres_grupos_json: str = "[]"
    observaciones: str = ""
    rol: str = ""
    operator_code: str = ""
    source_system: str = "local"


@dataclass
class PlanillaDesverdizadoSemillasRecord:
    """Planilla CALIDAD DESVERDIZADO_2 — medicion de semillas en cosecha."""
    id: Any
    lote_id: Any
    fecha: Optional[date] = None
    supervisor: str = ""
    productor: str = ""
    variedad: str = ""
    cuartel: str = ""
    sector: str = ""
    trazabilidad: str = ""
    cod_sdp: str = ""
    color: str = ""
    # JSON string: [{"n_fruto": int, "n_semillas": int}, ...] x50
    frutas_data_json: str = "[]"
    total_frutos_muestra: Optional[int] = None
    total_frutos_con_semillas: Optional[int] = None
    total_semillas: Optional[int] = None
    pct_frutos_con_semillas: Optional[Decimal] = None
    promedio_semillas: Optional[Decimal] = None
    rol: str = ""
    operator_code: str = ""
    source_system: str = "local"


@dataclass
class PlanillaCalidadPackingRecord:
    """Planilla CALIDAD PACKING CITRICOS — control de calidad exportacion."""
    id: Any
    pallet_id: Any
    # Identificacion
    productor: str = ""
    trazabilidad: str = ""
    cod_sdp: str = ""
    cuartel: str = ""
    sector: str = ""
    nombre_control: str = ""
    n_cuadrilla: str = ""
    supervisor: str = ""
    fecha_despacho: Optional[date] = None
    fecha_cosecha: Optional[date] = None
    numero_hoja: int = 1
    tipo_fruta: str = ""
    variedad: str = ""
    # Condiciones
    temperatura: Optional[Decimal] = None
    humedad: Optional[Decimal] = None
    horas_cosecha: str = ""
    color: str = ""
    n_frutos_muestreados: Optional[int] = None
    brix: Optional[Decimal] = None
    # Calibre
    pre_calibre: Optional[int] = None
    sobre_calibre: Optional[int] = None
    # Calidad
    color_contrario_evaluado: Optional[int] = None
    cantidad_frutos: Optional[int] = None
    ausencia_roseta: Optional[int] = None
    deformes: Optional[int] = None
    frutos_con_semilla: Optional[int] = None
    n_semillas: Optional[int] = None
    fumagina: Optional[int] = None
    h_cicatrizadas: Optional[int] = None
    manchas: Optional[int] = None
    peduculo_largo: Optional[int] = None
    residuos: Optional[int] = None
    rugosos: Optional[int] = None
    # Russet
    russet_leve_claros: Optional[int] = None
    russet_moderados_claros: Optional[int] = None
    russet_severos_oscuros: Optional[int] = None
    # Condicion
    creasing_leve: Optional[int] = None
    creasing_mod_sev: Optional[int] = None
    dano_frio_granulados: Optional[int] = None
    bufado: Optional[int] = None
    deshidratacion_roseta: Optional[int] = None
    golpe_sol: Optional[int] = None
    h_abiertas_superior: Optional[int] = None
    h_abiertas_inferior: Optional[int] = None
    acostillado: Optional[int] = None
    machucon: Optional[int] = None
    blandos: Optional[int] = None
    oleocelosis: Optional[int] = None
    ombligo_rasgado: Optional[int] = None
    colapso_corteza: Optional[int] = None
    pudricion: Optional[int] = None
    # Dano arana
    dano_arana_leve: Optional[int] = None
    dano_arana_moderado: Optional[int] = None
    dano_arana_severo: Optional[int] = None
    # Otros
    dano_mecanico: Optional[int] = None
    otros_condicion: str = ""
    total_defectos_pct: Optional[Decimal] = None
    rol: str = ""
    operator_code: str = ""
    source_system: str = "local"


@dataclass
class PlanillaCalidadCamaraRecord:
    """Planilla CALIDAD CAMARAS — control de proceso temperatura camara."""
    id: Any
    pallet_id: Any  # nullable
    fecha_control: Optional[date] = None
    tipo_proceso: str = ""
    zona_planta: str = ""
    tunel_camara: str = ""
    capacidad_maxima: str = ""
    temperatura_equipos: str = ""
    codigo_envases: str = ""
    cantidad_pallets: Optional[int] = None
    especie: str = ""
    variedad: str = ""
    fecha_embalaje: Optional[date] = None
    estiba: str = ""
    tipo_inversion: str = ""
    # JSON string: [{hora, ambiente, pulpa_ext_entrada, pulpa_ext_medio, pulpa_ext_salida,
    #                pulpa_int_entrada, pulpa_int_media, pulpa_int_salida}]
    mediciones_json: str = "[]"
    # Promedios
    temp_pulpa_ext_inicio: Optional[Decimal] = None
    temp_pulpa_ext_termino: Optional[Decimal] = None
    temp_pulpa_int_inicio: Optional[Decimal] = None
    temp_pulpa_int_termino: Optional[Decimal] = None
    temp_ambiente_inicio: Optional[Decimal] = None
    temp_ambiente_termino: Optional[Decimal] = None
    # Tiempos
    tiempo_carga_inicio: str = ""
    tiempo_carga_termino: str = ""
    tiempo_descarga_inicio: str = ""
    tiempo_descarga_termino: str = ""
    tiempo_enfriado_inicio: str = ""
    tiempo_enfriado_termino: str = ""
    observaciones: str = ""
    nombre_control: str = ""
    rol: str = ""
    operator_code: str = ""
    source_system: str = "local"


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

    def update(self, bin_id: Any, fields: dict) -> "BinRecord":
        """
        Actualiza campos variables de un bin.
        Campos soportados: numero_cuartel, hora_recepcion, kilos_bruto_ingreso,
        kilos_neto_ingreso, a_o_r, observaciones.
        """
        raise NotImplementedError("BinRepository.update() no implementado en este backend")

    def delete(self, bin_id: Any) -> None:
        """
        Elimina un bin. Debe llamarse despues de eliminar su BinLote asociado
        (PROTECT FK en SQLite; orden requerido en todos los backends).
        """
        raise NotImplementedError("BinRepository.delete() no implementado en este backend")


class LoteRepository(ABC):

    @abstractmethod
    def find_by_code(self, temporada: str, lote_code: str) -> Optional[LoteRecord]:
        """Busca un lote por temporada y codigo. Retorna None si no existe."""

    def find_by_id(self, lote_id: Any) -> Optional[LoteRecord]:
        """
        Busca un lote por su identificador interno.
        Implementacion por defecto: None. Dataverse sobreescribe para vistas que
        necesitan enriquecer contexto a partir de relaciones pallet-lote.
        """
        return None

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

    def list_recent(self, limit: int = 30) -> list[PalletRecord]:
        """
        Retorna los pallets mas recientes ordenados por fecha de creacion descendente.
        Implementacion por defecto: lista vacia. SQLite y Dataverse sobreescriben.
        Usado por vistas de paletizado y camaras en modo Dataverse.
        """
        return []


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

    def find_by_bin_and_lote(self, bin_id: Any, lote_id: Any) -> Optional[BinLoteRecord]:
        """
        Retorna el registro BinLote para el par (bin_id, lote_id), o None si no existe.
        Usado para verificar que un bin pertenece al lote antes de editar/eliminar.
        """
        raise NotImplementedError("BinLoteRepository.find_by_bin_and_lote() no implementado en este backend")

    def delete(self, bin_lote_id: Any) -> None:
        """
        Elimina el registro BinLote indicado.
        Debe llamarse antes de BinRepository.delete() para liberar la FK PROTECT.
        """
        raise NotImplementedError("BinLoteRepository.delete() no implementado en este backend")


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
# Repository abstract base classes — Planillas de Control de Calidad
# ---------------------------------------------------------------------------

class PlanillaDesverdizadoCalibreRepository(ABC):

    @abstractmethod
    def create(self, lote_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> PlanillaDesverdizadoCalibreRecord:
        """Crea un registro de planilla de calibres desverdizado."""

    @abstractmethod
    def list_by_lote(self, lote_id: Any) -> list[PlanillaDesverdizadoCalibreRecord]:
        """Lista las planillas de calibres de un lote."""


class PlanillaDesverdizadoSemillasRepository(ABC):

    @abstractmethod
    def create(self, lote_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> PlanillaDesverdizadoSemillasRecord:
        """Crea un registro de planilla de semillas desverdizado."""

    @abstractmethod
    def list_by_lote(self, lote_id: Any) -> list[PlanillaDesverdizadoSemillasRecord]:
        """Lista las planillas de semillas de un lote."""


class PlanillaCalidadPackingRepository(ABC):

    @abstractmethod
    def create(self, pallet_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> PlanillaCalidadPackingRecord:
        """Crea un registro de planilla de calidad packing citricos."""

    @abstractmethod
    def list_by_pallet(self, pallet_id: Any) -> list[PlanillaCalidadPackingRecord]:
        """Lista las planillas de calidad packing de un pallet."""


class PlanillaCalidadCamaraRepository(ABC):

    @abstractmethod
    def create(self, pallet_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> PlanillaCalidadCamaraRecord:
        """Crea un registro de planilla de control de camara."""

    @abstractmethod
    def list_by_pallet(self, pallet_id: Any) -> list[PlanillaCalidadCamaraRecord]:
        """Lista las planillas de control de camara de un pallet."""


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
    # Planillas de Control de Calidad
    planillas_desv_calibres: PlanillaDesverdizadoCalibreRepository
    planillas_desv_semillas: PlanillaDesverdizadoSemillasRepository
    planillas_calidad_packing: PlanillaCalidadPackingRepository
    planillas_calidad_camara: PlanillaCalidadCamaraRepository
    # Gestion de correlativos
    sequences: SequenceCounterRepository
