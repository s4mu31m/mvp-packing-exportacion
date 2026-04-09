"""
Vistas web del flujo operativo de packing.
Cada vista corresponde a una etapa del flujo.

Flujo de recepcion (preferido del MVP):
  RecepcionView — tres acciones: iniciar_lote / agregar_bin / cerrar_lote
  El lote activo se persiste en sesion como 'recepcion_lote_code'.

"""
import csv
import datetime
import json
import logging
import os
import tempfile
import threading
from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from usuarios.permissions import get_roles, is_admin


class RolRequiredMixin(UserPassesTestMixin):
    """Protege vistas por rol de negocio. Declarar roles_requeridos en subclase."""
    roles_requeridos: list[str] = []

    def test_func(self):
        if is_admin(self.request):
            return True
        return any(r in get_roles(self.request) for r in self.roles_requeridos)
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView, View
from django.utils import timezone

from operaciones.forms import (
    IniciarLoteForm,
    CerrarLoteForm,
    BinForm,
    EditBinVariableForm,
    CamaraMantencionForm,
    DesverdizadoForm,
    IngresoPackingForm,
    RegistroPackingForm,
    ControlProcesoPackingForm,
    CalidadPalletForm,
    CalidadPalletMuestraForm,
    CamaraFrioForm,
    MedicionTemperaturaForm,
    PlanillaDesverdizadoCalibreForm,
    PlanillaDesverdizadoSemillasForm,
    PlanillaCalidadPackingForm,
    PlanillaCalidadCamaraForm,
)
from operaciones.application.use_cases import (
    iniciar_lote_recepcion,
    agregar_bin_a_lote_abierto,
    cerrar_lote_recepcion,
    registrar_camara_mantencion,
    registrar_desverdizado,
    registrar_ingreso_packing,
    registrar_registro_packing,
    registrar_control_proceso_packing,
    registrar_calidad_pallet,
    cerrar_pallet,
    registrar_camara_frio,
    registrar_medicion_temperatura,
    guardar_muestra_calidad_pallet,
    registrar_planilla_desv_calibre,
    registrar_planilla_desv_semillas,
    registrar_planilla_calidad_packing,
    registrar_planilla_calidad_camara,
    eliminar_bin_de_lote,
    editar_bin_de_lote,
)
from operaciones.models import (
    Lote,
    LotePlantaEstado,
    Pallet,
)

def _temporada(request) -> str:
    """Devuelve la temporada activa: del POST, sesion o año actual."""
    return (
        request.POST.get("temporada")
        or request.session.get("temporada_activa")
        or str(datetime.date.today().year)
    )


def _serialize_form_value(value):
    """
    Normaliza cleaned_data para payloads de vistas web.

    Los TimeField de Django salen como HH:mm:ss, pero los validadores de la
    aplicacion esperan HH:mm.
    """
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, datetime.time):
        return value.strftime("%H:%M")
    if isinstance(value, datetime.date):
        return value.isoformat()
    return value


def _etapa_lote(lote: Lote) -> str:
    """
    Determina la etapa actual de un lote revisando qué registros existen.
    Usado para consulta jefatura y dashboard.
    """
    try:
        if hasattr(lote, "pallet_lotes") and lote.pallet_lotes.exists():
            pl = lote.pallet_lotes.first()
            if pl and hasattr(pl.pallet, "camara_frio"):
                return "Camara Frio"
            return "Pallet Cerrado"
    except Exception:
        pass
    try:
        if lote.registros_packing.exists() or lote.control_proceso_packing.exists():
            return "Packing / Proceso"
    except Exception:
        pass
    try:
        if hasattr(lote, "ingreso_packing"):
            return "Ingreso Packing"
    except Exception:
        pass
    try:
        if hasattr(lote, "desverdizado"):
            return "Desverdizado"
    except Exception:
        pass
    try:
        if hasattr(lote, "camara_mantencion"):
            return "Mantencion"
    except Exception:
        pass
    if lote.estado == LotePlantaEstado.CERRADO:
        if lote.requiere_desverdizado:
            return "Pendiente Desv."
        return "Pesado / Pendiente"
    if lote.estado == LotePlantaEstado.ABIERTO:
        return "Recepcion"
    return lote.get_estado_display()


def _kilos_recientes_lote(lote, *, include_bin_fallback: bool = True) -> tuple:
    """
    Retorna (kilos_bruto, kilos_neto) usando el pesaje mas reciente disponible.
    Prioridad: ingreso_packing > desverdizado salida > conformacion > suma bins.
    Usa reverse one-to-one accessors de Django ORM (lote.desverdizado, lote.ingreso_packing).
    """
    kb = float(lote.kilos_bruto_conformacion) if lote.kilos_bruto_conformacion is not None else None
    kn = float(lote.kilos_neto_conformacion) if lote.kilos_neto_conformacion is not None else None
    try:
        desv = lote.desverdizado
        if desv.kilos_bruto_salida is not None:
            kb = float(desv.kilos_bruto_salida)
        if desv.kilos_neto_salida is not None:
            kn = float(desv.kilos_neto_salida)
    except Exception:
        pass
    try:
        ip = lote.ingreso_packing
        if ip.kilos_bruto_ingreso_packing is not None:
            kb = float(ip.kilos_bruto_ingreso_packing)
        if ip.kilos_neto_ingreso_packing is not None:
            kn = float(ip.kilos_neto_ingreso_packing)
    except Exception:
        pass
    if include_bin_fallback and (kb is None or kn is None):
        try:
            bin_lotes = list(lote.bin_lotes.select_related("bin").all())
            if kb is None:
                total = sum(
                    float(bl.bin.kilos_bruto_ingreso)
                    for bl in bin_lotes
                    if bl.bin.kilos_bruto_ingreso is not None
                )
                if total > 0:
                    kb = total
            if kn is None:
                total = sum(
                    float(bl.bin.kilos_neto_ingreso)
                    for bl in bin_lotes
                    if bl.bin.kilos_neto_ingreso is not None
                )
                if total > 0:
                    kn = total
        except Exception:
            pass
    return kb, kn


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "operaciones/dashboard.html"
    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Dashboard — Turno Actual"
        temporada = (
            self.request.session.get("temporada_activa")
            or str(datetime.date.today().year)
        )
        ctx["temporada"] = temporada

        from django.conf import settings
        backend = getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip()

        if backend == "dataverse":
            ctx["kpis"], ctx["lotes_activos"] = self._context_dataverse()
        else:
            ctx["kpis"], ctx["lotes_activos"] = self._context_sqlite(temporada)

        return ctx

    def _context_sqlite(self, temporada: str):
        """KPIs y lista de lotes desde SQLite ORM."""
        try:
            lotes_qs = Lote.objects.filter(temporada=temporada, is_active=True)
            lotes_abiertos = lotes_qs.filter(estado=LotePlantaEstado.ABIERTO)
            lotes_cerrados = lotes_qs.filter(estado=LotePlantaEstado.CERRADO)
            lotes_finalizados = lotes_qs.filter(estado=LotePlantaEstado.FINALIZADO)

            from operaciones.models import BinLote
            hoy = datetime.date.today()
            bins_hoy = BinLote.objects.filter(created_at__date=hoy).count()

            lotes_activos_qs = lotes_qs.exclude(
                estado=LotePlantaEstado.FINALIZADO
            ).order_by("-created_at")[:20]

            lotes_activos = [
                {
                    "codigo": lote.lote_code,
                    "bins": lote.cantidad_bins,
                    "etapa": _etapa_lote(lote),
                    "estado": lote.estado,
                }
                for lote in lotes_activos_qs
            ]
            kpis = {
                "lotes_abiertos":    lotes_abiertos.count(),
                "lotes_cerrados":    lotes_cerrados.count(),
                "lotes_finalizados": lotes_finalizados.count(),
                "total_lotes":       lotes_qs.count(),
                "bins_hoy":          bins_hoy,
            }
            return kpis, lotes_activos
        except Exception:
            return {}, []

    def _context_dataverse(self):
        """
        KPIs y lista de lotes desde Dataverse.

        Usa crf21_etapa_actual como fuente principal de etapa (disponible desde 2026-03-31).
        Para lotes antiguos con etapa_actual=null, retorna 'Recepcion' como fallback
        conservador (sin queries adicionales para no afectar rendimiento del dashboard).

        Limitaciones residuales del modelo Dataverse:
        - 'estado' (ABIERTO/CERRADO/FINALIZADO) no existe en Dataverse.
          lotes_cerrados y lotes_finalizados se derivan por etapa: si etapa != 'Recepcion'
          se considera cerrado (recepcion completada).
        - 'bins_hoy' usa suma de bins de lotes recientes como aproximacion.
        """
        try:
            from infrastructure.repository_factory import get_repositories
            from infrastructure.dataverse.repositories import resolve_etapa_lote
            repos = get_repositories()
            lotes = repos.lotes.list_recent(limit=50)

            lotes_activos = []
            lotes_en_recepcion = 0
            lotes_post_recepcion = 0
            for l in lotes:
                etapa = resolve_etapa_lote(l)   # usa etapa_actual persistida; fallback "Recepcion"
                if etapa == "Recepcion":
                    lotes_en_recepcion += 1
                else:
                    lotes_post_recepcion += 1
                lotes_activos.append({
                    "codigo": l.lote_code,
                    "bins":   l.cantidad_bins,
                    "etapa":  etapa,
                    "estado": l.estado,    # siempre "abierto" (campo no existe en DV)
                })

            kpis = {
                "lotes_abiertos":    lotes_en_recepcion,
                "lotes_cerrados":    lotes_post_recepcion,
                "lotes_finalizados": 0,             # sin equivalente directo en Dataverse
                "total_lotes":       len(lotes),
                "bins_hoy":          sum(l.cantidad_bins for l in lotes),
            }
            return kpis, lotes_activos
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Dashboard Dataverse error: %s", exc)
            return {}, []


# ---------------------------------------------------------------------------
# Recepcion de bins — flujo de lote abierto
# ---------------------------------------------------------------------------

