"""
Vistas web del flujo operativo de packing.
Cada vista corresponde a una etapa del flujo.
"""
import datetime
import json

from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib import messages
from django.urls import reverse_lazy

from operaciones.forms import (
    IniciarLoteForm,
    CerrarLoteForm,
    BinForm,
    LoteForm,
    CamaraMantencionForm,
    DesverdizadoForm,
    IngresoPackingForm,
    RegistroPackingForm,
    ControlProcesoPackingForm,
    CalidadPalletForm,
    CamaraFrioForm,
    MedicionTemperaturaForm,
)
from operaciones.application.use_cases import (
    iniciar_lote_recepcion,
    agregar_bin_a_lote_abierto,
    cerrar_lote_recepcion,
    crear_lote_recepcion,
    registrar_camara_mantencion,
    registrar_desverdizado,
    registrar_ingreso_packing,
    registrar_registro_packing,
    registrar_control_proceso_packing,
    registrar_calidad_pallet,
    cerrar_pallet,
    registrar_camara_frio,
    registrar_medicion_temperatura,
)
from operaciones.models import (
    Lote,
    LotePlantaEstado,
)


def _temporada(request) -> str:
    """Devuelve la temporada activa: del POST, sesion o año actual."""
    return (
        request.POST.get("temporada")
        or request.session.get("temporada_activa")
        or str(datetime.date.today().year)
    )


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

        try:
            lotes_qs = Lote.objects.filter(temporada=temporada, is_active=True)
            lotes_abiertos = lotes_qs.filter(estado=LotePlantaEstado.ABIERTO)
            lotes_cerrados = lotes_qs.filter(estado=LotePlantaEstado.CERRADO)
            lotes_finalizados = lotes_qs.filter(estado=LotePlantaEstado.FINALIZADO)

            # Bins hoy
            from operaciones.models import BinLote
            hoy = datetime.date.today()
            bins_hoy = BinLote.objects.filter(
                created_at__date=hoy,
            ).count()

            # Lotes activos con datos para tabla
            lotes_activos_qs = lotes_qs.exclude(
                estado=LotePlantaEstado.FINALIZADO
            ).order_by("-created_at")[:20]

            lotes_activos = []
            for lote in lotes_activos_qs:
                lotes_activos.append({
                    "codigo": lote.lote_code,
                    "bins": lote.cantidad_bins,
                    "etapa": _etapa_lote(lote),
                    "estado": lote.estado,
                })

            ctx["kpis"] = {
                "lotes_abiertos": lotes_abiertos.count(),
                "lotes_cerrados": lotes_cerrados.count(),
                "lotes_finalizados": lotes_finalizados.count(),
                "total_lotes": lotes_qs.count(),
                "bins_hoy": bins_hoy,
            }
            ctx["lotes_activos"] = lotes_activos
        except Exception:
            ctx["kpis"] = {}
            ctx["lotes_activos"] = []

        return ctx


# ---------------------------------------------------------------------------
# Recepcion de bins — flujo de lote abierto
# ---------------------------------------------------------------------------

class RecepcionView(LoginRequiredMixin, TemplateView):
    template_name = "operaciones/recepcion.html"
    login_url = reverse_lazy("usuarios:login")

    CAMPOS_BASE = ["codigo_productor", "tipo_cultivo", "variedad_fruta", "color", "fecha_cosecha"]

    def _lote_activo(self, request):
        """Retorna el objeto Lote activo desde sesion, o None si no hay."""
        lote_code = request.session.get("lote_activo_code")
        if not lote_code:
            return None
        temporada = _temporada(request)
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

    def _bins_de_lote(self, lote):
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
            "operator_code": cd.get("operator_code", ""),
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
            "operator_code": cd.get("operator_code", ""),
            "source_system": "web",
            "fecha_cosecha": str(cd["fecha_cosecha"]) if cd.get("fecha_cosecha") else None,
            "variedad_fruta": cd.get("variedad_fruta") or "",
            "codigo_productor": cd.get("codigo_productor") or "",
            "tipo_cultivo": cd.get("tipo_cultivo") or "",
            "numero_cuartel": cd.get("numero_cuartel") or "",
            "color": cd.get("color") or "",
            "hora_recepcion": cd.get("hora_recepcion") or "",
            "kilos_bruto_ingreso": str(cd["kilos_bruto_ingreso"]) if cd.get("kilos_bruto_ingreso") else None,
            "kilos_neto_ingreso": str(cd["kilos_neto_ingreso"]) if cd.get("kilos_neto_ingreso") else None,
            "a_o_r": cd.get("a_o_r") or None,
            "observaciones": cd.get("observaciones") or "",
        }

        result = agregar_bin_a_lote_abierto(payload)
        if result.ok:
            # Guardar campos base desde el primer bin
            if not campos_base:
                request.session["lote_activo_campos_base"] = {
                    "codigo_productor": cd.get("codigo_productor", ""),
                    "tipo_cultivo": cd.get("tipo_cultivo", ""),
                    "variedad_fruta": cd.get("variedad_fruta", ""),
                    "color": cd.get("color", ""),
                    "fecha_cosecha": str(cd["fecha_cosecha"]) if cd.get("fecha_cosecha") else "",
                }
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
            "operator_code": cd.get("operator_code", ""),
            "source_system": "web",
            "requiere_desverdizado": cd.get("requiere_desverdizado") or False,
            "disponibilidad_camara_desverdizado": cd.get("disponibilidad_camara_desverdizado") or None,
            "kilos_bruto_conformacion": str(cd["kilos_bruto_conformacion"]) if cd.get("kilos_bruto_conformacion") else None,
            "kilos_neto_conformacion": str(cd["kilos_neto_conformacion"]) if cd.get("kilos_neto_conformacion") else None,
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


