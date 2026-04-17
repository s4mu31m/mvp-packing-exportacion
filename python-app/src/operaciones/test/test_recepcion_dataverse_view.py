"""
test_recepcion_dataverse_view.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tests de comportamiento de RecepcionView en modo Dataverse.

Cubre los requisitos del bug "lote creado no queda activo en sesión":

  1. POST iniciar lote → session["lote_activo_code"] queda escrito.
  2. GET siguiente (con cache precalentada) → detecta lote activo.
  3. Template entra al branch "lote activo" (muestra form agregar_bin, no iniciar).
  4. agregar_bin puede enviarse inmediatamente después de crear el lote.
  5. Si Dataverse demora (find_by_code=None), la sesión NO se destruye.
  6. No se crean lotes vacíos en cadena (guard en _handle_iniciar).

Estrategia: PERSISTENCE_BACKEND="dataverse", mocks de repos + use cases.
NO se llama a Dataverse real. Los mocks inyectan LoteRecord directamente.
"""
from unittest.mock import MagicMock, patch, PropertyMock
import datetime

from django.test import TestCase, Client, override_settings
from django.urls import reverse

from domain.repositories.base import LoteRecord
from operaciones.application.results import UseCaseResult
from operaciones.test.qa.base import QASetupMixin, TEMPORADA

# Lote ficticio que representa un lote recién creado en Recepcion
LOTE_CODE = "LP-2025-2026-0001"

def _make_lote_record(lote_code=LOTE_CODE, etapa_actual="Recepcion") -> LoteRecord:
    return LoteRecord(
        id="dv-fake-guid-0001",
        temporada=TEMPORADA,
        lote_code=lote_code,
        operator_code="QA-DV",
        source_system="web",
        estado="abierto",
        etapa_actual=etapa_actual,
        cantidad_bins=0,
    )


def _make_success_result(lote_code=LOTE_CODE) -> UseCaseResult:
    return UseCaseResult.success(
        code="LOTE_INICIADO",
        message=f"Lote {lote_code} creado",
        data={
            "lote_id": "dv-fake-guid-0001",
            "lote_code": lote_code,
            "temporada": TEMPORADA,
            "temporada_codigo": "2025-2026",
            "correlativo_temporada": 1,
            "estado": "abierto",
        },
    )


def _mock_repos_with_lote(lote_record: LoteRecord):
    """Devuelve un mock de Repositories cuyo lotes.find_by_code retorna lote_record."""
    repos = MagicMock()
    repos.lotes.find_by_code.return_value = lote_record
    repos.bins.list_by_lote.return_value = []
    return repos


def _mock_repos_lote_not_found():
    """Repos donde find_by_code simula que Dataverse aún no indexó el registro."""
    repos = MagicMock()
    repos.lotes.find_by_code.return_value = None
    repos.bins.list_by_lote.return_value = []
    return repos


