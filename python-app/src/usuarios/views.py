from django.shortcuts import render

from django.contrib.auth.views import LoginView, LogoutView

from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.generic import TemplateView

from django.urls import reverse_lazy


class CaliProLoginView(LoginView):

    """Login usando AuthenticationForm de Django + template personalizado."""

    template_name = "usuarios/login.html"

    redirect_authenticated_user = True

    def get_success_url(self):

        return reverse_lazy("usuarios:portal")


class CaliProLogoutView(LogoutView):

    next_page = reverse_lazy("usuarios:login")


class PortalView(LoginRequiredMixin, TemplateView):

    """Selector de módulo post-login."""

    template_name = "usuarios/portal.html"

    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):

        ctx = super().get_context_data(**kwargs)

        # Los módulos disponibles según rol del usuario

        ctx["modulos"] = self._get_modulos()

        return ctx

    def _get_modulos(self):

        return [

            {

                "nombre": "Producción Packing",

                "descripcion": "Flujo operativo de bins, lotes y pallets",

                "icono": "🍋",

                "url_name": "operaciones:dashboard",

                "disponible": True,

            },

            {

                "nombre": "Consulta Jefatura",

                "descripcion": "Seguimiento y trazabilidad de lotes",

                "icono": "📊",

                "url_name": "operaciones:consulta",

                "disponible": True,

            },

            {

                "nombre": "Frigorífico",

                "descripcion": "Cámaras de frío y temperaturas",

                "icono": "❄️",

                "disponible": False,

            },

        ]