# ---------------------------------------------------------------------------
# Conformar lote (pesaje) — flujo legacy via lista de bin_codes
# ---------------------------------------------------------------------------

class PesajeView(LoginRequiredMixin, TemplateView):
    template_name = "operaciones/pesaje.html"
    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Conformar Lote"
        ctx["form"] = LoteForm()
        return ctx

    def post(self, request, *args, **kwargs):
        form = LoteForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Formulario invalido.")
            ctx = self.get_context_data()
            ctx["form"] = form
            return render(request, self.template_name, ctx)

        cd = form.cleaned_data
        payload = {
            "temporada": _temporada(request),
            "bin_codes": cd["bin_codes"],
            "operator_code": cd.get("operator_code", ""),
            "source_system": "web",
        }
        result = crear_lote_recepcion(payload)
        if result.ok:
            messages.success(request, result.message)
            return redirect("operaciones:pesaje")
        for err in result.errors:
            messages.error(request, err)
        ctx = self.get_context_data()
        ctx["form"] = form
        return render(request, self.template_name, ctx)


# ---------------------------------------------------------------------------
# Desverdizado (camara mantencion + desverdizado)
# ---------------------------------------------------------------------------

def _lotes_pendientes_desverdizado(temporada: str):
    """
    Retorna lotes cerrados que requieren desverdizado y aun no tienen
    registro de desverdizado. Se muestran en el selector de la vista.
    """
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