class RecepcionView(LoginRequiredMixin, RolRequiredMixin, TemplateView):
    roles_requeridos = ["Recepcion"]
    template_name = "operaciones/recepcion.html"
    login_url = reverse_lazy("usuarios:login")

    CAMPOS_BASE = ["codigo_productor", "tipo_cultivo", "variedad_fruta", "color", "fecha_cosecha"]

    def _lote_activo(self, request):
        """
        Retorna el lote activo desde sesion.

        En SQLite retorna la instancia ORM (Lote).
        En Dataverse retorna un LoteRecord (dataclass) obtenido via repositorio.
        En ambos casos el objeto expone .lote_code, .cantidad_bins, .estado.
        """
        lote_code = request.session.get("lote_activo_code")
        if not lote_code:
            return None
        temporada = _temporada(request)

        from django.conf import settings
        if getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip() == "dataverse":
            return self._lote_activo_dataverse(request, temporada, lote_code)

        # -- Backend SQLite: usa ORM Django --
        try:
            lote = Lote.objects.get(temporada=temporada, lote_code=lote_code)
            if lote.estado != LotePlantaEstado.ABIERTO:
                request.session.pop("lote_activo_code", None)
                request.session.pop("lote_activo_campos_base", None)
                return None
            return lote
        except Lote.DoesNotExist:
            request.session.pop("lote_activo_code", None)
            request.session.pop("lote_activo_campos_base", None)
            return None

    def _lote_activo_dataverse(self, request, temporada, lote_code):
        """
        Resuelve el lote activo consultando Dataverse via repositorio.
        Usa etapa_actual para validar que el lote siga en 'Recepcion'.
        Si etapa_actual != 'Recepcion' (o distinto de null), el lote ya
        fue cerrado y no se permite agregar bins — se limpia la sesion.
        """
        try:
            from infrastructure.repository_factory import get_repositories
            from infrastructure.dataverse.repositories import resolve_etapa_lote
            repos = get_repositories()
            lote = repos.lotes.find_by_code(temporada, lote_code)
            if not lote:
                request.session.pop("lote_activo_code", None)
                request.session.pop("lote_activo_campos_base", None)
                return None
            # Validar que el lote siga en etapa Recepcion
            etapa = resolve_etapa_lote(lote)
            if etapa and etapa != "Recepcion":
                request.session.pop("lote_activo_code", None)
                request.session.pop("lote_activo_campos_base", None)
                return None
            return lote
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "RecepcionView._lote_activo_dataverse error para %s: %s", lote_code, exc
            )
            return None

    def _bins_de_lote(self, lote):
        """
        Retorna los bins del lote.
        En SQLite usa ORM. En Dataverse usa repos.bins.list_by_lote.
        """
        from django.conf import settings
        if getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip() == "dataverse":
            try:
                from infrastructure.repository_factory import get_repositories
                repos = get_repositories()
                return repos.bins.list_by_lote(lote.id)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning(
                    "RecepcionView._bins_de_lote dataverse error: %s", exc
                )
                return []
        return [bl.bin for bl in lote.bin_lotes.select_related("bin").order_by("created_at")]

    def get(self, request, *args, **kwargs):
        lote = self._lote_activo(request)
        campos_base = request.session.get("lote_activo_campos_base", {})

        bins = []
        total_peso_neto = 0
        form_bin = BinForm(initial=campos_base) if campos_base else BinForm()

        if lote:
            bins = self._bins_de_lote(lote)
            total_peso_neto = sum((b.kilos_neto_ingreso or 0) for b in bins)

        ctx = {
            "page_title": "Recepcion de Bins",
            "lote": lote,
            "bins_del_lote": bins,
            "total_peso_neto": total_peso_neto,
            "campos_base": campos_base,
            "form_iniciar": IniciarLoteForm(),
            "form_bin": form_bin,
            "form_cerrar": CerrarLoteForm(),
            "campos_base_keys": self.CAMPOS_BASE,
        }
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action", "")
        if action == "iniciar":
            return self._handle_iniciar(request)
        if action == "agregar_bin":
            return self._handle_agregar_bin(request)
        if action == "cerrar":
            return self._handle_cerrar(request)
        if action == "eliminar_bin":
            return self._handle_eliminar_bin(request)
        if action == "editar_bin":
            return self._handle_editar_bin(request)
        messages.error(request, "Accion desconocida.")
        return redirect("operaciones:recepcion")

    def _handle_iniciar(self, request):
        form = IniciarLoteForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Formulario invalido para iniciar lote.")
            return redirect("operaciones:recepcion")
        cd = form.cleaned_data
        payload = {
            "temporada": _temporada(request),
            "operator_code": request.session.get("crf21_codigooperador", ""),
            "source_system": "web",
        }
        result = iniciar_lote_recepcion(payload)
        if result.ok:
            request.session["lote_activo_code"] = result.data["lote_code"]
            request.session.pop("lote_activo_campos_base", None)
            messages.success(
                request,
                f"Lote {result.data['lote_code']} iniciado. Agregue los bins.",
            )
        else:
            for err in result.errors:
                messages.error(request, err)
        return redirect("operaciones:recepcion")

    def _handle_agregar_bin(self, request):
        lote_code = request.session.get("lote_activo_code")
        if not lote_code:
            messages.error(request, "No hay lote abierto. Inicie un lote primero.")
            return redirect("operaciones:recepcion")

        form = BinForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Formulario invalido.")
            return redirect("operaciones:recepcion")

        cd = form.cleaned_data
        campos_base = request.session.get("lote_activo_campos_base", {})

        # Validar consistencia con campos base si ya existe al menos un bin
        if campos_base:
            incompatibles = []
            mapeo = {
                "codigo_productor": "Codigo productor",
                "tipo_cultivo": "Tipo cultivo",
                "variedad_fruta": "Variedad",
                "color": "Color",
                "fecha_cosecha": "Fecha cosecha",
            }
            for campo, etiqueta in mapeo.items():
                val_nuevo = str(cd.get(campo) or "").strip()
                val_base = str(campos_base.get(campo, "")).strip()
                if val_base and val_nuevo and val_nuevo != val_base:
                    incompatibles.append(f"{etiqueta}: esperado '{val_base}', recibido '{val_nuevo}'")
            if incompatibles:
                messages.error(
                    request,
                    "Bin incompatible con el lote — " + " | ".join(incompatibles),
                )
                return redirect("operaciones:recepcion")

        payload = {
            "temporada": _temporada(request),
            "lote_code": lote_code,
            "operator_code": request.session.get("crf21_codigooperador", ""),
            "source_system": "web",
            "fecha_cosecha": _serialize_form_value(cd["fecha_cosecha"]) if cd.get("fecha_cosecha") else None,
            "variedad_fruta": cd.get("variedad_fruta") or "",
            "codigo_productor": cd.get("codigo_productor") or "",
            "tipo_cultivo": cd.get("tipo_cultivo") or "",
            "numero_cuartel": cd.get("numero_cuartel") or "",
            "color": cd.get("color") or "",
            "hora_recepcion": _serialize_form_value(cd["hora_recepcion"]) if cd.get("hora_recepcion") else "",
            "kilos_bruto_ingreso": float(cd["kilos_bruto_ingreso"]) if cd.get("kilos_bruto_ingreso") else None,
            "kilos_neto_ingreso": float(cd["kilos_neto_ingreso"]) if cd.get("kilos_neto_ingreso") else None,
            "a_o_r": cd.get("a_o_r") or None,
            "observaciones": cd.get("observaciones") or "",
        }

        result = agregar_bin_a_lote_abierto(payload)
        if result.ok:
            # Actualizar campos_base con los valores del bin — solo rellena campos vacios
            current = dict(campos_base)
            for campo in ("codigo_productor", "tipo_cultivo", "variedad_fruta", "color"):
                if not current.get(campo) and cd.get(campo):
                    current[campo] = cd[campo]
            if not current.get("fecha_cosecha") and cd.get("fecha_cosecha"):
                current["fecha_cosecha"] = _serialize_form_value(cd["fecha_cosecha"])
            request.session["lote_activo_campos_base"] = current
            messages.success(
                request,
                f"Bin {result.data['bin_code']} agregado al lote {lote_code}.",
            )
        else:
            for err in result.errors:
                messages.error(request, err)
        return redirect("operaciones:recepcion")

    def _handle_cerrar(self, request):
        lote_code = request.session.get("lote_activo_code")
        if not lote_code:
            messages.error(request, "No hay lote abierto para cerrar.")
            return redirect("operaciones:recepcion")

        form = CerrarLoteForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Formulario invalido para cerrar lote.")
            return redirect("operaciones:recepcion")

        cd = form.cleaned_data
        payload = {
            "temporada": _temporada(request),
            "lote_code": lote_code,
            "operator_code": request.session.get("crf21_codigooperador", ""),
            "source_system": "web",
            "requiere_desverdizado": cd.get("requiere_desverdizado") or False,
            "disponibilidad_camara_desverdizado": cd.get("disponibilidad_camara_desverdizado") or None,
            "kilos_bruto_conformacion": float(cd["kilos_bruto_conformacion"]) if cd.get("kilos_bruto_conformacion") else None,
            "kilos_neto_conformacion": float(cd["kilos_neto_conformacion"]) if cd.get("kilos_neto_conformacion") else None,
        }
        result = cerrar_lote_recepcion(payload)
        if result.ok:
            request.session.pop("lote_activo_code", None)
            request.session.pop("lote_activo_campos_base", None)
            messages.success(request, result.message)
        else:
            for err in result.errors:
                messages.error(request, err)
        return redirect("operaciones:recepcion")

    def _handle_eliminar_bin(self, request):
        lote_code = request.session.get("lote_activo_code")
        if not lote_code:
            messages.error(request, "No hay lote abierto.")
            return redirect("operaciones:recepcion")

        bin_code = request.POST.get("bin_code", "").strip()
        if not bin_code:
            messages.error(request, "Bin no identificado.")
            return redirect("operaciones:recepcion")

        result = eliminar_bin_de_lote({
            "temporada": _temporada(request),
            "lote_code": lote_code,
            "bin_code": bin_code,
        })
        if result.ok:
            if result.data.get("cantidad_bins_restantes", 1) == 0:
                request.session.pop("lote_activo_campos_base", None)
            messages.success(request, f"Bin {bin_code} eliminado del lote.")
        else:
            for err in result.errors:
                messages.error(request, err)
        return redirect("operaciones:recepcion")

    def _handle_editar_bin(self, request):
        lote_code = request.session.get("lote_activo_code")
        if not lote_code:
            messages.error(request, "No hay lote abierto.")
            return redirect("operaciones:recepcion")

        bin_code = request.POST.get("bin_code", "").strip()
        if not bin_code:
            messages.error(request, "Bin no identificado.")
            return redirect("operaciones:recepcion")

        form = EditBinVariableForm(request.POST)
        if not form.is_valid():
            for field_errors in form.errors.values():
                for err in field_errors:
                    messages.error(request, err)
            return redirect("operaciones:recepcion")

        cd = form.cleaned_data
        result = editar_bin_de_lote({
            "temporada": _temporada(request),
            "lote_code": lote_code,
            "bin_code": bin_code,
            "campos": {
                "numero_cuartel":      cd.get("numero_cuartel") or "",
                "hora_recepcion":      _serialize_form_value(cd["hora_recepcion"]) if cd.get("hora_recepcion") else "",
                "kilos_bruto_ingreso": float(cd["kilos_bruto_ingreso"]) if cd.get("kilos_bruto_ingreso") else None,
                "kilos_neto_ingreso":  float(cd["kilos_neto_ingreso"]) if cd.get("kilos_neto_ingreso") else None,
                "a_o_r":               cd.get("a_o_r") or None,
                "observaciones":       cd.get("observaciones") or "",
            },
        })
        if result.ok:
            messages.success(request, f"Bin {bin_code} actualizado correctamente.")
        else:
            for err in result.errors:
                messages.error(request, err)
        return redirect("operaciones:recepcion")


# ---------------------------------------------------------------------------
# Desverdizado (camara mantencion + desverdizado)
# ---------------------------------------------------------------------------

def _lotes_pendientes_desverdizado(temporada: str):
    """
    Retorna lotes cerrados que requieren desverdizado y aun no tienen
    registro de desverdizado. Se muestran en el selector de la vista.
    """
    from django.conf import settings
    if getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip() == "dataverse":
        try:
            from infrastructure.repository_factory import get_repositories
            repos = get_repositories()
            lotes = repos.lotes.list_recent(limit=200)
            return [
                l for l in lotes
                if l.is_active and l.requiere_desverdizado
                and l.etapa_actual in ("Pesaje", "Mantencion")
            ]
        except Exception:
            return []
    from operaciones.models import Desverdizado
    lotes_con_desv = set(
        Desverdizado.objects.values_list("lote_id", flat=True)
    )
    qs = (
        Lote.objects
        .filter(temporada=temporada, is_active=True, estado=LotePlantaEstado.CERRADO)
        .exclude(id__in=lotes_con_desv)
        .order_by("-created_at")
    )
    return list(qs)


class DesverdizadoView(LoginRequiredMixin, RolRequiredMixin, TemplateView):
    roles_requeridos = ["Desverdizado"]
    template_name = "operaciones/desverdizado.html"
    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Desverdizado"
        ctx["form_mantencion"] = CamaraMantencionForm()
        ctx["form_desverdizado"] = DesverdizadoForm()
        temporada = (
            self.request.session.get("temporada_activa")
            or str(datetime.date.today().year)
        )
        lotes = _lotes_pendientes_desverdizado(temporada)
        ctx["lotes_pendientes"] = lotes
        from django.conf import settings
        if getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip() == "dataverse":
            from infrastructure.repository_factory import get_repositories
            ctx["lotes_data_json"] = _lotes_json_from_records(lotes, get_repositories())
        else:
            ctx["lotes_data_json"] = _lotes_data_json(temporada, lotes)
        return ctx

    def _lote_context(self, temporada: str, lote_code: str) -> dict:
        """Datos del lote para mostrar en el panel de contexto."""
        try:
            lote = Lote.objects.get(temporada=temporada, lote_code=lote_code)
            primer_bin = None
            bin_lotes = list(lote.bin_lotes.select_related("bin").order_by("created_at"))
            if bin_lotes:
                primer_bin = bin_lotes[0].bin
            _kb, _kn = _kilos_recientes_lote(lote)
            return {
                "lote_code": lote.lote_code,
                "cantidad_bins": lote.cantidad_bins,
                "kilos_bruto": _kb,
                "kilos_neto": _kn,
                "requiere_desverdizado": lote.requiere_desverdizado,
                "disponibilidad_camara": lote.disponibilidad_camara_desverdizado,
                "productor": primer_bin.codigo_productor if primer_bin else "",
                "variedad": primer_bin.variedad_fruta if primer_bin else "",
                "color": primer_bin.color if primer_bin else "",
                "fecha_cosecha": primer_bin.fecha_cosecha if primer_bin else None,
            }
        except Lote.DoesNotExist:
            return {}

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action", "mantencion")
        temporada = _temporada(request)
        lote_code = request.POST.get("lote_code", "").strip()

        if action == "mantencion":
            form = CamaraMantencionForm(request.POST)
            if form.is_valid():
                cd = form.cleaned_data
                payload = {
                    "temporada": temporada,
                    "lote_code": lote_code,
                    "operator_code": request.session.get("crf21_codigooperador", ""),
                    "source_system": "web",
                    "extra": {
                        "camara_numero": cd.get("camara_numero"),
                        "fecha_ingreso": _serialize_form_value(cd["fecha_ingreso"]) if cd.get("fecha_ingreso") else None,
                        "hora_ingreso": _serialize_form_value(cd["hora_ingreso"]) if cd.get("hora_ingreso") else None,
                        "temperatura_camara": float(cd["temperatura_camara"]) if cd.get("temperatura_camara") else None,
                        "humedad_relativa": float(cd["humedad_relativa"]) if cd.get("humedad_relativa") else None,
                        "observaciones": cd.get("observaciones"),
                    },
                }
                result = registrar_camara_mantencion(payload)
                _handle_result(request, result)
            else:
                messages.error(request, "Formulario de camara mantencion invalido.")

        elif action == "desverdizado":
            form = DesverdizadoForm(request.POST)
            if form.is_valid():
                cd = form.cleaned_data
                payload = {
                    "temporada": temporada,
                    "lote_code": lote_code,
                    "operator_code": request.session.get("crf21_codigooperador", ""),
                    "source_system": "web",
                    "extra": {
                        "numero_camara": cd.get("numero_camara"),
                        "fecha_ingreso": _serialize_form_value(cd["fecha_ingreso"]) if cd.get("fecha_ingreso") else None,
                        "hora_ingreso": _serialize_form_value(cd["hora_ingreso"]) if cd.get("hora_ingreso") else None,
                        "color_salida": cd.get("color") or "",
                        "horas_desverdizado": cd.get("horas_desverdizado"),
                    },
                }
                result = registrar_desverdizado(payload)
                _handle_result(request, result)
            else:
                messages.error(request, "Formulario de desverdizado invalido.")

        return redirect("operaciones:desverdizado")


# ---------------------------------------------------------------------------
# Ingreso a packing
# ---------------------------------------------------------------------------

def _lotes_pendientes_ingreso_packing(temporada: str):
    """
    Retorna lotes cerrados que aun no tienen registro de ingreso a packing.
    """
    from django.conf import settings
    if getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip() == "dataverse":
        try:
            from infrastructure.repository_factory import get_repositories
            repos = get_repositories()
            lotes = repos.lotes.list_recent(limit=200)
            _ANTES_INGRESO = ("Pesaje", "Mantencion", "Desverdizado")
            return [l for l in lotes if l.is_active and l.etapa_actual in _ANTES_INGRESO]
        except Exception:
            return []
    from operaciones.models import IngresoAPacking
    lotes_con_ingreso = set(
        IngresoAPacking.objects.values_list("lote_id", flat=True)
    )
    qs = (
        Lote.objects
        .filter(temporada=temporada, is_active=True, estado=LotePlantaEstado.CERRADO)
        .exclude(id__in=lotes_con_ingreso)
        .order_by("-created_at")
    )
    return list(qs)


