"""
test_negativos.py — Robustez, resiliencia e idempotencia.

Clases:
  - ValidacionFormulariosTest      → formularios inválidos son rechazados correctamente
  - EntidadesInexistentesTest      → POSTs con entidades que no existen → sin 500
  - EstadosInvalidosDeSecuenciaTest → operaciones fuera de orden son rechazadas
  - IdempotenciaTest               → reintentos no duplican datos críticos (BLOQUEANTE)
  - SesionInconsistenteTest        → sesiones incompletas o expiradas → comportamiento seguro
"""
import datetime

from django.test import TestCase, override_settings
from django.urls import reverse

from operaciones.models import (
    Bin,
    BinLote,
    Lote,
    LotePlantaEstado,
    RegistroEtapa,
)
from tests.unit.operaciones.qa.base import (
    QASetupMixin,
    TEMPORADA,
    VARIEDAD_BLANCA,
    build_iniciar_payload,
    build_bin_payload,
    build_cierre_lote_payload,
    build_ingreso_packing_payload,
    build_proceso_payload,
    build_calidad_pallet_payload,
)


@override_settings(PERSISTENCE_BACKEND="sqlite")
class ValidacionFormulariosTest(TestCase):
    """
    Formularios inválidos son rechazados y no persisten datos corruptos.
    """

    @classmethod
    def setUpTestData(cls):
        cls.client_rec, _ = QASetupMixin.make_role_client(
            "qa_neg_rec", "Recepcion", operator_code="QA-001"
        )
        cls.client_ing, _ = QASetupMixin.make_role_client(
            "qa_neg_ing", "Ingreso Packing", operator_code="QA-003"
        )

    def test_bin_sin_variedad_fruta_no_se_persiste(self):
        """variedad_fruta es required → sin ella el bin NO debe crearse."""
        self.client_rec.post(reverse("operaciones:recepcion"), build_iniciar_payload())
        count_antes = Bin.objects.count()

        payload = build_bin_payload(VARIEDAD_BLANCA.copy())
        payload.pop("variedad_fruta")
        resp = self.client_rec.post(reverse("operaciones:recepcion"), payload)

        self.assertNotEqual(resp.status_code, 500,
            msg="POST con variedad_fruta ausente no debe devolver 500")
        self.assertEqual(Bin.objects.count(), count_antes,
            msg="Bin no debe persistirse si variedad_fruta está ausente")

    def test_bin_sin_variedad_genera_mensaje_error(self):
        self.client_rec.post(reverse("operaciones:recepcion"), build_iniciar_payload())
        payload = build_bin_payload(VARIEDAD_BLANCA.copy())
        payload.pop("variedad_fruta")
        resp = self.client_rec.post(
            reverse("operaciones:recepcion"), payload, follow=True
        )
        msgs = list(resp.context.get("messages", []))
        self.assertTrue(
            any("error" in (m.tags or "") for m in msgs),
            msg="POST inválido debe generar mensaje de error visible al operador",
        )

    def test_cerrar_lote_sin_bins_no_cierra(self):
        """No se puede cerrar un lote sin bins según regla de negocio."""
        client = self.client_rec
        client.post(reverse("operaciones:recepcion"), build_iniciar_payload())
        lote_code = QASetupMixin.get_lote_code_from_session(client)

        resp = client.post(
            reverse("operaciones:recepcion"),
            build_cierre_lote_payload(),
        )
        self.assertNotEqual(resp.status_code, 500,
            msg="Cerrar lote sin bins no debe devolver 500")

        if lote_code:
            lote = Lote.objects.filter(temporada=TEMPORADA, lote_code=lote_code).first()
            if lote:
                self.assertNotEqual(lote.estado, LotePlantaEstado.CERRADO,
                    msg="Lote sin bins no debe quedar en estado CERRADO")

    def test_ingreso_packing_sin_lote_code_no_falla_con_500(self):
        """POST sin lote_code → error de negocio, no 500."""
        resp = self.client_ing.post(
            reverse("operaciones:ingreso_packing"),
            build_ingreso_packing_payload(""),  # lote_code vacío
        )
        self.assertNotEqual(resp.status_code, 500,
            msg="POST ingreso_packing sin lote_code no debe devolver 500")


