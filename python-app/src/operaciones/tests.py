"""
Tests del flujo de recepcion con lote abierto (MVP).

Cobertura:
  - iniciar_lote_recepcion: crea lote en estado 'abierto' con lote_code autogenerado
  - agregar_bin_a_lote_abierto: registra bin y lo asocia al lote; rechaza lote cerrado
  - cerrar_lote_recepcion: cierra lote; rechaza si no tiene bins; impide agregar bins post-cierre
  - RecepcionView (integracion): iniciar_lote / agregar_bin / cerrar_lote via POST web
  - Sesion: lote_code persiste y se limpia correctamente
"""
import datetime

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from operaciones.application.use_cases import (
    iniciar_lote_recepcion,
    agregar_bin_a_lote_abierto,
    cerrar_lote_recepcion,
)
from infrastructure.repository_factory import get_repositories
from operaciones.models import (
    Bin,
    BinLote,
    Lote,
    LotePlantaEstado,
)

User = get_user_model()

TEMPORADA = str(datetime.date.today().year)
SESSION_LOTE_ACTIVO = "recepcion_lote_code"



def _make_user():
    return User.objects.create_user(username="tester", password="pass1234", is_superuser=True)


def _make_lote(estado=LotePlantaEstado.ABIERTO, **kwargs):
    defaults = dict(
        temporada=TEMPORADA,
        lote_code=f"LP-TEST-{Lote.objects.count()+1:03d}",
        estado=estado,
        is_active=True,
    )
    defaults.update(kwargs)
    return Lote.objects.create(**defaults)


def _make_bin(lote, **kwargs):
    defaults = dict(
        temporada=TEMPORADA,
        bin_code=f"BIN-T-{Bin.objects.count()+1:04d}",
        codigo_productor="PROD-01",
        tipo_cultivo="Uva de mesa",
        variedad_fruta="Thompson",
        color="2",
        fecha_cosecha=datetime.date.today(),
        kilos_bruto_ingreso=500,
        kilos_neto_ingreso=480,
    )
    defaults.update(kwargs)
    b = Bin.objects.create(**defaults)
    BinLote.objects.create(bin=b, lote=lote)
    return b


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iniciar(extra=None):
    payload = {"temporada": TEMPORADA, "operator_code": "OP-TEST", "source_system": "test"}
    if extra:
        payload.update(extra)
    return iniciar_lote_recepcion(payload)


def _agregar_bin(lote_code, extra=None):
    payload = {
        "temporada": TEMPORADA,
        "lote_code": lote_code,
        "operator_code": "OP-TEST",
        "source_system": "test",
        "variedad_fruta": "Thompson",
        "kilos_neto_ingreso": "200",
        "kilos_bruto_ingreso": "210",
    }
    if extra:
        payload.update(extra)
    return agregar_bin_a_lote_abierto(payload)


def _cerrar(lote_code):
    return cerrar_lote_recepcion({
        "temporada": TEMPORADA,
        "lote_code": lote_code,
        "operator_code": "OP-TEST",
        "source_system": "test",
    })


# ---------------------------------------------------------------------------
# Use case: iniciar_lote_recepcion
# ---------------------------------------------------------------------------

class IniciarLoteRecepcionTest(TestCase):

    def test_crea_lote_abierto(self):
        result = _iniciar()
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.code, "LOTE_INICIADO")
        self.assertIn("lote_code", result.data)
        self.assertEqual(result.data["estado"], "abierto")

    def test_lote_code_autogenerado_no_vacio(self):
        result = _iniciar()
        self.assertTrue(result.ok)
        lote_code = result.data["lote_code"]
        self.assertTrue(len(lote_code) > 0)

    def test_lote_persiste_en_db(self):
        result = _iniciar()
        self.assertTrue(result.ok)
        repos = get_repositories()
        lote = repos.lotes.find_by_code(TEMPORADA, result.data["lote_code"])
        self.assertIsNotNone(lote)
        self.assertEqual(lote.estado, "abierto")
        self.assertEqual(lote.cantidad_bins, 0)

    def test_dos_lotes_codigos_distintos(self):
        r1 = _iniciar()
        r2 = _iniciar()
        self.assertTrue(r1.ok)
        self.assertTrue(r2.ok)
        self.assertNotEqual(r1.data["lote_code"], r2.data["lote_code"])

    def test_rechaza_sin_temporada(self):
        result = iniciar_lote_recepcion({})
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "INVALID_PAYLOAD")