def _lote_info(temporada: str, lote_code: str) -> dict:
    """
    Datos base de un lote para autocompletar formularios.
    Todos los valores son JSON-serializables (str, int, bool, None).
    """
    from django.conf import settings
    if getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip() == "dataverse":
        try:
            from infrastructure.repository_factory import get_repositories
            repos = get_repositories()
            lote = repos.lotes.find_by_code(temporada, lote_code)
            if not lote:
                return {}
            kilos_bruto = float(lote.kilos_bruto_conformacion) if lote.kilos_bruto_conformacion else None
            kilos_neto = float(lote.kilos_neto_conformacion) if lote.kilos_neto_conformacion else None
            via_desv = lote.etapa_actual in ("Desverdizado", "Mantencion") if lote.etapa_actual else False
            try:
                desv = repos.desverdizados.find_by_lote(lote.id)
                if desv:
                    if desv.kilos_bruto_salida is not None:
                        kilos_bruto = float(desv.kilos_bruto_salida)
                    if desv.kilos_neto_salida is not None:
                        kilos_neto = float(desv.kilos_neto_salida)
                    via_desv = True
            except Exception:
                pass
            try:
                ip = repos.ingresos_packing.find_by_lote(lote.id)
                if ip:
                    if ip.kilos_bruto_ingreso_packing is not None:
                        kilos_bruto = float(ip.kilos_bruto_ingreso_packing)
                    if ip.kilos_neto_ingreso_packing is not None:
                        kilos_neto = float(ip.kilos_neto_ingreso_packing)
            except Exception:
                pass
            return {
                "lote_code": lote.lote_code,
                "estado": lote.etapa_actual or lote.estado,
                "cantidad_bins": lote.cantidad_bins,
                "kilos_bruto": kilos_bruto,
                "kilos_neto": kilos_neto,
                "via_desverdizado": via_desv,
                "requiere_desverdizado": lote.requiere_desverdizado,
                "productor": getattr(lote, "codigo_productor", ""),
                "variedad": "",
                "color": "",
                "fecha_cosecha": str(lote.fecha_conformacion) if lote.fecha_conformacion else "",
                "tipo_cultivo": "",
            }
        except Exception:
            return {}
    try:
        lote = Lote.objects.get(temporada=temporada, lote_code=lote_code)
        bin_lotes = list(lote.bin_lotes.select_related("bin").order_by("created_at"))
        primer_bin = bin_lotes[0].bin if bin_lotes else None

        # Kilos heredables desde desverdizado si existe
        kilos_bruto = float(lote.kilos_bruto_conformacion) if lote.kilos_bruto_conformacion is not None else None
        kilos_neto  = float(lote.kilos_neto_conformacion)  if lote.kilos_neto_conformacion  is not None else None
        via_desv = False
        try:
            desv = lote.desverdizado
            if desv.kilos_bruto_salida is not None:
                kilos_bruto = float(desv.kilos_bruto_salida)
            if desv.kilos_neto_salida is not None:
                kilos_neto = float(desv.kilos_neto_salida)
            via_desv = True
        except Exception:
            pass
        try:
            lote.camara_mantencion
            via_desv = True
        except Exception:
            pass
        try:
            ip = lote.ingreso_packing
            if ip.kilos_bruto_ingreso_packing is not None:
                kilos_bruto = float(ip.kilos_bruto_ingreso_packing)
            if ip.kilos_neto_ingreso_packing is not None:
                kilos_neto = float(ip.kilos_neto_ingreso_packing)
        except Exception:
            pass

        # Fallback: suma de kilos de bins si no hay conformacion ni desverdizado
        if kilos_neto is None:
            total_bin_neto = sum(
                float(bl.bin.kilos_neto_ingreso)
                for bl in bin_lotes
                if bl.bin.kilos_neto_ingreso is not None
            )
            if total_bin_neto > 0:
                kilos_neto = total_bin_neto
        if kilos_bruto is None:
            total_bin_bruto = sum(
                float(bl.bin.kilos_bruto_ingreso)
                for bl in bin_lotes
                if bl.bin.kilos_bruto_ingreso is not None
            )
            if total_bin_bruto > 0:
                kilos_bruto = total_bin_bruto

        fecha_cosecha_str = ""
        if primer_bin and primer_bin.fecha_cosecha:
            fecha_cosecha_str = str(primer_bin.fecha_cosecha)

        # color: usar el primer bin que lo tenga
        color = next(
            (bl.bin.color for bl in bin_lotes if bl.bin.color),
            "",
        )

        return {
            "lote_code":           lote.lote_code,
            "estado":              lote.estado,
            "cantidad_bins":       lote.cantidad_bins,
            "kilos_bruto":         kilos_bruto,
            "kilos_neto":          kilos_neto,
            "via_desverdizado":    via_desv,
            "requiere_desverdizado": lote.requiere_desverdizado,
            "productor":    primer_bin.codigo_productor if primer_bin else "",
            "variedad":     primer_bin.variedad_fruta   if primer_bin else "",
            "color":        color,
            "fecha_cosecha": fecha_cosecha_str,
            "tipo_cultivo": primer_bin.tipo_cultivo     if primer_bin else "",
        }
    except Lote.DoesNotExist:
        return {}


def _lotes_data_json(temporada: str, lotes: list) -> str:
    """
    Serializa la lista de lotes como JSON para consumo del JS del template.
    Retorna una cadena JSON: {lote_code: {productor, variedad, ...}, ...}
    """
    data = {}
    for lote in lotes:
        info = _lote_info(temporada, lote.lote_code)
        if info:
            data[lote.lote_code] = info
    return json.dumps(data, ensure_ascii=False)


def _lotes_json_from_records(lotes, repos=None) -> str:
    """
    Serializa LoteRecord objects como JSON para autocomplete del template.
    Usado en modo Dataverse donde los lotes ya fueron cargados via repos.
    Si se pasa repos, obtiene el primer bin de cada lote en batch (2 queries)
    para poblar productor, variedad, color y fecha_cosecha.
    """
    import logging
    _log = logging.getLogger(__name__)

    # Batch: primer bin por lote en 2 queries (no N×2)
    primer_bin_por_lote: dict = {}
    if repos is not None and lotes:
        try:
            lote_ids = [l.id for l in lotes if l.id]
            _log.debug("_lotes_json_from_records: llamando first_bin_by_lotes con %d lote_ids", len(lote_ids))
            primer_bin_por_lote = repos.bins.first_bin_by_lotes(lote_ids)
            _log.debug("_lotes_json_from_records: primer_bin_por_lote tiene %d entradas", len(primer_bin_por_lote))
        except Exception as exc:
            _log.warning("_lotes_json_from_records: error al obtener bins en batch: %s", exc, exc_info=True)

    data = {}
    for lote in lotes:
        if lote.lote_code in data:
            continue
        via_desv = (
            lote.etapa_actual in ("Desverdizado", "Mantencion")
            if lote.etapa_actual else False
        )
        primer_bin = primer_bin_por_lote.get(lote.id)

        # Resolver kilos mas recientes: conformacion → desverdizado salida → ingreso packing
        kilos_bruto = float(lote.kilos_bruto_conformacion) if lote.kilos_bruto_conformacion else None
        kilos_neto = float(lote.kilos_neto_conformacion) if lote.kilos_neto_conformacion else None
        if repos is not None:
            try:
                desv = repos.desverdizados.find_by_lote(lote.id)
                if desv:
                    if desv.kilos_bruto_salida is not None:
                        kilos_bruto = float(desv.kilos_bruto_salida)
                    if desv.kilos_neto_salida is not None:
                        kilos_neto = float(desv.kilos_neto_salida)
                    via_desv = True
            except Exception:
                pass
            try:
                ip = repos.ingresos_packing.find_by_lote(lote.id)
                if ip:
                    if ip.kilos_bruto_ingreso_packing is not None:
                        kilos_bruto = float(ip.kilos_bruto_ingreso_packing)
                    if ip.kilos_neto_ingreso_packing is not None:
                        kilos_neto = float(ip.kilos_neto_ingreso_packing)
            except Exception:
                pass

        data[lote.lote_code] = {
            "lote_code": lote.lote_code,
            "estado": lote.etapa_actual or lote.estado,
            "cantidad_bins": lote.cantidad_bins,
            "kilos_bruto": kilos_bruto,
            "kilos_neto": kilos_neto,
            "via_desverdizado": via_desv,
            "requiere_desverdizado": lote.requiere_desverdizado,
            "disponibilidad_camara": lote.disponibilidad_camara_desverdizado,
            "productor": (primer_bin.codigo_productor if primer_bin else None) or getattr(lote, "codigo_productor", ""),
            "variedad": primer_bin.variedad_fruta if primer_bin else "",
            "color": primer_bin.color if primer_bin else "",
            "fecha_cosecha": str(primer_bin.fecha_cosecha) if primer_bin and primer_bin.fecha_cosecha else "",
            "tipo_cultivo": "",
        }
    return json.dumps(data, ensure_ascii=False)


def _build_pallet_context_map_from_records(pallets, repos=None) -> dict:
    """
    Enriquecer pallets Dataverse con el lote asociado y su primer bin.

    La relacion pallet->lote no se expande en list_recent(), por lo que aquí
    resolvemos pallet_lote y luego reutilizamos first_bin_by_lotes() para traer
    el contexto heredado visible en UI.
    """
    data = {
        p.pallet_code: {
            "pallet_code": p.pallet_code,
            "lote_code": "",
            "tipo_caja": p.tipo_caja or "",
            "peso_total": float(p.peso_total_kg) if p.peso_total_kg else None,
            "productor": "",
            "tipo_cultivo": "",
            "variedad": "",
            "color": "",
            "fecha_cosecha": "",
        }
        for p in pallets
    }
    if repos is None or not pallets:
        return data

    ordered_codes: list[str] = []
    deduped_pallets = []
    for pallet in pallets:
        if pallet.pallet_code in data and pallet.pallet_code in ordered_codes:
            continue
        ordered_codes.append(pallet.pallet_code)
        deduped_pallets.append(pallet)

    data = {p.pallet_code: data[p.pallet_code] for p in deduped_pallets}
    pallets = deduped_pallets

    pallet_to_lote: dict = {}
    lote_ids: list = []
    for pallet in pallets:
        try:
            pl = repos.pallet_lotes.find_by_pallet(pallet.id)
        except Exception:
            pl = None
        if pl and pl.lote_id:
            pallet_to_lote[pallet.id] = pl.lote_id
            if pl.lote_id not in lote_ids:
                lote_ids.append(pl.lote_id)

    lotes_by_id = {}
    for lote_id in lote_ids:
        try:
            lote = repos.lotes.find_by_id(lote_id)
        except Exception:
            lote = None
        if lote:
            lotes_by_id[lote_id] = lote

    try:
        primer_bin_por_lote = repos.bins.first_bin_by_lotes(lote_ids) if lote_ids else {}
    except Exception:
        primer_bin_por_lote = {}

    for pallet in pallets:
        lote_id = pallet_to_lote.get(pallet.id)
        lote = lotes_by_id.get(lote_id)
        primer_bin = primer_bin_por_lote.get(lote_id) if lote_id else None
        data[pallet.pallet_code].update({
            "lote_code": lote.lote_code if lote else "",
            "productor": (primer_bin.codigo_productor if primer_bin else None) or (getattr(lote, "codigo_productor", "") if lote else ""),
            "tipo_cultivo": primer_bin.tipo_cultivo if primer_bin else "",
            "variedad": primer_bin.variedad_fruta if primer_bin else "",
            "color": primer_bin.color if primer_bin else "",
            "fecha_cosecha": str(primer_bin.fecha_cosecha) if primer_bin and primer_bin.fecha_cosecha else "",
        })
    return data


def _pallets_json_from_records(pallets, repos=None) -> str:
    """Serializa PalletRecord objects como JSON para autocomplete del template."""
    return json.dumps(_build_pallet_context_map_from_records(pallets, repos), ensure_ascii=False)


def _campos_base_lote(lote: Lote) -> dict:
    """
    Deriva los campos base del lote (productor, tipo_cultivo, variedad, color,
    fecha_cosecha) desde el primer bin asociado. No depende de sesion.
    """
    bin_lotes = list(lote.bin_lotes.select_related("bin").order_by("created_at")[:1])
    primer_bin = bin_lotes[0].bin if bin_lotes else None
    return {
        "productor":     primer_bin.codigo_productor if primer_bin else "",
        "tipo_cultivo":  primer_bin.tipo_cultivo     if primer_bin else "",
        "variedad":      primer_bin.variedad_fruta   if primer_bin else "",
        "color":         primer_bin.color            if primer_bin else "",
        "fecha_cosecha": str(primer_bin.fecha_cosecha) if primer_bin and primer_bin.fecha_cosecha else "",
    }


def _lotes_para_paletizar(temporada: str) -> list:
    """
    Retorna lotes con ingreso a packing que aun no han sido vinculados a un pallet.
    Estos son los lotes disponibles para ser convertidos en pallet.
    """
    from django.conf import settings
    if getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip() == "dataverse":
        try:
            from infrastructure.repository_factory import get_repositories
            repos = get_repositories()
            lotes = repos.lotes.list_recent(limit=200)
            return [l for l in lotes if l.is_active and l.etapa_actual in ("Proceso", "Ingreso Packing")]
        except Exception:
            return []
    from operaciones.models import IngresoAPacking, PalletLote
    paletizados_ids = set(PalletLote.objects.values_list("lote_id", flat=True))
    return list(
        Lote.objects
        .filter(temporada=temporada, is_active=True, ingreso_packing__isnull=False)
        .exclude(id__in=paletizados_ids)
        .order_by("-created_at")[:50]
    )


def _pallets_pendientes_calidad(temporada: str) -> list:
    """Pallets activos que aun no tienen registro de CalidadPallet."""
    from django.conf import settings
    if getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip() == "dataverse":
        try:
            from infrastructure.repository_factory import get_repositories
            # En Dataverse retornamos los pallets recientes sin filtrar por calidad;
            # la logica de negocio en el use case previene registros duplicados.
            return get_repositories().pallets.list_recent(limit=30)
        except Exception:
            return []
    from operaciones.models import CalidadPallet
    pallets_con_calidad = set(CalidadPallet.objects.values_list("pallet_id", flat=True))
    return list(
        Pallet.objects
        .filter(temporada=temporada, is_active=True)
        .exclude(id__in=pallets_con_calidad)
        .order_by("-created_at")[:30]
    )


def _pallets_pendientes_camara_frio(temporada: str) -> list:
    """Pallets activos que aun no tienen registro de CamaraFrio."""
    from django.conf import settings
    if getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip() == "dataverse":
        try:
            from infrastructure.repository_factory import get_repositories
            return get_repositories().pallets.list_recent(limit=30)
        except Exception:
            return []
    from operaciones.models import CamaraFrio
    pallets_con_camara = set(CamaraFrio.objects.values_list("pallet_id", flat=True))
    return list(
        Pallet.objects
        .filter(temporada=temporada, is_active=True)
        .exclude(id__in=pallets_con_camara)
        .order_by("-created_at")[:30]
    )


def _pallet_info(temporada: str, pallet_code: str) -> dict:
    """Datos base de un pallet para autocompletar formularios."""
    from django.conf import settings
    if getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip() == "dataverse":
        try:
            from infrastructure.repository_factory import get_repositories
            repos = get_repositories()
            pallet = repos.pallets.find_by_code(temporada, pallet_code)
            if not pallet:
                return {}
            return _build_pallet_context_map_from_records([pallet], repos).get(pallet_code, {})
        except Exception:
            return {}
    try:
        pallet = Pallet.objects.get(temporada=temporada, pallet_code=pallet_code)
        lote_code = ""
        campos = {}
        pl = pallet.pallet_lotes.select_related("lote").first()
        if pl:
            lote_code = pl.lote.lote_code
            campos = _campos_base_lote(pl.lote)
        return {
            "pallet_code": pallet.pallet_code,
            "lote_code":   lote_code,
            "tipo_caja":   pallet.tipo_caja,
            "peso_total":  float(pallet.peso_total_kg) if pallet.peso_total_kg else None,
            **campos,
        }
    except Pallet.DoesNotExist:
        return {}


