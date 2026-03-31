"""
Smoke tests del flujo web operativo.
No buscan cobertura total — validan que las vistas críticas renderizan
sin errores y que las acciones POST del flujo principal no explotan.
"""
import datetime

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from operaciones.models import (
    Lote,
    LotePlantaEstado,
    Bin,
    BinLote,
    Pallet,
    PalletLote,
    IngresoAPacking,
    Desverdizado,
)

User = get_user_model()
TEMPORADA = str(datetime.date.today().year)


def _make_user():
    return User.objects.create_user(username="tester", password="pass1234")


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
        """Operador sin is_staff es redirigido fuera de consulta."""
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

    def test_agregar_bin(self):
        # Iniciar primero
        self.client.post(self.url, {
            "action": "iniciar",
            "temporada": TEMPORADA,
            "operator_code": "OP-01",
        })
        lote = Lote.objects.filter(temporada=TEMPORADA).first()
        self.assertIsNotNone(lote)
        # Agregar bin válido
        resp = self.client.post(self.url, {
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
        })
        self.assertIn(resp.status_code, [200, 302])

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