# ---------------------------------------------------------------------------
# Use case: agregar_bin_a_lote_abierto
# ---------------------------------------------------------------------------

class AgregarBinALoteAbiertoTest(TestCase):

    def setUp(self):
        result = _iniciar()
        self.assertTrue(result.ok)
        self.lote_code = result.data["lote_code"]

    def test_agrega_bin_exitosamente(self):
        result = _agregar_bin(self.lote_code)
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.code, "BIN_AGREGADO")
        self.assertIn("bin_code", result.data)
        self.assertEqual(result.data["lote_code"], self.lote_code)

    def test_bin_code_autogenerado(self):
        result = _agregar_bin(self.lote_code)
        self.assertTrue(result.ok)
        self.assertTrue(len(result.data["bin_code"]) > 0)

    def test_lote_cantidad_bins_incrementa(self):
        repos = get_repositories()
        _agregar_bin(self.lote_code)
        _agregar_bin(self.lote_code)
        lote = repos.lotes.find_by_code(TEMPORADA, self.lote_code)
        self.assertEqual(lote.cantidad_bins, 2)

    def test_bin_queda_asociado_al_lote(self):
        result = _agregar_bin(self.lote_code)
        self.assertTrue(result.ok)
        repos = get_repositories()
        lote = repos.lotes.find_by_code(TEMPORADA, self.lote_code)
        bins = repos.bins.list_by_lote(lote.id)
        self.assertEqual(len(bins), 1)
        self.assertEqual(bins[0].bin_code, result.data["bin_code"])

    def test_rechaza_lote_inexistente(self):
        result = _agregar_bin("LOTE-NOEXISTE")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "LOTE_NOT_FOUND")

    def test_rechaza_lote_cerrado(self):
        _agregar_bin(self.lote_code)
        _cerrar(self.lote_code)
        result = _agregar_bin(self.lote_code)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "LOTE_NOT_OPEN")

    def test_rechaza_sin_lote_code(self):
        result = agregar_bin_a_lote_abierto({"temporada": TEMPORADA})
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "INVALID_PAYLOAD")


# ---------------------------------------------------------------------------
# Use case: cerrar_lote_recepcion
# ---------------------------------------------------------------------------

class CerrarLoteRecepcionTest(TestCase):

    def setUp(self):
        result = _iniciar()
        self.assertTrue(result.ok)
        self.lote_code = result.data["lote_code"]

    def test_rechaza_cerrar_lote_sin_bins(self):
        result = _cerrar(self.lote_code)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "LOTE_SIN_BINS")

    def test_cierra_lote_con_bins(self):
        _agregar_bin(self.lote_code)
        result = _cerrar(self.lote_code)
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.code, "LOTE_CERRADO")
        self.assertEqual(result.data["estado"], "cerrado")

    def test_estado_persiste_cerrado_en_db(self):
        _agregar_bin(self.lote_code)
        _cerrar(self.lote_code)
        repos = get_repositories()
        lote = repos.lotes.find_by_code(TEMPORADA, self.lote_code)
        self.assertEqual(lote.estado, "cerrado")

    def test_rechaza_cerrar_lote_ya_cerrado(self):
        _agregar_bin(self.lote_code)
        _cerrar(self.lote_code)
        result = _cerrar(self.lote_code)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "LOTE_NOT_OPEN")

    def test_rechaza_cerrar_lote_inexistente(self):
        result = cerrar_lote_recepcion({
            "temporada": TEMPORADA,
            "lote_code": "LOTE-NOEXISTE",
        })
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "LOTE_NOT_FOUND")


# ---------------------------------------------------------------------------
# Repository: list_by_lote / list_recent
# ---------------------------------------------------------------------------