def _pallets_data_json(temporada: str, pallets: list) -> str:
    data = {}
    for p in pallets:
        info = _pallet_info(temporada, p.pallet_code)
        if info:
            data[p.pallet_code] = info
    return json.dumps(data, ensure_ascii=False)


class IngresoPackingView(LoginRequiredMixin, RolRequiredMixin, TemplateView):
    roles_requeridos = ["Ingreso Packing"]
    template_name = "operaciones/ingreso_packing.html"
    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Ingreso a Packing"
        ctx["form"] = IngresoPackingForm()
        temporada = (
            self.request.session.get("temporada_activa")
            or str(datetime.date.today().year)
        )
        lotes = _lotes_pendientes_ingreso_packing(temporada)
        ctx["lotes_pendientes"] = lotes
        from django.conf import settings
        if getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip() == "dataverse":
            from infrastructure.repository_factory import get_repositories
            ctx["lotes_data_json"] = _lotes_json_from_records(lotes, get_repositories())
        else:
            ctx["lotes_data_json"] = _lotes_data_json(temporada, lotes)
        ctx["lote_info"] = {}
        return ctx

    def post(self, request, *args, **kwargs):
        form = IngresoPackingForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Formulario invalido.")
            ctx = self.get_context_data()
            ctx["form"] = form
            return render(request, self.template_name, ctx)

        cd = form.cleaned_data
        lote_code = request.POST.get("lote_code", "").strip()
        temporada = _temporada(request)
        info = _lote_info(temporada, lote_code) if lote_code else {}

        payload = {
            "temporada": temporada,
            "lote_code": lote_code,
            "operator_code": request.session.get("crf21_codigooperador", ""),
            "source_system": "web",
            "via_desverdizado": cd.get("via_desverdizado") or info.get("via_desverdizado", False),
            "extra": {
                "fecha_ingreso": _serialize_form_value(cd["fecha_ingreso"]) if cd.get("fecha_ingreso") else None,
                "hora_ingreso": _serialize_form_value(cd["hora_ingreso"]) if cd.get("hora_ingreso") else None,
                "kilos_bruto_ingreso_packing": float(cd["kilos_bruto_ingreso_packing"]) if cd.get("kilos_bruto_ingreso_packing") else None,
                "kilos_neto_ingreso_packing": float(cd["kilos_neto_ingreso_packing"]) if cd.get("kilos_neto_ingreso_packing") else None,
                "observaciones": cd.get("observaciones"),
            },
        }
        result = registrar_ingreso_packing(payload)
        if result.ok:
            messages.success(request, result.message)
            return redirect("operaciones:ingreso_packing")
        for err in result.errors:
            messages.error(request, err)
        ctx = self.get_context_data()
        ctx["form"] = form
        ctx["lote_info"] = info
        return render(request, self.template_name, ctx)


# ---------------------------------------------------------------------------
# Proceso packing (registro de produccion)
# ---------------------------------------------------------------------------

class ProcesoView(LoginRequiredMixin, RolRequiredMixin, TemplateView):
    roles_requeridos = ["Proceso"]
    template_name = "operaciones/proceso.html"
    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Proceso Packing"
        ctx["form"] = RegistroPackingForm()
        temporada = (
            self.request.session.get("temporada_activa")
            or str(datetime.date.today().year)
        )
        from django.conf import settings
        backend = getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip()
        if backend == "dataverse":
            try:
                from infrastructure.repository_factory import get_repositories
                repos = get_repositories()
                todos = repos.lotes.list_recent(limit=200)
                _CON_INGRESO = ("Ingreso Packing", "Packing / Proceso", "Paletizado",
                                "Calidad Pallet", "Camara Frio", "Temperatura Salida")
                lotes = [l for l in todos if l.is_active and l.etapa_actual in _CON_INGRESO][:30]
            except Exception:
                lotes = []
            ctx["lotes_pendientes"] = lotes
            ctx["lotes_data_json"] = _lotes_json_from_records(lotes, repos)
        else:
            # Lotes que ya tienen ingreso packing (aptos para proceso)
            from operaciones.models import IngresoAPacking
            lotes_con_ingreso = set(
                IngresoAPacking.objects.values_list("lote_id", flat=True)
            )
            lotes = list(
                Lote.objects
                .filter(temporada=temporada, is_active=True, id__in=lotes_con_ingreso)
                .order_by("-created_at")[:30]
            )
            ctx["lotes_pendientes"] = lotes
            ctx["lotes_data_json"] = _lotes_data_json(temporada, lotes)
        return ctx

    def post(self, request, *args, **kwargs):
        form = RegistroPackingForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Formulario invalido.")
            ctx = self.get_context_data()
            ctx["form"] = form
            return render(request, self.template_name, ctx)

        cd = form.cleaned_data
        lote_code = request.POST.get("lote_code", "").strip()
        payload = {
            "temporada": _temporada(request),
            "lote_code": lote_code,
            "operator_code": request.session.get("crf21_codigooperador", ""),
            "source_system": "web",
            "extra": {
                "fecha": _serialize_form_value(cd["fecha"]) if cd.get("fecha") else None,
                "hora_inicio": _serialize_form_value(cd["hora_inicio"]) if cd.get("hora_inicio") else None,
                "linea_proceso": cd.get("linea_proceso"),
                "categoria_calidad": cd.get("categoria_calidad"),
                "calibre": cd.get("calibre"),
                "tipo_envase": cd.get("tipo_envase"),
                "cantidad_cajas_producidas": cd.get("cantidad_cajas_producidas"),
                "merma_seleccion_pct": float(cd["merma_seleccion_pct"]) if cd.get("merma_seleccion_pct") else None,
            },
        }
        result = registrar_registro_packing(payload)
        _handle_result(request, result)
        return redirect("operaciones:proceso")


# ---------------------------------------------------------------------------
# Control proceso packing (parámetros máquina volcado/tina)
# ---------------------------------------------------------------------------

class ControlProcesoView(LoginRequiredMixin, RolRequiredMixin, TemplateView):
    roles_requeridos = ["Control"]
    template_name = "operaciones/control_proceso.html"
    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Control Proceso Packing"
        ctx["form"] = ControlProcesoPackingForm()
        temporada = (
            self.request.session.get("temporada_activa")
            or str(datetime.date.today().year)
        )
        from django.conf import settings
        backend = getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip()
        if backend == "dataverse":
            try:
                from infrastructure.repository_factory import get_repositories
                repos = get_repositories()
                todos = repos.lotes.list_recent(limit=200)
                _CON_INGRESO = ("Ingreso Packing", "Packing / Proceso", "Paletizado",
                                "Calidad Pallet", "Camara Frio", "Temperatura Salida")
                lotes = [l for l in todos if l.is_active and l.etapa_actual in _CON_INGRESO][:30]
            except Exception:
                lotes = []
            ctx["lotes_pendientes"] = lotes
            ctx["lotes_data_json"] = _lotes_json_from_records(lotes, repos)
        else:
            from operaciones.models import IngresoAPacking
            lotes_con_ingreso = set(IngresoAPacking.objects.values_list("lote_id", flat=True))
            lotes = list(
                Lote.objects
                .filter(temporada=temporada, is_active=True, id__in=lotes_con_ingreso)
                .order_by("-created_at")[:30]
            )
            ctx["lotes_pendientes"] = lotes
            ctx["lotes_data_json"] = _lotes_data_json(temporada, lotes)
        return ctx

    def post(self, request, *args, **kwargs):
        form = ControlProcesoPackingForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Formulario invalido.")
            ctx = self.get_context_data()
            ctx["form"] = form
            return render(request, self.template_name, ctx)

        cd = form.cleaned_data
        lote_code = request.POST.get("lote_code", "").strip()
        payload = {
            "temporada": _temporada(request),
            "lote_code": lote_code,
            "operator_code": request.session.get("crf21_codigooperador", ""),
            "source_system": "web",
            "extra": {
                "fecha": _serialize_form_value(cd["fecha"]) if cd.get("fecha") else None,
                "hora": _serialize_form_value(cd["hora"]) if cd.get("hora") else None,
                "n_bins_procesados": cd.get("n_bins_procesados"),
                "temp_agua_tina": float(cd["temp_agua_tina"]) if cd.get("temp_agua_tina") else None,
                "ph_agua": float(cd["ph_agua"]) if cd.get("ph_agua") else None,
                "recambio_agua": cd.get("recambio_agua"),
                "rendimiento_lote_pct": float(cd["rendimiento_lote_pct"]) if cd.get("rendimiento_lote_pct") else None,
                "observaciones_generales": cd.get("observaciones_generales"),
            },
        }
        result = registrar_control_proceso_packing(payload)
        _handle_result(request, result)
        return redirect("operaciones:control_proceso")


# ---------------------------------------------------------------------------
# Control de Calidad — Índice
# ---------------------------------------------------------------------------

class ControlCalidadIndexView(LoginRequiredMixin, RolRequiredMixin, TemplateView):
    roles_requeridos = ["Control"]
    template_name = "operaciones/control_calidad_index.html"
    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Control de Calidad"
        return ctx


# ---------------------------------------------------------------------------
# Control de Calidad — Desverdizado (Planilla 1: Calibres, Planilla 2: Semillas)
# ---------------------------------------------------------------------------

class ControlCalidadDesverdizadoView(LoginRequiredMixin, RolRequiredMixin, TemplateView):
    roles_requeridos = ["Control"]
    template_name = "operaciones/control_calidad_desverdizado.html"
    login_url = reverse_lazy("usuarios:login")

    def _get_lotes(self, request):
        temporada = (
            request.session.get("temporada_activa")
            or str(datetime.date.today().year)
        )
        from django.conf import settings
        backend = getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip()
        if backend == "dataverse":
            try:
                from infrastructure.repository_factory import get_repositories
                repos = get_repositories()
                todos = repos.lotes.list_recent(limit=200)
                lotes = [l for l in todos if l.is_active][:50]
            except Exception:
                lotes = []
            return lotes, backend, temporada
        else:
            lotes = list(
                Lote.objects
                .filter(temporada=temporada, is_active=True)
                .order_by("-created_at")[:50]
            )
            return lotes, backend, temporada

    def _build_lotes_data_json(self, lotes, backend, temporada) -> str:
        """Construye JSON con datos del lote+bin para autocompletar los formularios."""
        data = {}
        if backend == "dataverse":
            try:
                from infrastructure.repository_factory import get_repositories
                repos = get_repositories()
                lote_ids = [l.id for l in lotes if l.id]
                primer_bin_por_lote = repos.bins.first_bin_by_lotes(lote_ids) if lote_ids else {}
            except Exception:
                primer_bin_por_lote = {}
            for lote in lotes:
                b = primer_bin_por_lote.get(lote.id)
                data[lote.lote_code] = {
                    "productor": (b.codigo_productor if b else None) or getattr(lote, "codigo_productor", ""),
                    "variedad":  b.variedad_fruta if b else "",
                    "color":     b.color if b else "",
                    "fecha_cosecha": str(b.fecha_cosecha) if b and b.fecha_cosecha else "",
                    "trazabilidad": lote.lote_code,
                    "cuartel": "",
                    "sector":  "",
                }
        else:
            from operaciones.models import BinLote
            # Batch: prefetch bins para todos los lotes de una vez
            lote_ids = [l.pk for l in lotes]
            bins_qs = (
                BinLote.objects
                .filter(lote_id__in=lote_ids)
                .select_related("bin", "lote")
                .order_by("lote_id", "created_at")
            )
            primer_bin_map = {}
            for bl in bins_qs:
                if bl.lote_id not in primer_bin_map:
                    primer_bin_map[bl.lote_id] = bl.bin
            for lote in lotes:
                b = primer_bin_map.get(lote.pk)
                data[lote.lote_code] = {
                    "productor": b.productor if b else "",
                    "variedad":  b.variedad_fruta if b else "",
                    "color":     b.color if b else "",
                    "fecha_cosecha": str(b.fecha_cosecha) if b and b.fecha_cosecha else "",
                    "trazabilidad": lote.lote_code,
                    "cuartel": (b.nombre_cuartel or b.numero_cuartel) if b else "",
                    "sector":  b.sector if b else "",
                }
        return json.dumps(data, ensure_ascii=False)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Control Calidad Desverdizado"
        lotes, backend, temporada = self._get_lotes(self.request)
        ctx["lotes_pendientes"] = lotes
        ctx["lotes_data_json"] = self._build_lotes_data_json(lotes, backend, temporada)
        ctx["supervisor_default"] = self.request.session.get("crf21_codigooperador", "")
        ctx["form_calibres"] = PlanillaDesverdizadoCalibreForm()
        ctx["form_semillas"] = PlanillaDesverdizadoSemillasForm()
        ctx["calibres_nombres"] = ["1xx", "1x", "1", "2", "3", "4", "5", "Precalibre"]
        ctx["grupos_calibre"] = [1, 2, 3]
        ctx["grupos_semillas"] = [1, 2, 3, 4, 5]
        ctx["frutas_range"] = list(range(1, 11))
        ctx["defectos_nombres"] = [
            ("oleocelosis", "Oleocelosis"),
            ("heridas_abiertas", "Heridas abiertas"),
            ("rugoso", "Rugoso"),
            ("deforme", "Deforme"),
            ("golpe_sol", "Golpe sol"),
            ("verdes", "Verdes"),
            ("pre_calibre", "Pre-calibre"),
            ("palo_largo", "Palo largo"),
        ]
        return ctx

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action", "calibres")
        lote_code = request.POST.get("lote_code", "").strip()

        if action == "calibres":
            form = PlanillaDesverdizadoCalibreForm(request.POST)
            if not form.is_valid():
                messages.error(request, "Formulario de calibres inválido.")
                ctx = self.get_context_data()
                ctx["form_calibres"] = form
                ctx["tab_activo"] = "calibres"
                return render(request, self.template_name, ctx)
            cd = form.cleaned_data
            # Parse calibres grupos from dynamic POST fields (3 groups)
            calibres_grupos = []
            for g in range(1, 4):
                calibres = {}
                for cal in ["1xx", "1x", "1", "2", "3", "4", "5", "Precalibre"]:
                    key = f"grupo_{g}_cal_{cal}"
                    val = request.POST.get(key, "")
                    try:
                        calibres[cal] = int(val) if val else None
                    except ValueError:
                        calibres[cal] = None
                calibres_grupos.append({
                    "color": request.POST.get(f"grupo_{g}_color", ""),
                    "calibres": calibres,
                    "observacion": request.POST.get(f"grupo_{g}_obs", ""),
                })
            payload = {
                "lote_code": lote_code,
                "operator_code": request.session.get("crf21_codigooperador", ""),
                "source_system": "web",
                "extra": {
                    **{k: _serialize_form_value(v)
                       for k, v in cd.items()},
                    "calibres_grupos": calibres_grupos,
                },
            }
            result = registrar_planilla_desv_calibre(payload)
            _handle_result(request, result)
            return redirect("operaciones:control_desverdizado")

        elif action == "semillas":
            form = PlanillaDesverdizadoSemillasForm(request.POST)
            if not form.is_valid():
                messages.error(request, "Formulario de semillas inválido.")
                ctx = self.get_context_data()
                ctx["form_semillas"] = form
                ctx["tab_activo"] = "semillas"
                return render(request, self.template_name, ctx)
            cd = form.cleaned_data
            # Parse 50 frutas: g{G}_f{N}_semillas (G=1-5, N=1-10)
            frutas_data = []
            n = 1
            for g in range(1, 6):
                for f in range(1, 11):
                    val = request.POST.get(f"g{g}_f{f}_semillas", "")
                    try:
                        semillas = int(val) if val else 0
                    except ValueError:
                        semillas = 0
                    frutas_data.append({"n_fruto": n, "n_semillas": semillas})
                    n += 1
            payload = {
                "lote_code": lote_code,
                "operator_code": request.session.get("crf21_codigooperador", ""),
                "source_system": "web",
                "extra": {
                    **{k: _serialize_form_value(v)
                       for k, v in cd.items()},
                    "frutas_data": frutas_data,
                },
            }
            result = registrar_planilla_desv_semillas(payload)
            _handle_result(request, result)
            return redirect("operaciones:control_desverdizado")

        messages.error(request, "Acción desconocida.")
        return redirect("operaciones:control_desverdizado")