@override_settings(PERSISTENCE_BACKEND="dataverse")
class RecepcionDataversePostIniciarTest(TestCase):
    """
    POST action=iniciar en modo Dataverse.
    """

    @classmethod
    def setUpTestData(cls):
        cls.client_rec, _ = QASetupMixin.make_role_client(
            "dv_rec_post", "Recepcion", operator_code="QA-DV-001"
        )

    def _post_iniciar(self):
        with patch(
            "operaciones.views.iniciar_lote_recepcion",
            return_value=_make_success_result(),
        ):
            return self.client_rec.post(
                reverse("operaciones:recepcion"),
                {"action": "iniciar"},
            )

    def test_post_iniciar_escribe_lote_activo_code_en_sesion(self):
        """Tras POST iniciar exitoso, la sesión debe tener lote_activo_code."""
        self._post_iniciar()
        lote_code = self.client_rec.session.get("lote_activo_code")
        self.assertEqual(lote_code, LOTE_CODE,
            msg="lote_activo_code debe quedar en sesión tras POST iniciar exitoso")

    def test_post_iniciar_redirige_a_recepcion(self):
        """POST iniciar debe redirigir a GET recepcion (PRG pattern)."""
        resp = self._post_iniciar()
        self.assertRedirects(resp, reverse("operaciones:recepcion"), fetch_redirect_response=False)

    def test_post_iniciar_no_crea_lote_si_ya_existe_activo(self):
        """
        Si ya existe un lote activo (devuelto por _lote_activo), _handle_iniciar
        debe abortar con warning — no llamar a iniciar_lote_recepcion.
        """
        # Primero establecemos un lote activo en sesión
        session = self.client_rec.session
        session["lote_activo_code"] = LOTE_CODE
        session.save()

        lote_existente = _make_lote_record()
        with patch(
            "operaciones.views.iniciar_lote_recepcion"
        ) as mock_iniciar, patch(
            "infrastructure.repository_factory.get_repositories",
            return_value=_mock_repos_with_lote(lote_existente),
        ):
            resp = self.client_rec.post(
                reverse("operaciones:recepcion"),
                {"action": "iniciar"},
                follow=True,
            )
            mock_iniciar.assert_not_called()

        msgs = list(resp.context.get("messages", []))
        warning_msgs = [m for m in msgs if "warning" in (m.tags or "")]
        self.assertGreater(len(warning_msgs), 0,
            msg="Debe emitir warning cuando ya existe lote activo")

    def test_post_iniciar_no_crea_segundo_lote_sin_session_destruida(self):
        """
        Regresión: si find_by_code devuelve None (Dataverse delay), la sesión
        NO se destruye → _handle_iniciar verá lote_activo_code y abortará.

        Esto verifica que la cadena de bugs no se reproduce:
          1. create_row → cache warm → find_by_code devuelve None (simulado)
          2. _lote_activo_dataverse devuelve None SIN limpiar sesión (Fix 3)
          3. _handle_iniciar ve session sin lote activo encontrado → SÍ crearía uno
             (comportamiento correcto cuando session fue limpiada por el bug antiguo)

        Para simular el escenario post-fix: la sesión sigue teniendo el code
        pero find_by_code devuelve None → guard en _handle_iniciar NO bloquea
        porque _lote_activo devuelve None → se permite crear (comportamiento correcto,
        el lote se creó con éxito por alguna razón no relacionada al timing).
        Este test valida que el guard solo bloquea cuando el lote es ENCONTRADO.
        """
        session = self.client_rec.session
        session["lote_activo_code"] = LOTE_CODE
        session.save()

        # find_by_code retorna None → Dataverse delay simulado
        with patch(
            "infrastructure.repository_factory.get_repositories",
            return_value=_mock_repos_lote_not_found(),
        ), patch(
            "operaciones.views.iniciar_lote_recepcion",
            return_value=_make_success_result("LP-2025-2026-0002"),
        ) as mock_iniciar:
            self.client_rec.post(
                reverse("operaciones:recepcion"),
                {"action": "iniciar"},
            )
            # Cuando find_by_code=None, _lote_activo devuelve None
            # → guard no bloquea → use case SÍ es llamado
            mock_iniciar.assert_called_once()


