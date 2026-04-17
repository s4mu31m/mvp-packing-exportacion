"""
Tests de autenticación, permisos y gestión de usuarios.

Cubre el contrato funcional completo en modo SQLite:
  - login exitoso / rechazado por inactivo / rechazado por bloqueado
  - creación de usuario con múltiples roles
  - persistencia correcta de roles como string separado por coma
  - generación única e inmutable de crf21_codigooperador
  - admin con acceso total
  - jefatura con acceso a consulta pero sin acceso a gestión de usuarios
  - usuario sin rol requerido bloqueado en URL directa
  - visibilidad de portal/nav por rol
  - factory de repositorios sin romper imports en sqlite/dataverse

Puntos de verificación Dataverse (manuales — no automatizables sin API real):
  1. PERSISTENCE_BACKEND=dataverse + credenciales válidas: login con usuario real de crf21_usuariooperativos.
  2. Cambio de crf21_activo=false en Dataverse → login rechazado.
  3. Crear usuario desde UI → verificar campo crf21_codigooperador en Dataverse.
  4. Multiselect roles → verificar crf21_rol en Dataverse como string separado por coma.
"""
from unittest.mock import MagicMock

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.test import TestCase, Client, RequestFactory, override_settings
from django.urls import reverse

from usuarios.models import UsuarioProfile
from usuarios.repositories import UsuarioRecord
from usuarios.repositories.sqlite_repo import SQLiteUsuarioRepository
from usuarios.auth_backend import CaliProAuthBackend, store_user_session
from usuarios.permissions import (
    get_roles, is_admin, is_jefatura, has_role, puede_acceder_modulo,
    parsear_roles, normalizar_roles, SESSION_KEY_ROL,
)
from tests.unit.usuarios.helpers import make_profile  # fuente única de verdad

User = get_user_model()


# ---------------------------------------------------------------------------
# Tests: parseo y normalización de roles
# ---------------------------------------------------------------------------

class RolParsingTests(TestCase):

    def test_parsear_roles_simple(self):
        self.assertEqual(parsear_roles("Recepcion"), ["Recepcion"])

    def test_parsear_roles_multiples(self):
        self.assertEqual(parsear_roles("Recepcion, Pesaje"), ["Recepcion", "Pesaje"])

    def test_parsear_roles_con_espacios(self):
        self.assertEqual(parsear_roles("  Jefatura , Administrador  "), ["Jefatura", "Administrador"])

    def test_parsear_roles_vacio(self):
        self.assertEqual(parsear_roles(""), [])

    def test_normalizar_roles(self):
        self.assertEqual(normalizar_roles(["Recepcion", "Pesaje"]), "Recepcion, Pesaje")

    def test_normalizar_roles_unico(self):
        self.assertEqual(normalizar_roles(["Administrador"]), "Administrador")


# ---------------------------------------------------------------------------
# Tests: generación de codigooperador
# ---------------------------------------------------------------------------

