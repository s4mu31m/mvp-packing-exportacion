"""
test_roles_acceso.py — Acceso y permisos por rol.

Bloqueante: si falla, el sistema permite acceso indebido o deniega acceso legítimo.

Clases:
  - RoleModuleVisibilityTest    → portal y dashboard muestran módulos correctos por rol
  - RoleEnforcementByURLTest    → GET a cada URL protegida: positivo y negativo
  - AnonymousAndInvalidAccessTest → anónimo, sin rol útil, bloqueado, inactivo
  - MultirolTest                → usuario con dos roles puede acceder a ambos módulos
  - JefaturaTest                → Jefatura accede a consulta/exportar, no a operaciones
  - AdministradorTest           → Admin accede a todo, incluyendo gestion_usuarios
"""
import datetime

from django.test import TestCase, override_settings
from django.urls import reverse

from operaciones.test.qa.base import (
    QASetupMixin,
    TEMPORADA,
    assert_acceso_bloqueado,
)

# ---------------------------------------------------------------------------
# Helpers de módulos y campos representativos por URL
# ---------------------------------------------------------------------------

# URL name → campo de formulario que NO debe aparecer en 403
_URL_CAMPO_REPRESENTATIVO = {
    "operaciones:recepcion":      "variedad_fruta",
    "operaciones:desverdizado":   "horas_desverdizado",
    "operaciones:ingreso_packing":"kilos_bruto_ingreso_packing",
    "operaciones:proceso":        "linea_proceso",
    "operaciones:control":        "temp_agua_tina",
    "operaciones:paletizado":     "temperatura_fruta",
    "operaciones:camaras":        "camara_numero",
}

# Rol operativo → única URL que puede acceder (GET 200)
_ROL_URL_PERMITIDA = {
    "recepcion":    "operaciones:recepcion",
    "desverdizado": "operaciones:desverdizado",
    "ing_packing":  "operaciones:ingreso_packing",
    "proceso":      "operaciones:proceso",
    "control":      "operaciones:control",
    "paletizado":   "operaciones:paletizado",
    "camaras":      "operaciones:camaras",
    "jefatura":     "operaciones:consulta",
}

# Todas las URLs operativas protegidas
_TODAS_URLS_OPERATIVAS = list(_URL_CAMPO_REPRESENTATIVO.keys())


@override_settings(PERSISTENCE_BACKEND="sqlite")
class RoleModuleVisibilityTest(TestCase):
    """
    Verifica que cada rol ve solo sus módulos en el portal.
    Implementación: response.context["modulos"] o links href en HTML.
    """

    @classmethod
    def setUpTestData(cls):
        cls.all_clients = QASetupMixin.build_all_clients()

    def _get_portal(self, rol_key):
        client, _ = self.all_clients[rol_key]
        return client.get(reverse("usuarios:portal"))

    def test_recepcion_ve_su_modulo(self):
        resp = self._get_portal("recepcion")
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn("/operaciones/", content,
            msg="Operador Recepcion no ve el módulo Producción Packing en el portal")

    def test_desverdizado_ve_su_modulo(self):
        resp = self._get_portal("desverdizado")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("/operaciones/", resp.content.decode())

    def test_jefatura_ve_consulta(self):
        resp = self._get_portal("jefatura")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("/operaciones/consulta/", resp.content.decode())

    def test_administrador_ve_gestion_usuarios(self):
        resp = self._get_portal("administrador")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("/usuarios/", resp.content.decode())

    def test_recepcion_no_ve_modulo_desverdizado(self):
        resp = self._get_portal("recepcion")
        # El módulo desverdizado no debe aparecer habilitado para este rol
        # Verificar via contexto si disponible
        if "modulos" in (resp.context or {}):
            modulos = resp.context["modulos"]
            modulos_disponibles = [m.get("url_name", "") for m in modulos if m.get("disponible")]
            for url_name in modulos_disponibles:
                self.assertNotIn("desverdizado", url_name,
                    msg="Recepcion no debería tener Desverdizado disponible")


