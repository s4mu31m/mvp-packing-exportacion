from django.shortcuts import render

# Create your views here.
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, FormView
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy

# Importar los use_cases y DTOs que YA existen en el proyecto

# (ajustar los imports según lo que realmente hay en application/use_cases/)

#from operaciones.application.dto import BinDTO, LoteDTO

# from operaciones.application.use_cases.registrar_bin import RegistrarBinRecibidoUseCase

# from operaciones.application.use_cases.crear_lote import CrearLoteRecepcionUseCase


class DashboardView(LoginRequiredMixin, TemplateView):

    template_name = "operaciones/dashboard.html"

    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):

        ctx = super().get_context_data(**kwargs)

        # TODO: llamar use_case para lotes activos cuando Dataverse esté configurado

        # Por ahora: datos mock mientras no hay Dataverse

        ctx["lotes_activos"] = self._mock_lotes()

        ctx["kpis"] = self._mock_kpis()

        ctx["page_title"] = "Dashboard — Turno Actual"

        return ctx

    def _mock_lotes(self):
        """Datos de ejemplo hasta conectar Dataverse."""

        return [

            {"codigo": "LP-2026-041", "variedad": "Thompson Seedless",

             "bins": 24, "peso_kg": 9840, "etapa": "Packing", "estado": "activo"},

            {"codigo": "LP-2026-040", "variedad": "Red Globe",

             "bins": 18, "peso_kg": 7290, "etapa": "Control", "estado": "activo"},

            {"codigo": "LP-2026-039", "variedad": "Crimson Seedless",

             "bins": 32, "peso_kg": 13440, "etapa": "Cámara Frío", "estado": "completado"},

        ]

    def _mock_kpis(self):

        return {

            "bins_recibidos": 84,

            "pallets_cerrados": 17,

            "lineas_activas": 6,

            "kg_procesados": 22400,

        }


class RecepcionView(LoginRequiredMixin, TemplateView):

    template_name = "operaciones/recepcion.html"

    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):

        ctx = super().get_context_data(**kwargs)

        ctx["page_title"] = "Recepción de Bins"

        ctx["lote_activo"] = {"codigo": "LP-2026-041"}

        ctx["bins_del_lote"] = []  # TODO: use_case

        return ctx

    def post(self, request, *args, **kwargs):
        """Registrar un bin — llamará al use_case cuando esté listo."""

        codigo = request.POST.get("codigo_bin", "")

        peso_bruto = request.POST.get("peso_bruto", 0)

        peso_tara = request.POST.get("peso_tara", 0)

        # TODO: llamar RegistrarBinRecibidoUseCase con estos datos

        # use_case = RegistrarBinRecibidoUseCase(repository=...)

        # resultado = use_case.execute(BinDTO(...))

        messages.success(request, f"Bin {codigo} registrado (modo demo).")

        return redirect("operaciones:recepcion")


class ConsultaJefaturaView(LoginRequiredMixin, TemplateView):

    template_name = "operaciones/consulta.html"

    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):

        ctx = super().get_context_data(**kwargs)

        ctx["page_title"] = "Consulta Jefatura"

        ctx["lotes"] = []  # TODO: use_case para listar lotes con filtros

        return ctx