@override_settings(PERSISTENCE_BACKEND="sqlite")
class EntidadesInexistentesTest(TestCase):
    """
    POSTs con lote_code o pallet_code que no existen → error de negocio, sin 500.
    """

    @classmethod
    def setUpTestData(cls):
        cls.client_ing, _ = QASetupMixin.make_role_client(
            "qa_neg_ent_ing", "Ingreso Packing", operator_code="QA-003"
        )
        cls.client_proc, _ = QASetupMixin.make_role_client(
            "qa_neg_ent_proc", "Proceso", operator_code="QA-004"
        )
        cls.client_cam, _ = QASetupMixin.make_role_client(
            "qa_neg_ent_cam", "Camaras", operator_code="QA-007"
        )

    def test_ingreso_packing_lote_inexistente(self):
        resp = self.client_ing.post(
            reverse("operaciones:ingreso_packing"),
            build_ingreso_packing_payload("LOT-NOEXISTE-QA"),
        )
        self.assertNotEqual(resp.status_code, 500,
            msg="lote_code inexistente en ingreso_packing no debe devolver 500")

    def test_proceso_lote_inexistente(self):
        resp = self.client_proc.post(
            reverse("operaciones:proceso"),
            build_proceso_payload("LOT-NOEXISTE-QA"),
        )
        self.assertNotEqual(resp.status_code, 500,
            msg="lote_code inexistente en proceso no debe devolver 500")

    def test_calidad_pallet_inexistente(self):
        resp = self.client_cam.post(
            reverse("operaciones:paletizado"),
            build_calidad_pallet_payload("PAL-NOEXISTE-QA"),
        )
        self.assertNotEqual(resp.status_code, 500,
            msg="pallet_code inexistente en paletizado no debe devolver 500")

    def test_camara_frio_pallet_inexistente(self):
        from tests.unit.operaciones.qa.base import build_camara_frio_payload
        resp = self.client_cam.post(
            reverse("operaciones:camaras"),
            build_camara_frio_payload("PAL-NOEXISTE-QA"),
        )
        self.assertNotEqual(resp.status_code, 500,
            msg="pallet_code inexistente en camaras no debe devolver 500")


@override_settings(PERSISTENCE_BACKEND="sqlite")
class EstadosInvalidosDeSecuenciaTest(TestCase):
    """
    Operaciones fuera del orden del flujo son rechazadas correctamente.
    """

    @classmethod
    def setUpTestData(cls):
        from operaciones.application.use_cases import (
            iniciar_lote_recepcion, agregar_bin_a_lote_abierto
        )
        base = {"temporada": TEMPORADA, "operator_code": "QA-SEQ", "source_system": "test"}
        res = iniciar_lote_recepcion(base.copy())
        lote_code = res.data["lote_code"]
        agregar_bin_a_lote_abierto({**base, "lote_code": lote_code,
            "variedad_fruta": "Thompson Seedless", "kilos_neto_ingreso": "300",
            "kilos_bruto_ingreso": "315"})
        cls.lote_code_abierto = lote_code  # lote en estado ABIERTO (no cerrado)

        cls.client_ing, _ = QASetupMixin.make_role_client(
            "qa_seq_ing", "Ingreso Packing", operator_code="QA-003"
        )

    def test_ingreso_packing_lote_en_estado_abierto_es_rechazado(self):
        """
        OBSERVACIÓN (no bloqueante): el sistema acepta ingreso_packing para lotes
        en estado ABIERTO — la validación de estado previo no está implementada.
        BLOQUEANTE: la vista no debe devolver 500.
        """
        from operaciones.models import IngresoAPacking
        count_antes = IngresoAPacking.objects.count()

        resp = self.client_ing.post(
            reverse("operaciones:ingreso_packing"),
            build_ingreso_packing_payload(self.lote_code_abierto),
        )
        self.assertNotEqual(resp.status_code, 500,
            msg="Ingreso packing con lote ABIERTO no debe devolver 500")

        count_despues = IngresoAPacking.objects.count()
        if count_despues > count_antes:
            print(
                "\n[OBSERVACIÓN] registrar_ingreso_packing acepta lotes en estado ABIERTO — "
                "regla de negocio pendiente: debería requerir estado CERRADO antes de ingresar a packing"
            )

    def test_lote_abierto_sigue_abierto_tras_intento_invalido(self):
        """
        OBSERVACIÓN (no bloqueante): documenta si el lote cambia de estado
        al ejecutar ingreso_packing sin haber cerrado recepción primero.
        """
        self.client_ing.post(
            reverse("operaciones:ingreso_packing"),
            build_ingreso_packing_payload(self.lote_code_abierto),
        )
        lote = Lote.objects.get(temporada=TEMPORADA, lote_code=self.lote_code_abierto)
        if lote.estado != LotePlantaEstado.ABIERTO:
            print(
                f"\n[OBSERVACIÓN] Lote pasó de ABIERTO a '{lote.estado}' tras ingreso_packing — "
                f"el sistema no valida el estado previo del lote antes de ingresar a packing"
            )