class RepositoryQueryTest(TestCase):

    def test_bins_list_by_lote_vacio(self):
        r = _iniciar()
        repos = get_repositories()
        lote = repos.lotes.find_by_code(TEMPORADA, r.data["lote_code"])
        bins = repos.bins.list_by_lote(lote.id)
        self.assertEqual(bins, [])

    def test_bins_list_by_lote_con_datos(self):
        r = _iniciar()
        lote_code = r.data["lote_code"]
        _agregar_bin(lote_code)
        _agregar_bin(lote_code)
        repos = get_repositories()
        lote = repos.lotes.find_by_code(TEMPORADA, lote_code)
        bins = repos.bins.list_by_lote(lote.id)
        self.assertEqual(len(bins), 2)

    def test_lotes_list_recent(self):
        _iniciar()
        _iniciar()
        repos = get_repositories()
        lotes = repos.lotes.list_recent(TEMPORADA)
        self.assertGreaterEqual(len(lotes), 2)

    def test_bin_lotes_list_by_lote(self):
        r = _iniciar()
        lote_code = r.data["lote_code"]
        _agregar_bin(lote_code)
        repos = get_repositories()
        lote = repos.lotes.find_by_code(TEMPORADA, lote_code)
        bin_lotes = repos.bin_lotes.list_by_lote(lote.id)
        self.assertEqual(len(bin_lotes), 1)
        self.assertEqual(bin_lotes[0].lote_id, lote.id)


# ---------------------------------------------------------------------------
# View integration: RecepcionView
# ---------------------------------------------------------------------------

class RecepcionViewTest(TestCase):

    def setUp(self):
        self.client = Client()

        self.user = _make_user()
        self.client.force_login(self.user)

    def _get_ok(self, url_name):
        url = reverse(f"operaciones:{url_name}")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200, f"GET {url_name} returned {resp.status_code}")

    def test_dashboard(self):
        self._get_ok("dashboard")

    def test_recepcion(self):
        self._get_ok("recepcion")

    def test_desverdizado(self):
        self._get_ok("desverdizado")

    def test_ingreso_packing(self):
        self._get_ok("ingreso_packing")

    def test_proceso(self):
        self._get_ok("proceso")

    def test_control(self):
        self._get_ok("control")

    def test_paletizado(self):
        self._get_ok("paletizado")

    def test_camaras(self):
        self._get_ok("camaras")

    def test_consulta_jefatura(self):
        # Consulta requires jefatura role (is_staff)
        self.user.is_staff = True
        self.user.save()
        self._get_ok("consulta")

    def test_consulta_jefatura_con_filtros(self):
        self.user.is_staff = True
        self.user.save()
        url = reverse("operaciones:consulta") + "?productor=PROD&estado=cerrado"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_consulta_jefatura_redirect_sin_rol(self):
        """Operador sin rol admin/jefatura es redirigido fuera de consulta."""
        self.user.is_superuser = False
        self.user.is_staff = False
        self.user.save()
        url = reverse("operaciones:consulta")
        resp = self.client.get(url)
        self.assertIn(resp.status_code, [302, 403])

    def test_redirect_sin_auth(self):
        """Sin login debe redirigir al login."""
        self.client.logout()
        url = reverse("operaciones:dashboard")
        resp = self.client.get(url)
        self.assertIn(resp.status_code, [302, 301])


# ---------------------------------------------------------------------------
# Flujo recepcion: iniciar lote → agregar bin → rechazar bin → cerrar lote
# ---------------------------------------------------------------------------

class RecepcionFlowTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = _make_user()
        self.client.force_login(self.user)
        self.url = reverse("operaciones:recepcion")

    def _session_set_temporada(self):
        session = self.client.session
        session["temporada_activa"] = TEMPORADA
        session.save()

    def test_get_sin_lote_activo(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context["lote_activo"])
        self.assertEqual(resp.context["bins_del_lote"], [])

    def test_post_iniciar_lote_crea_sesion(self):
        self._session_set_temporada()
        resp = self.client.post(self.url, {
            "action": "iniciar_lote",
            "operator_code": "OP-001",
            "temporada": TEMPORADA,
        })
        self.assertRedirects(resp, self.url)
        self.assertIn(SESSION_LOTE_ACTIVO, self.client.session)
        lote_code = self.client.session[SESSION_LOTE_ACTIVO]
        self.assertTrue(len(lote_code) > 0)

    def test_post_iniciar_lote_dos_veces_no_sobreescribe(self):
        self._session_set_temporada()
        self.client.post(self.url, {
            "action": "iniciar_lote",
            "operator_code": "OP-001",
            "temporada": TEMPORADA,
        })
        lote_code_1 = self.client.session[SESSION_LOTE_ACTIVO]
        self.client.post(self.url, {
            "action": "iniciar_lote",
            "operator_code": "OP-001",
            "temporada": TEMPORADA,
        })
        lote_code_2 = self.client.session[SESSION_LOTE_ACTIVO]
        # El segundo intento debe mostrar advertencia y mantener el primero
        self.assertEqual(lote_code_1, lote_code_2)

    def test_post_agregar_bin_sin_lote_activo_muestra_error(self):
        self._session_set_temporada()
        resp = self.client.post(self.url, {
            "action": "agregar_bin",
            "temporada": TEMPORADA,
        }, follow=True)
        messages_list = list(resp.context["messages"])
        self.assertTrue(any("No hay lote activo" in str(m) for m in messages_list))

    def test_flujo_completo_iniciar_agregar_cerrar(self):
        self._session_set_temporada()
        # 1. Iniciar lote
        self.client.post(self.url, {
            "action": "iniciar_lote",
            "operator_code": "OP-001",
            "temporada": TEMPORADA,
        })
        lote_code = self.client.session[SESSION_LOTE_ACTIVO]
        self.assertIsNotNone(lote_code)

        # 2. Agregar bin
        resp = self.client.post(self.url, {
            "action": "agregar_bin",
            "temporada": TEMPORADA,
            "operator_code": "OP-001",
            "codigo_productor": "AG001",
            "tipo_cultivo": "Uva",
            "variedad_fruta": "Thompson",
            "numero_cuartel": "C01",
            "fecha_cosecha": "2025-12-01",
            "kilos_neto_ingreso": "200",
            "kilos_bruto_ingreso": "210",
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        # Verificar bin en DB
        repos = get_repositories()
        lote = repos.lotes.find_by_code(TEMPORADA, lote_code)
        bins = repos.bins.list_by_lote(lote.id)
        self.assertEqual(len(bins), 1)

        # 3. Cerrar lote
        resp = self.client.post(self.url, {
            "action": "cerrar_lote",
            "temporada": TEMPORADA,
            "operator_code": "OP-001",
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        # Sesion limpia
        self.assertNotIn(SESSION_LOTE_ACTIVO, self.client.session)
        # Lote cerrado en DB
        lote_actualizado = repos.lotes.find_by_code(TEMPORADA, lote_code)
        self.assertEqual(lote_actualizado.estado, "cerrado")

    def test_post_cerrar_sin_bins_muestra_error(self):
        self._session_set_temporada()
        self.client.post(self.url, {
            "action": "iniciar_lote",
            "operator_code": "OP-001",
            "temporada": TEMPORADA,
        })
        resp = self.client.post(self.url, {
            "action": "cerrar_lote",
            "temporada": TEMPORADA,
            "operator_code": "OP-001",
        }, follow=True)
        messages_list = list(resp.context["messages"])
        self.assertTrue(any("bin" in str(m).lower() for m in messages_list))
        # Lote sigue activo en sesion
        self.assertIn(SESSION_LOTE_ACTIVO, self.client.session)

    def test_get_con_lote_activo_muestra_lote(self):
        self._session_set_temporada()
        self.client.post(self.url, {
            "action": "iniciar_lote",
            "operator_code": "OP-001",
            "temporada": TEMPORADA,
        })
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.context["lote_activo"])
        lote_code = self.client.session[SESSION_LOTE_ACTIVO]
        self.assertEqual(resp.context["lote_activo"].lote_code, lote_code)