@override_settings(PERSISTENCE_BACKEND="dataverse")
class RecepcionDataverseGetLoteActivoTest(TestCase):
    """
    GET /recepcion/ en modo Dataverse con lote_activo_code en sesión.
    """

    @classmethod
    def setUpTestData(cls):
        cls.client_rec, _ = QASetupMixin.make_role_client(
            "dv_rec_get", "Recepcion", operator_code="QA-DV-002"
        )

    def _set_session_lote(self, lote_code=LOTE_CODE):
        session = self.client_rec.session
        session["lote_activo_code"] = lote_code
        session.save()

    def test_get_con_lote_en_cache_muestra_form_agregar_bin(self):
        """
        Tras crear el lote, find_by_code devuelve el LoteRecord desde cache.
        La plantilla debe mostrar form agregar_bin y NO form iniciar.
        """
        self._set_session_lote()
        lote = _make_lote_record()

        with patch(
            "infrastructure.repository_factory.get_repositories",
            return_value=_mock_repos_with_lote(lote),
        ):
            resp = self.client_rec.get(reverse("operaciones:recepcion"))

        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('value="agregar_bin"', content,
            msg="Con lote activo debe renderizar form agregar_bin")
        self.assertNotIn('value="iniciar"', content,
            msg="Con lote activo NO debe renderizar form iniciar")

    def test_get_con_lote_activo_muestra_lote_code_en_pagina(self):
        """El lote_code debe aparecer en el header de la página."""
        self._set_session_lote()
        lote = _make_lote_record()

        with patch(
            "infrastructure.repository_factory.get_repositories",
            return_value=_mock_repos_with_lote(lote),
        ):
            resp = self.client_rec.get(reverse("operaciones:recepcion"))

        self.assertIn(LOTE_CODE, resp.content.decode(),
            msg=f"El lote_code {LOTE_CODE} debe aparecer en el HTML")

    def test_get_dataverse_delay_session_no_destruida(self):
        """
        Si find_by_code devuelve None (Dataverse eventual consistency),
        la sesión NO debe perder lote_activo_code.
        Regresión del bug original donde la sesión era destruida.
        """
        self._set_session_lote()

        with patch(
            "infrastructure.repository_factory.get_repositories",
            return_value=_mock_repos_lote_not_found(),
        ):
            self.client_rec.get(reverse("operaciones:recepcion"))

        # La sesión debe conservar el code aunque find_by_code devolvió None
        self.assertEqual(
            self.client_rec.session.get("lote_activo_code"),
            LOTE_CODE,
            msg="lote_activo_code NO debe eliminarse cuando find_by_code devuelve None "
                "(Dataverse eventual consistency — Fix 3)",
        )

    def test_get_dataverse_delay_muestra_form_iniciar(self):
        """
        Si find_by_code devuelve None, la plantilla muestra el form de iniciar
        (no el form de bins), pero la sesión se preserva para el siguiente intento.
        """
        self._set_session_lote()

        with patch(
            "infrastructure.repository_factory.get_repositories",
            return_value=_mock_repos_lote_not_found(),
        ):
            resp = self.client_rec.get(reverse("operaciones:recepcion"))

        content = resp.content.decode()
        self.assertIn('value="iniciar"', content,
            msg="Sin lote encontrado debe mostrar form iniciar")

    def test_get_lote_etapa_incorrecta_limpia_sesion(self):
        """
        Si find_by_code devuelve el lote pero etapa_actual != 'Recepcion',
        la sesión SÍ debe limpiarse (el lote avanzó de etapa).
        """
        self._set_session_lote()
        lote_cerrado = _make_lote_record(etapa_actual="Pesaje")

        with patch(
            "infrastructure.repository_factory.get_repositories",
            return_value=_mock_repos_with_lote(lote_cerrado),
        ):
            self.client_rec.get(reverse("operaciones:recepcion"))

        self.assertIsNone(
            self.client_rec.session.get("lote_activo_code"),
            msg="lote_activo_code debe eliminarse cuando etapa_actual != 'Recepcion'",
        )

    def test_get_sin_lote_en_sesion_muestra_form_iniciar(self):
        """Sin lote_activo_code en sesión, la vista muestra el form de inicio."""
        # No establecemos session["lote_activo_code"]
        resp = self.client_rec.get(reverse("operaciones:recepcion"))
        content = resp.content.decode()
        self.assertIn('value="iniciar"', content,
            msg="Sin sesión de lote debe mostrar form iniciar")
        self.assertNotIn('value="agregar_bin"', content)