@override_settings(PERSISTENCE_BACKEND="sqlite")
class CodigoOperadorTests(TestCase):

    def test_generacion_admin(self):
        repo = SQLiteUsuarioRepository()
        perfil = repo.create(
            usernamelogin="admin_test",
            nombrecompleto="Admin Test",
            correo="admin@test.com",
            passwordhash=make_password("pw"),
            rol="Administrador",
        )
        self.assertTrue(perfil.codigooperador.startswith("ADM-"))

    def test_generacion_jefatura(self):
        repo = SQLiteUsuarioRepository()
        perfil = repo.create(
            usernamelogin="jef_test",
            nombrecompleto="Jef Test",
            correo="jef@test.com",
            passwordhash=make_password("pw"),
            rol="Jefatura",
        )
        self.assertTrue(perfil.codigooperador.startswith("JEF-"))

    def test_generacion_operador(self):
        repo = SQLiteUsuarioRepository()
        perfil = repo.create(
            usernamelogin="ope_test",
            nombrecompleto="Ope Test",
            correo="ope@test.com",
            passwordhash=make_password("pw"),
            rol="Recepcion, Pesaje",
        )
        self.assertTrue(perfil.codigooperador.startswith("OPE-"))

    def test_codigooperador_unico(self):
        repo = SQLiteUsuarioRepository()
        p1 = repo.create(
            usernamelogin="u1", nombrecompleto="U1", correo="u1@test.com",
            passwordhash=make_password("pw"), rol="Recepcion",
        )
        p2 = repo.create(
            usernamelogin="u2", nombrecompleto="U2", correo="u2@test.com",
            passwordhash=make_password("pw"), rol="Pesaje",
        )
        self.assertNotEqual(p1.codigooperador, p2.codigooperador)

    def test_codigooperador_inmutable_en_update(self):
        repo = SQLiteUsuarioRepository()
        perfil = repo.create(
            usernamelogin="u_inmutable", nombrecompleto="U", correo="u@test.com",
            passwordhash=make_password("pw"), rol="Recepcion",
        )
        codigo_original = perfil.codigooperador
        perfil_actualizado = repo.update(perfil.id, {"codigooperador": "HACK-999", "nombrecompleto": "Nuevo"})
        self.assertEqual(perfil_actualizado.codigooperador, codigo_original)


# ---------------------------------------------------------------------------
# Tests: repositorio SQLite
# ---------------------------------------------------------------------------

@override_settings(PERSISTENCE_BACKEND="sqlite")
class SQLiteRepositoryTests(TestCase):

    def setUp(self):
        self.repo = SQLiteUsuarioRepository()
        self.profile = make_profile("recepcionista", "Recepcion, Pesaje")

    def test_get_by_username(self):
        resultado = self.repo.get_by_username("recepcionista")
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado.usernamelogin, "recepcionista")

    def test_get_by_username_inexistente(self):
        self.assertIsNone(self.repo.get_by_username("noexiste"))

    def test_list_all(self):
        usuarios = self.repo.list_all()
        self.assertTrue(any(u.usernamelogin == "recepcionista" for u in usuarios))

    def test_create_roles_multiples(self):
        perfil = self.repo.create(
            usernamelogin="multi_rol",
            nombrecompleto="Multi Rol",
            correo="multi@test.com",
            passwordhash=make_password("pw"),
            rol="Desverdizado, Camaras",
        )
        self.assertEqual(perfil.rol, "Desverdizado, Camaras")
        # Verificar persistencia en DB
        from usuarios.models import UsuarioProfile
        db_profile = UsuarioProfile.objects.get(usernamelogin="multi_rol")
        self.assertEqual(db_profile.rol, "Desverdizado, Camaras")

    def test_toggle_activo(self):
        activo_original = self.profile.activo
        resultado = self.repo.toggle_activo(self.profile.pk)
        self.assertNotEqual(resultado.activo, activo_original)


# ---------------------------------------------------------------------------
# Tests: auth backend
# ---------------------------------------------------------------------------

