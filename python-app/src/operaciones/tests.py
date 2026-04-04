"""
Tests del flujo operativo de packing.

Cobertura:
  - Use cases: iniciar_lote_recepcion, agregar_bin_a_lote_abierto, cerrar_lote_recepcion
  - Repositories: list_by_lote, list_recent
  - Smoke tests: vistas críticas renderizan 200
  - Flujo recepcion via POST web
"""
import datetime

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

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
    Pallet,
    PalletLote,
    IngresoAPacking,
    Desverdizado,
)

User = get_user_model()

TEMPORADA = str(datetime.date.today().year)


def _make_user():
    return User.objects.create_user(username="tester", password="pass1234", is_superuser=True, is_staff=True)


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
# GET smoke — todas las vistas deben renderizar 200 (auth requerida)
# ---------------------------------------------------------------------------

class ViewsGetSmokeTest(TestCase):

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

    def test_iniciar_lote(self):
        resp = self.client.post(self.url, {
            "action": "iniciar",
            "temporada": TEMPORADA,
            "operator_code": "OP-01",
        })
        self.assertIn(resp.status_code, [200, 302])
        self.assertTrue(Lote.objects.filter(temporada=TEMPORADA).exists())

    def _datos_bin(self):
        return {
            "action": "agregar_bin",
            "temporada": TEMPORADA,
            "codigo_productor": "PROD-01",
            "tipo_cultivo": "Uva de mesa",
            "variedad_fruta": "Thompson",
            "color": "2",
            "fecha_cosecha": str(datetime.date.today()),
            "kilos_bruto_ingreso": "500",
            "kilos_neto_ingreso": "480",
            "operator_code": "OP-01",
        }

    def test_agregar_bin(self):
        # Iniciar primero
        self.client.post(self.url, {
            "action": "iniciar",
            "temporada": TEMPORADA,
            "operator_code": "OP-01",
        })
        lote = Lote.objects.filter(temporada=TEMPORADA).first()
        self.assertIsNotNone(lote)
        # Agregar bin valido
        resp = self.client.post(self.url, self._datos_bin())
        self.assertIn(resp.status_code, [200, 302])

    def test_agregar_multiples_bins_mismas_campos_base(self):
        """
        Agregar dos bins consecutivos con los mismos campos base no debe
        lanzar IntegrityError en RegistroEtapa.event_key.
        Regresion: agregar_bin_a_lote_abierto usaba create() en lugar de
        get_or_create() para RegistroEtapa, causando UNIQUE constraint fail
        ante reintento o bin_code repetido por datos de dev inconsistentes.
        """
        self.client.post(self.url, {
            "action": "iniciar",
            "temporada": TEMPORADA,
            "operator_code": "OP-01",
        })
        lote = Lote.objects.filter(temporada=TEMPORADA).first()
        self.assertIsNotNone(lote)
        datos = self._datos_bin()
        resp1 = self.client.post(self.url, datos)
        self.assertIn(resp1.status_code, [200, 302])
        resp2 = self.client.post(self.url, datos)
        self.assertIn(resp2.status_code, [200, 302])
        from operaciones.models import BinLote
        self.assertEqual(
            BinLote.objects.filter(lote=lote).count(), 2,
            "Deben existir dos bins distintos en el lote",
        )

    def test_cerrar_lote(self):
        # Crear lote abierto con un bin directo en BD
        lote = _make_lote(estado=LotePlantaEstado.ABIERTO)
        _make_bin(lote)
        self.client.session["lote_activo_code"] = lote.lote_code
        session = self.client.session
        session["lote_activo_code"] = lote.lote_code
        session["temporada_activa"] = TEMPORADA
        session.save()

        resp = self.client.post(self.url, {
            "action": "cerrar",
            "temporada": TEMPORADA,
            "operator_code": "OP-01",
            "kilos_bruto_conformacion": "500",
            "kilos_neto_conformacion": "480",
        })
        self.assertIn(resp.status_code, [200, 302])


# ---------------------------------------------------------------------------
# Flujo desverdizado: carga con selector/contexto
# ---------------------------------------------------------------------------

class DesverdizadoViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = _make_user()
        self.client.force_login(self.user)
        self.url = reverse("operaciones:desverdizado")

    def test_get_renderiza_con_lotes_pendientes(self):
        lote = _make_lote(
            estado=LotePlantaEstado.CERRADO,
            requiere_desverdizado=True,
            disponibilidad_camara_desverdizado="disponible",
        )
        _make_bin(lote)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("lotes_data_json", resp.context)
        self.assertIn(lote.lote_code, resp.context["lotes_data_json"])

    def test_contexto_lote_contiene_campos_base(self):
        lote = _make_lote(
            estado=LotePlantaEstado.CERRADO,
            requiere_desverdizado=True,
            disponibilidad_camara_desverdizado="disponible",
        )
        _make_bin(lote, codigo_productor="PROD-77", variedad_fruta="Red Globe")
        resp = self.client.get(self.url)
        self.assertIn("PROD-77", resp.context["lotes_data_json"])
        self.assertIn("Red Globe", resp.context["lotes_data_json"])