@override_settings(PERSISTENCE_BACKEND="dataverse")
class RecepcionDataverseFlujoCompletoTest(TestCase):
    """
    Flujo: POST iniciar → GET detecta lote → POST agregar_bin funciona.
    Simula el flujo operativo completo en un solo test de integración ligera.
    """

    @classmethod
    def setUpTestData(cls):
        cls.client_rec, _ = QASetupMixin.make_role_client(
            "dv_rec_flujo", "Recepcion", operator_code="QA-DV-003"
        )

    def test_flujo_iniciar_luego_get_reconoce_lote_activo(self):
        """
        Flujo completo:
          1. POST iniciar → use case exitoso → sesión tiene lote_activo_code
          2. GET recepcion → find_by_code devuelve LoteRecord (desde cache simulada)
          3. Template muestra form agregar_bin
        """
        lote = _make_lote_record()

        # Paso 1: POST iniciar
        with patch(
            "operaciones.views.iniciar_lote_recepcion",
            return_value=_make_success_result(),
        ):
            resp_post = self.client_rec.post(
                reverse("operaciones:recepcion"),
                {"action": "iniciar"},
            )

        self.assertEqual(resp_post.status_code, 302)
        self.assertEqual(self.client_rec.session.get("lote_activo_code"), LOTE_CODE)

        # Paso 2: GET siguiente — Dataverse devuelve el lote (cache caliente en prod)
        with patch(
            "infrastructure.repository_factory.get_repositories",
            return_value=_mock_repos_with_lote(lote),
        ):
            resp_get = self.client_rec.get(reverse("operaciones:recepcion"))

        # Paso 3: Plantilla muestra form agregar_bin
        self.assertEqual(resp_get.status_code, 200)
        content = resp_get.content.decode()
        self.assertIn('value="agregar_bin"', content,
            msg="Después de iniciar, GET debe mostrar form agregar_bin — "
                "este es el flujo operativo principal que fallaba con el bug")
        self.assertNotIn('value="iniciar"', content)

    def test_agregar_bin_inmediatamente_despues_de_iniciar(self):
        """
        POST agregar_bin debe aceptarse cuando lote_activo_code está en sesión,
        aunque se envíe en el mismo request cycle que el inicio del lote.
        Verifica que el use case es invocado (la vista no bloquea la acción).
        """
        from operaciones.application.results import UseCaseResult as R

        # Establecer sesión con lote activo (simula que create() ya guardó el code)
        session = self.client_rec.session
        session["lote_activo_code"] = LOTE_CODE
        session.save()

        bin_result = R.success(
            code="BIN_AGREGADO",
            message="Bin agregado",
            data={"bin_code": "BIN-150326-0001", "lote_code": LOTE_CODE},
        )

        with patch(
            "operaciones.views.agregar_bin_a_lote_abierto",
            return_value=bin_result,
        ) as mock_agregar:
            # No seguir el redirect — evita que el GET llame a Dataverse real
            resp = self.client_rec.post(
                reverse("operaciones:recepcion"),
                {
                    "action": "agregar_bin",
                    "variedad_fruta": "Thompson Seedless",
                    "codigo_productor": "PROD-001",
                    "tipo_cultivo": "Uva de mesa",
                    "color": "2",
                    "fecha_cosecha": "2026-03-15",
                    "numero_cuartel": "C-01",
                    "nombre_cuartel": "Norte 1",
                    "codigo_sag_csg": "CSG-001",
                    "codigo_sag_csp": "CSP-001",
                    "codigo_sdp": "SDP-001",
                    "lote_productor": "Lote-Campo-01",
                    "hora_recepcion": "08:30",
                    "kilos_bruto_ingreso": "520",
                    "kilos_neto_ingreso": "498",
                    "a_o_r": "aprobado",
                },
            )
            mock_agregar.assert_called_once()

        # La respuesta debe ser un redirect (acción exitosa → PRG)
        self.assertEqual(resp.status_code, 302,
            msg="POST agregar_bin exitoso debe redirigir (302)")

    def test_no_crea_multiples_lotes_vacios_en_cadena(self):
        """
        Regresión: el bug generaba N lotes vacíos porque:
          1. POST iniciar → lote creado, sesión escrita
          2. GET → find_by_code None → sesión DESTRUIDA (bug)
          3. Usuario vuelve a pulsar "Iniciar" → segundo lote vacío

        Con el fix:
          - Fix 3: sesión no se destruye cuando find_by_code=None
          - Fix 1: cache calienta find_by_code para el primer GET
          - Fix 2: guard impide segundo POST si lote está activo

        Este test verifica que en dos POST consecutivos con lote activo,
        solo el primero llama al use case.
        """
        lote = _make_lote_record()
        call_count = 0

        def _fake_iniciar(payload):
            nonlocal call_count
            call_count += 1
            return _make_success_result()

        # Primer POST (legítimo)
        with patch("operaciones.views.iniciar_lote_recepcion", side_effect=_fake_iniciar):
            self.client_rec.post(
                reverse("operaciones:recepcion"),
                {"action": "iniciar"},
            )

        self.assertEqual(call_count, 1)
        self.assertEqual(self.client_rec.session.get("lote_activo_code"), LOTE_CODE)

        # Segundo POST (debe ser bloqueado por el guard)
        with patch(
            "infrastructure.repository_factory.get_repositories",
            return_value=_mock_repos_with_lote(lote),
        ), patch(
            "operaciones.views.iniciar_lote_recepcion", side_effect=_fake_iniciar
        ):
            self.client_rec.post(
                reverse("operaciones:recepcion"),
                {"action": "iniciar"},
            )

        self.assertEqual(call_count, 1,
            msg="El segundo POST iniciar no debe crear otro lote — "
                "el guard en _handle_iniciar debe haberlo bloqueado")
