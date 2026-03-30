"""
Vistas web del flujo operativo de packing.
Cada vista corresponde a una etapa del flujo.

Flujo de recepcion (preferido del MVP):
  RecepcionView — tres acciones: iniciar_lote / agregar_bin / cerrar_lote
  El lote activo se persiste en sesion como 'recepcion_lote_code'.

Flujo legacy (solo compatibilidad):
  PesajeView — conformacion de lote desde lista manual de bin_codes.
  Marcado como legacy; no es el flujo principal del MVP.
"""
import datetime

from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib import messages
from django.urls import reverse_lazy

from operaciones.forms import (
    BinForm,
    PesajeLoteForm,
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
    iniciar_lote_recepcion,
    agregar_bin_a_lote_abierto,
    cerrar_lote_recepcion,
    registrar_pesaje_lote,
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
from infrastructure.repository_factory import get_repositories


# Claves de sesion para el flujo de recepcion y pesaje
SESSION_LOTE_ACTIVO = "recepcion_lote_code"
SESSION_PESAJE_LOTE = "pesaje_lote_code"


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
        ctx["page_title"] = "Dashboard — Turno Actual"
        temporada = (
            self.request.session.get("temporada_activa")
            or str(datetime.date.today().year)
        )
        ctx["temporada"] = temporada

        try:
            repos = get_repositories()
            lotes_recientes = repos.lotes.list_recent(temporada, limit=10)
            ctx["lotes_recientes"] = lotes_recientes
            ctx["kpis"] = {
                "lotes_total": len(lotes_recientes),
                "lotes_abiertos": sum(1 for l in lotes_recientes if l.estado == "abierto"),
                "lotes_cerrados": sum(1 for l in lotes_recientes if l.estado == "cerrado"),
                "bins_total": sum(l.cantidad_bins for l in lotes_recientes),
            }
            ctx["backend_error"] = None
        except Exception as exc:
            ctx["lotes_recientes"] = []
            ctx["kpis"] = {"lotes_total": 0, "lotes_abiertos": 0, "lotes_cerrados": 0, "bins_total": 0}
            ctx["backend_error"] = str(exc)

        return ctx


# ---------------------------------------------------------------------------
# Recepcion de bins — flujo principal MVP (lote abierto)
# ---------------------------------------------------------------------------

class RecepcionView(LoginRequiredMixin, TemplateView):
    """
    Vista principal de recepcion con flujo de lote abierto.

    Acciones POST:
      action=iniciar_lote  — crea lote en estado 'abierto', guarda lote_code en sesion.
      action=agregar_bin   — registra bin y lo asocia al lote activo de la sesion.
      action=cerrar_lote   — cierra el lote activo y limpia la sesion.
    """
    template_name = "operaciones/recepcion.html"
    login_url = reverse_lazy("usuarios:login")

    def _get_lote_activo(self, request):
        """Retorna (lote_record, bins) del lote activo en sesion, o (None, [])."""
        lote_code = request.session.get(SESSION_LOTE_ACTIVO)
        if not lote_code:
            return None, []
        temporada = _temporada(request)
        try:
            repos = get_repositories()
            lote = repos.lotes.find_by_code(temporada, lote_code)
            if lote is None:
                # El lote ya no existe; limpiar sesion
                del request.session[SESSION_LOTE_ACTIVO]
                return None, []
            bins = repos.bins.list_by_lote(lote.id)
        except Exception:
            return None, []
        return lote, bins

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Recepcion de Bins"
        ctx["form_bin"] = BinForm()
        lote, bins = self._get_lote_activo(self.request)
        ctx["lote_activo"] = lote
        ctx["bins_del_lote"] = bins
        ctx["total_peso_neto"] = sum(
            (b.kilos_neto_ingreso or 0) for b in bins
        )
        return ctx

    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data(**kwargs)
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action", "")
        temporada = _temporada(request)

        if action == "iniciar_lote":
            return self._handle_iniciar_lote(request, temporada)
        elif action == "agregar_bin":
            return self._handle_agregar_bin(request, temporada)
        elif action == "cerrar_lote":
            return self._handle_cerrar_lote(request, temporada)
        else:
            messages.error(request, "Accion desconocida.")
            return redirect("operaciones:recepcion")

    def _handle_iniciar_lote(self, request, temporada):
        if request.session.get(SESSION_LOTE_ACTIVO):
            messages.warning(
                request,
                "Ya existe un lote activo en sesion. Cierre el lote actual antes de iniciar uno nuevo.",
            )
            return redirect("operaciones:recepcion")

        payload = {
            "temporada": temporada,
            "operator_code": request.POST.get("operator_code", "").strip(),
            "source_system": "web",
        }
        result = iniciar_lote_recepcion(payload)
        if result.ok:
            request.session[SESSION_LOTE_ACTIVO] = result.data["lote_code"]
            messages.success(request, f"Lote {result.data['lote_code']} iniciado. Puede comenzar a agregar bins.")
        else:
            for err in result.errors:
                messages.error(request, err)
        return redirect("operaciones:recepcion")

    def _handle_agregar_bin(self, request, temporada):
        lote_code = request.session.get(SESSION_LOTE_ACTIVO)
        if not lote_code:
            messages.error(request, "No hay lote activo. Inicie un lote antes de agregar bins.")
            return redirect("operaciones:recepcion")

        form = BinForm(request.POST)
        if not form.is_valid():
            lote, bins = self._get_lote_activo(request)
            ctx = {
                "page_title": "Recepcion de Bins",
                "form_bin": form,
                "lote_activo": lote,
                "bins_del_lote": bins,
                "total_peso_neto": sum((b.kilos_neto_ingreso or 0) for b in bins),
            }
            messages.error(request, "Formulario de bin invalido. Revise los campos.")
            return render(request, self.template_name, ctx)

        cd = form.cleaned_data
        payload = {
            "temporada": temporada,
            "lote_code": lote_code,
            "operator_code": cd.get("operator_code", ""),
            "source_system": "web",
            "codigo_productor": cd.get("codigo_productor") or "",
            "tipo_cultivo": cd.get("tipo_cultivo") or "",
            "variedad_fruta": cd.get("variedad_fruta") or "",
            "numero_cuartel": cd.get("numero_cuartel") or "",
            "fecha_cosecha": str(cd["fecha_cosecha"]) if cd.get("fecha_cosecha") else None,
            "hora_recepcion": cd.get("hora_recepcion") or "",
            "kilos_bruto_ingreso": str(cd["kilos_bruto_ingreso"]) if cd.get("kilos_bruto_ingreso") else None,
            "kilos_neto_ingreso": str(cd["kilos_neto_ingreso"]) if cd.get("kilos_neto_ingreso") else None,
            "a_o_r": cd.get("a_o_r") or None,
            "observaciones": cd.get("observaciones") or "",
        }
        result = agregar_bin_a_lote_abierto(payload)
        if result.ok:
            messages.success(request, result.message)
        else:
            for err in result.errors:
                messages.error(request, err)
        return redirect("operaciones:recepcion")

    def _handle_cerrar_lote(self, request, temporada):
        lote_code = request.session.get(SESSION_LOTE_ACTIVO)
        if not lote_code:
            messages.error(request, "No hay lote activo para cerrar.")
            return redirect("operaciones:recepcion")

        payload = {
            "temporada": temporada,
            "lote_code": lote_code,
            "operator_code": request.POST.get("operator_code", "").strip(),
            "source_system": "web",
        }
        result = cerrar_lote_recepcion(payload)
        if result.ok:
            del request.session[SESSION_LOTE_ACTIVO]
            request.session[SESSION_PESAJE_LOTE] = lote_code
            messages.success(
                request,
                f"Lote {lote_code} cerrado con {result.data['cantidad_bins']} bin(s). "
                "Registre el pesaje del lote.",
            )
            return redirect("operaciones:pesaje")
        for err in result.errors:
            messages.error(request, err)
        return redirect("operaciones:recepcion")


# ---------------------------------------------------------------------------
# Pesaje de lote — segundo paso del flujo MVP post-recepcion
# ---------------------------------------------------------------------------

class PesajeView(LoginRequiredMixin, TemplateView):
    """
    Pesaje del lote cerrado: registra kilos bruto/neto y define si requiere desverdizado.
    Se accede automaticamente al cerrar un lote en RecepcionView.
    El lote pendiente de pesaje se persiste en sesion como SESSION_PESAJE_LOTE.
    """
    template_name = "operaciones/pesaje.html"
    login_url = reverse_lazy("usuarios:login")

    def _get_lote_y_bins(self, request):
        """Retorna (lote_record, bins) del lote pendiente de pesaje, o (None, [])."""
        lote_code = request.session.get(SESSION_PESAJE_LOTE)
        if not lote_code:
            return None, []
        temporada = _temporada(request)
        try:
            repos = get_repositories()
            lote = repos.lotes.find_by_code(temporada, lote_code)
            if lote is None:
                del request.session[SESSION_PESAJE_LOTE]
                return None, []
            bins = repos.bins.list_by_lote(lote.id)
        except Exception:
            return None, []
        return lote, bins

    def _build_context(self, request, form=None):
        lote, bins = self._get_lote_y_bins(request)
        primer_bin = bins[0] if bins else None
        return {
            "page_title": "Pesaje de Lote",
            "lote": lote,
            "bins": bins,
            "fecha_cosecha": primer_bin.fecha_cosecha if primer_bin else None,
            "color": primer_bin.color if primer_bin else "",
            "form": form or PesajeLoteForm(),
        }

    def get(self, request, *args, **kwargs):
        ctx = self._build_context(request)
        if not ctx["lote"]:
            messages.info(request, "No hay lote pendiente de pesaje. Cierre un lote desde Recepcion.")
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        lote_code = request.session.get(SESSION_PESAJE_LOTE)
        if not lote_code:
            messages.error(request, "No hay lote pendiente de pesaje.")
            return redirect("operaciones:recepcion")

        form = PesajeLoteForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Formulario invalido. Revise los campos.")
            ctx = self._build_context(request, form=form)
            return render(request, self.template_name, ctx)

        cd = form.cleaned_data
        payload = {
            "temporada": _temporada(request),
            "lote_code": lote_code,
            "kilos_bruto_conformacion": str(cd["kilos_bruto_conformacion"]),
            "kilos_neto_conformacion":  str(cd["kilos_neto_conformacion"]),
            "requiere_desverdizado":    cd.get("requiere_desverdizado", False),
            "operator_code": cd.get("operator_code", ""),
            "source_system": "web",
        }
        result = registrar_pesaje_lote(payload)
        if result.ok:
            del request.session[SESSION_PESAJE_LOTE]
            messages.success(request, result.message)
            return redirect("operaciones:desverdizado")
        for err in result.errors:
            messages.error(request, err)
        ctx = self._build_context(request, form=form)
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
