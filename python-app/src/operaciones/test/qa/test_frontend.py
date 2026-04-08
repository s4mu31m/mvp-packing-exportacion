"""
test_frontend.py — La UI responde al estado del negocio.

Diagnóstico: valida comportamiento operativo visible al operador.
No valida copy ni diseño — valida estructura funcional del HTML.

Clases:
  - EstadoFormularioRecepcionTest  → formularios correctos según estado del lote
  - ContextoLotesEnVistaTest       → lotes disponibles en selector coinciden con DB
  - MensajesPostPOSTTest           → mensajes funcionales tras POST exitoso e inválido
  - CSRFPresenciaTest              → formularios POST tienen csrfmiddlewaretoken
  - CamposReadonlyTest             → codigo_operador aparece como disabled con su valor
  - EstadoCondicionalDesverdizadoTest → tab correcto según disponibilidad_camara
"""
import datetime

from django.test import TestCase, override_settings
from django.urls import reverse

from operaciones.test.qa.base import (
    QASetupMixin,
    TEMPORADA,
    build_iniciar_payload,
    build_bin_payload,
    build_cierre_lote_payload,
    VARIEDAD_BLANCA,
)


@override_settings(PERSISTENCE_BACKEND="sqlite")
class EstadoFormularioRecepcionTest(TestCase):
    """
    Verifica que el template de recepción renderiza los formularios
    correctos según el estado del lote (sin lote / lote abierto con/sin bins).
    """

    @classmethod
    def setUpTestData(cls):
        cls.client_rec, _ = QASetupMixin.make_role_client(
            "qa_fe_rec", "Recepcion", operator_code="QA-001"
        )

    def _content(self):
        return self.client_rec.get(reverse("operaciones:recepcion")).content.decode()

    def test_sin_lote_activo_muestra_form_iniciar(self):
        content = self._content()
        self.assertIn('value="iniciar"', content,
            msg="Sin lote activo debe mostrar formulario de iniciar")

    def test_sin_lote_activo_no_muestra_form_agregar_bin(self):
        content = self._content()
        self.assertNotIn('value="agregar_bin"', content,
            msg="Sin lote activo NO debe mostrar form agregar_bin")

    def test_sin_lote_activo_no_muestra_form_cerrar(self):
        content = self._content()
        self.assertNotIn('value="cerrar"', content,
            msg="Sin lote activo NO debe mostrar form cerrar")

    def test_lote_iniciado_muestra_form_agregar_bin(self):
        self.client_rec.post(
            reverse("operaciones:recepcion"),
            build_iniciar_payload(),
        )
        resp = self.client_rec.get(reverse("operaciones:recepcion"))
        content = resp.content.decode()
        self.assertIn('value="agregar_bin"', content,
            msg="Con lote activo debe mostrar formulario agregar_bin")
        self.assertNotIn('value="iniciar"', content,
            msg="Con lote activo NO debe mostrar form iniciar")

    def test_lote_con_bins_habilita_form_cerrar(self):
        # Iniciar lote
        self.client_rec.post(
            reverse("operaciones:recepcion"),
            build_iniciar_payload(),
        )
        # Agregar bin
        self.client_rec.post(
            reverse("operaciones:recepcion"),
            build_bin_payload(),
        )
        content = self.client_rec.get(
            reverse("operaciones:recepcion")
        ).content.decode()
        self.assertIn('value="cerrar"', content,
            msg="Lote con bins debe mostrar formulario cerrar")

    def test_form_agregar_bin_tiene_campo_variedad(self):
        self.client_rec.post(
            reverse("operaciones:recepcion"),
            build_iniciar_payload(),
        )
        content = self.client_rec.get(
            reverse("operaciones:recepcion")
        ).content.decode()
        self.assertIn('name="variedad_fruta"', content,
            msg="Formulario agregar_bin debe tener campo variedad_fruta")