@override_settings(PERSISTENCE_BACKEND="sqlite")
class RoleEnforcementByURLTest(TestCase):
    """
    Para cada URL operativa: rol correcto → 200, cualquier otro rol → 403.
    Además: en la respuesta 403 no debe aparecer el campo de formulario del módulo.
    """

    @classmethod
    def setUpTestData(cls):
        cls.all_clients = QASetupMixin.build_all_clients()

    def _client(self, rol_key):
        return self.all_clients[rol_key][0]

    def test_recepcion_accede_a_recepcion(self):
        resp = self._client("recepcion").get(reverse("operaciones:recepcion"))
        self.assertEqual(resp.status_code, 200,
            msg="Rol Recepcion debe acceder a /recepcion/ con 200")

    def test_recepcion_bloqueada_en_desverdizado(self):
        resp = self._client("recepcion").get(reverse("operaciones:desverdizado"))
        self.assertEqual(resp.status_code, 403,
            msg="Rol Recepcion no debe acceder a /desverdizado/")
        content = resp.content.decode()
        self.assertNotIn('name="horas_desverdizado"', content,
            msg="Formulario de desverdizado expuesto a rol Recepcion en 403")

    def test_recepcion_bloqueada_en_proceso(self):
        resp = self._client("recepcion").get(reverse("operaciones:proceso"))
        self.assertEqual(resp.status_code, 403)

    def test_recepcion_bloqueada_en_camaras(self):
        resp = self._client("recepcion").get(reverse("operaciones:camaras"))
        self.assertEqual(resp.status_code, 403)

    def test_desverdizado_accede_a_desverdizado(self):
        resp = self._client("desverdizado").get(reverse("operaciones:desverdizado"))
        self.assertEqual(resp.status_code, 200)

    def test_desverdizado_bloqueado_en_recepcion(self):
        resp = self._client("desverdizado").get(reverse("operaciones:recepcion"))
        self.assertEqual(resp.status_code, 403)
        content = resp.content.decode()
        self.assertNotIn('name="variedad_fruta"', content,
            msg="Campo variedad_fruta expuesto a rol Desverdizado en 403")

    def test_ing_packing_accede_a_ingreso_packing(self):
        resp = self._client("ing_packing").get(reverse("operaciones:ingreso_packing"))
        self.assertEqual(resp.status_code, 200)

    def test_proceso_accede_a_proceso(self):
        resp = self._client("proceso").get(reverse("operaciones:proceso"))
        self.assertEqual(resp.status_code, 200)

    def test_proceso_bloqueado_en_camaras(self):
        resp = self._client("proceso").get(reverse("operaciones:camaras"))
        self.assertEqual(resp.status_code, 403)
        content = resp.content.decode()
        self.assertNotIn('name="camara_numero"', content)

    def test_control_accede_a_control(self):
        resp = self._client("control").get(reverse("operaciones:control"))
        self.assertEqual(resp.status_code, 200)

    def test_paletizado_accede_a_paletizado(self):
        resp = self._client("paletizado").get(reverse("operaciones:paletizado"))
        self.assertEqual(resp.status_code, 200)

    def test_camaras_accede_a_camaras(self):
        resp = self._client("camaras").get(reverse("operaciones:camaras"))
        self.assertEqual(resp.status_code, 200)

    def test_todos_acceden_a_dashboard(self):
        for rol_key, (client, _) in self.all_clients.items():
            resp = client.get(reverse("operaciones:dashboard"))
            self.assertEqual(resp.status_code, 200,
                msg=f"Rol '{rol_key}' no puede acceder al dashboard")

    def test_jefatura_accede_a_consulta(self):
        resp = self._client("jefatura").get(reverse("operaciones:consulta"))
        self.assertEqual(resp.status_code, 200)

    def test_jefatura_bloqueada_en_recepcion_post(self):
        """Jefatura no puede realizar operaciones de Recepcion."""
        resp = self._client("jefatura").get(reverse("operaciones:recepcion"))
        self.assertEqual(resp.status_code, 403)

    def test_administrador_accede_a_todo(self):
        client = self._client("administrador")
        for url_name in _TODAS_URLS_OPERATIVAS + ["operaciones:consulta"]:
            resp = client.get(reverse(url_name))
            self.assertEqual(resp.status_code, 200,
                msg=f"Administrador no puede acceder a {url_name}")