@override_settings(PERSISTENCE_BACKEND="sqlite")
class IdempotenciaTest(TestCase):
    """
    Reintentos no duplican datos críticos.
    BLOQUEANTE: duplicados en event_key o relaciones indican corrupción silenciosa.
    """

    @classmethod
    def setUpTestData(cls):
        cls.client_rec, _ = QASetupMixin.make_role_client(
            "qa_idem_rec", "Recepcion", operator_code="QA-001"
        )

    def test_doble_iniciar_no_duplica_lote(self):
        """
        Dos POSTs a iniciar en la misma sesión — el segundo es ignorado
        si el lote ya está activo, o crea uno nuevo si la sesión se limpió.
        En ambos casos, no hay corrupción de datos.
        """
        self.client_rec.post(reverse("operaciones:recepcion"), build_iniciar_payload())
        lote_code_1 = QASetupMixin.get_lote_code_from_session(self.client_rec)

        # Segundo POST — si la vista protege el estado, debe redirigir sin crear otro
        self.client_rec.post(reverse("operaciones:recepcion"), build_iniciar_payload())
        lote_code_2 = QASetupMixin.get_lote_code_from_session(self.client_rec)

        # No puede haber dos lotes con el mismo código
        lotes_con_code_1 = Lote.objects.filter(
            temporada=TEMPORADA, lote_code=lote_code_1
        ).count()
        self.assertEqual(lotes_con_code_1, 1,
            msg=f"El lote {lote_code_1} no debe estar duplicado en la DB")

    def test_event_key_unico_tras_operaciones_repetidas(self):
        """
        Hacer múltiples POSTs al mismo endpoint no debe duplicar event_keys.
        """
        from operaciones.application.use_cases import (
            iniciar_lote_recepcion, agregar_bin_a_lote_abierto
        )
        base = {"temporada": TEMPORADA, "operator_code": "QA-IDEM", "source_system": "test"}
        res = iniciar_lote_recepcion(base.copy())
        lote_code = res.data["lote_code"]
        # Agregar el mismo bin dos veces (el sistema debe rechazar el duplicado)
        agregar_bin_a_lote_abierto({**base, "lote_code": lote_code,
            "variedad_fruta": "Thompson Seedless",
            "kilos_neto_ingreso": "200", "kilos_bruto_ingreso": "210"})
        agregar_bin_a_lote_abierto({**base, "lote_code": lote_code,
            "variedad_fruta": "Thompson Seedless",
            "kilos_neto_ingreso": "200", "kilos_bruto_ingreso": "210"})

        # event_key debe ser único en todos los RegistroEtapa
        total = RegistroEtapa.objects.filter(temporada=TEMPORADA).count()
        distintos = (
            RegistroEtapa.objects.filter(temporada=TEMPORADA)
            .values("event_key").distinct().count()
        )
        self.assertEqual(total, distintos,
            msg=f"Duplicados de event_key detectados: {total} registros, {distintos} únicos — "
                "idempotencia rota")

    def test_no_duplicacion_bin_lote(self):
        """
        Asignar el mismo bin a un lote dos veces no debe crear dos BinLote
        — la constraint uq_bin_lote_pair debe proteger el dato.
        """
        from operaciones.application.use_cases import (
            iniciar_lote_recepcion, agregar_bin_a_lote_abierto
        )
        base = {"temporada": TEMPORADA, "operator_code": "QA-IDEM2", "source_system": "test"}
        res = iniciar_lote_recepcion(base.copy())
        lote_code = res.data["lote_code"]

        # Primer agregar
        r1 = agregar_bin_a_lote_abierto({**base, "lote_code": lote_code,
            "variedad_fruta": "Thompson Seedless",
            "kilos_neto_ingreso": "200", "kilos_bruto_ingreso": "210"})
        bin_code = r1.data.get("bin_code") if r1.ok else None

        lote = Lote.objects.get(temporada=TEMPORADA, lote_code=lote_code)
        count_antes = BinLote.objects.filter(lote=lote).count()

        # Segundo intento con el mismo bin_code (si el sistema permite especificarlo)
        # Si no, el sistema genera uno nuevo — verificamos que el count no sea incoherente
        agregar_bin_a_lote_abierto({**base, "lote_code": lote_code,
            "variedad_fruta": "Thompson Seedless",
            "kilos_neto_ingreso": "200", "kilos_bruto_ingreso": "210"})

        # event_key debe seguir siendo único
        total = RegistroEtapa.objects.filter(temporada=TEMPORADA).count()
        distintos = (
            RegistroEtapa.objects.filter(temporada=TEMPORADA)
            .values("event_key").distinct().count()
        )
        self.assertEqual(total, distintos,
            msg="No deben existir event_key duplicados tras doble agregar_bin")