@override_settings(PERSISTENCE_BACKEND="sqlite")
class ContextoLotesEnVistaTest(TestCase):
    """
    En vistas que inyectan LOTES_DATA (proceso, control, ingreso_packing),
    el lote recién creado debe aparecer en el contexto — coherencia DB ↔ UI.
    """

    @classmethod
    def setUpTestData(cls):
        from operaciones.application.use_cases import (
            iniciar_lote_recepcion,
            agregar_bin_a_lote_abierto,
            cerrar_lote_recepcion,
            registrar_ingreso_packing,
        )
        # Crear lote cerrado con ingreso a packing (visible en proceso/control)
        res_init = iniciar_lote_recepcion({
            "temporada": TEMPORADA, "operator_code": "QA-SETUP", "source_system": "test"
        })
        lote_code = res_init.data["lote_code"]
        agregar_bin_a_lote_abierto({
            "temporada": TEMPORADA, "lote_code": lote_code,
            "operator_code": "QA-SETUP", "source_system": "test",
            "variedad_fruta": "Thompson Seedless",
            "kilos_neto_ingreso": "200", "kilos_bruto_ingreso": "210",
        })
        cerrar_lote_recepcion({
            "temporada": TEMPORADA, "lote_code": lote_code,
            "operator_code": "QA-SETUP", "source_system": "test",
        })
        registrar_ingreso_packing({
            "temporada": TEMPORADA, "lote_code": lote_code,
            "operator_code": "QA-SETUP", "source_system": "test",
            "via_desverdizado": False, "extra": {},
        })
        cls.lote_code = lote_code

        cls.client_proc, _ = QASetupMixin.make_role_client(
            "qa_fe_proc", "Proceso", operator_code="QA-004"
        )
        cls.client_ctrl, _ = QASetupMixin.make_role_client(
            "qa_fe_ctrl", "Control", operator_code="QA-005"
        )

    def test_lote_aparece_en_contexto_proceso(self):
        resp = self.client_proc.get(reverse("operaciones:proceso"))
        self.assertEqual(resp.status_code, 200)
        # El lote debe estar en lotes_pendientes del contexto
        lotes = resp.context.get("lotes_pendientes", [])
        lote_codes = [getattr(l, "lote_code", None) for l in lotes]
        self.assertIn(
            self.lote_code, lote_codes,
            msg=f"Lote {self.lote_code} no aparece en lotes_pendientes de /proceso/",
        )

    def test_lote_aparece_en_contexto_control(self):
        # La vista de índice /control/ no tiene lotes_pendientes — esa info
        # está en /control/proceso/ (ControlProcesoView)
        resp = self.client_ctrl.get(reverse("operaciones:control_proceso"))
        self.assertEqual(resp.status_code, 200)
        lotes = resp.context.get("lotes_pendientes", [])
        lote_codes = [getattr(l, "lote_code", None) for l in lotes]
        self.assertIn(
            self.lote_code, lote_codes,
            msg=f"Lote {self.lote_code} no aparece en lotes_pendientes de /control/proceso/",
        )

    def test_lote_data_json_en_html(self):
        """El lote_code debe aparecer en el HTML del template (en LOTES_DATA JSON)."""
        resp = self.client_proc.get(reverse("operaciones:proceso"))
        content = resp.content.decode()
        self.assertIn(self.lote_code, content,
            msg=f"Lote {self.lote_code} no aparece en el HTML de /proceso/")