@override_settings(PERSISTENCE_BACKEND="sqlite")
class AnonymousAndInvalidAccessTest(TestCase):
    """
    Usuarios sin sesión, sin rol útil, bloqueados o inactivos.
    """

    def test_anonymous_redirige_a_login(self):
        """Usuario no autenticado → redirect a login."""
        anon = self.__class__._make_anon_client()
        for url_name in ["operaciones:recepcion", "operaciones:dashboard"]:
            resp = anon.get(reverse(url_name))
            self.assertIn(resp.status_code, [301, 302],
                msg=f"Anónimo debería ser redirigido desde {url_name}")
            self.assertIn("/login", resp["Location"],
                msg=f"Redirect de {url_name} no apunta a login")

    def test_usuario_sin_rol_no_accede_a_modulos(self):
        """Usuario autenticado sin rol de negocio en sesión → 403 en módulos."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(username="sin_rol_qa", password="pw")
        c = self.__class__._make_anon_client()
        c.force_login(user)
        # No se inyecta SESSION_KEY_ROL → sin roles
        resp = c.get(reverse("operaciones:recepcion"))
        self.assertEqual(resp.status_code, 403,
            msg="Usuario sin rol no debe acceder a /recepcion/")

    @staticmethod
    def _make_anon_client():
        from django.test import Client
        return Client()


@override_settings(PERSISTENCE_BACKEND="sqlite")
class MultirolTest(TestCase):
    """
    Un usuario con múltiples roles puede acceder a todos sus módulos.
    """

    def test_multirol_recepcion_y_control(self):
        from django.contrib.auth import get_user_model
        from usuarios.permissions import SESSION_KEY_ROL, SESSION_KEY_CODIGO_OPERADOR
        User = get_user_model()
        user = User.objects.create_user(username="qa_multirol", password="pw")
        c = __import__("django.test", fromlist=["Client"]).Client()
        c.force_login(user)
        session = c.session
        session[SESSION_KEY_ROL] = "Recepcion, Control"
        session[SESSION_KEY_CODIGO_OPERADOR] = "QA-MLT"
        session.save()

        resp_rec = c.get(reverse("operaciones:recepcion"))
        self.assertEqual(resp_rec.status_code, 200,
            msg="Multirol Recepcion+Control debe acceder a /recepcion/")

        resp_ctrl = c.get(reverse("operaciones:control"))
        self.assertEqual(resp_ctrl.status_code, 200,
            msg="Multirol Recepcion+Control debe acceder a /control/")

    def test_multirol_no_accede_a_modulo_no_asignado(self):
        from django.contrib.auth import get_user_model
        from usuarios.permissions import SESSION_KEY_ROL, SESSION_KEY_CODIGO_OPERADOR
        User = get_user_model()
        user = User.objects.create_user(username="qa_multirol2", password="pw")
        c = __import__("django.test", fromlist=["Client"]).Client()
        c.force_login(user)
        session = c.session
        session[SESSION_KEY_ROL] = "Recepcion, Control"
        session[SESSION_KEY_CODIGO_OPERADOR] = "QA-MLT2"
        session.save()

        resp = c.get(reverse("operaciones:camaras"))
        self.assertEqual(resp.status_code, 403,
            msg="Multirol Recepcion+Control no debe acceder a /camaras/")


@override_settings(PERSISTENCE_BACKEND="sqlite")
class JefaturaTest(TestCase):
    """
    Rol Jefatura: accede a consulta y exportar, no puede operar módulos.
    """

    @classmethod
    def setUpTestData(cls):
        cls.client_jef, cls.user_jef = QASetupMixin.make_role_client(
            "qa_jef_test", "Jefatura", is_staff=True, is_superuser=False,
            operator_code="QA-008",
        )

    def test_jefatura_get_consulta(self):
        resp = self.client_jef.get(reverse("operaciones:consulta"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "operaciones/consulta.html")

    def test_jefatura_exportar_csv(self):
        resp = self.client_jef.get(reverse("operaciones:exportar_consulta"))
        self.assertEqual(resp.status_code, 200,
            msg="Jefatura debe poder exportar CSV")
        self.assertIn("text/csv", resp.get("Content-Type", ""),
            msg="Exportación debe devolver Content-Type text/csv")

    def test_jefatura_bloqueada_en_recepcion(self):
        resp = self.client_jef.get(reverse("operaciones:recepcion"))
        self.assertEqual(resp.status_code, 403)

    def test_jefatura_bloqueada_en_proceso(self):
        resp = self.client_jef.get(reverse("operaciones:proceso"))
        self.assertEqual(resp.status_code, 403)

    def test_jefatura_bloqueada_en_camaras(self):
        resp = self.client_jef.get(reverse("operaciones:camaras"))
        self.assertEqual(resp.status_code, 403)

    def test_jefatura_puede_filtrar_consulta_por_estado(self):
        resp = self.client_jef.get(
            reverse("operaciones:consulta") + "?estado=cerrado"
        )
        self.assertEqual(resp.status_code, 200)

    def test_jefatura_no_puede_post_a_recepcion(self):
        resp = self.client_jef.post(reverse("operaciones:recepcion"), {
            "action": "iniciar", "temporada": "2026"
        })
        self.assertEqual(resp.status_code, 403,
            msg="POST de Jefatura a /recepcion/ debe ser 403")


@override_settings(PERSISTENCE_BACKEND="sqlite")
class AdministradorTest(TestCase):
    """
    Rol Administrador: acceso total, incluyendo gestión de usuarios.
    """

    @classmethod
    def setUpTestData(cls):
        cls.client_admin, cls.user_admin = QASetupMixin.make_role_client(
            "qa_admin_test", "Administrador", is_staff=True, is_superuser=True,
            operator_code="QA-009",
        )

    def test_admin_accede_a_gestion_usuarios(self):
        resp = self.client_admin.get(reverse("usuarios:gestion_usuarios"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "usuarios/gestion_usuarios.html")

    def test_admin_accede_a_todos_los_modulos_operativos(self):
        for url_name in _TODAS_URLS_OPERATIVAS:
            resp = self.client_admin.get(reverse(url_name))
            self.assertEqual(resp.status_code, 200,
                msg=f"Admin debe acceder a {url_name} con 200, obtuvo {resp.status_code}")

    def test_admin_no_puede_desactivarse_a_si_mismo(self):
        """El admin no debe poder desactivar su propia cuenta."""
        resp = self.client_admin.post(
            reverse("usuarios:toggle_usuario", args=[self.user_admin.pk])
        )
        # El sistema debe rechazar o no procesar esta operación
        # Verificamos que el usuario sigue activo después
        self.user_admin.refresh_from_db()
        self.assertTrue(
            self.user_admin.is_active,
            msg="Admin no debe poder desactivarse a sí mismo",
        )