# ---------------------------------------------------------------------------
# Flujo ingreso packing: via_desverdizado derivado
# ---------------------------------------------------------------------------

class IngresoPackingViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = _make_user()
        self.client.force_login(self.user)
        self.url = reverse("operaciones:ingreso_packing")

    def test_get_renderiza(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("lotes_data_json", resp.context)

    def test_lote_con_desverdizado_tiene_via_desverdizado_true(self):
        lote = _make_lote(
            estado=LotePlantaEstado.CERRADO,
            requiere_desverdizado=True,
            disponibilidad_camara_desverdizado="disponible",
        )
        _make_bin(lote)
        Desverdizado.objects.create(
            lote=lote,
            source_system="test",
        )
        resp = self.client.get(self.url)
        import json
        data = json.loads(resp.context["lotes_data_json"])
        if lote.lote_code in data:
            self.assertTrue(data[lote.lote_code]["via_desverdizado"])


# ---------------------------------------------------------------------------
# horas_desverdizado se persiste en el modelo
# ---------------------------------------------------------------------------

class HorasDesverdizadoModelTest(TestCase):

    def test_campo_existe_y_persiste(self):
        lote = _make_lote(
            estado=LotePlantaEstado.CERRADO,
            requiere_desverdizado=True,
            disponibilidad_camara_desverdizado="disponible",
        )
        desv = Desverdizado.objects.create(
            lote=lote,
            horas_desverdizado=72,
            source_system="test",
        )
        desv.refresh_from_db()
        self.assertEqual(desv.horas_desverdizado, 72)
        # El campo proceso queda vacio (no se mezclan mas)
        self.assertEqual(desv.proceso, "")

    def test_horas_null_por_defecto(self):
        lote = _make_lote(estado=LotePlantaEstado.CERRADO, requiere_desverdizado=True)
        desv = Desverdizado.objects.create(lote=lote, source_system="test")
        desv.refresh_from_db()
        self.assertIsNone(desv.horas_desverdizado)

    def test_proceso_legacy_no_interfiere(self):
        """proceso (legacy) y horas_desverdizado son independientes."""
        lote = _make_lote(estado=LotePlantaEstado.CERRADO, requiere_desverdizado=True)
        desv = Desverdizado.objects.create(
            lote=lote, horas_desverdizado=48, proceso="conservacion frio",
            source_system="test",
        )
        desv.refresh_from_db()
        self.assertEqual(desv.horas_desverdizado, 48)
        self.assertEqual(desv.proceso, "conservacion frio")


# ---------------------------------------------------------------------------
# DesverdizadoForm — validacion server-side de horas_desverdizado
# ---------------------------------------------------------------------------

class DesverdizadoFormValidationTest(TestCase):

    def test_horas_valido(self):
        from operaciones.forms import DesverdizadoForm
        form = DesverdizadoForm(data={"horas_desverdizado": 72})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["horas_desverdizado"], 72)

    def test_horas_limite_inferior(self):
        from operaciones.forms import DesverdizadoForm
        form = DesverdizadoForm(data={"horas_desverdizado": 1})
        self.assertTrue(form.is_valid(), form.errors)

    def test_horas_limite_superior(self):
        from operaciones.forms import DesverdizadoForm
        form = DesverdizadoForm(data={"horas_desverdizado": 240})
        self.assertTrue(form.is_valid(), form.errors)

    def test_horas_cero_invalido(self):
        from operaciones.forms import DesverdizadoForm
        form = DesverdizadoForm(data={"horas_desverdizado": 0})
        self.assertFalse(form.is_valid())
        self.assertIn("horas_desverdizado", form.errors)

    def test_horas_excede_maximo(self):
        from operaciones.forms import DesverdizadoForm
        form = DesverdizadoForm(data={"horas_desverdizado": 241})
        self.assertFalse(form.is_valid())
        self.assertIn("horas_desverdizado", form.errors)

    def test_horas_negativo_invalido(self):
        from operaciones.forms import DesverdizadoForm
        form = DesverdizadoForm(data={"horas_desverdizado": -5})
        self.assertFalse(form.is_valid())

    def test_horas_vacio_ok(self):
        from operaciones.forms import DesverdizadoForm
        form = DesverdizadoForm(data={})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data["horas_desverdizado"])


