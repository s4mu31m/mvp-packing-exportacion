from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import TemplateView, View

from .forms import CaliProUserCreationForm, CaliProUserEditForm

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers de permisos — fuente única de verdad para roles
# ---------------------------------------------------------------------------

def es_administrador(user):
    """Superusuario: acceso completo, gestión de usuarios."""
    return user.is_active and user.is_superuser


def es_jefatura(user):
    """Staff o superusuario: acceso a consulta y exportación."""
    return user.is_active and (user.is_staff or user.is_superuser)


def es_operador(user):
    """Cualquier usuario autenticado y activo."""
    return user.is_active


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class CaliProLoginView(LoginView):
    """Login usando AuthenticationForm de Django + template personalizado."""
    template_name = "usuarios/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("usuarios:portal")


class CaliProLogoutView(LogoutView):
    next_page = reverse_lazy("usuarios:login")


# ---------------------------------------------------------------------------
# Portal
# ---------------------------------------------------------------------------

class PortalView(LoginRequiredMixin, TemplateView):
    """Selector de módulo post-login. Navegación diferenciada por rol."""
    template_name = "usuarios/portal.html"
    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["modulos"] = self._get_modulos(user)
        ctx["es_admin"] = es_administrador(user)
        ctx["es_jefatura"] = es_jefatura(user)
        return ctx

    def _get_modulos(self, user):
        modulos = []

        # Todos los usuarios autenticados ven el flujo operativo
        modulos.append({
            "nombre": "Producción Packing",
            "descripcion": "Flujo operativo de bins, lotes y pallets",
            "icono": "🍋",
            "url_name": "operaciones:dashboard",
            "disponible": True,
            "rol_requerido": None,
        })

        # Jefatura y administradores ven consulta
        if es_jefatura(user):
            modulos.append({
                "nombre": "Consulta Jefatura",
                "descripcion": "Seguimiento, trazabilidad y exportación de lotes",
                "icono": "📊",
                "url_name": "operaciones:consulta",
                "disponible": True,
                "rol_requerido": "Jefatura / Admin",
            })

        # Solo administradores ven gestión de usuarios
        if es_administrador(user):
            modulos.append({
                "nombre": "Gestión de Usuarios",
                "descripcion": "Crear y administrar usuarios del sistema",
                "icono": "👥",
                "url_name": "usuarios:gestion_usuarios",
                "disponible": True,
                "rol_requerido": "Administrador",
            })

        # Módulo futuro — visible para todos como referencia
        modulos.append({
            "nombre": "Frigorífico",
            "descripcion": "Cámaras de frío y control de temperaturas",
            "icono": "❄️",
            "disponible": False,
            "rol_requerido": None,
        })

        return modulos


# ---------------------------------------------------------------------------
# Gestión de usuarios — solo administradores
# ---------------------------------------------------------------------------

class AdminRequiredMixin(UserPassesTestMixin):
    """Restringe el acceso a superusuarios (administradores)."""
    def test_func(self):
        return es_administrador(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "Acceso denegado: se requiere rol de administrador.")
        return redirect("usuarios:portal")


class GestionUsuariosView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Lista de usuarios con opción de crear nuevos."""
    template_name = "usuarios/gestion_usuarios.html"
    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Gestión de Usuarios"
        ctx["usuarios"] = User.objects.all().order_by("username")
        ctx["form"] = CaliProUserCreationForm()
        return ctx


class CrearUsuarioView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Procesa la creación de un nuevo usuario."""
    login_url = reverse_lazy("usuarios:login")

    def post(self, request):
        form = CaliProUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f"Usuario '{user.username}' creado correctamente.",
            )
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f"{field}: {err}")
        return redirect("usuarios:gestion_usuarios")


class ToggleUsuarioActivoView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Activa o desactiva un usuario."""
    login_url = reverse_lazy("usuarios:login")

    def post(self, request, pk):
        try:
            usuario = User.objects.get(pk=pk)
            if usuario == request.user:
                messages.error(request, "No puedes desactivar tu propio usuario.")
            else:
                usuario.is_active = not usuario.is_active
                usuario.save(update_fields=["is_active"])
                estado = "activado" if usuario.is_active else "desactivado"
                messages.success(request, f"Usuario '{usuario.username}' {estado}.")
        except User.DoesNotExist:
            messages.error(request, "Usuario no encontrado.")
        return redirect("usuarios:gestion_usuarios")