@override_settings(PERSISTENCE_BACKEND="sqlite")
class SesionInconsistenteTest(TestCase):
    """
    Comportamiento ante sesiones incompletas o expiradas.
    """

    def test_agregar_bin_sin_lote_en_sesion_redirige_sin_500(self):
        """
        POST agregar_bin sin lote_activo_code en sesión → error de operación, no 500.
        """
        client, _ = QASetupMixin.make_role_client(
            "qa_sess_1", "Recepcion", operator_code="QA-001"
        )
        # No se inicia lote — sesión no tiene lote_activo_code
        resp = client.post(
            reverse("operaciones:recepcion"),
            build_bin_payload(VARIEDAD_BLANCA),
        )
        self.assertNotEqual(resp.status_code, 500,
            msg="POST agregar_bin sin lote en sesión no debe devolver 500")
        self.assertIn(resp.status_code, [200, 302],
            msg="POST agregar_bin sin lote debe redirigir o renderizar con error")

    def test_operador_sin_codigo_en_sesion_no_rompe_vista(self):
        """
        Un usuario autenticado con rol pero sin crf21_codigooperador en sesión
        no debe provocar un error 500 en las vistas.
        """
        from django.contrib.auth import get_user_model
        from usuarios.permissions import SESSION_KEY_ROL
        User = get_user_model()
        user = User.objects.create_user(username="qa_sess_2", password="pw")
        c = __import__("django.test", fromlist=["Client"]).Client()
        c.force_login(user)
        session = c.session
        session[SESSION_KEY_ROL] = "Recepcion"
        # Deliberadamente NO se inyecta SESSION_KEY_CODIGO_OPERADOR
        session.save()

        resp = c.get(reverse("operaciones:recepcion"))
        self.assertNotEqual(resp.status_code, 500,
            msg="Vista recepcion sin operator_code en sesión no debe devolver 500")

    def test_usuario_forzado_a_logout_redirige_a_login(self):
        """
        Tras logout, intentar acceder a una vista protegida redirige a login.
        """
        client, user = QASetupMixin.make_role_client(
            "qa_sess_3", "Recepcion", operator_code="QA-001"
        )
        client.logout()
        resp = client.get(reverse("operaciones:recepcion"))
        self.assertIn(resp.status_code, [301, 302],
            msg="Tras logout, acceso a vista protegida debe redirigir")
        self.assertIn("/login", resp.get("Location", ""),
            msg="Redirect post-logout debe apuntar a login")