# ---------------------------------------------------------------------------
# CalidadPalletMuestra — modelo y flujo
# ---------------------------------------------------------------------------

class CalidadPalletMuestraModelTest(TestCase):

    def setUp(self):
        self.lote = _make_lote(estado=LotePlantaEstado.CERRADO)
        _make_bin(self.lote)
        self.pallet = Pallet.objects.create(
            temporada=TEMPORADA,
            pallet_code=f"PAL-TEST-{Pallet.objects.count()+1:03d}",
            is_active=True,
        )
        PalletLote.objects.create(pallet=self.pallet, lote=self.lote)

    def test_crear_muestra(self):
        from operaciones.models import CalidadPalletMuestra
        m = CalidadPalletMuestra.objects.create(
            pallet=self.pallet,
            numero_muestra=1,
            temperatura_fruta=18.5,
            peso_caja_muestra=8.200,
            n_frutos=42,
            aprobado=True,
            source_system="test",
        )
        m.refresh_from_db()
        self.assertEqual(m.numero_muestra, 1)
        self.assertEqual(float(m.temperatura_fruta), 18.5)
        self.assertTrue(m.aprobado)

    def test_multiples_muestras_por_pallet(self):
        from operaciones.models import CalidadPalletMuestra
        for i in range(1, 4):
            CalidadPalletMuestra.objects.create(
                pallet=self.pallet, numero_muestra=i,
                temperatura_fruta=17 + i, source_system="test",
            )
        self.assertEqual(self.pallet.muestras_calidad.count(), 3)

    def test_muestra_sin_datos_opcionales(self):
        from operaciones.models import CalidadPalletMuestra
        m = CalidadPalletMuestra.objects.create(
            pallet=self.pallet, numero_muestra=1, source_system="test",
        )
        m.refresh_from_db()
        self.assertIsNone(m.temperatura_fruta)
        self.assertIsNone(m.aprobado)

    def test_ordering(self):
        from operaciones.models import CalidadPalletMuestra
        CalidadPalletMuestra.objects.create(
            pallet=self.pallet, numero_muestra=3, source_system="test",
        )
        CalidadPalletMuestra.objects.create(
            pallet=self.pallet, numero_muestra=1, source_system="test",
        )
        nums = list(
            self.pallet.muestras_calidad.values_list("numero_muestra", flat=True)
        )
        self.assertEqual(nums, [1, 3])


# ---------------------------------------------------------------------------
# PaletizadoView — contexto y flujo de muestras
# ---------------------------------------------------------------------------

class PaletizadoViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = _make_user()
        self.client.force_login(self.user)
        self.url = reverse("operaciones:paletizado")

    def test_get_incluye_form_muestra(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("form_muestra", resp.context)
        self.assertIn("pallets_data_json", resp.context)

    def test_pallets_data_json_contiene_campos(self):
        lote = _make_lote(estado=LotePlantaEstado.CERRADO)
        _make_bin(lote, codigo_productor="PROD-55", variedad_fruta="Flame")
        pallet = Pallet.objects.create(
            temporada=TEMPORADA,
            pallet_code="PAL-CTX-001",
            is_active=True,
            peso_total_kg=1200,
        )
        PalletLote.objects.create(pallet=pallet, lote=lote)
        resp = self.client.get(self.url)
        import json
        data = json.loads(resp.context["pallets_data_json"])
        if "PAL-CTX-001" in data:
            entry = data["PAL-CTX-001"]
            self.assertEqual(entry["productor"], "PROD-55")
            self.assertEqual(entry["variedad"], "Flame")
            self.assertEqual(entry["peso_total"], 1200.0)


# ---------------------------------------------------------------------------
# CamarasView — contexto con color y peso
# ---------------------------------------------------------------------------

class CamarasViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = _make_user()
        self.client.force_login(self.user)
        self.url = reverse("operaciones:camaras")

    def test_get_renderiza(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("pallets_data_json", resp.context)

    def test_pallets_data_incluye_color_y_peso(self):
        lote = _make_lote(estado=LotePlantaEstado.CERRADO)
        _make_bin(lote, color="4")
        pallet = Pallet.objects.create(
            temporada=TEMPORADA,
            pallet_code="PAL-CAM-001",
            is_active=True,
            peso_total_kg=950,
        )
        PalletLote.objects.create(pallet=pallet, lote=lote)
        resp = self.client.get(self.url)
        import json
        data = json.loads(resp.context["pallets_data_json"])
        if "PAL-CAM-001" in data:
            self.assertEqual(data["PAL-CAM-001"]["color"], "4")
            self.assertEqual(data["PAL-CAM-001"]["peso_total"], 950.0)
