"""
Vistas de usuarios — autenticación, portal y gestión.

Fuente de verdad de permisos: usuarios/permissions.py (roles desde sesión).
La persistencia de usuarios usa UsuarioRepository (SQLite o Dataverse).
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView, View

from .forms import UsuarioCreacionForm, ROLES_CHOICES
from .permissions import is_admin, is_jefatura, get_roles


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class CaliProLoginView(LoginView):
    """
    Login usando AuthenticationForm de Django.
    CaliProAuthBackend (registrado en AUTHENTICATION_BACKENDS) verifica
    la contraseña contra crf21_passwordhash y rechaza inactivos/bloqueados.
    Tras el login, almacena datos del perfil operativo en sesión.
    """
    template_name = "usuarios/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("usuarios:portal")

    def form_valid(self, form):
        """Llama login() estándar; luego almacena el perfil operativo en sesión."""
        response = super().form_valid(form)
        try:
            from usuarios.repositories import get_usuario_repository
            from usuarios.auth_backend import store_user_session
            repo = get_usuario_repository()
            perfil = repo.get_by_username(self.request.user.username)
            if perfil:
                store_user_session(self.request, perfil)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "No se pudo cargar perfil post-login para '%s': %s",
                self.request.user.username, exc,
            )
        return response


class CaliProLogoutView(LogoutView):
    next_page = reverse_lazy("usuarios:login")


# ---------------------------------------------------------------------------
# Portal
# ---------------------------------------------------------------------------

class PortalView(LoginRequiredMixin, TemplateView):
    """Selector de módulo post-login. Módulos filtrados por rol real."""
    template_name = "usuarios/portal.html"
    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request = self.request
        ctx["modulos"]    = self._get_modulos(request)
        ctx["es_admin"]   = is_admin(request)
        ctx["es_jefatura"] = is_jefatura(request)
        return ctx

    def _get_modulos(self, request):
        modulos = [
            {
                "nombre":      "Producción Packing",
                "descripcion": "Flujo operativo de bins, lotes y pallets",
                "icono":       "🍋",
                "url_name":    "operaciones:dashboard",
                "disponible":  True,
                "rol_requerido": None,
            },
        ]
        if is_jefatura(request):
            modulos.append({
                "nombre":      "Consulta Jefatura",
                "descripcion": "Seguimiento, trazabilidad y exportación de lotes",
                "icono":       "📊",
                "url_name":    "operaciones:consulta",
                "disponible":  True,
                "rol_requerido": "Jefatura / Administrador",
            })
        if is_admin(request):
            modulos.append({
                "nombre":      "Gestión de Usuarios",
                "descripcion": "Crear y administrar usuarios del sistema",
                "icono":       "👥",
                "url_name":    "usuarios:gestion_usuarios",
                "disponible":  True,
                "rol_requerido": "Administrador",
            })
        modulos.append({
            "nombre":      "Frigorífico",
            "descripcion": "Cámaras de frío y control de temperaturas",
            "icono":       "❄️",
            "disponible":  False,
            "rol_requerido": None,
        })
        return modulos


# ---------------------------------------------------------------------------
# Mixins de acceso
# ---------------------------------------------------------------------------

class AdminRequiredMixin(UserPassesTestMixin):
    """Restringe el acceso a usuarios con rol Administrador."""
    def test_func(self):
        return is_admin(self.request)

    def handle_no_permission(self):
        messages.error(self.request, "Acceso denegado: se requiere rol Administrador.")
        return redirect("usuarios:portal")


class RolRequiredMixin(UserPassesTestMixin):
    """
    Mixin reutilizable para proteger vistas por rol de negocio.
    Subclases deben declarar `roles_requeridos = ["Pesaje", "Proceso"]`.
    """
    roles_requeridos: list[str] = []

    def test_func(self):
        if is_admin(self.request):
            return True
        user_roles = get_roles(self.request)
        return any(r in user_roles for r in self.roles_requeridos)

    def handle_no_permission(self):
        requeridos = ", ".join(self.roles_requeridos) or "desconocido"
        messages.error(
            self.request,
            f"Acceso denegado: se requiere rol [{requeridos}].",
        )
        return redirect("usuarios:portal")


# ---------------------------------------------------------------------------
# Gestión de usuarios — solo administradores
# ---------------------------------------------------------------------------

class GestionUsuariosView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Lista de usuarios con formulario de creación."""
    template_name = "usuarios/gestion_usuarios.html"
    login_url = reverse_lazy("usuarios:login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from usuarios.repositories import get_usuario_repository
        repo = get_usuario_repository()
        ctx["page_title"]    = "Gestión de Usuarios"
        ctx["usuarios"]      = repo.list_all()
        ctx["form"]          = UsuarioCreacionForm()
        ctx["roles_choices"] = ROLES_CHOICES
        return ctx


class CrearUsuarioView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Procesa la creación de un nuevo usuario operativo."""
    login_url = reverse_lazy("usuarios:login")

    def post(self, request):
        form = UsuarioCreacionForm(request.POST)
        if form.is_valid():
            from usuarios.repositories import get_usuario_repository
            from usuarios.auth_backend import CaliProAuthBackend
            repo = get_usuario_repository()

            username = form.cleaned_data["usernamelogin"]
            if repo.get_by_username(username):
                messages.error(request, f"Ya existe un usuario con login '{username}'.")
                return redirect("usuarios:gestion_usuarios")

            perfil = repo.create(
                usernamelogin=username,
                nombrecompleto=form.cleaned_data.get("nombrecompleto", ""),
                correo=form.cleaned_data.get("correo", ""),
                passwordhash=form.get_passwordhash(),
                rol=form.get_rol_string(),
                activo=bool(form.cleaned_data.get("activo", True)),
                bloqueado=bool(form.cleaned_data.get("bloqueado", False)),
            )
            # Sincronizar Django User para compatibilidad de sesión
            CaliProAuthBackend()._get_or_create_django_user(perfil)

            messages.success(
                request,
                f"Usuario '{perfil.usernamelogin}' creado. Código: {perfil.codigooperador}",
            )
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f"{field}: {err}")
        return redirect("usuarios:gestion_usuarios")


class ToggleUsuarioActivoView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Alterna crf21_activo de un usuario (activo ↔ inactivo)."""
    login_url = reverse_lazy("usuarios:login")

    def post(self, request, pk):
        from usuarios.repositories import get_usuario_repository
        from django.contrib.auth import get_user_model
        repo = get_usuario_repository()
        try:
            perfil = repo.get_by_id(pk)
            if perfil is None:
                messages.error(request, "Usuario no encontrado.")
                return redirect("usuarios:gestion_usuarios")
            if perfil.usernamelogin == request.user.username:
                messages.error(request, "No puedes desactivar tu propio usuario.")
                return redirect("usuarios:gestion_usuarios")

            perfil = repo.toggle_activo(pk)

            # Sincronizar flag is_active en Django User
            User = get_user_model()
            try:
                django_user = User.objects.get(username=perfil.usernamelogin)
                if django_user.is_active != perfil.activo:
                    django_user.is_active = perfil.activo
                    django_user.save(update_fields=["is_active"])
            except User.DoesNotExist:
                pass

            estado = "activado" if perfil.activo else "desactivado"
            messages.success(request, f"Usuario '{perfil.usernamelogin}' {estado}.")
        except Exception as exc:
            messages.error(request, f"Error al actualizar usuario: {exc}")
        return redirect("usuarios:gestion_usuarios")
