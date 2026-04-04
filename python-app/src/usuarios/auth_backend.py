"""
Backend de autenticación CaliPro.

Autentica contra crf21_usuariooperativos (Dataverse o SQLite según
PERSISTENCE_BACKEND). Compatible con LoginRequiredMixin y sesiones Django.

Flujo de autenticación:
    1. Busca el usuario por crf21_usernamelogin vía UsuarioRepository.
    2. Verifica la contraseña con check_password() sobre crf21_passwordhash.
    3. Rechaza si crf21_activo=False o crf21_bloqueado=True.
    4. Obtiene o crea un registro Django User (solo para sesión/middleware).
    5. Sincroniza is_staff e is_superuser desde crf21_rol.

La sesión con datos del perfil operativo (roles, codigooperador, etc.) se
almacena en store_user_session(), que debe llamarse desde CaliProLoginView
después del login exitoso.
"""
from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password

from usuarios.permissions import SESSION_KEY_ROL, SESSION_KEY_CODIGO_OPERADOR, \
    SESSION_KEY_USUARIO_ID, SESSION_KEY_ACTIVO, SESSION_KEY_BLOQUEADO, parsear_roles
from infrastructure.dataverse.auth import DataverseAuthError
from infrastructure.dataverse.client import DataverseAPIError

logger = logging.getLogger(__name__)
User = get_user_model()


class CaliProAuthBackend:
    """Backend de autenticación que verifica contra el repositorio de usuarios operativos."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        try:
            from usuarios.repositories import get_usuario_repository
            repo = get_usuario_repository()
            perfil = repo.get_by_username(username)
            if perfil is None:
                return None
            if not check_password(password, perfil.passwordhash):
                return None
            if not perfil.activo:
                logger.info("Login rechazado: usuario '%s' inactivo", username)
                return None
            if perfil.bloqueado:
                logger.info("Login rechazado: usuario '%s' bloqueado", username)
                return None

            django_user = self._get_or_create_django_user(perfil)
            # Adjuntamos perfil al objeto user para que CaliProLoginView
            # pueda leerlo en form_valid() sin un segundo query al repo.
            django_user._calipro_perfil = perfil
            return django_user

        except DataverseAuthError as exc:
            logger.error("Error de credenciales Dataverse para '%s': %s", username, exc)
            return None
        except DataverseAPIError as exc:
            logger.error("Error de API Dataverse para '%s': %s", username, exc)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error inesperado en CaliProAuthBackend.authenticate para '%s': %s", username, exc)
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def _get_or_create_django_user(self, perfil):
        """
        Obtiene o crea el usuario Django que Django auth necesita para la sesión.
        Sincroniza is_staff / is_superuser desde crf21_rol.
        No guarda la contraseña en Django (la fuente de verdad es passwordhash).
        """
        roles = parsear_roles(perfil.rol)
        flag_admin     = "Administrador" in roles
        flag_jefatura  = "Jefatura" in roles

        user, created = User.objects.get_or_create(
            username=perfil.usernamelogin,
            defaults={
                "first_name": perfil.nombrecompleto.split()[0] if perfil.nombrecompleto else "",
                "last_name":  " ".join(perfil.nombrecompleto.split()[1:]) if perfil.nombrecompleto else "",
                "email":        perfil.correo,
                "is_active":    perfil.activo,
                "is_staff":     flag_admin or flag_jefatura,
                "is_superuser": flag_admin,
                # Contraseña inutilizable: no se usa para auth, se usa CaliProAuthBackend
                "password":     "!unusable",
            }
        )
        if not created:
            needs_save = False
            if user.is_active != perfil.activo:
                user.is_active = perfil.activo
                needs_save = True
            if user.is_staff != (flag_admin or flag_jefatura):
                user.is_staff = flag_admin or flag_jefatura
                needs_save = True
            if user.is_superuser != flag_admin:
                user.is_superuser = flag_admin
                needs_save = True
            if needs_save:
                user.save(update_fields=["is_active", "is_staff", "is_superuser"])
        return user


def store_user_session(request, perfil) -> None:
    """
    Almacena datos del perfil operativo en la sesión Django post-login.
    Debe llamarse desde CaliProLoginView.form_valid() después de login().
    """
    request.session[SESSION_KEY_ROL]             = perfil.rol
    request.session[SESSION_KEY_CODIGO_OPERADOR] = perfil.codigooperador
    request.session[SESSION_KEY_USUARIO_ID]      = str(perfil.dataverse_id or perfil.id)
    request.session[SESSION_KEY_ACTIVO]          = perfil.activo
    request.session[SESSION_KEY_BLOQUEADO]       = perfil.bloqueado