# ---------------------------------------------------------------------------
# Control de Calidad — Packing Cítricos
# ---------------------------------------------------------------------------

class ControlCalidadPackingView(LoginRequiredMixin, RolRequiredMixin, TemplateView):
    roles_requeridos = ["Control"]
    template_name = "operaciones/control_calidad_packing.html"
    login_url = reverse_lazy("usuarios:login")

    def _get_pallets(self, request):
        from django.conf import settings
        backend = getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip()
        if backend == "dataverse":
            try:
                from infrastructure.repository_factory import get_repositories
                repos = get_repositories()
                pallets = repos.pallets.list_recent(limit=50)
            except Exception:
                pallets = []
            return pallets
        else:
            return list(Pallet.objects.order_by("-created_at")[:50])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Control Calidad Packing Cítricos"
        ctx["pallets"] = self._get_pallets(self.request)
        ctx["form"] = PlanillaCalidadPackingForm()
        return ctx

    def post(self, request, *args, **kwargs):
        form = PlanillaCalidadPackingForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Formulario inválido.")
            ctx = self.get_context_data()
            ctx["form"] = form
            return render(request, self.template_name, ctx)
        cd = form.cleaned_data
        pallet_id = request.POST.get("pallet_id", "").strip() or None
        payload = {
            "pallet_id": pallet_id,
            "operator_code": request.session.get("crf21_codigooperador", ""),
            "source_system": "web",
            "extra": {
                k: _serialize_form_value(v)
                for k, v in cd.items()
            },
        }
        result = registrar_planilla_calidad_packing(payload)
        _handle_result(request, result)
        return redirect("operaciones:control_packing")


# ---------------------------------------------------------------------------
# Control de Calidad — Cámaras
# ---------------------------------------------------------------------------

class ControlCalidadCamarasView(LoginRequiredMixin, RolRequiredMixin, TemplateView):
    roles_requeridos = ["Control"]
    template_name = "operaciones/control_calidad_camaras.html"
    login_url = reverse_lazy("usuarios:login")

    def _get_pallets(self, request):
        from django.conf import settings
        backend = getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip()
        if backend == "dataverse":
            try:
                from infrastructure.repository_factory import get_repositories
                repos = get_repositories()
                pallets = repos.pallets.list_recent(limit=50)
            except Exception:
                pallets = []
            return pallets
        else:
            return list(Pallet.objects.order_by("-created_at")[:50])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Control Calidad Cámaras"
        ctx["pallets"] = self._get_pallets(self.request)
        ctx["form"] = PlanillaCalidadCamaraForm()
        return ctx

    def post(self, request, *args, **kwargs):
        form = PlanillaCalidadCamaraForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Formulario inválido.")
            ctx = self.get_context_data()
            ctx["form"] = form
            return render(request, self.template_name, ctx)
        cd = form.cleaned_data
        pallet_id = request.POST.get("pallet_id", "").strip() or None
        # Parse dynamic hourly measurement rows: med_{i}_{campo}
        mediciones = []
        i = 0
        while True:
            hora = request.POST.get(f"med_{i}_hora", "")
            if not hora:
                break
            fila = {"hora": hora}
            for campo in ["ambiente", "pulpa_ext_entrada", "pulpa_ext_medio",
                          "pulpa_ext_salida", "pulpa_int_entrada", "pulpa_int_media",
                          "pulpa_int_salida"]:
                fila[campo] = request.POST.get(f"med_{i}_{campo}", "") or None
            mediciones.append(fila)
            i += 1
        payload = {
            "pallet_id": pallet_id,
            "operator_code": request.session.get("crf21_codigooperador", ""),
            "source_system": "web",
            "extra": {
                **{k: _serialize_form_value(v)
                   for k, v in cd.items()},
                "mediciones": mediciones,
            },
        }
        result = registrar_planilla_calidad_camara(payload)
        _handle_result(request, result)
        return redirect("operaciones:control_camaras")


# ---------------------------------------------------------------------------
# Paletizado (calidad + cerrar pallet)
# ---------------------------------------------------------------------------

class PaletizadoView(LoginRequiredMixin, RolRequiredMixin, TemplateView):
    roles_requeridos = ["Paletizado"]
    template_name = "operaciones/paletizado.html"
    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Paletizado"
        ctx["form_calidad"] = CalidadPalletForm()
        ctx["form_muestra"] = CalidadPalletMuestraForm()
        temporada = (
            self.request.session.get("temporada_activa")
            or str(datetime.date.today().year)
        )
        # Lotes listos para convertirse en pallet (accion primaria)
        lotes = _lotes_para_paletizar(temporada)
        ctx["lotes_para_paletizar"] = lotes
        # Pallets ya cerrados pendientes de control de calidad (accion secundaria)
        pallets = _pallets_pendientes_calidad(temporada)
        ctx["pallets_pendientes"] = pallets
        from django.conf import settings
        backend = getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip()
        if backend == "dataverse":
            from infrastructure.repository_factory import get_repositories
            repos = get_repositories()
            ctx["lotes_data_json"] = _lotes_json_from_records(lotes, repos)
            ctx["pallets_data_json"] = _pallets_json_from_records(pallets, repos)
        else:
            ctx["lotes_data_json"] = _lotes_data_json(temporada, lotes)
            ctx["pallets_data_json"] = _pallets_data_json(temporada, pallets)
        return ctx

    def _save_muestras(self, request, pallet, operator_code):
        """
        Guarda muestras individuales de calidad enviadas desde el template.
        Cada muestra llega como muestra_N_<campo> en el POST.
        Persiste via repositorio (SQLite o Dataverse segun PERSISTENCE_BACKEND).
        Retorna el numero de muestras guardadas exitosamente.
        """
        import logging
        logger = logging.getLogger(__name__)
        saved = 0
        for i in range(1, 4):  # maximo 3 muestras por sesion
            prefix = f"muestra_{i}_"
            temp = request.POST.get(f"{prefix}temperatura_fruta", "").strip()
            peso = request.POST.get(f"{prefix}peso_caja_muestra", "").strip()
            n_frutos = request.POST.get(f"{prefix}n_frutos", "").strip()
            aprobado_raw = request.POST.get(f"{prefix}aprobado", "")
            obs = request.POST.get(f"{prefix}observaciones", "").strip()

            # Solo guardar si al menos un campo de medicion tiene dato
            if not any([temp, peso, n_frutos]):
                continue

            aprobado = None
            if aprobado_raw == "true":
                aprobado = True
            elif aprobado_raw == "false":
                aprobado = False

            result = guardar_muestra_calidad_pallet({
                "pallet_id": pallet.id,
                "operator_code": operator_code,
                "source_system": "web",
                "extra": {
                    "numero_muestra":    i,
                    "temperatura_fruta": float(temp) if temp else None,
                    "peso_caja_muestra": float(peso) if peso else None,
                    "n_frutos":          int(n_frutos) if n_frutos else None,
                    "aprobado":          aprobado,
                    "observaciones":     obs,
                    "rol": request.session.get("crf21_rol", ""),
                },
            })
            if result.ok:
                saved += 1
            else:
                logger.warning(
                    "Muestra %s no guardada para pallet %s: [%s] %s",
                    i, pallet.id, result.code, result.message,
                )
        return saved

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action", "calidad")
        temporada = _temporada(request)
        pallet_code = request.POST.get("pallet_code", "").strip()

        if action == "calidad":
            form = CalidadPalletForm(request.POST)
            if form.is_valid():
                cd = form.cleaned_data
                payload = {
                    "temporada": temporada,
                    "pallet_code": pallet_code,
                    "operator_code": request.session.get("crf21_codigooperador", ""),
                    "source_system": "web",
                    "extra": {
                        "fecha": _serialize_form_value(cd["fecha"]) if cd.get("fecha") else None,
                        "hora": _serialize_form_value(cd["hora"]) if cd.get("hora") else None,
                        "temperatura_fruta": float(cd["temperatura_fruta"]) if cd.get("temperatura_fruta") else None,
                        "peso_caja_muestra": float(cd["peso_caja_muestra"]) if cd.get("peso_caja_muestra") else None,
                        "estado_visual_fruta": cd.get("estado_visual_fruta"),
                        "presencia_defectos": cd.get("presencia_defectos"),
                        "aprobado": cd.get("aprobado"),
                        "observaciones": cd.get("observaciones"),
                    },
                }
                result = registrar_calidad_pallet(payload)
                _handle_result(request, result)

                # Guardar muestras individuales
                if result.ok and pallet_code:
                    try:
                        from infrastructure.repository_factory import get_repositories
                        pallet = get_repositories().pallets.find_by_code(temporada, pallet_code)
                        if pallet:
                            n = self._save_muestras(
                                request, pallet, request.session.get("crf21_codigooperador", ""),
                            )
                            if n:
                                messages.info(
                                    request, f"{n} muestra(s) de calidad registrada(s).",
                                )
                    except Exception:
                        pass
            else:
                messages.error(request, "Formulario de calidad invalido.")

        elif action == "cerrar":
            lote_code = request.POST.get("lote_code", "").strip()
            payload = {
                "temporada": temporada,
                "lote_codes": [lote_code] if lote_code else [],
                "pallet_code": pallet_code,
                "operator_code": request.session.get("crf21_codigooperador", ""),
                "source_system": "web",
            }
            result = cerrar_pallet(payload)
            _handle_result(request, result)

        return redirect("operaciones:paletizado")


# ---------------------------------------------------------------------------
# Camaras (frio + medicion temperatura)
# ---------------------------------------------------------------------------

class CamarasView(LoginRequiredMixin, RolRequiredMixin, TemplateView):
    roles_requeridos = ["Camaras"]
    template_name = "operaciones/camaras.html"
    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Camaras de Frio"
        ctx["form_camara"] = CamaraFrioForm()
        ctx["form_medicion"] = MedicionTemperaturaForm()
        temporada = (
            self.request.session.get("temporada_activa")
            or str(datetime.date.today().year)
        )
        pallets = _pallets_pendientes_camara_frio(temporada)
        ctx["pallets_pendientes"] = pallets
        from django.conf import settings
        if getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip() == "dataverse":
            from infrastructure.repository_factory import get_repositories
            ctx["pallets_data_json"] = _pallets_json_from_records(pallets, get_repositories())
        else:
            ctx["pallets_data_json"] = _pallets_data_json(temporada, pallets)
        return ctx

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action", "camara")
        temporada = _temporada(request)
        pallet_code = request.POST.get("pallet_code", "").strip()

        if action == "camara":
            form = CamaraFrioForm(request.POST)
            if form.is_valid():
                cd = form.cleaned_data
                payload = {
                    "temporada": temporada,
                    "pallet_code": pallet_code,
                    "operator_code": request.session.get("crf21_codigooperador", ""),
                    "source_system": "web",
                    "extra": {
                        "camara_numero": cd.get("camara_numero"),
                        "temperatura_camara": float(cd["temperatura_camara"]) if cd.get("temperatura_camara") else None,
                        "humedad_relativa": float(cd["humedad_relativa"]) if cd.get("humedad_relativa") else None,
                        "fecha_ingreso": _serialize_form_value(cd["fecha_ingreso"]) if cd.get("fecha_ingreso") else None,
                        "hora_ingreso": _serialize_form_value(cd["hora_ingreso"]) if cd.get("hora_ingreso") else None,
                        "destino_despacho": cd.get("destino_despacho"),
                    },
                }
                result = registrar_camara_frio(payload)
                _handle_result(request, result)
            else:
                messages.error(request, "Formulario de camara frio invalido.")

        elif action == "medicion":
            form = MedicionTemperaturaForm(request.POST)
            if form.is_valid():
                cd = form.cleaned_data
                payload = {
                    "temporada": temporada,
                    "pallet_code": pallet_code,
                    "operator_code": request.session.get("crf21_codigooperador", ""),
                    "source_system": "web",
                    "extra": {
                        "fecha": _serialize_form_value(cd["fecha"]) if cd.get("fecha") else None,
                        "hora": _serialize_form_value(cd["hora"]) if cd.get("hora") else None,
                        "temperatura_pallet": float(cd["temperatura_pallet"]) if cd.get("temperatura_pallet") else None,
                        "punto_medicion": cd.get("punto_medicion"),
                        "dentro_rango": cd.get("dentro_rango"),
                        "observaciones": cd.get("observaciones"),
                    },
                }
                result = registrar_medicion_temperatura(payload)
                _handle_result(request, result)
            else:
                messages.error(request, "Formulario de medicion invalido.")

        return redirect("operaciones:camaras")


# ---------------------------------------------------------------------------
# Consulta jefatura — helpers internos
# ---------------------------------------------------------------------------

CONSULTA_TAB_LOTES = "lotes"
CONSULTA_TAB_PALLETS = "pallets"
CONSULTA_TAB_DEFAULT = CONSULTA_TAB_LOTES
CONSULTA_ESTADO_EN_CAMARA_FRIO = "en_camara_frio"

CONSULTA_COLUMNAS_LOTES = [
    ("Temporada", "temporada"),
    ("Lote (code)", "lote_code"),
    ("Estado", "estado_display"),
    ("Etapa actual", "etapa"),
    ("Productor", "productor"),
    ("Tipo cultivo", "tipo_cultivo"),
    ("Variedad", "variedad"),
    ("Bins", "cantidad_bins"),
    ("Kg neto", "kilos_neto"),
    ("Fecha", "fecha"),
]