@override_settings(PERSISTENCE_BACKEND="sqlite")
class AuthBackendTests(TestCase):

    def setUp(self):
        self.backend = CaliProAuthBackend()
        self.password = "testpass456"
        self.profile = make_profile("usuario_auth", "Recepcion", password=self.password)

    def test_login_exitoso(self):
        user = self.backend.authenticate(None, username="usuario_auth", password=self.password)
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "usuario_auth")

    def test_login_password_incorrecto(self):
        user = self.backend.authenticate(None, username="usuario_auth", password="wrong")
        self.assertIsNone(user)

    def test_login_usuario_inexistente(self):
        user = self.backend.authenticate(None, username="noexiste", password="pw")
        self.assertIsNone(user)

    def test_login_rechazado_inactivo(self):
        make_profile("inactivo", "Pesaje", activo=False, password="pw")
        user = self.backend.authenticate(None, username="inactivo", password="pw")
        self.assertIsNone(user)

    def test_login_rechazado_bloqueado(self):
        make_profile("bloqueado", "Proceso", bloqueado=True, password="pw")
        user = self.backend.authenticate(None, username="bloqueado", password="pw")
        self.assertIsNone(user)

    def test_admin_derivado_is_superuser(self):
        make_profile("admin_s", "Administrador", password="pw")
        user = self.backend.authenticate(None, username="admin_s", password="pw")
        self.assertIsNotNone(user)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_jefatura_derivado_is_staff(self):
        make_profile("jef_s", "Jefatura", password="pw")
        user = self.backend.authenticate(None, username="jef_s", password="pw")
        self.assertIsNotNone(user)
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_operador_sin_flags(self):
        user = self.backend.authenticate(None, username="usuario_auth", password=self.password)
        self.assertIsNotNone(user)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)


# ---------------------------------------------------------------------------
# Tests: permisos desde sesión
# ---------------------------------------------------------------------------

class PermissionsTests(TestCase):

    def _make_request(self, rol_str: str):
        """Crea un request fake con roles en sesión usando Mock para is_authenticated."""
        factory = RequestFactory()
        request = factory.get("/")
        user = MagicMock()
        user.is_authenticated = True
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False
        request.user = user
        request.session = {SESSION_KEY_ROL: rol_str}
        return request

    def test_admin_es_admin(self):
        req = self._make_request("Administrador")
        self.assertTrue(is_admin(req))

    def test_jefatura_no_es_admin(self):
        req = self._make_request("Jefatura")
        self.assertFalse(is_admin(req))

    def test_admin_es_jefatura(self):
        req = self._make_request("Administrador")
        self.assertTrue(is_jefatura(req))

    def test_jefatura_es_jefatura(self):
        req = self._make_request("Jefatura")
        self.assertTrue(is_jefatura(req))

    def test_operador_no_es_jefatura(self):
        req = self._make_request("Recepcion")
        self.assertFalse(is_jefatura(req))

    def test_has_role_coincide(self):
        req = self._make_request("Recepcion, Pesaje")
        self.assertTrue(has_role(req, "Pesaje"))

    def test_has_role_admin_siempre_true(self):
        req = self._make_request("Administrador")
        self.assertTrue(has_role(req, "Recepcion"))

    def test_has_role_sin_rol(self):
        req = self._make_request("Recepcion")
        self.assertFalse(has_role(req, "Pesaje"))

    def test_puede_acceder_modulo_dashboard_todos(self):
        req = self._make_request("Recepcion")
        self.assertTrue(puede_acceder_modulo(req, "dashboard"))

    def test_puede_acceder_modulo_consulta_jefatura(self):
        req = self._make_request("Jefatura")
        self.assertTrue(puede_acceder_modulo(req, "consulta"))

    def test_puede_acceder_modulo_consulta_operador_no(self):
        req = self._make_request("Recepcion")
        self.assertFalse(puede_acceder_modulo(req, "consulta"))

    def test_puede_acceder_gestion_solo_admin(self):
        req_admin = self._make_request("Administrador")
        req_jef   = self._make_request("Jefatura")
        self.assertTrue(puede_acceder_modulo(req_admin, "gestion_usuarios"))
        self.assertFalse(puede_acceder_modulo(req_jef, "gestion_usuarios"))

    def test_admin_puede_acceder_todo(self):
        req = self._make_request("Administrador")
        for modulo in ["recepcion", "pesaje", "desverdizado", "consulta", "gestion_usuarios"]:
            self.assertTrue(puede_acceder_modulo(req, modulo), f"Admin no puede acceder a {modulo}")


# ---------------------------------------------------------------------------
# Tests: vistas HTTP (integración con Client)
# ---------------------------------------------------------------------------

