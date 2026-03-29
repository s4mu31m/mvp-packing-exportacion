"""
Vistas web del flujo operativo de packing.
Cada vista corresponde a una etapa del flujo.
"""
import datetime

from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, FormView
from django.contrib import messages
from django.urls import reverse_lazy

from operaciones.forms import (
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
    registrar_bin_recibido,
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


def _temporada(request) -> str:
    """Devuelve la temporada activa: del POST, sesion o año actual."""
    return (
        request.POST.get("temporada")
        or request.session.get("temporada_activa")
        or str(datetime.date.today().year)
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "operaciones/dashboard.html"
    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["lotes_activos"] = self._mock_lotes()
        ctx["kpis"] = self._mock_kpis()
        ctx["page_title"] = "Dashboard — Turno Actual"
        return ctx

    def _mock_lotes(self):
        return [
            {"codigo": "LP-2026-041", "variedad": "Thompson Seedless",
             "bins": 24, "peso_kg": 9840, "etapa": "Packing", "estado": "activo"},
            {"codigo": "LP-2026-040", "variedad": "Red Globe",
             "bins": 18, "peso_kg": 7290, "etapa": "Control", "estado": "activo"},
            {"codigo": "LP-2026-039", "variedad": "Crimson Seedless",
             "bins": 32, "peso_kg": 13440, "etapa": "Camara Frio", "estado": "completado"},
        ]

    def _mock_kpis(self):
        return {
            "bins_recibidos": 84,
            "pallets_cerrados": 17,
            "lineas_activas": 6,
            "kg_procesados": 22400,
        }


# ---------------------------------------------------------------------------
# Recepcion de bins
# ---------------------------------------------------------------------------

class RecepcionView(LoginRequiredMixin, TemplateView):
    template_name = "operaciones/recepcion.html"
    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Recepcion de Bins"
        ctx["form"] = BinForm()
        ctx["bins_del_lote"] = []
        return ctx

    def post(self, request, *args, **kwargs):
        form = BinForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Formulario invalido.")
            ctx = self.get_context_data()
            ctx["form"] = form
            return render(request, self.template_name, ctx)

        cd = form.cleaned_data
        payload = {
            "temporada": _temporada(request),
            "bin_code": cd["bin_code"],
            "operator_code": cd.get("operator_code", ""),
            "source_system": "web",
            "fecha_cosecha": str(cd["fecha_cosecha"]) if cd.get("fecha_cosecha") else None,
            "variedad_fruta": cd.get("variedad_fruta"),
            "codigo_productor": cd.get("codigo_productor"),
            "hora_recepcion": cd.get("hora_recepcion"),
            "kilos_bruto_ingreso": str(cd["kilos_bruto_ingreso"]) if cd.get("kilos_bruto_ingreso") else None,
            "kilos_neto_ingreso": str(cd["kilos_neto_ingreso"]) if cd.get("kilos_neto_ingreso") else None,
            "a_o_r": cd.get("a_o_r") or None,
            "observaciones": cd.get("observaciones"),
        }
        result = registrar_bin_recibido(payload)
        if result.ok:
            messages.success(request, result.message)
        else:
            for err in result.errors:
                messages.error(request, err)
        return redirect("operaciones:recepcion")


# ---------------------------------------------------------------------------
# Conformar lote (pesaje)
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
            "lote_code": cd["lote_code"],
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

class DesverdizadoView(LoginRequiredMixin, TemplateView):
    template_name = "operaciones/desverdizado.html"
    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Desverdizado"
        ctx["form_mantencion"] = CamaraMantencionForm()
        ctx["form_desverdizado"] = DesverdizadoForm()
        return ctx

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
                        "kilos_enviados_terreno": str(cd["kilos_enviados_terreno"]) if cd.get("kilos_enviados_terreno") else None,
                        "kilos_recepcionados": str(cd["kilos_recepcionados"]) if cd.get("kilos_recepcionados") else None,
                        "proceso": cd.get("proceso"),
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

class IngresoPackingView(LoginRequiredMixin, TemplateView):
    template_name = "operaciones/ingreso_packing.html"
    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Ingreso a Packing"
        ctx["form"] = IngresoPackingForm()
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
        payload = {
            "temporada": _temporada(request),
            "lote_code": lote_code,
            "operator_code": cd.get("operator_code", ""),
            "source_system": "web",
            "via_desverdizado": cd.get("via_desverdizado"),
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
        ctx["lotes"] = []
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