CONSULTA_COLUMNAS_PALLETS = [
    ("Temporada", "temporada"),
    ("Pallet (code)", "pallet_code"),
    ("Lote relacionado", "lote_code"),
    ("Tipo caja", "tipo_caja"),
    ("Peso total (kg)", "peso_total"),
    ("Productor", "productor"),
    ("Variedad", "variedad"),
]

CONSULTA_CACHE_VERSION = 1
_CONSULTA_CACHE_REFRESH_LOCK = threading.Lock()
_CONSULTA_CACHE_REFRESH_IN_PROGRESS: set[str] = set()
_CONSULTA_CACHE_TYPE_KEY = "__consulta_cache_type__"
_CONSULTA_CACHE_TYPE_DATE = "date"
_CONSULTA_CACHE_TYPE_DATETIME = "datetime"


def _consulta_now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _consulta_cache_file_path() -> Path:
    from django.conf import settings
    raw_path = getattr(
        settings,
        "CONSULTA_DATAVERSE_CACHE_FILE",
        str(Path(settings.BASE_DIR) / ".cache" / "consulta_dataverse.json"),
    )
    return Path(raw_path)


def _consulta_cache_ttl_seconds() -> int:
    from django.conf import settings
    ttl = getattr(settings, "CONSULTA_DATAVERSE_CACHE_TTL_SECONDS", 3600)
    try:
        ttl_int = int(ttl)
    except (TypeError, ValueError):
        ttl_int = 3600
    return max(60, ttl_int)


def _consulta_cache_empty_payload() -> dict:
    return {
        "version": CONSULTA_CACHE_VERSION,
        "backend": "dataverse",
        "updated_at": None,
        "temporadas": {},
    }


def _consulta_cache_json_default(value):
    if isinstance(value, datetime.datetime):
        return {
            _CONSULTA_CACHE_TYPE_KEY: _CONSULTA_CACHE_TYPE_DATETIME,
            "value": value.isoformat(),
        }
    if isinstance(value, datetime.date):
        return {
            _CONSULTA_CACHE_TYPE_KEY: _CONSULTA_CACHE_TYPE_DATE,
            "value": value.isoformat(),
        }
    raise TypeError(f"Tipo no serializable para cache: {type(value)!r}")


def _consulta_cache_json_hook(payload: dict):
    marker = payload.get(_CONSULTA_CACHE_TYPE_KEY)
    if not marker:
        return payload
    raw = payload.get("value")
    try:
        if marker == _CONSULTA_CACHE_TYPE_DATETIME:
            return datetime.datetime.fromisoformat(raw)
        if marker == _CONSULTA_CACHE_TYPE_DATE:
            return datetime.date.fromisoformat(raw)
    except Exception:
        return raw
    return payload


def _consulta_cache_read() -> dict:
    cache_path = _consulta_cache_file_path()
    if not cache_path.exists():
        return _consulta_cache_empty_payload()
    try:
        with cache_path.open("r", encoding="utf-8") as handler:
            data = json.load(handler, object_hook=_consulta_cache_json_hook)
        if not isinstance(data, dict):
            return _consulta_cache_empty_payload()
        data.setdefault("version", CONSULTA_CACHE_VERSION)
        data.setdefault("backend", "dataverse")
        data.setdefault("temporadas", {})
        return data
    except Exception as exc:
        logging.getLogger(__name__).warning("No se pudo leer cache consulta: %s", exc)
        return _consulta_cache_empty_payload()


def _consulta_cache_write(payload: dict) -> bool:
    cache_path = _consulta_cache_file_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(
            prefix=f"{cache_path.name}.",
            suffix=".tmp",
            dir=str(cache_path.parent),
        )
        with os.fdopen(fd, "w", encoding="utf-8") as handler:
            json.dump(
                payload,
                handler,
                ensure_ascii=False,
                default=_consulta_cache_json_default,
            )
        os.replace(tmp_path, cache_path)
        return True
    except Exception as exc:
        logging.getLogger(__name__).warning("No se pudo escribir cache consulta: %s", exc)
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return False


def _consulta_cache_updated_at(payload: dict) -> datetime.datetime | None:
    raw = payload.get("updated_at")
    if isinstance(raw, datetime.datetime):
        if raw.tzinfo is None:
            return raw.replace(tzinfo=datetime.timezone.utc)
        return raw.astimezone(datetime.timezone.utc)
    if isinstance(raw, str):
        try:
            parsed = datetime.datetime.fromisoformat(raw)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=datetime.timezone.utc)
            return parsed.astimezone(datetime.timezone.utc)
        except Exception:
            return None
    return None


def _consulta_cache_temporada(payload: dict, temporada: str) -> dict | None:
    temporadas = payload.get("temporadas") or {}
    data = temporadas.get(str(temporada))
    if not isinstance(data, dict):
        return None
    lotes = data.get("lotes")
    pallets = data.get("pallets")
    if not isinstance(lotes, list) or not isinstance(pallets, list):
        return None
    return data


def _consulta_cache_is_fresh(payload: dict) -> bool:
    updated_at = _consulta_cache_updated_at(payload)
    if not updated_at:
        return False
    age = (_consulta_now_utc() - updated_at).total_seconds()
    return age <= _consulta_cache_ttl_seconds()


def _consulta_dataverse_dataset_live(temporada: str) -> dict:
    lotes = _lotes_enriquecidos_dataverse("", "")
    pallets = _pallets_enriquecidos_dataverse(temporada, "", "")
    lotes_rows = [{k: v for k, v in item.items() if k != "lote"} for item in lotes]
    pallets_rows = [{k: v for k, v in item.items() if k != "pallet"} for item in pallets]
    return {"lotes": lotes_rows, "pallets": pallets_rows}


def _consulta_dataverse_cache_refresh_now(temporada: str) -> tuple[dict, datetime.datetime, bool]:
    data = _consulta_dataverse_dataset_live(temporada)
    payload = _consulta_cache_read()
    updated_at = _consulta_now_utc()
    payload["version"] = CONSULTA_CACHE_VERSION
    payload["backend"] = "dataverse"
    payload["updated_at"] = updated_at
    payload.setdefault("temporadas", {})
    payload["temporadas"][str(temporada)] = data
    wrote = _consulta_cache_write(payload)
    return data, updated_at, wrote


def _consulta_dataverse_cache_refresh_background(temporada: str) -> bool:
    key = str(temporada)
    with _CONSULTA_CACHE_REFRESH_LOCK:
        if key in _CONSULTA_CACHE_REFRESH_IN_PROGRESS:
            return False
        _CONSULTA_CACHE_REFRESH_IN_PROGRESS.add(key)

    def _worker():
        try:
            _consulta_dataverse_cache_refresh_now(temporada)
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "Fallo refresco en segundo plano de consulta (temporada=%s): %s",
                temporada,
                exc,
            )
        finally:
            with _CONSULTA_CACHE_REFRESH_LOCK:
                _CONSULTA_CACHE_REFRESH_IN_PROGRESS.discard(key)

    threading.Thread(target=_worker, daemon=True).start()
    return True


def _filtrar_lotes_consulta(rows: list, filtro_productor: str, filtro_estado: str) -> list:
    resultado = []
    filtro_productor_lc = (filtro_productor or "").lower()
    for raw in rows or []:
        item = dict(raw)
        estado = (item.get("estado") or "").strip()
        etapa = (item.get("etapa") or "").strip()
        productor = (item.get("productor") or "").strip()
        if filtro_productor_lc and filtro_productor_lc not in productor.lower():
            continue
        if not _coincide_filtro_estado_lote(filtro_estado, estado=estado, etapa=etapa):
            continue
        resultado.append(item)
    return resultado


def _filtrar_pallets_consulta(rows: list, filtro_productor: str, filtro_estado: str) -> list:
    resultado = []
    filtro_productor_lc = (filtro_productor or "").lower()
    for raw in rows or []:
        item = dict(raw)
        productor = (item.get("productor") or "").strip()
        if filtro_productor_lc and filtro_productor_lc not in productor.lower():
            continue
        if not _coincide_filtro_estado_pallet(
            filtro_estado,
            en_camara_frio=bool(item.get("en_camara_frio")),
            lote_estado=(item.get("estado") or "").strip(),
            lote_etapa=(item.get("etapa") or "").strip(),
        ):
            continue
        resultado.append(item)
    return resultado


def _consulta_dataset(
    temporada: str,
    filtro_productor: str,
    filtro_estado: str,
    *,
    force_refresh: bool = False,
) -> tuple[list, list, dict]:
    from django.conf import settings
    backend = getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip()
    if backend != "dataverse":
        return (
            _lotes_enriquecidos_qs(temporada, filtro_productor, filtro_estado),
            _pallets_enriquecidos_qs(temporada, filtro_productor, filtro_estado),
            {
                "is_dataverse_backend": False,
                "cache_source": "none",
                "cache_last_updated": None,
                "cache_is_stale": False,
                "background_refresh_started": False,
                "refreshed_now": False,
                "warning_message": "",
            },
        )

    cache_payload = _consulta_cache_read()
    cache_rows = _consulta_cache_temporada(cache_payload, temporada)
    cache_updated_at = _consulta_cache_updated_at(cache_payload)
    cache_is_fresh = _consulta_cache_is_fresh(cache_payload)

    meta = {
        "is_dataverse_backend": True,
        "cache_source": "cache",
        "cache_last_updated": cache_updated_at,
        "cache_is_stale": bool(cache_rows) and (not cache_is_fresh),
        "background_refresh_started": False,
        "refreshed_now": False,
        "warning_message": "",
    }

    if force_refresh:
        try:
            live_data, updated_at, _ = _consulta_dataverse_cache_refresh_now(temporada)
            meta["cache_source"] = "live"
            meta["cache_last_updated"] = updated_at
            meta["cache_is_stale"] = False
            meta["refreshed_now"] = True
            lotes = _filtrar_lotes_consulta(live_data.get("lotes", []), filtro_productor, filtro_estado)
            pallets = _filtrar_pallets_consulta(live_data.get("pallets", []), filtro_productor, filtro_estado)
            return lotes, pallets, meta
        except Exception as exc:
            logging.getLogger(__name__).warning("Refresco manual consulta fallo: %s", exc)
            if cache_rows:
                meta["warning_message"] = (
                    "No fue posible sincronizar Dataverse. Se muestra cache disponible."
                )
                lotes = _filtrar_lotes_consulta(cache_rows.get("lotes", []), filtro_productor, filtro_estado)
                pallets = _filtrar_pallets_consulta(cache_rows.get("pallets", []), filtro_productor, filtro_estado)
                return lotes, pallets, meta
            meta["warning_message"] = (
                "No fue posible sincronizar Dataverse y no existe cache disponible."
            )
            return [], [], meta

    if cache_rows and cache_is_fresh:
        lotes = _filtrar_lotes_consulta(cache_rows.get("lotes", []), filtro_productor, filtro_estado)
        pallets = _filtrar_pallets_consulta(cache_rows.get("pallets", []), filtro_productor, filtro_estado)
        return lotes, pallets, meta

    if cache_rows and not cache_is_fresh:
        meta["background_refresh_started"] = _consulta_dataverse_cache_refresh_background(temporada)
        lotes = _filtrar_lotes_consulta(cache_rows.get("lotes", []), filtro_productor, filtro_estado)
        pallets = _filtrar_pallets_consulta(cache_rows.get("pallets", []), filtro_productor, filtro_estado)
        return lotes, pallets, meta

    try:
        live_data, updated_at, _ = _consulta_dataverse_cache_refresh_now(temporada)
        meta["cache_source"] = "live"
        meta["cache_last_updated"] = updated_at
        meta["cache_is_stale"] = False
        lotes = _filtrar_lotes_consulta(live_data.get("lotes", []), filtro_productor, filtro_estado)
        pallets = _filtrar_pallets_consulta(live_data.get("pallets", []), filtro_productor, filtro_estado)
        return lotes, pallets, meta
    except Exception as exc:
        logging.getLogger(__name__).warning("Carga inicial Dataverse para consulta fallo: %s", exc)
        meta["warning_message"] = (
            "No fue posible consultar Dataverse y no hay cache disponible."
        )
        return [], [], meta


def _normalizar_tab_consulta(tab_raw: str) -> str:
    tab = (tab_raw or "").strip().lower()
    if tab in {CONSULTA_TAB_LOTES, CONSULTA_TAB_PALLETS}:
        return tab
    return CONSULTA_TAB_DEFAULT


def _consulta_estado_choices() -> list[tuple[str, str]]:
    choices = list(LotePlantaEstado.choices)
    choices.append((CONSULTA_ESTADO_EN_CAMARA_FRIO, "En Camara de Frio"))
    return choices


def _estado_display_consulta(estado: str, *, fallback: str = "") -> str:
    if estado == CONSULTA_ESTADO_EN_CAMARA_FRIO:
        return "En Camara de Frio"
    if not estado:
        return fallback or "—"
    return dict(LotePlantaEstado.choices).get(estado, fallback or estado)


def _coincide_filtro_estado_lote(filtro_estado: str, *, estado: str, etapa: str) -> bool:
    if not filtro_estado:
        return True
    if filtro_estado == CONSULTA_ESTADO_EN_CAMARA_FRIO:
        return etapa == "Camara Frio"
    if filtro_estado == LotePlantaEstado.ABIERTO:
        return etapa == "Recepcion" or estado == LotePlantaEstado.ABIERTO
    if filtro_estado == LotePlantaEstado.CERRADO:
        return etapa != "Recepcion" or estado == LotePlantaEstado.CERRADO
    return estado == filtro_estado


def _coincide_filtro_estado_pallet(
    filtro_estado: str,
    *,
    en_camara_frio: bool,
    lote_estado: str,
    lote_etapa: str,
) -> bool:
    if not filtro_estado:
        return True
    if filtro_estado == CONSULTA_ESTADO_EN_CAMARA_FRIO:
        return en_camara_frio
    if en_camara_frio and filtro_estado == LotePlantaEstado.CERRADO:
        return True
    if en_camara_frio:
        return False
    return _coincide_filtro_estado_lote(
        filtro_estado,
        estado=lote_estado or "",
        etapa=lote_etapa or "",
    )


def _query_consulta(
    tab: str,
    filtro_productor: str,
    filtro_estado: str,
    *,
    refresh: bool = False,
) -> str:
    params = {"tab": _normalizar_tab_consulta(tab)}
    if filtro_productor:
        params["productor"] = filtro_productor
    if filtro_estado:
        params["estado"] = filtro_estado
    if refresh:
        params["refresh"] = "1"
    return urlencode(params)