class DesverdizadoView(LoginRequiredMixin, TemplateView):
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
            return {
                "lote_code": lote.lote_code,
                "cantidad_bins": lote.cantidad_bins,
                "kilos_bruto": lote.kilos_bruto_conformacion,
                "kilos_neto": lote.kilos_neto_conformacion,
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
                    "operator_code": cd.get("operator_code", ""),
                    "source_system": "web",
                    "extra": {
                        "camara_numero": cd.get("camara_numero"),
                        "fecha_ingreso": str(cd["fecha_ingreso"]) if cd.get("fecha_ingreso") else None,
                        "hora_ingreso": cd.get("hora_ingreso"),
                        "temperatura_camara": str(cd["temperatura_camara"]) if cd.get("temperatura_camara") else None,
                        "humedad_relativa": str(cd["humedad_relativa"]) if cd.get("humedad_relativa") else None,
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
                    "operator_code": cd.get("operator_code", ""),
                    "source_system": "web",
                    "extra": {
                        "fecha_ingreso": str(cd["fecha_ingreso"]) if cd.get("fecha_ingreso") else None,
                        "hora_ingreso": cd.get("hora_ingreso"),
                        "color_salida": cd.get("color") or "",
                        # horas_desverdizado se guarda en el campo 'proceso' por ahora
                        "proceso": str(cd["horas_desverdizado"]) + "h" if cd.get("horas_desverdizado") else "",
                        "kilos_enviados_terreno": str(cd["kilos_enviados_terreno"]) if cd.get("kilos_enviados_terreno") else None,
                        "kilos_recepcionados": str(cd["kilos_recepcionados"]) if cd.get("kilos_recepcionados") else None,
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

        fecha_cosecha_str = ""
        if primer_bin and primer_bin.fecha_cosecha:
            fecha_cosecha_str = str(primer_bin.fecha_cosecha)

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
            "color":        primer_bin.color            if primer_bin else "",
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


class IngresoPackingView(LoginRequiredMixin, TemplateView):
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
            "operator_code": cd.get("operator_code", ""),
            "source_system": "web",
            "via_desverdizado": cd.get("via_desverdizado") or info.get("via_desverdizado", False),
            "extra": {
                "fecha_ingreso": str(cd["fecha_ingreso"]) if cd.get("fecha_ingreso") else None,
                "hora_ingreso": cd.get("hora_ingreso"),
                "kilos_bruto_ingreso_packing": str(cd["kilos_bruto_ingreso_packing"]) if cd.get("kilos_bruto_ingreso_packing") else None,
                "kilos_neto_ingreso_packing": str(cd["kilos_neto_ingreso_packing"]) if cd.get("kilos_neto_ingreso_packing") else None,
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

class ProcesoView(LoginRequiredMixin, TemplateView):
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
        # Lotes que ya tienen ingreso packing (aptos para proceso)
        from operaciones.models import IngresoAPacking
        lotes_con_ingreso = set(
            IngresoAPacking.objects.values_list("lote_id", flat=True)
        )
        ctx["lotes_pendientes"] = list(
            Lote.objects
            .filter(temporada=temporada, is_active=True, id__in=lotes_con_ingreso)
            .order_by("-created_at")[:30]
        )
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
            "operator_code": cd.get("operator_code", ""),
            "source_system": "web",
            "extra": {
                "fecha": str(cd["fecha"]) if cd.get("fecha") else None,
                "hora_inicio": cd.get("hora_inicio"),
                "linea_proceso": cd.get("linea_proceso"),
                "categoria_calidad": cd.get("categoria_calidad"),
                "calibre": cd.get("calibre"),
                "tipo_envase": cd.get("tipo_envase"),
                "cantidad_cajas_producidas": cd.get("cantidad_cajas_producidas"),
                "merma_seleccion_pct": str(cd["merma_seleccion_pct"]) if cd.get("merma_seleccion_pct") else None,
            },
        }
        result = registrar_registro_packing(payload)
        _handle_result(request, result)
        return redirect("operaciones:proceso")


# ---------------------------------------------------------------------------
# Control proceso packing
# ---------------------------------------------------------------------------

class ControlView(LoginRequiredMixin, TemplateView):
    template_name = "operaciones/control.html"
    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Control Proceso Packing"
        ctx["form"] = ControlProcesoPackingForm()
        temporada = (
            self.request.session.get("temporada_activa")
            or str(datetime.date.today().year)
        )
        from operaciones.models import IngresoAPacking
        lotes_con_ingreso = set(IngresoAPacking.objects.values_list("lote_id", flat=True))
        ctx["lotes_pendientes"] = list(
            Lote.objects
            .filter(temporada=temporada, is_active=True, id__in=lotes_con_ingreso)
            .order_by("-created_at")[:30]
        )
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
            "operator_code": cd.get("operator_code", ""),
            "source_system": "web",
            "extra": {
                "fecha": str(cd["fecha"]) if cd.get("fecha") else None,
                "hora": cd.get("hora"),
                "n_bins_procesados": cd.get("n_bins_procesados"),
                "temp_agua_tina": str(cd["temp_agua_tina"]) if cd.get("temp_agua_tina") else None,
                "ph_agua": str(cd["ph_agua"]) if cd.get("ph_agua") else None,
                "recambio_agua": cd.get("recambio_agua"),
                "rendimiento_lote_pct": str(cd["rendimiento_lote_pct"]) if cd.get("rendimiento_lote_pct") else None,
                "observaciones_generales": cd.get("observaciones_generales"),
            },
        }
        result = registrar_control_proceso_packing(payload)
        _handle_result(request, result)
        return redirect("operaciones:control")


# ---------------------------------------------------------------------------
# Paletizado (calidad + cerrar pallet)
# ---------------------------------------------------------------------------

class PaletizadoView(LoginRequiredMixin, TemplateView):
    template_name = "operaciones/paletizado.html"
    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Paletizado"
        ctx["form_calidad"] = CalidadPalletForm()
        return ctx

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
                    "operator_code": cd.get("operator_code", ""),
                    "source_system": "web",
                    "extra": {
                        "fecha": str(cd["fecha"]) if cd.get("fecha") else None,
                        "hora": cd.get("hora"),
                        "temperatura_fruta": str(cd["temperatura_fruta"]) if cd.get("temperatura_fruta") else None,
                        "peso_caja_muestra": str(cd["peso_caja_muestra"]) if cd.get("peso_caja_muestra") else None,
                        "estado_visual_fruta": cd.get("estado_visual_fruta"),
                        "presencia_defectos": cd.get("presencia_defectos"),
                        "aprobado": cd.get("aprobado"),
                        "observaciones": cd.get("observaciones"),
                    },
                }
                result = registrar_calidad_pallet(payload)
                _handle_result(request, result)
            else:
                messages.error(request, "Formulario de calidad invalido.")

        elif action == "cerrar":
            lote_code = request.POST.get("lote_code", "").strip()
            operator_code = request.POST.get("operator_code", "").strip()
            payload = {
                "temporada": temporada,
                "lote_code": lote_code,
                "pallet_code": pallet_code,
                "operator_code": operator_code,
                "source_system": "web",
            }
            result = cerrar_pallet(payload)
            _handle_result(request, result)

        return redirect("operaciones:paletizado")


# ---------------------------------------------------------------------------
# Camaras (frio + medicion temperatura)
# ---------------------------------------------------------------------------

class CamarasView(LoginRequiredMixin, TemplateView):
    template_name = "operaciones/camaras.html"
    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Camaras de Frio"
        ctx["form_camara"] = CamaraFrioForm()
        ctx["form_medicion"] = MedicionTemperaturaForm()
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
                    "operator_code": cd.get("operator_code", ""),
                    "source_system": "web",
                    "extra": {
                        "camara_numero": cd.get("camara_numero"),
                        "temperatura_camara": str(cd["temperatura_camara"]) if cd.get("temperatura_camara") else None,
                        "humedad_relativa": str(cd["humedad_relativa"]) if cd.get("humedad_relativa") else None,
                        "fecha_ingreso": str(cd["fecha_ingreso"]) if cd.get("fecha_ingreso") else None,
                        "hora_ingreso": cd.get("hora_ingreso"),
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
                    "operator_code": cd.get("operator_code", ""),
                    "source_system": "web",
                    "extra": {
                        "fecha": str(cd["fecha"]) if cd.get("fecha") else None,
                        "hora": cd.get("hora"),
                        "temperatura_pallet": str(cd["temperatura_pallet"]) if cd.get("temperatura_pallet") else None,
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
# Consulta jefatura
# ---------------------------------------------------------------------------

class ConsultaJefaturaView(LoginRequiredMixin, TemplateView):
    template_name = "operaciones/consulta.html"
    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Consulta Jefatura"
        temporada = (
            self.request.session.get("temporada_activa")
            or str(datetime.date.today().year)
        )
        filtro_productor = self.request.GET.get("productor", "").strip()
        filtro_estado = self.request.GET.get("estado", "").strip()

        qs = Lote.objects.filter(temporada=temporada, is_active=True)
        if filtro_estado:
            qs = qs.filter(estado=filtro_estado)

        lotes_raw = list(qs.order_by("-created_at")[:100])
        lotes_enriquecidos = []
        for lote in lotes_raw:
            # Obtener datos base del primer bin
            bin_lotes = list(lote.bin_lotes.select_related("bin").order_by("created_at")[:1])
            primer_bin = bin_lotes[0].bin if bin_lotes else None
            productor = primer_bin.codigo_productor if primer_bin else ""
            variedad = primer_bin.variedad_fruta if primer_bin else ""

            # Filtrar por productor si se solicita
            if filtro_productor and filtro_productor.lower() not in productor.lower():
                continue

            lotes_enriquecidos.append({
                "lote": lote,
                "lote_code": lote.lote_code,
                "estado": lote.estado,
                "estado_display": lote.get_estado_display(),
                "etapa": _etapa_lote(lote),
                "cantidad_bins": lote.cantidad_bins,
                "kilos_neto": lote.kilos_neto_conformacion,
                "productor": productor,
                "variedad": variedad,
                "fecha": lote.fecha_conformacion or lote.created_at.date() if lote.created_at else None,
            })

        ctx["lotes"] = lotes_enriquecidos
        ctx["temporada"] = temporada
        ctx["filtro_productor"] = filtro_productor
        ctx["filtro_estado"] = filtro_estado
        ctx["estados_choices"] = LotePlantaEstado.choices
        return ctx


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _handle_result(request, result) -> None:
    if result.ok:
        messages.success(request, result.message)
    else:
        for err in result.errors:
            messages.error(request, err)
