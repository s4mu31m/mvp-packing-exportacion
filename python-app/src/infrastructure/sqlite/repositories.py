"""
Implementaciones SQLite (Django ORM) de los repositorios de dominio.

Las importaciones de operaciones.models se hacen dentro de los metodos para
evitar problemas de orden de inicializacion del registro de apps de Django.
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
    CalidadPalletMuestraRecord,
    CalidadPalletMuestraRepository,
    CamaraFrioRecord,
    CamaraFrioRepository,
    MedicionTemperaturaSalidaRecord,
    MedicionTemperaturaSalidaRepository,
    SequenceCounterRecord,
    SequenceCounterRepository,
    PlanillaDesverdizadoCalibreRecord,
    PlanillaDesverdizadoCalibreRepository,
    PlanillaDesverdizadoSemillasRecord,
    PlanillaDesverdizadoSemillasRepository,
    PlanillaCalidadPackingRecord,
    PlanillaCalidadPackingRepository,
    PlanillaCalidadCamaraRecord,
    PlanillaCalidadCamaraRepository,
)


# ---------------------------------------------------------------------------
# Helpers: model instance → record type (entidades base)
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
        id_bin=obj.id_bin or "",
        fecha_cosecha=obj.fecha_cosecha,
        variedad_fruta=obj.variedad_fruta or "",
        color=obj.color or "",
        kilos_bruto_ingreso=obj.kilos_bruto_ingreso,
        kilos_neto_ingreso=obj.kilos_neto_ingreso,
        codigo_productor=obj.codigo_productor or "",
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
        id_lote_planta=obj.id_lote_planta or "",
        fecha_conformacion=obj.fecha_conformacion,
        cantidad_bins=obj.cantidad_bins or 0,
        kilos_bruto_conformacion=obj.kilos_bruto_conformacion,
        kilos_neto_conformacion=obj.kilos_neto_conformacion,
        requiere_desverdizado=obj.requiere_desverdizado,
        disponibilidad_camara_desverdizado=obj.disponibilidad_camara_desverdizado,
        estado=obj.estado,
        temporada_codigo=obj.temporada_codigo or "",
        correlativo_temporada=obj.correlativo_temporada,
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
        id_pallet=obj.id_pallet or "",
        fecha=obj.fecha,
        tipo_caja=obj.tipo_caja or "",
        cajas_por_pallet=obj.cajas_por_pallet,
        peso_total_kg=obj.peso_total_kg,
        destino_mercado=obj.destino_mercado or "",
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


# Helpers para nuevas entidades

def _camara_mantencion_to_record(obj) -> CamaraMantencionRecord:
    return CamaraMantencionRecord(
        id=obj.id,
        lote_id=obj.lote_id,
        camara_numero=obj.camara_numero or "",
        fecha_ingreso=obj.fecha_ingreso,
        hora_ingreso=obj.hora_ingreso or "",
        fecha_salida=obj.fecha_salida,
        hora_salida=obj.hora_salida or "",
        temperatura_camara=obj.temperatura_camara,
        humedad_relativa=obj.humedad_relativa,
        observaciones=obj.observaciones or "",
        operator_code=obj.operator_code,
        source_system=obj.source_system,
        rol=obj.rol or "",
    )


def _desverdizado_to_record(obj) -> DesverdizadoRecord:
    return DesverdizadoRecord(
        id=obj.id,
        lote_id=obj.lote_id,
        fecha_ingreso=obj.fecha_ingreso,
        hora_ingreso=obj.hora_ingreso or "",
        fecha_salida=obj.fecha_salida,
        hora_salida=obj.hora_salida or "",
        kilos_enviados_terreno=obj.kilos_enviados_terreno,
        kilos_recepcionados=obj.kilos_recepcionados,
        kilos_procesados=obj.kilos_procesados,
        kilos_bruto_salida=obj.kilos_bruto_salida,
        kilos_neto_salida=obj.kilos_neto_salida,
        color_salida=obj.color_salida or "",
        proceso=obj.proceso or "",
        operator_code=obj.operator_code,
        source_system=obj.source_system,
        rol=obj.rol or "",
    )


def _calidad_desv_to_record(obj) -> CalidadDesverdizadoRecord:
    return CalidadDesverdizadoRecord(
        id=obj.id,
        lote_id=obj.lote_id,
        fecha=obj.fecha,
        hora=obj.hora or "",
        temperatura_fruta=obj.temperatura_fruta,
        color_evaluado=obj.color_evaluado or "",
        estado_visual=obj.estado_visual or "",
        presencia_defectos=obj.presencia_defectos,
        aprobado=obj.aprobado,
        observaciones=obj.observaciones or "",
        operator_code=obj.operator_code,
        source_system=obj.source_system,
        rol=obj.rol or "",
    )


def _ingreso_packing_to_record(obj) -> IngresoAPackingRecord:
    return IngresoAPackingRecord(
        id=obj.id,
        lote_id=obj.lote_id,
        fecha_ingreso=obj.fecha_ingreso,
        hora_ingreso=obj.hora_ingreso or "",
        kilos_bruto_ingreso_packing=obj.kilos_bruto_ingreso_packing,
        kilos_neto_ingreso_packing=obj.kilos_neto_ingreso_packing,
        via_desverdizado=obj.via_desverdizado,
        observaciones=obj.observaciones or "",
        operator_code=obj.operator_code,
        source_system=obj.source_system,
        rol=obj.rol or "",
    )


def _registro_packing_to_record(obj) -> RegistroPackingRecord:
    return RegistroPackingRecord(
        id=obj.id,
        lote_id=obj.lote_id,
        fecha=obj.fecha,
        hora_inicio=obj.hora_inicio or "",
        linea_proceso=obj.linea_proceso or "",
        categoria_calidad=obj.categoria_calidad or "",
        calibre=obj.calibre or "",
        tipo_envase=obj.tipo_envase or "",
        cantidad_cajas_producidas=obj.cantidad_cajas_producidas,
        peso_promedio_caja_kg=obj.peso_promedio_caja_kg,
        merma_seleccion_pct=obj.merma_seleccion_pct,
        operator_code=obj.operator_code,
        source_system=obj.source_system,
        rol=obj.rol or "",
    )


def _control_proceso_to_record(obj) -> ControlProcesoPackingRecord:
    return ControlProcesoPackingRecord(
        id=obj.id,
        lote_id=obj.lote_id,
        fecha=obj.fecha,
        hora=obj.hora or "",
        n_bins_procesados=obj.n_bins_procesados,
        temp_agua_tina=obj.temp_agua_tina,
        ph_agua=obj.ph_agua,
        recambio_agua=obj.recambio_agua,
        rendimiento_lote_pct=obj.rendimiento_lote_pct,
        observaciones_generales=obj.observaciones_generales or "",
        operator_code=obj.operator_code,
        source_system=obj.source_system,
        rol=obj.rol or "",
    )


def _calidad_pallet_to_record(obj) -> CalidadPalletRecord:
    return CalidadPalletRecord(
        id=obj.id,
        pallet_id=obj.pallet_id,
        fecha=obj.fecha,
        hora=obj.hora or "",
        temperatura_fruta=obj.temperatura_fruta,
        peso_caja_muestra=obj.peso_caja_muestra,
        estado_visual_fruta=obj.estado_visual_fruta or "",
        presencia_defectos=obj.presencia_defectos,
        aprobado=obj.aprobado,
        observaciones=obj.observaciones or "",
        operator_code=obj.operator_code,
        source_system=obj.source_system,
        rol=obj.rol or "",
    )


def _calidad_pallet_muestra_to_record(obj) -> CalidadPalletMuestraRecord:
    return CalidadPalletMuestraRecord(
        id=obj.id,
        pallet_id=obj.pallet_id,
        numero_muestra=obj.numero_muestra,
        temperatura_fruta=obj.temperatura_fruta,
        peso_caja_muestra=obj.peso_caja_muestra,
        n_frutos=obj.n_frutos,
        aprobado=obj.aprobado,
        observaciones=obj.observaciones or "",
        operator_code=obj.operator_code,
        source_system=obj.source_system,
        rol=obj.rol or "",
    )


def _camara_frio_to_record(obj) -> CamaraFrioRecord:
    return CamaraFrioRecord(
        id=obj.id,
        pallet_id=obj.pallet_id,
        camara_numero=obj.camara_numero or "",
        temperatura_camara=obj.temperatura_camara,
        humedad_relativa=obj.humedad_relativa,
        fecha_ingreso=obj.fecha_ingreso,
        hora_ingreso=obj.hora_ingreso or "",
        fecha_salida=obj.fecha_salida,
        hora_salida=obj.hora_salida or "",
        destino_despacho=obj.destino_despacho or "",
        operator_code=obj.operator_code,
        source_system=obj.source_system,
        rol=obj.rol or "",
    )


def _medicion_temp_to_record(obj) -> MedicionTemperaturaSalidaRecord:
    return MedicionTemperaturaSalidaRecord(
        id=obj.id,
        pallet_id=obj.pallet_id,
        fecha=obj.fecha,
        hora=obj.hora or "",
        temperatura_pallet=obj.temperatura_pallet,
        punto_medicion=obj.punto_medicion or "",
        dentro_rango=obj.dentro_rango,
        observaciones=obj.observaciones or "",
        operator_code=obj.operator_code,
        source_system=obj.source_system,
        rol=obj.rol or "",
    )


# ---------------------------------------------------------------------------
# Concrete repositories — entidades base
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
        extra: Optional[dict] = None,
    ) -> BinRecord:
        from operaciones.models import Bin
        fields = dict(extra or {})
        obj = Bin.objects.create(
            temporada=temporada,
            bin_code=bin_code,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
            **{k: v for k, v in fields.items() if hasattr(Bin, k)},
        )
        return _bin_to_record(obj)

    def filter_by_codes(self, temporada: str, bin_codes: list[str]) -> list[BinRecord]:
        from operaciones.models import Bin
        objs = list(Bin.objects.filter(temporada=temporada, bin_code__in=bin_codes))
        return [_bin_to_record(obj) for obj in objs]

    def list_by_lote(self, lote_id: Any) -> list[BinRecord]:
        from operaciones.models import Bin, BinLote
        bin_ids = list(BinLote.objects.filter(lote_id=lote_id).values_list("bin_id", flat=True))
        if not bin_ids:
            return []
        objs = list(Bin.objects.filter(id__in=bin_ids).order_by("id"))
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
        extra: Optional[dict] = None,
    ) -> LoteRecord:
        from operaciones.models import Lote
        fields = dict(extra or {})
        obj = Lote.objects.create(
            temporada=temporada,
            lote_code=lote_code,
            operator_code=operator_code,
            source_system=source_system,
            source_event_id=source_event_id,
            **{k: v for k, v in fields.items() if hasattr(Lote, k)},
        )
        return _lote_to_record(obj)

    def filter_by_codes(self, temporada: str, lote_codes: list[str]) -> list[LoteRecord]:
        from operaciones.models import Lote
        objs = list(Lote.objects.filter(temporada=temporada, lote_code__in=lote_codes))
        return [_lote_to_record(obj) for obj in objs]

    def update(self, lote_id: Any, fields: dict) -> LoteRecord:
        from operaciones.models import Lote
        # Filtrar solo campos que existen en el modelo SQLite para evitar FieldError
        # cuando el llamante (use case compartido con Dataverse) pasa campos como
        # 'etapa_actual' que solo existen en Dataverse y no en el schema SQLite.
        model_fields = {f.name for f in Lote._meta.get_fields() if hasattr(f, "name")}
        safe_fields = {k: v for k, v in fields.items() if k in model_fields}
        if safe_fields:
            Lote.objects.filter(pk=lote_id).update(**safe_fields)
        obj = Lote.objects.get(pk=lote_id)
        return _lote_to_record(obj)

    def list_recent(self, temporada: str, limit: int = 20) -> list[LoteRecord]:
        from operaciones.models import Lote
        objs = list(Lote.objects.filter(temporada=temporada).order_by("-id")[:limit])
        return [_lote_to_record(obj) for obj in objs]


class SqlitePalletRepository(PalletRepository):

    def find_by_code(self, temporada: str, pallet_code: str) -> Optional[PalletRecord]:
        from operaciones.models import Pallet
        obj = Pallet.objects.filter(temporada=temporada, pallet_code=pallet_code).first()
        return _pallet_to_record(obj) if obj else None

    def list_recent(self, limit: int = 30) -> list[PalletRecord]:
        from operaciones.models import Pallet
        qs = Pallet.objects.filter(is_active=True).order_by("-created_at")[:limit]
        return [_pallet_to_record(obj) for obj in qs]

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
        from operaciones.models import Pallet
        defaults = {
            "operator_code": operator_code,
            "source_system": source_system,
            "source_event_id": source_event_id,
        }
        if extra:
            defaults.update({k: v for k, v in extra.items() if hasattr(Pallet, k)})
        obj, created = Pallet.objects.get_or_create(
            temporada=temporada,
            pallet_code=pallet_code,
            defaults=defaults,
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

    def list_by_lote(self, lote_id: Any) -> list[BinLoteRecord]:
        from operaciones.models import BinLote
        objs = list(BinLote.objects.filter(lote_id=lote_id).order_by("id"))
        return [_bin_lote_to_record(obj) for obj in objs]


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

    def find_by_lote(self, lote_id: Any) -> Optional[PalletLoteRecord]:
        from operaciones.models import PalletLote
        obj = PalletLote.objects.filter(lote_id=lote_id).first()
        return _pallet_lote_to_record(obj) if obj else None


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
# Concrete repositories — nuevas entidades del flujo operativo
# ---------------------------------------------------------------------------

class SqliteCamaraMantencionRepository(CamaraMantencionRepository):

    def find_by_lote(self, lote_id: Any) -> Optional[CamaraMantencionRecord]:
        from operaciones.models import CamaraMantencion
        obj = CamaraMantencion.objects.filter(lote_id=lote_id).first()
        return _camara_mantencion_to_record(obj) if obj else None

    def create(self, lote_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> CamaraMantencionRecord:
        from operaciones.models import CamaraMantencion
        fields = dict(extra or {})
        obj = CamaraMantencion.objects.create(
            lote_id=lote_id,
            operator_code=operator_code,
            source_system=source_system,
            **{k: v for k, v in fields.items() if hasattr(CamaraMantencion, k)},
        )
        return _camara_mantencion_to_record(obj)

    def update(self, record_id: Any, fields: dict) -> CamaraMantencionRecord:
        from operaciones.models import CamaraMantencion
        CamaraMantencion.objects.filter(pk=record_id).update(**fields)
        obj = CamaraMantencion.objects.get(pk=record_id)
        return _camara_mantencion_to_record(obj)


class SqliteDesverdizadoRepository(DesverdizadoRepository):

    def find_by_lote(self, lote_id: Any) -> Optional[DesverdizadoRecord]:
        from operaciones.models import Desverdizado
        obj = Desverdizado.objects.filter(lote_id=lote_id).first()
        return _desverdizado_to_record(obj) if obj else None

    def create(self, lote_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> DesverdizadoRecord:
        from operaciones.models import Desverdizado
        fields = dict(extra or {})
        obj = Desverdizado.objects.create(
            lote_id=lote_id,
            operator_code=operator_code,
            source_system=source_system,
            **{k: v for k, v in fields.items() if hasattr(Desverdizado, k)},
        )
        return _desverdizado_to_record(obj)

    def update(self, record_id: Any, fields: dict) -> DesverdizadoRecord:
        from operaciones.models import Desverdizado
        Desverdizado.objects.filter(pk=record_id).update(**fields)
        obj = Desverdizado.objects.get(pk=record_id)
        return _desverdizado_to_record(obj)


class SqliteCalidadDesverdizadoRepository(CalidadDesverdizadoRepository):

    def create(self, lote_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> CalidadDesverdizadoRecord:
        from operaciones.models import CalidadDesverdizado
        fields = dict(extra or {})
        obj = CalidadDesverdizado.objects.create(
            lote_id=lote_id,
            operator_code=operator_code,
            source_system=source_system,
            **{k: v for k, v in fields.items() if hasattr(CalidadDesverdizado, k)},
        )
        return _calidad_desv_to_record(obj)

    def list_by_lote(self, lote_id: Any) -> list[CalidadDesverdizadoRecord]:
        from operaciones.models import CalidadDesverdizado
        objs = CalidadDesverdizado.objects.filter(lote_id=lote_id).order_by("-created_at")
        return [_calidad_desv_to_record(obj) for obj in objs]


class SqliteIngresoAPackingRepository(IngresoAPackingRepository):

    def find_by_lote(self, lote_id: Any) -> Optional[IngresoAPackingRecord]:
        from operaciones.models import IngresoAPacking
        obj = IngresoAPacking.objects.filter(lote_id=lote_id).first()
        return _ingreso_packing_to_record(obj) if obj else None

    def create(self, lote_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> IngresoAPackingRecord:
        from operaciones.models import IngresoAPacking
        fields = dict(extra or {})
        obj = IngresoAPacking.objects.create(
            lote_id=lote_id,
            operator_code=operator_code,
            source_system=source_system,
            **{k: v for k, v in fields.items() if hasattr(IngresoAPacking, k)},
        )
        return _ingreso_packing_to_record(obj)


class SqliteRegistroPackingRepository(RegistroPackingRepository):

    def create(self, lote_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> RegistroPackingRecord:
        from operaciones.models import RegistroPacking
        fields = dict(extra or {})
        obj = RegistroPacking.objects.create(
            lote_id=lote_id,
            operator_code=operator_code,
            source_system=source_system,
            **{k: v for k, v in fields.items() if hasattr(RegistroPacking, k)},
        )
        return _registro_packing_to_record(obj)

    def list_by_lote(self, lote_id: Any) -> list[RegistroPackingRecord]:
        from operaciones.models import RegistroPacking
        objs = RegistroPacking.objects.filter(lote_id=lote_id).order_by("-created_at")
        return [_registro_packing_to_record(obj) for obj in objs]


class SqliteControlProcesoPackingRepository(ControlProcesoPackingRepository):

    def create(self, lote_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> ControlProcesoPackingRecord:
        from operaciones.models import ControlProcesoPacking
        fields = dict(extra or {})
        obj = ControlProcesoPacking.objects.create(
            lote_id=lote_id,
            operator_code=operator_code,
            source_system=source_system,
            **{k: v for k, v in fields.items() if hasattr(ControlProcesoPacking, k)},
        )
        return _control_proceso_to_record(obj)

    def list_by_lote(self, lote_id: Any) -> list[ControlProcesoPackingRecord]:
        from operaciones.models import ControlProcesoPacking
        objs = ControlProcesoPacking.objects.filter(lote_id=lote_id).order_by("-created_at")
        return [_control_proceso_to_record(obj) for obj in objs]


class SqliteCalidadPalletRepository(CalidadPalletRepository):

    def create(self, pallet_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> CalidadPalletRecord:
        from operaciones.models import CalidadPallet
        fields = dict(extra or {})
        obj = CalidadPallet.objects.create(
            pallet_id=pallet_id,
            operator_code=operator_code,
            source_system=source_system,
            **{k: v for k, v in fields.items() if hasattr(CalidadPallet, k)},
        )
        return _calidad_pallet_to_record(obj)

    def list_by_pallet(self, pallet_id: Any) -> list[CalidadPalletRecord]:
        from operaciones.models import CalidadPallet
        objs = CalidadPallet.objects.filter(pallet_id=pallet_id).order_by("-created_at")
        return [_calidad_pallet_to_record(obj) for obj in objs]


class SqliteCalidadPalletMuestraRepository(CalidadPalletMuestraRepository):

    def create(self, pallet_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> CalidadPalletMuestraRecord:
        from operaciones.models import CalidadPalletMuestra
        fields = dict(extra or {})
        obj = CalidadPalletMuestra.objects.create(
            pallet_id=pallet_id,
            operator_code=operator_code,
            source_system=source_system,
            **{k: v for k, v in fields.items() if hasattr(CalidadPalletMuestra, k)},
        )
        return _calidad_pallet_muestra_to_record(obj)

    def list_by_pallet(self, pallet_id: Any) -> list[CalidadPalletMuestraRecord]:
        from operaciones.models import CalidadPalletMuestra
        objs = CalidadPalletMuestra.objects.filter(pallet_id=pallet_id).order_by("numero_muestra")
        return [_calidad_pallet_muestra_to_record(obj) for obj in objs]


class SqliteCamaraFrioRepository(CamaraFrioRepository):

    def find_by_pallet(self, pallet_id: Any) -> Optional[CamaraFrioRecord]:
        from operaciones.models import CamaraFrio
        obj = CamaraFrio.objects.filter(pallet_id=pallet_id).first()
        return _camara_frio_to_record(obj) if obj else None

    def create(self, pallet_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> CamaraFrioRecord:
        from operaciones.models import CamaraFrio
        fields = dict(extra or {})
        obj = CamaraFrio.objects.create(
            pallet_id=pallet_id,
            operator_code=operator_code,
            source_system=source_system,
            **{k: v for k, v in fields.items() if hasattr(CamaraFrio, k)},
        )
        return _camara_frio_to_record(obj)

    def update(self, record_id: Any, fields: dict) -> CamaraFrioRecord:
        from operaciones.models import CamaraFrio
        CamaraFrio.objects.filter(pk=record_id).update(**fields)
        obj = CamaraFrio.objects.get(pk=record_id)
        return _camara_frio_to_record(obj)


class SqliteMedicionTemperaturaSalidaRepository(MedicionTemperaturaSalidaRepository):

    def create(self, pallet_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> MedicionTemperaturaSalidaRecord:
        from operaciones.models import MedicionTemperaturaSalida
        fields = dict(extra or {})
        obj = MedicionTemperaturaSalida.objects.create(
            pallet_id=pallet_id,
            operator_code=operator_code,
            source_system=source_system,
            **{k: v for k, v in fields.items() if hasattr(MedicionTemperaturaSalida, k)},
        )
        return _medicion_temp_to_record(obj)

    def list_by_pallet(self, pallet_id: Any) -> list[MedicionTemperaturaSalidaRecord]:
        from operaciones.models import MedicionTemperaturaSalida
        objs = MedicionTemperaturaSalida.objects.filter(pallet_id=pallet_id).order_by("-created_at")
        return [_medicion_temp_to_record(obj) for obj in objs]


class SqliteSequenceCounterRepository(SequenceCounterRepository):

    def get_next(self, entity_name: str, dimension: str) -> int:
        from django.db import transaction as db_transaction
        from operaciones.models import SequenceCounter
        with db_transaction.atomic():
            obj, _ = SequenceCounter.objects.select_for_update().get_or_create(
                entity_name=entity_name,
                dimension=dimension,
                defaults={"last_value": 0},
            )
            obj.last_value += 1
            obj.save(update_fields=["last_value"])
            return obj.last_value

    def current_value(self, entity_name: str, dimension: str) -> int:
        from operaciones.models import SequenceCounter
        obj = SequenceCounter.objects.filter(
            entity_name=entity_name,
            dimension=dimension,
        ).first()
        return obj.last_value if obj else 0


# ---------------------------------------------------------------------------
# Helpers: model instance → record type — Planillas de Control de Calidad
# ---------------------------------------------------------------------------

def _planilla_desv_calibre_to_record(obj) -> PlanillaDesverdizadoCalibreRecord:
    import json
    grupos = obj.calibres_grupos
    calibres_json = json.dumps(grupos, ensure_ascii=False) if isinstance(grupos, list) else (grupos or "[]")
    return PlanillaDesverdizadoCalibreRecord(
        id=obj.pk,
        lote_id=obj.lote_id,
        supervisor=obj.supervisor or "",
        productor=obj.productor or "",
        variedad=obj.variedad or "",
        trazabilidad=obj.trazabilidad or "",
        cod_sdp=obj.cod_sdp or "",
        fecha_cosecha=obj.fecha_cosecha,
        fecha_despacho=obj.fecha_despacho,
        cuartel=obj.cuartel or "",
        sector=obj.sector or "",
        oleocelosis=obj.oleocelosis,
        heridas_abiertas=obj.heridas_abiertas,
        rugoso=obj.rugoso,
        deforme=obj.deforme,
        golpe_sol=obj.golpe_sol,
        verdes=obj.verdes,
        pre_calibre_defecto=obj.pre_calibre_defecto,
        palo_largo=obj.palo_largo,
        calibres_grupos_json=calibres_json,
        observaciones=obj.observaciones or "",
        rol=obj.rol or "",
        operator_code=getattr(obj, "operator_code", "") or "",
        source_system=getattr(obj, "source_system", "local") or "local",
    )


def _planilla_desv_semillas_to_record(obj) -> PlanillaDesverdizadoSemillasRecord:
    import json
    frutas = obj.frutas_data
    frutas_json = json.dumps(frutas, ensure_ascii=False) if isinstance(frutas, list) else (frutas or "[]")
    return PlanillaDesverdizadoSemillasRecord(
        id=obj.pk,
        lote_id=obj.lote_id,
        fecha=obj.fecha,
        supervisor=obj.supervisor or "",
        productor=obj.productor or "",
        variedad=obj.variedad or "",
        cuartel=obj.cuartel or "",
        sector=obj.sector or "",
        trazabilidad=obj.trazabilidad or "",
        cod_sdp=obj.cod_sdp or "",
        color=obj.color or "",
        frutas_data_json=frutas_json,
        total_frutos_muestra=obj.total_frutos_muestra,
        total_frutos_con_semillas=obj.total_frutos_con_semillas,
        total_semillas=obj.total_semillas,
        pct_frutos_con_semillas=obj.pct_frutos_con_semillas,
        promedio_semillas=obj.promedio_semillas,
        rol=obj.rol or "",
        operator_code=getattr(obj, "operator_code", "") or "",
        source_system=getattr(obj, "source_system", "local") or "local",
    )


def _planilla_calidad_packing_to_record(obj) -> PlanillaCalidadPackingRecord:
    return PlanillaCalidadPackingRecord(
        id=obj.pk,
        pallet_id=obj.pallet_id,
        productor=obj.productor or "",
        trazabilidad=obj.trazabilidad or "",
        cod_sdp=obj.cod_sdp or "",
        cuartel=obj.cuartel or "",
        sector=obj.sector or "",
        nombre_control=obj.nombre_control or "",
        n_cuadrilla=obj.n_cuadrilla or "",
        supervisor=obj.supervisor or "",
        fecha_despacho=obj.fecha_despacho,
        fecha_cosecha=obj.fecha_cosecha,
        numero_hoja=obj.numero_hoja or 1,
        tipo_fruta=obj.tipo_fruta or "",
        variedad=obj.variedad or "",
        temperatura=obj.temperatura,
        humedad=obj.humedad,
        horas_cosecha=obj.horas_cosecha or "",
        color=obj.color or "",
        n_frutos_muestreados=obj.n_frutos_muestreados,
        brix=obj.brix,
        pre_calibre=obj.pre_calibre,
        sobre_calibre=obj.sobre_calibre,
        color_contrario_evaluado=obj.color_contrario_evaluado,
        cantidad_frutos=obj.cantidad_frutos,
        ausencia_roseta=obj.ausencia_roseta,
        deformes=obj.deformes,
        frutos_con_semilla=obj.frutos_con_semilla,
        n_semillas=obj.n_semillas,
        fumagina=obj.fumagina,
        h_cicatrizadas=obj.h_cicatrizadas,
        manchas=obj.manchas,
        peduculo_largo=obj.peduculo_largo,
        residuos=obj.residuos,
        rugosos=obj.rugosos,
        russet_leve_claros=obj.russet_leve_claros,
        russet_moderados_claros=obj.russet_moderados_claros,
        russet_severos_oscuros=obj.russet_severos_oscuros,
        creasing_leve=obj.creasing_leve,
        creasing_mod_sev=obj.creasing_mod_sev,
        dano_frio_granulados=obj.dano_frio_granulados,
        bufado=obj.bufado,
        deshidratacion_roseta=obj.deshidratacion_roseta,
        golpe_sol=obj.golpe_sol,
        h_abiertas_superior=obj.h_abiertas_superior,
        h_abiertas_inferior=obj.h_abiertas_inferior,
        acostillado=obj.acostillado,
        machucon=obj.machucon,
        blandos=obj.blandos,
        oleocelosis=obj.oleocelosis,
        ombligo_rasgado=obj.ombligo_rasgado,
        colapso_corteza=obj.colapso_corteza,
        pudricion=obj.pudricion,
        dano_arana_leve=obj.dano_arana_leve,
        dano_arana_moderado=obj.dano_arana_moderado,
        dano_arana_severo=obj.dano_arana_severo,
        dano_mecanico=obj.dano_mecanico,
        otros_condicion=obj.otros_condicion or "",
        total_defectos_pct=obj.total_defectos_pct,
        rol=obj.rol or "",
        operator_code=getattr(obj, "operator_code", "") or "",
        source_system=getattr(obj, "source_system", "local") or "local",
    )


def _planilla_calidad_camara_to_record(obj) -> PlanillaCalidadCamaraRecord:
    import json
    meds = obj.mediciones
    meds_json = json.dumps(meds, ensure_ascii=False) if isinstance(meds, list) else (meds or "[]")
    return PlanillaCalidadCamaraRecord(
        id=obj.pk,
        pallet_id=obj.pallet_id,
        fecha_control=obj.fecha_control,
        tipo_proceso=obj.tipo_proceso or "",
        zona_planta=obj.zona_planta or "",
        tunel_camara=obj.tunel_camara or "",
        capacidad_maxima=obj.capacidad_maxima or "",
        temperatura_equipos=obj.temperatura_equipos or "",
        codigo_envases=obj.codigo_envases or "",
        cantidad_pallets=obj.cantidad_pallets,
        especie=obj.especie or "",
        variedad=obj.variedad or "",
        fecha_embalaje=obj.fecha_embalaje,
        estiba=obj.estiba or "",
        tipo_inversion=obj.tipo_inversion or "",
        mediciones_json=meds_json,
        temp_pulpa_ext_inicio=obj.temp_pulpa_ext_inicio,
        temp_pulpa_ext_termino=obj.temp_pulpa_ext_termino,
        temp_pulpa_int_inicio=obj.temp_pulpa_int_inicio,
        temp_pulpa_int_termino=obj.temp_pulpa_int_termino,
        temp_ambiente_inicio=obj.temp_ambiente_inicio,
        temp_ambiente_termino=obj.temp_ambiente_termino,
        tiempo_carga_inicio=obj.tiempo_carga_inicio or "",
        tiempo_carga_termino=obj.tiempo_carga_termino or "",
        tiempo_descarga_inicio=obj.tiempo_descarga_inicio or "",
        tiempo_descarga_termino=obj.tiempo_descarga_termino or "",
        tiempo_enfriado_inicio=obj.tiempo_enfriado_inicio or "",
        tiempo_enfriado_termino=obj.tiempo_enfriado_termino or "",
        observaciones=obj.observaciones or "",
        nombre_control=obj.nombre_control or "",
        rol=obj.rol or "",
        operator_code=getattr(obj, "operator_code", "") or "",
        source_system=getattr(obj, "source_system", "local") or "local",
    )


# ---------------------------------------------------------------------------
# SQLite repositories — Planillas de Control de Calidad
# ---------------------------------------------------------------------------

class SqlitePlanillaDesverdizadoCalibreRepository(PlanillaDesverdizadoCalibreRepository):

    def create(self, lote_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> PlanillaDesverdizadoCalibreRecord:
        from operaciones.models import PlanillaDesverdizadoCalibre
        fields = dict(extra or {})
        obj = PlanillaDesverdizadoCalibre.objects.create(
            lote_id=lote_id,
            operator_code=operator_code,
            source_system=source_system,
            **{k: v for k, v in fields.items() if hasattr(PlanillaDesverdizadoCalibre, k)},
        )
        return _planilla_desv_calibre_to_record(obj)

    def list_by_lote(self, lote_id: Any) -> list[PlanillaDesverdizadoCalibreRecord]:
        from operaciones.models import PlanillaDesverdizadoCalibre
        objs = PlanillaDesverdizadoCalibre.objects.filter(lote_id=lote_id).order_by("-created_at")
        return [_planilla_desv_calibre_to_record(obj) for obj in objs]


class SqlitePlanillaDesverdizadoSemillasRepository(PlanillaDesverdizadoSemillasRepository):

    def create(self, lote_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> PlanillaDesverdizadoSemillasRecord:
        from operaciones.models import PlanillaDesverdizadoSemillas
        fields = dict(extra or {})
        obj = PlanillaDesverdizadoSemillas.objects.create(
            lote_id=lote_id,
            operator_code=operator_code,
            source_system=source_system,
            **{k: v for k, v in fields.items() if hasattr(PlanillaDesverdizadoSemillas, k)},
        )
        return _planilla_desv_semillas_to_record(obj)

    def list_by_lote(self, lote_id: Any) -> list[PlanillaDesverdizadoSemillasRecord]:
        from operaciones.models import PlanillaDesverdizadoSemillas
        objs = PlanillaDesverdizadoSemillas.objects.filter(lote_id=lote_id).order_by("-created_at")
        return [_planilla_desv_semillas_to_record(obj) for obj in objs]


class SqlitePlanillaCalidadPackingRepository(PlanillaCalidadPackingRepository):

    def create(self, pallet_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> PlanillaCalidadPackingRecord:
        from operaciones.models import PlanillaCalidadPacking
        fields = dict(extra or {})
        obj = PlanillaCalidadPacking.objects.create(
            pallet_id=pallet_id,
            operator_code=operator_code,
            source_system=source_system,
            **{k: v for k, v in fields.items() if hasattr(PlanillaCalidadPacking, k)},
        )
        return _planilla_calidad_packing_to_record(obj)

    def list_by_pallet(self, pallet_id: Any) -> list[PlanillaCalidadPackingRecord]:
        from operaciones.models import PlanillaCalidadPacking
        objs = PlanillaCalidadPacking.objects.filter(pallet_id=pallet_id).order_by("-created_at")
        return [_planilla_calidad_packing_to_record(obj) for obj in objs]


class SqlitePlanillaCalidadCamaraRepository(PlanillaCalidadCamaraRepository):

    def create(self, pallet_id: Any, *, operator_code: str = "",
               source_system: str = "local", extra: Optional[dict] = None,
               ) -> PlanillaCalidadCamaraRecord:
        from operaciones.models import PlanillaCalidadCamara
        fields = dict(extra or {})
        obj = PlanillaCalidadCamara.objects.create(
            pallet_id=pallet_id,
            operator_code=operator_code,
            source_system=source_system,
            **{k: v for k, v in fields.items() if hasattr(PlanillaCalidadCamara, k)},
        )
        return _planilla_calidad_camara_to_record(obj)

    def list_by_pallet(self, pallet_id: Any) -> list[PlanillaCalidadCamaraRecord]:
        from operaciones.models import PlanillaCalidadCamara
        objs = PlanillaCalidadCamara.objects.filter(pallet_id=pallet_id).order_by("-created_at")
        return [_planilla_calidad_camara_to_record(obj) for obj in objs]


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
        camara_mantencions=SqliteCamaraMantencionRepository(),
        desverdizados=SqliteDesverdizadoRepository(),
        calidad_desverdizados=SqliteCalidadDesverdizadoRepository(),
        ingresos_packing=SqliteIngresoAPackingRepository(),
        registros_packing=SqliteRegistroPackingRepository(),
        control_proceso_packings=SqliteControlProcesoPackingRepository(),
        calidad_pallets=SqliteCalidadPalletRepository(),
        calidad_pallet_muestras=SqliteCalidadPalletMuestraRepository(),
        camara_frios=SqliteCamaraFrioRepository(),
        mediciones_temperatura=SqliteMedicionTemperaturaSalidaRepository(),
        planillas_desv_calibres=SqlitePlanillaDesverdizadoCalibreRepository(),
        planillas_desv_semillas=SqlitePlanillaDesverdizadoSemillasRepository(),
        planillas_calidad_packing=SqlitePlanillaCalidadPackingRepository(),
        planillas_calidad_camara=SqlitePlanillaCalidadCamaraRepository(),
        sequences=SqliteSequenceCounterRepository(),
    )