def _url_consulta(
    tab: str,
    filtro_productor: str = "",
    filtro_estado: str = "",
    *,
    refresh: bool = False,
) -> str:
    base = reverse("operaciones:consulta")
    qs = _query_consulta(tab, filtro_productor, filtro_estado, refresh=refresh)
    return f"{base}?{qs}" if qs else base


def _filtros_consulta_request(request, default_tab: str = CONSULTA_TAB_DEFAULT) -> tuple[str, str, str]:
    tab = _normalizar_tab_consulta(request.GET.get("tab", default_tab))
    filtro_productor = request.GET.get("productor", "").strip()
    filtro_estado = request.GET.get("estado", "").strip()
    return tab, filtro_productor, filtro_estado


def _refresh_consulta_request(request) -> bool:
    raw = (request.GET.get("refresh") or "").strip().lower()
    return raw in {"1", "true", "si", "yes"}


def _cache_last_updated_display(updated_at: datetime.datetime | None) -> str:
    if not updated_at:
        return ""
    try:
        local_dt = timezone.localtime(updated_at)
    except Exception:
        local_dt = updated_at
    return local_dt.strftime("%d/%m/%Y %H:%M")


def _float_or_none(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _export_cell_value(value):
    if value is None:
        return ""
    if isinstance(value, datetime.datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, datetime.date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, bool):
        return "Si" if value else "No"
    return value


def _campos_base_lote_prefetch(lote: Lote | None) -> dict:
    if not lote:
        return {
            "productor": "",
            "tipo_cultivo": "",
            "variedad": "",
            "color": "",
            "fecha_cosecha": "",
        }
    primer_bin = None
    try:
        for rel in lote.bin_lotes.all():
            primer_bin = rel.bin
            break
    except Exception:
        primer_bin = None
    if not primer_bin:
        return {
            "productor": "",
            "tipo_cultivo": "",
            "variedad": "",
            "color": "",
            "fecha_cosecha": "",
        }
    return {
        "productor": primer_bin.codigo_productor or "",
        "tipo_cultivo": primer_bin.tipo_cultivo or "",
        "variedad": primer_bin.variedad_fruta or "",
        "color": primer_bin.color or "",
        "fecha_cosecha": str(primer_bin.fecha_cosecha) if primer_bin.fecha_cosecha else "",
    }

def _es_jefatura(user) -> bool:
    """
    Compatibilidad: usa is_staff/is_superuser como fallback.
    Preferir is_jefatura(request) desde usuarios.permissions cuando se dispone del request.
    """
    return user.is_active and (user.is_staff or user.is_superuser)


def _lotes_enriquecidos_qs(temporada: str, filtro_productor: str, filtro_estado: str) -> list:
    """
    Devuelve lista de dicts con datos enriquecidos de lotes filtrados.
    Encapsulado para reutilizar en vista HTML y exportaciones.
    """
    from django.conf import settings
    backend = getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip()

    if backend == "dataverse":
        return _lotes_enriquecidos_dataverse(filtro_productor, filtro_estado)

    lotes_raw = list(
        Lote.objects
        .filter(temporada=temporada, is_active=True)
        .prefetch_related("desverdizado", "ingreso_packing", "bin_lotes__bin")
        .order_by("-created_at")[:500]
    )
    resultado = []
    filtro_productor_lc = (filtro_productor or "").lower()
    for lote in lotes_raw:
        etapa = _etapa_lote(lote)
        if not _coincide_filtro_estado_lote(filtro_estado, estado=lote.estado, etapa=etapa):
            continue

        campos = _campos_base_lote_prefetch(lote)
        productor = campos["productor"]
        if filtro_productor_lc and filtro_productor_lc not in productor.lower():
            continue

        _, kilos_neto = _kilos_recientes_lote(lote, include_bin_fallback=False)
        resultado.append({
            "lote": lote,
            "lote_code": lote.lote_code,
            "estado": lote.estado,
            "estado_display": lote.get_estado_display(),
            "etapa": etapa,
            "cantidad_bins": lote.cantidad_bins,
            "kilos_neto": kilos_neto,
            "productor": productor,
            "variedad": campos["variedad"],
            "tipo_cultivo": campos["tipo_cultivo"],
            "color": campos["color"],
            "fecha": lote.fecha_conformacion or (lote.created_at.date() if lote.created_at else None),
        })
    return resultado


def _lotes_enriquecidos_dataverse(filtro_productor: str, filtro_estado: str) -> list:
    """
    Version Dataverse de _lotes_enriquecidos_qs.
    Usa etapa_actual persistida en crf21_etapa_actual como fuente principal.
    """
    try:
        from infrastructure.repository_factory import get_repositories
        from infrastructure.dataverse.repositories import resolve_etapa_lote
        repos = get_repositories()
        lotes = repos.lotes.list_recent(limit=500)
        lote_ids = [l.id for l in lotes if l.id]
        primer_bin_por_lote = repos.bins.first_bin_by_lotes(lote_ids) if lote_ids else {}

        # Resolver kilos recientes para cada lote en un pase previo
        desv_por_lote: dict = {}
        ip_por_lote: dict = {}
        for lote in lotes:
            if lote.id:
                try:
                    d = repos.desverdizados.find_by_lote(lote.id)
                    if d:
                        desv_por_lote[lote.id] = d
                except Exception:
                    pass
                try:
                    ip = repos.ingresos_packing.find_by_lote(lote.id)
                    if ip:
                        ip_por_lote[lote.id] = ip
                except Exception:
                    pass

        resultado = []
        filtro_productor_lc = (filtro_productor or "").lower()
        for lote in lotes:
            etapa = resolve_etapa_lote(lote)
            estado = (lote.estado or "").strip() or etapa
            if not _coincide_filtro_estado_lote(filtro_estado, estado=estado, etapa=etapa):
                continue
            primer_bin = primer_bin_por_lote.get(lote.id)
            productor = (primer_bin.codigo_productor if primer_bin else None) or lote.codigo_productor or ""
            if filtro_productor_lc and filtro_productor_lc not in productor.lower():
                continue

            _kn = _float_or_none(lote.kilos_neto_conformacion)
            _d = desv_por_lote.get(lote.id)
            if _d and _d.kilos_neto_salida is not None:
                _kn = float(_d.kilos_neto_salida)
            _ip = ip_por_lote.get(lote.id)
            if _ip and _ip.kilos_neto_ingreso_packing is not None:
                _kn = float(_ip.kilos_neto_ingreso_packing)

            resultado.append({
                "lote": lote,
                "lote_code": lote.lote_code,
                "estado": estado,
                "estado_display": _estado_display_consulta(estado, fallback=etapa),
                "etapa": etapa,
                "cantidad_bins": lote.cantidad_bins,
                "kilos_neto": _kn,
                "productor": productor,
                "variedad": primer_bin.variedad_fruta if primer_bin else "",
                "tipo_cultivo": primer_bin.tipo_cultivo if primer_bin else "",
                "color": primer_bin.color if primer_bin else "",
                "fecha": lote.fecha_conformacion,
            })
        return resultado
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("_lotes_enriquecidos_dataverse error: %s", exc)
        return []


def _pallets_enriquecidos_qs(temporada: str, filtro_productor: str, filtro_estado: str) -> list:
    from django.conf import settings
    backend = getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip()
    if backend == "dataverse":
        return _pallets_enriquecidos_dataverse(temporada, filtro_productor, filtro_estado)

    pallets = list(
        Pallet.objects
        .filter(temporada=temporada, is_active=True)
        .select_related("camara_frio")
        .prefetch_related("pallet_lotes__lote__bin_lotes__bin")
        .order_by("-created_at")[:500]
    )

    resultado = []
    filtro_productor_lc = (filtro_productor or "").lower()
    for pallet in pallets:
        relacion = None
        for rel in pallet.pallet_lotes.all():
            relacion = rel
            break
        lote = relacion.lote if relacion else None
        campos = _campos_base_lote_prefetch(lote)

        productor = campos["productor"]
        if filtro_productor_lc and filtro_productor_lc not in productor.lower():
            continue

        en_camara_frio = False
        try:
            en_camara_frio = bool(pallet.camara_frio)
        except Exception:
            en_camara_frio = False

        lote_etapa = _etapa_lote(lote) if lote else ""
        lote_estado = lote.estado if lote else ""
        if not _coincide_filtro_estado_pallet(
            filtro_estado,
            en_camara_frio=en_camara_frio,
            lote_estado=lote_estado,
            lote_etapa=lote_etapa,
        ):
            continue

        estado = CONSULTA_ESTADO_EN_CAMARA_FRIO if en_camara_frio else (lote_estado or "")
        estado_display = (
            "En Camara de Frio"
            if en_camara_frio
            else (lote.get_estado_display() if lote else "Sin lote relacionado")
        )
        etapa = "Camara Frio" if en_camara_frio else (lote_etapa or "Sin lote relacionado")
        resultado.append({
            "pallet": pallet,
            "pallet_code": pallet.pallet_code,
            "lote_code": lote.lote_code if lote else "",
            "tipo_caja": pallet.tipo_caja or "",
            "peso_total": _float_or_none(pallet.peso_total_kg),
            "productor": productor,
            "variedad": campos["variedad"],
            "color": campos["color"],
            "fecha_cosecha": campos["fecha_cosecha"],
            "estado": estado,
            "estado_display": estado_display,
            "etapa": etapa,
            "en_camara_frio": en_camara_frio,
            "fecha": pallet.fecha or (pallet.created_at.date() if pallet.created_at else None),
        })
    return resultado


def _pallets_enriquecidos_dataverse(temporada: str, filtro_productor: str, filtro_estado: str) -> list:
    try:
        from infrastructure.repository_factory import get_repositories
        from infrastructure.dataverse.repositories import resolve_etapa_lote

        repos = get_repositories()
        pallets = repos.pallets.list_recent(limit=500)
        contexto = _build_pallet_context_map_from_records(pallets, repos)

        resultado = []
        filtro_productor_lc = (filtro_productor or "").lower()
        lote_cache: dict[str, object] = {}

        for pallet in pallets:
            base = contexto.get(pallet.pallet_code, {})
            productor = (base.get("productor") or "").strip()
            if filtro_productor_lc and filtro_productor_lc not in productor.lower():
                continue

            lote_code = (base.get("lote_code") or "").strip()
            lote = None
            if lote_code:
                if lote_code not in lote_cache:
                    lote_cache[lote_code] = repos.lotes.find_by_code(temporada, lote_code)
                lote = lote_cache.get(lote_code)

            lote_estado = getattr(lote, "estado", "") if lote else ""
            lote_etapa = resolve_etapa_lote(lote, repos) if lote else ""

            en_camara_frio = False
            try:
                en_camara_frio = bool(repos.camara_frios.find_by_pallet(pallet.id))
            except Exception:
                en_camara_frio = False

            if not _coincide_filtro_estado_pallet(
                filtro_estado,
                en_camara_frio=en_camara_frio,
                lote_estado=lote_estado,
                lote_etapa=lote_etapa,
            ):
                continue

            estado = CONSULTA_ESTADO_EN_CAMARA_FRIO if en_camara_frio else (lote_estado or lote_etapa)
            estado_display = (
                "En Camara de Frio"
                if en_camara_frio
                else _estado_display_consulta(estado, fallback=lote_etapa or "Sin lote relacionado")
            )
            etapa = "Camara Frio" if en_camara_frio else (lote_etapa or "Sin lote relacionado")

            resultado.append({
                "pallet": pallet,
                "pallet_code": pallet.pallet_code,
                "lote_code": lote_code,
                "tipo_caja": pallet.tipo_caja or "",
                "peso_total": _float_or_none(pallet.peso_total_kg),
                "productor": productor,
                "variedad": base.get("variedad", ""),
                "color": base.get("color", ""),
                "fecha_cosecha": base.get("fecha_cosecha", ""),
                "estado": estado,
                "estado_display": estado_display,
                "etapa": etapa,
                "en_camara_frio": en_camara_frio,
                "fecha": getattr(pallet, "fecha", None),
            })
        return resultado
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("_pallets_enriquecidos_dataverse error: %s", exc)
        return []


def _detalle_lote_context(temporada: str, lote_code: str) -> dict:
    from django.conf import settings
    backend = getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip()
    if backend == "dataverse":
        try:
            from infrastructure.repository_factory import get_repositories
            from infrastructure.dataverse.repositories import resolve_etapa_lote

            repos = get_repositories()
            lote = repos.lotes.find_by_code(temporada, lote_code)
            if not lote:
                return {}

            info = _lote_info(temporada, lote_code)
            bins = repos.bins.list_by_lote(lote.id) if lote.id else []
            bins_data = []
            for b in bins:
                bins_data.append({
                    "bin_code": getattr(b, "bin_code", ""),
                    "productor": getattr(b, "codigo_productor", ""),
                    "variedad": getattr(b, "variedad_fruta", ""),
                    "color": getattr(b, "color", ""),
                    "fecha_cosecha": getattr(b, "fecha_cosecha", None),
                    "kilos_bruto": _float_or_none(getattr(b, "kilos_bruto_ingreso", None)),
                    "kilos_neto": _float_or_none(getattr(b, "kilos_neto_ingreso", None)),
                    "tipo_cultivo": getattr(b, "tipo_cultivo", ""),
                })

            etapa = resolve_etapa_lote(lote, repos)
            estado = info.get("estado") or getattr(lote, "estado", "") or etapa
            return {
                "lote_code": lote.lote_code,
                "estado": estado,
                "estado_display": _estado_display_consulta(estado, fallback=etapa),
                "etapa": etapa,
                "cantidad_bins": lote.cantidad_bins,
                "kilos_bruto": info.get("kilos_bruto"),
                "kilos_neto": info.get("kilos_neto"),
                "via_desverdizado": bool(info.get("via_desverdizado")),
                "requiere_desverdizado": bool(info.get("requiere_desverdizado")),
                "productor": info.get("productor", ""),
                "variedad": info.get("variedad", ""),
                "tipo_cultivo": info.get("tipo_cultivo", ""),
                "color": info.get("color", ""),
                "fecha_cosecha": info.get("fecha_cosecha", ""),
                "fecha_conformacion": getattr(lote, "fecha_conformacion", None),
                "bins": bins_data,
            }
        except Exception:
            return {}

    try:
        lote = Lote.objects.get(temporada=temporada, lote_code=lote_code, is_active=True)
    except Lote.DoesNotExist:
        return {}

    info = _lote_info(temporada, lote_code)
    etapa = _etapa_lote(lote)
    bin_lotes = list(lote.bin_lotes.select_related("bin").order_by("created_at"))
    bins_data = []
    for rel in bin_lotes:
        b = rel.bin
        bins_data.append({
            "bin_code": b.bin_code,
            "productor": b.codigo_productor or "",
            "variedad": b.variedad_fruta or "",
            "color": b.color or "",
            "fecha_cosecha": b.fecha_cosecha,
            "kilos_bruto": _float_or_none(b.kilos_bruto_ingreso),
            "kilos_neto": _float_or_none(b.kilos_neto_ingreso),
            "tipo_cultivo": b.tipo_cultivo or "",
        })

    return {
        "lote_code": lote.lote_code,
        "estado": lote.estado,
        "estado_display": lote.get_estado_display(),
        "etapa": etapa,
        "cantidad_bins": lote.cantidad_bins,
        "kilos_bruto": info.get("kilos_bruto"),
        "kilos_neto": info.get("kilos_neto"),
        "via_desverdizado": bool(info.get("via_desverdizado")),
        "requiere_desverdizado": bool(info.get("requiere_desverdizado")),
        "productor": info.get("productor", ""),
        "variedad": info.get("variedad", ""),
        "tipo_cultivo": info.get("tipo_cultivo", ""),
        "color": info.get("color", ""),
        "fecha_cosecha": info.get("fecha_cosecha", ""),
        "fecha_conformacion": lote.fecha_conformacion,
        "bins": bins_data,
    }


def _detalle_pallet_context(temporada: str, pallet_code: str) -> dict:
    from django.conf import settings
    backend = getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip()
    if backend == "dataverse":
        try:
            from infrastructure.repository_factory import get_repositories
            from infrastructure.dataverse.repositories import resolve_etapa_lote

            repos = get_repositories()
            pallet = repos.pallets.find_by_code(temporada, pallet_code)
            if not pallet:
                return {}

            base = _pallet_info(temporada, pallet_code)
            lote_code = (base.get("lote_code") or "").strip()
            lote = repos.lotes.find_by_code(temporada, lote_code) if lote_code else None
            lote_etapa = resolve_etapa_lote(lote, repos) if lote else ""
            lote_estado = getattr(lote, "estado", "") if lote else ""

            en_camara_frio = False
            try:
                en_camara_frio = bool(repos.camara_frios.find_by_pallet(pallet.id))
            except Exception:
                en_camara_frio = False

            estado = CONSULTA_ESTADO_EN_CAMARA_FRIO if en_camara_frio else (lote_estado or lote_etapa)
            estado_display = (
                "En Camara de Frio"
                if en_camara_frio
                else _estado_display_consulta(estado, fallback=lote_etapa or "Sin lote relacionado")
            )
            return {
                "pallet_code": pallet.pallet_code,
                "tipo_caja": pallet.tipo_caja or "",
                "peso_total": _float_or_none(pallet.peso_total_kg),
                "lote_code": lote_code,
                "productor": base.get("productor", ""),
                "variedad": base.get("variedad", ""),
                "color": base.get("color", ""),
                "fecha_cosecha": base.get("fecha_cosecha", ""),
                "estado": estado,
                "estado_display": estado_display,
                "etapa": "Camara Frio" if en_camara_frio else (lote_etapa or "Sin lote relacionado"),
                "en_camara_frio": en_camara_frio,
                "fecha": getattr(pallet, "fecha", None),
            }
        except Exception:
            return {}

    try:
        pallet = Pallet.objects.get(temporada=temporada, pallet_code=pallet_code, is_active=True)
    except Pallet.DoesNotExist:
        return {}

    relacion = pallet.pallet_lotes.select_related("lote").first()
    lote = relacion.lote if relacion else None
    campos = _campos_base_lote(lote) if lote else {
        "productor": "",
        "tipo_cultivo": "",
        "variedad": "",
        "color": "",
        "fecha_cosecha": "",
    }

    en_camara_frio = False
    try:
        en_camara_frio = bool(pallet.camara_frio)
    except Exception:
        en_camara_frio = False

    lote_etapa = _etapa_lote(lote) if lote else ""
    lote_estado = lote.estado if lote else ""
    estado = CONSULTA_ESTADO_EN_CAMARA_FRIO if en_camara_frio else lote_estado
    estado_display = (
        "En Camara de Frio"
        if en_camara_frio
        else (lote.get_estado_display() if lote else "Sin lote relacionado")
    )
    return {
        "pallet_code": pallet.pallet_code,
        "tipo_caja": pallet.tipo_caja or "",
        "peso_total": _float_or_none(pallet.peso_total_kg),
        "lote_code": lote.lote_code if lote else "",
        "productor": campos.get("productor", ""),
        "variedad": campos.get("variedad", ""),
        "color": campos.get("color", ""),
        "fecha_cosecha": campos.get("fecha_cosecha", ""),
        "estado": estado,
        "estado_display": estado_display,
        "etapa": "Camara Frio" if en_camara_frio else (lote_etapa or "Sin lote relacionado"),
        "en_camara_frio": en_camara_frio,
        "fecha": pallet.fecha or (pallet.created_at.date() if pallet.created_at else None),
    }


def _consulta_export_bundle(
    temporada: str,
    tab: str,
    filtro_productor: str,
    filtro_estado: str,
    *,
    force_refresh: bool = False,
) -> tuple[list[tuple[str, str]], list[dict], str, dict]:
    tab_norm = _normalizar_tab_consulta(tab)
    lotes, pallets, meta = _consulta_dataset(
        temporada,
        filtro_productor,
        filtro_estado,
        force_refresh=force_refresh,
    )
    if tab_norm == CONSULTA_TAB_PALLETS:
        rows = [dict(item) for item in pallets]
        for item in rows:
            item["temporada"] = temporada
        return CONSULTA_COLUMNAS_PALLETS, rows, CONSULTA_TAB_PALLETS, meta

    rows = [dict(item) for item in lotes]
    for item in rows:
        item["temporada"] = temporada
    return CONSULTA_COLUMNAS_LOTES, rows, CONSULTA_TAB_LOTES, meta


class JefaturaRequiredMixin(UserPassesTestMixin):
    """Restringe el acceso a usuarios con rol Jefatura o Administrador."""
    def test_func(self):
        from usuarios.permissions import is_jefatura
        return is_jefatura(self.request)

    def handle_no_permission(self):
        messages.error(self.request, "Acceso denegado: se requiere rol Jefatura o Administrador.")
        return redirect("usuarios:portal")


# ---------------------------------------------------------------------------
# Consulta jefatura — vista HTML
# ---------------------------------------------------------------------------

class ConsultaJefaturaView(LoginRequiredMixin, JefaturaRequiredMixin, TemplateView):
    template_name = "operaciones/consulta.html"
    login_url = reverse_lazy("usuarios:login")
    raise_exception = True

    def test_func(self):
        """Solo jefatura y administradores (is_staff o is_superuser)."""
        user = self.request.user
        return user.is_active and (user.is_staff or user.is_superuser)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        temporada = self.request.session.get("temporada_activa") or str(datetime.date.today().year)
        tab_actual, filtro_productor, filtro_estado = _filtros_consulta_request(
            self.request,
            CONSULTA_TAB_DEFAULT,
        )
        force_refresh = _refresh_consulta_request(self.request)

        lotes, pallets, cache_meta = _consulta_dataset(
            temporada,
            filtro_productor,
            filtro_estado,
            force_refresh=force_refresh,
        )
        query_consulta = _query_consulta(tab_actual, filtro_productor, filtro_estado)

        ctx["page_title"] = "Consulta Jefatura"
        ctx["temporada"] = temporada
        ctx["filtro_productor"] = filtro_productor
        ctx["filtro_estado"] = filtro_estado
        ctx["tab_actual"] = tab_actual
        ctx["lotes"] = lotes
        ctx["pallets"] = pallets
        ctx["lotes_count"] = len(lotes)
        ctx["pallets_count"] = len(pallets)
        ctx["estados_choices"] = _consulta_estado_choices()
        ctx["query_consulta"] = query_consulta
        ctx["tab_lotes_url"] = _url_consulta(CONSULTA_TAB_LOTES, filtro_productor, filtro_estado)
        ctx["tab_pallets_url"] = _url_consulta(CONSULTA_TAB_PALLETS, filtro_productor, filtro_estado)
        ctx["refresh_url"] = _url_consulta(
            tab_actual,
            filtro_productor,
            filtro_estado,
            refresh=True,
        )
        ctx["export_csv_url"] = f"{reverse('operaciones:exportar_consulta')}?{query_consulta}"
        ctx["export_excel_url"] = f"{reverse('operaciones:exportar_consulta_excel')}?{query_consulta}"
        ctx["is_dataverse_backend"] = cache_meta.get("is_dataverse_backend", False)
        ctx["cache_is_stale"] = cache_meta.get("cache_is_stale", False)
        ctx["cache_source"] = cache_meta.get("cache_source", "none")
        ctx["cache_last_updated"] = cache_meta.get("cache_last_updated")
        ctx["cache_last_updated_display"] = _cache_last_updated_display(ctx["cache_last_updated"])
        ctx["background_refresh_started"] = cache_meta.get("background_refresh_started", False)
        ctx["refreshed_now"] = cache_meta.get("refreshed_now", False)

        warning_message = cache_meta.get("warning_message", "").strip()
        if warning_message:
            messages.warning(self.request, warning_message)
        elif force_refresh and cache_meta.get("refreshed_now"):
            messages.success(self.request, "Consulta sincronizada desde Dataverse.")
        return ctx


# ---------------------------------------------------------------------------
# Exportación CSV — mismos filtros que la vista
# ---------------------------------------------------------------------------

class ConsultaLoteDetalleView(LoginRequiredMixin, JefaturaRequiredMixin, TemplateView):
    template_name = "operaciones/consulta_lote_detalle.html"
    login_url = reverse_lazy("usuarios:login")
    raise_exception = True

    def get(self, request, *args, **kwargs):
        temporada = request.session.get("temporada_activa") or str(datetime.date.today().year)
        lote_code = (kwargs.get("lote_code") or "").strip()
        tab, filtro_productor, filtro_estado = _filtros_consulta_request(
            request,
            CONSULTA_TAB_LOTES,
        )
        detalle = _detalle_lote_context(temporada, lote_code)
        if not detalle:
            messages.error(request, f"Lote '{lote_code}' no encontrado.")
            return redirect(_url_consulta(tab, filtro_productor, filtro_estado))

        context = self.get_context_data(
            temporada=temporada,
            detalle=detalle,
            back_url=_url_consulta(tab, filtro_productor, filtro_estado),
            query_consulta=_query_consulta(tab, filtro_productor, filtro_estado),
        )
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        detalle = kwargs["detalle"]
        ctx["page_title"] = f"Detalle Lote {detalle['lote_code']}"
        ctx["temporada"] = kwargs["temporada"]
        ctx["detalle"] = detalle
        ctx["back_url"] = kwargs["back_url"]
        ctx["query_consulta"] = kwargs["query_consulta"]
        return ctx


class ConsultaPalletDetalleView(LoginRequiredMixin, JefaturaRequiredMixin, TemplateView):
    template_name = "operaciones/consulta_pallet_detalle.html"
    login_url = reverse_lazy("usuarios:login")
    raise_exception = True

    def get(self, request, *args, **kwargs):
        temporada = request.session.get("temporada_activa") or str(datetime.date.today().year)
        pallet_code = (kwargs.get("pallet_code") or "").strip()
        tab, filtro_productor, filtro_estado = _filtros_consulta_request(
            request,
            CONSULTA_TAB_PALLETS,
        )
        detalle = _detalle_pallet_context(temporada, pallet_code)
        if not detalle:
            messages.error(request, f"Pallet '{pallet_code}' no encontrado.")
            return redirect(_url_consulta(tab, filtro_productor, filtro_estado))

        context = self.get_context_data(
            temporada=temporada,
            detalle=detalle,
            back_url=_url_consulta(tab, filtro_productor, filtro_estado),
            query_consulta=_query_consulta(tab, filtro_productor, filtro_estado),
            query_lote=_query_consulta(CONSULTA_TAB_LOTES, filtro_productor, filtro_estado),
        )
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        detalle = kwargs["detalle"]
        ctx["page_title"] = f"Detalle Pallet {detalle['pallet_code']}"
        ctx["temporada"] = kwargs["temporada"]
        ctx["detalle"] = detalle
        ctx["back_url"] = kwargs["back_url"]
        ctx["query_consulta"] = kwargs["query_consulta"]
        ctx["query_lote"] = kwargs["query_lote"]
        return ctx


class ExportarConsultaCSVView(LoginRequiredMixin, JefaturaRequiredMixin, View):
    login_url = reverse_lazy("usuarios:login")

    def get(self, request):
        temporada = request.session.get("temporada_activa") or str(datetime.date.today().year)
        tab, filtro_productor, filtro_estado = _filtros_consulta_request(
            request,
            CONSULTA_TAB_DEFAULT,
        )
        force_refresh = _refresh_consulta_request(request)
        columnas, rows, tab_norm, _ = _consulta_export_bundle(
            temporada,
            tab,
            filtro_productor,
            filtro_estado,
            force_refresh=force_refresh,
        )

        fecha_hoy = datetime.date.today().strftime("%Y%m%d")
        filename = f"consulta_{tab_norm}_{temporada}_{fecha_hoy}.csv"

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.write("\ufeff")

        writer = csv.writer(response)
        writer.writerow([header for header, _ in columnas])
        for item in rows:
            writer.writerow([_export_cell_value(item.get(key, "")) for _, key in columnas])
        return response


class ExportarConsultaExcelView(LoginRequiredMixin, JefaturaRequiredMixin, View):
    login_url = reverse_lazy("usuarios:login")

    def get(self, request):
        temporada = request.session.get("temporada_activa") or str(datetime.date.today().year)
        tab, filtro_productor, filtro_estado = _filtros_consulta_request(
            request,
            CONSULTA_TAB_DEFAULT,
        )
        force_refresh = _refresh_consulta_request(request)
        columnas, rows, tab_norm, _ = _consulta_export_bundle(
            temporada,
            tab,
            filtro_productor,
            filtro_estado,
            force_refresh=force_refresh,
        )

        try:
            from openpyxl import Workbook
            from openpyxl.utils import get_column_letter
        except Exception:
            messages.error(
                request,
                "No fue posible generar Excel porque openpyxl no esta instalado en este entorno.",
            )
            return redirect(_url_consulta(tab, filtro_productor, filtro_estado))

        wb = Workbook()
        ws = wb.active
        ws.title = "Consulta"
        ws.append([header for header, _ in columnas])
        for item in rows:
            ws.append([_export_cell_value(item.get(key, "")) for _, key in columnas])

        for idx, _ in enumerate(columnas, start=1):
            ws.column_dimensions[get_column_letter(idx)].width = 20

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        fecha_hoy = datetime.date.today().strftime("%Y%m%d")
        filename = f"consulta_{tab_norm}_{temporada}_{fecha_hoy}.xlsx"
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _handle_result(request, result) -> None:
    if result.ok:
        messages.success(request, result.message)
    else:
        for err in result.errors:
            messages.error(request, err)