@override_settings(PERSISTENCE_BACKEND="sqlite")
class MensajesPostPOSTTest(TestCase):
    """
    Mensajes funcionales después de POST — valida resultado de operación, no texto UI.
    """

    @classmethod
    def setUpTestData(cls):
        cls.client_rec, _ = QASetupMixin.make_role_client(
            "qa_fe_msg", "Recepcion", operator_code="QA-001"
        )

    def test_post_iniciar_exitoso_genera_mensaje_success(self):
        resp = self.client_rec.post(
            reverse("operaciones:recepcion"),
            build_iniciar_payload(),
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        msgs = list(resp.context.get("messages", []))
        success_msgs = [m for m in msgs if "success" in (m.tags or "")]
        self.assertGreater(len(success_msgs), 0,
            msg="POST iniciar exitoso debe generar al menos un mensaje de tipo 'success'")

    def test_post_agregar_bin_sin_variedad_genera_error(self):
        # Iniciar lote primero
        self.client_rec.post(
            reverse("operaciones:recepcion"),
            build_iniciar_payload(),
        )
        # Agregar bin sin variedad_fruta (campo required)
        payload = build_bin_payload()
        payload.pop("variedad_fruta")
        resp = self.client_rec.post(
            reverse("operaciones:recepcion"),
            payload,
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        msgs = list(resp.context.get("messages", []))
        error_msgs = [m for m in msgs if "error" in (m.tags or "")]
        self.assertGreater(len(error_msgs), 0,
            msg="POST bin sin variedad debe generar mensaje de error")

    def test_bin_no_creado_si_formulario_invalido(self):
        from operaciones.models import Bin
        count_antes = Bin.objects.count()
        self.client_rec.post(
            reverse("operaciones:recepcion"),
            build_iniciar_payload(),
        )
        payload = build_bin_payload()
        payload.pop("variedad_fruta")
        self.client_rec.post(reverse("operaciones:recepcion"), payload)
        self.assertEqual(Bin.objects.count(), count_antes,
            msg="Bin inválido no debe persistirse en la DB")


@override_settings(PERSISTENCE_BACKEND="sqlite")
class CSRFPresenciaTest(TestCase):
    """
    Todos los formularios POST tienen csrfmiddlewaretoken.
    """

    @classmethod
    def setUpTestData(cls):
        cls.all_clients = QASetupMixin.build_all_clients()

    def _client(self, rol_key):
        return self.all_clients[rol_key][0]

    def _assert_csrf_in_response(self, resp, url):
        content = resp.content.decode()
        self.assertIn(
            'name="csrfmiddlewaretoken"', content,
            msg=f"Formulario en {url} no contiene csrfmiddlewaretoken",
        )

    def test_csrf_en_recepcion(self):
        resp = self._client("recepcion").get(reverse("operaciones:recepcion"))
        self._assert_csrf_in_response(resp, "recepcion")

    def test_csrf_en_desverdizado(self):
        resp = self._client("desverdizado").get(reverse("operaciones:desverdizado"))
        self._assert_csrf_in_response(resp, "desverdizado")

    def test_csrf_en_ingreso_packing(self):
        resp = self._client("ing_packing").get(reverse("operaciones:ingreso_packing"))
        self._assert_csrf_in_response(resp, "ingreso_packing")

    def test_csrf_en_proceso(self):
        resp = self._client("proceso").get(reverse("operaciones:proceso"))
        self._assert_csrf_in_response(resp, "proceso")

    def test_csrf_en_control(self):
        resp = self._client("control").get(reverse("operaciones:control"))
        self._assert_csrf_in_response(resp, "control")

    def test_csrf_en_paletizado(self):
        resp = self._client("paletizado").get(reverse("operaciones:paletizado"))
        self._assert_csrf_in_response(resp, "paletizado")

    def test_csrf_en_camaras(self):
        resp = self._client("camaras").get(reverse("operaciones:camaras"))
        self._assert_csrf_in_response(resp, "camaras")


@override_settings(PERSISTENCE_BACKEND="sqlite")
class CamposReadonlyTest(TestCase):
    """
    El campo codigo_operador se inyecta desde la sesión y se renderiza
    como disabled con el valor correcto del operador.
    """

    @classmethod
    def setUpTestData(cls):
        cls.client_rec, _ = QASetupMixin.make_role_client(
            "qa_fe_ro", "Recepcion", operator_code="QA-001"
        )

    def test_codigo_operador_en_html_recepcion(self):
        # Iniciar lote para que aparezca el formulario con el campo
        self.client_rec.post(
            reverse("operaciones:recepcion"),
            build_iniciar_payload(),
        )
        content = self.client_rec.get(
            reverse("operaciones:recepcion")
        ).content.decode()
        self.assertIn("QA-001", content,
            msg="El operator_code del usuario (QA-001) debe aparecer en el HTML")

    def test_campo_readonly_presente_en_recepcion(self):
        self.client_rec.post(
            reverse("operaciones:recepcion"),
            build_iniciar_payload(),
        )
        content = self.client_rec.get(
            reverse("operaciones:recepcion")
        ).content.decode()
        self.assertIn("disabled", content,
            msg="El formulario de recepción debe tener al menos un campo disabled")


@override_settings(PERSISTENCE_BACKEND="sqlite")
class EstadoCondicionalDesverdizadoTest(TestCase):
    """
    La vista /desverdizado/ renderiza el tab correcto según el estado
    de disponibilidad_camara_desverdizado del lote.
    """

    @classmethod
    def setUpTestData(cls):
        from operaciones.application.use_cases import (
            iniciar_lote_recepcion,
            agregar_bin_a_lote_abierto,
            cerrar_lote_recepcion,
        )
        # Lote con desverdizado requerido, cámara NO disponible → debe mostrar mantención
        res = iniciar_lote_recepcion({
            "temporada": TEMPORADA, "operator_code": "QA-SETUP-DV", "source_system": "test"
        })
        lote_code = res.data["lote_code"]
        agregar_bin_a_lote_abierto({
            "temporada": TEMPORADA, "lote_code": lote_code,
            "operator_code": "QA-SETUP-DV", "source_system": "test",
            "variedad_fruta": "Red Globe", "kilos_neto_ingreso": "300",
            "kilos_bruto_ingreso": "315",
        })
        cerrar_lote_recepcion({
            "temporada": TEMPORADA, "lote_code": lote_code,
            "operator_code": "QA-SETUP-DV", "source_system": "test",
            "requiere_desverdizado": True,
            "disponibilidad_camara_desverdizado": "no_disponible",
        })
        cls.lote_code_no_disp = lote_code

        # Lote con cámara DISPONIBLE → debe mostrar formulario desverdizado
        res2 = iniciar_lote_recepcion({
            "temporada": TEMPORADA, "operator_code": "QA-SETUP-DV2", "source_system": "test"
        })
        lote_code2 = res2.data["lote_code"]
        agregar_bin_a_lote_abierto({
            "temporada": TEMPORADA, "lote_code": lote_code2,
            "operator_code": "QA-SETUP-DV2", "source_system": "test",
            "variedad_fruta": "Thompson Seedless", "kilos_neto_ingreso": "400",
            "kilos_bruto_ingreso": "415",
        })
        cerrar_lote_recepcion({
            "temporada": TEMPORADA, "lote_code": lote_code2,
            "operator_code": "QA-SETUP-DV2", "source_system": "test",
            "requiere_desverdizado": True,
            "disponibilidad_camara_desverdizado": "disponible",
        })
        cls.lote_code_disp = lote_code2

        cls.client_desv, _ = QASetupMixin.make_role_client(
            "qa_fe_desv", "Desverdizado", operator_code="QA-002"
        )

    def test_lote_no_disponible_aparece_en_lista_pendientes(self):
        resp = self.client_desv.get(reverse("operaciones:desverdizado"))
        self.assertEqual(resp.status_code, 200)
        lotes = resp.context.get("lotes_pendientes", [])
        lote_codes = [getattr(l, "lote_code", None) for l in lotes]
        self.assertIn(self.lote_code_no_disp, lote_codes,
            msg="Lote con cámara no disponible debe aparecer en /desverdizado/ pendientes")

    def test_desverdizado_tiene_form_mantencion(self):
        resp = self.client_desv.get(reverse("operaciones:desverdizado"))
        content = resp.content.decode()
        self.assertIn('value="mantencion"', content,
            msg="Vista desverdizado debe contener formulario de mantencion")

    def test_desverdizado_tiene_form_desverdizado(self):
        resp = self.client_desv.get(reverse("operaciones:desverdizado"))
        content = resp.content.decode()
        self.assertIn('value="desverdizado"', content,
            msg="Vista desverdizado debe contener formulario de desverdizado")