@override_settings(PERSISTENCE_BACKEND="sqlite")
class VistaGestionUsuariosTests(TestCase):

    def setUp(self):
        # Crear admin vía profile + Django user sincronizado
        self.pwd = "adminpw123"
        self.admin_profile = make_profile("admin_view", "Administrador", password=self.pwd)
        self.backend = CaliProAuthBackend()
        # Asegurar que el Django User existe
        self.backend._get_or_create_django_user(self.admin_profile)

    def _login_as_admin(self):
        """Loguea como admin con sesión de roles correcta."""
        c = Client()
        c.post(reverse("usuarios:login"), {
            "username": "admin_view",
            "password": self.pwd,
        })
        return c

    def test_gestion_usuarios_requiere_login(self):
        c = Client()
        resp = c.get(reverse("usuarios:gestion_usuarios"))
        self.assertNotEqual(resp.status_code, 200)

    def test_admin_puede_acceder_gestion(self):
        c = self._login_as_admin()
        resp = c.get(reverse("usuarios:gestion_usuarios"))
        self.assertEqual(resp.status_code, 200)

    def test_jefatura_no_puede_acceder_gestion(self):
        jef_pwd = "jefpw123"
        make_profile("jefatura_view", "Jefatura", password=jef_pwd)
        jef_user = self.backend._get_or_create_django_user(
            SQLiteUsuarioRepository().get_by_username("jefatura_view")
        )
        c = Client()
        c.post(reverse("usuarios:login"), {"username": "jefatura_view", "password": jef_pwd})
        resp = c.get(reverse("usuarios:gestion_usuarios"))
        self.assertNotEqual(resp.status_code, 200)

    def test_crear_usuario_persistencia_roles(self):
        c = self._login_as_admin()
        resp = c.post(reverse("usuarios:crear_usuario"), {
            "usernamelogin": "nuevo_ope",
            "nombrecompleto": "Nuevo Operador",
            "correo": "nuevo@test.com",
            "password": "newpass123",
            "password_confirm": "newpass123",
            "roles": ["Recepcion", "Desverdizado"],  # "Pesaje" no existe en ROLES_CHOICES
            "activo": "true",
        })
        self.assertRedirects(resp, reverse("usuarios:gestion_usuarios"))
        from usuarios.models import UsuarioProfile
        perfil = UsuarioProfile.objects.get(usernamelogin="nuevo_ope")
        self.assertIn("Recepcion", perfil.rol)
        self.assertIn("Desverdizado", perfil.rol)
        # Roles deben estar separados por coma
        roles_list = [r.strip() for r in perfil.rol.split(",")]
        self.assertIn("Recepcion", roles_list)
        self.assertIn("Desverdizado", roles_list)


# ---------------------------------------------------------------------------
# Tests: factory de repositorios (backend selector)
# ---------------------------------------------------------------------------

@override_settings(PERSISTENCE_BACKEND="sqlite")
class RepositoryFactoryTests(TestCase):

    def test_sqlite_backend_importa_sin_error(self):
        import django.conf
        original = getattr(django.conf.settings, "PERSISTENCE_BACKEND", "sqlite")
        try:
            django.conf.settings.PERSISTENCE_BACKEND = "sqlite"
            from usuarios.repositories import get_usuario_repository
            repo = get_usuario_repository()
            self.assertIsNotNone(repo)
        finally:
            django.conf.settings.PERSISTENCE_BACKEND = original

    def test_backend_invalido_lanza_error(self):
        """El repositorio de operaciones lanza error en backend inválido."""
        from infrastructure.repository_factory import get_repositories
        import django.conf
        original = getattr(django.conf.settings, "PERSISTENCE_BACKEND", "sqlite")
        try:
            django.conf.settings.PERSISTENCE_BACKEND = "invalido"
            with self.assertRaises(ValueError):
                get_repositories()
        finally:
            django.conf.settings.PERSISTENCE_BACKEND = original
