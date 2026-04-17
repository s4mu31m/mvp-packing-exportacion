"""
Tests para los use cases de etapas asociadas a Lote:
- registrar_camara_mantencion
- registrar_desverdizado
- registrar_calidad_desverdizado
- registrar_ingreso_packing
- registrar_registro_packing
- registrar_control_proceso_packing
"""
from django.test import TestCase

from operaciones.models import (
    CamaraMantencion, Desverdizado, CalidadDesverdizado,
    IngresoAPacking, RegistroPacking, ControlProcesoPacking,
    RegistroEtapa, TipoEvento,
)
from operaciones.application.use_cases import (
    registrar_camara_mantencion,
    registrar_desverdizado,
    registrar_calidad_desverdizado,
    registrar_ingreso_packing,
    registrar_registro_packing,
    registrar_control_proceso_packing,
)
from .helpers import make_lote, make_lote_con_desverdizado, base_payload


# ---------------------------------------------------------------------------
# CamaraMantencion
# ---------------------------------------------------------------------------

class RegistrarCamaraMantencionTests(TestCase):

    def test_crea_registro_y_evento(self):
        make_lote_con_desverdizado(disponible=False)
        result = registrar_camara_mantencion(base_payload(lote_code="LOT-001"))
        self.assertTrue(result.ok)
        self.assertEqual(result.code, "CAMARA_MANTENCION_REGISTERED")
        self.assertEqual(CamaraMantencion.objects.count(), 1)
        self.assertEqual(
            RegistroEtapa.objects.filter(tipo_evento=TipoEvento.CAMARA_MANTENCION).count(), 1
        )

    def test_rechaza_lote_inexistente(self):
        result = registrar_camara_mantencion(base_payload(lote_code="NO-EXISTE"))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "LOTE_NOT_FOUND")

    def test_rechaza_si_no_requiere_desverdizado(self):
        make_lote()  # requiere_desverdizado=False por defecto
        result = registrar_camara_mantencion(base_payload(lote_code="LOT-001"))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "CAMARA_MANTENCION_NO_APLICA")

    def test_rechaza_si_camara_disponible(self):
        make_lote_con_desverdizado(disponible=True)
        result = registrar_camara_mantencion(base_payload(lote_code="LOT-001"))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "CAMARA_DISPONIBLE")

    def test_rechaza_duplicado(self):
        make_lote_con_desverdizado(disponible=False)
        registrar_camara_mantencion(base_payload(lote_code="LOT-001"))
        result = registrar_camara_mantencion(base_payload(lote_code="LOT-001"))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "CAMARA_MANTENCION_ALREADY_EXISTS")
        self.assertEqual(CamaraMantencion.objects.count(), 1)

    def test_idempotencia_evento(self):
        make_lote_con_desverdizado(disponible=False)
        registrar_camara_mantencion(base_payload(lote_code="LOT-001"))
        # El event_key ya existe — get_or_create no duplica
        self.assertEqual(
            RegistroEtapa.objects.filter(tipo_evento=TipoEvento.CAMARA_MANTENCION).count(), 1
        )


# ---------------------------------------------------------------------------
# Desverdizado
# ---------------------------------------------------------------------------

class RegistrarDesverdizadoTests(TestCase):

    def test_crea_registro_y_evento(self):
        make_lote_con_desverdizado(disponible=True)
        result = registrar_desverdizado(base_payload(lote_code="LOT-001"))
        self.assertTrue(result.ok)
        self.assertEqual(result.code, "DESVERDIZADO_REGISTERED")
        self.assertEqual(Desverdizado.objects.count(), 1)
        self.assertEqual(
            RegistroEtapa.objects.filter(tipo_evento=TipoEvento.DESVERDIZADO_INGRESO).count(), 1
        )

    def test_rechaza_lote_inexistente(self):
        result = registrar_desverdizado(base_payload(lote_code="NO-EXISTE"))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "LOTE_NOT_FOUND")

    def test_rechaza_si_no_requiere_desverdizado(self):
        make_lote()
        result = registrar_desverdizado(base_payload(lote_code="LOT-001"))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "DESVERDIZADO_NO_APLICA")

    def test_rechaza_si_camara_no_disponible(self):
        make_lote_con_desverdizado(disponible=False)
        result = registrar_desverdizado(base_payload(lote_code="LOT-001"))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "CAMARA_NO_DISPONIBLE")

    def test_rechaza_duplicado(self):
        make_lote_con_desverdizado(disponible=True)
        registrar_desverdizado(base_payload(lote_code="LOT-001"))
        result = registrar_desverdizado(base_payload(lote_code="LOT-001"))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "DESVERDIZADO_ALREADY_EXISTS")
        self.assertEqual(Desverdizado.objects.count(), 1)


# ---------------------------------------------------------------------------
# CalidadDesverdizado
# ---------------------------------------------------------------------------

class RegistrarCalidadDesverdizadoTests(TestCase):

    def _setup(self):
        make_lote_con_desverdizado(disponible=True)
        registrar_desverdizado(base_payload(lote_code="LOT-001"))

    def test_crea_registro_y_evento(self):
        self._setup()
        result = registrar_calidad_desverdizado(base_payload(lote_code="LOT-001"))
        self.assertTrue(result.ok)
        self.assertEqual(result.code, "CALIDAD_DESVERDIZADO_REGISTERED")
        self.assertEqual(CalidadDesverdizado.objects.count(), 1)
        self.assertEqual(
            RegistroEtapa.objects.filter(tipo_evento=TipoEvento.CALIDAD_DESVERDIZADO).count(), 1
        )

    def test_permite_multiples_registros(self):
        self._setup()
        registrar_calidad_desverdizado(base_payload(lote_code="LOT-001"))
        registrar_calidad_desverdizado(base_payload(lote_code="LOT-001"))
        self.assertEqual(CalidadDesverdizado.objects.count(), 2)

    def test_rechaza_sin_desverdizado_previo(self):
        make_lote_con_desverdizado(disponible=True)  # sin crear desverdizado
        result = registrar_calidad_desverdizado(base_payload(lote_code="LOT-001"))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "DESVERDIZADO_NOT_FOUND")

    def test_rechaza_lote_inexistente(self):
        result = registrar_calidad_desverdizado(base_payload(lote_code="NO-EXISTE"))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "LOTE_NOT_FOUND")


# ---------------------------------------------------------------------------
# IngresoAPacking
# ---------------------------------------------------------------------------

class RegistrarIngresoPackingTests(TestCase):

    def test_crea_registro_directo(self):
        make_lote()
        result = registrar_ingreso_packing(base_payload(lote_code="LOT-001"))
        self.assertTrue(result.ok)
        self.assertEqual(result.code, "INGRESO_PACKING_REGISTERED")
        self.assertEqual(IngresoAPacking.objects.count(), 1)
        self.assertFalse(result.data["via_desverdizado"])

    def test_autodetecta_via_desverdizado(self):
        make_lote_con_desverdizado(disponible=True)
        registrar_desverdizado(base_payload(lote_code="LOT-001"))
        result = registrar_ingreso_packing(base_payload(lote_code="LOT-001"))
        self.assertTrue(result.ok)
        self.assertTrue(result.data["via_desverdizado"])

    def test_rechaza_duplicado(self):
        make_lote()
        registrar_ingreso_packing(base_payload(lote_code="LOT-001"))
        result = registrar_ingreso_packing(base_payload(lote_code="LOT-001"))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "INGRESO_PACKING_ALREADY_EXISTS")
        self.assertEqual(IngresoAPacking.objects.count(), 1)

    def test_rechaza_lote_inexistente(self):
        result = registrar_ingreso_packing(base_payload(lote_code="NO-EXISTE"))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "LOTE_NOT_FOUND")

    def test_registra_evento_ingreso_packing(self):
        make_lote()
        registrar_ingreso_packing(base_payload(lote_code="LOT-001"))
        self.assertEqual(
            RegistroEtapa.objects.filter(tipo_evento=TipoEvento.INGRESO_PACKING).count(), 1
        )


# ---------------------------------------------------------------------------
# RegistroPacking
# ---------------------------------------------------------------------------

class RegistrarRegistroPackingTests(TestCase):

    def _setup(self):
        make_lote()
        registrar_ingreso_packing(base_payload(lote_code="LOT-001"))

    def test_crea_registro_y_evento(self):
        self._setup()
        result = registrar_registro_packing(base_payload(lote_code="LOT-001"))
        self.assertTrue(result.ok)
        self.assertEqual(result.code, "REGISTRO_PACKING_REGISTERED")
        self.assertEqual(RegistroPacking.objects.count(), 1)

    def test_permite_multiples_registros(self):
        self._setup()
        registrar_registro_packing(base_payload(lote_code="LOT-001"))
        registrar_registro_packing(base_payload(lote_code="LOT-001"))
        self.assertEqual(RegistroPacking.objects.count(), 2)

    def test_rechaza_sin_ingreso_packing_previo(self):
        make_lote()
        result = registrar_registro_packing(base_payload(lote_code="LOT-001"))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "INGRESO_PACKING_REQUIRED")

    def test_rechaza_lote_inexistente(self):
        result = registrar_registro_packing(base_payload(lote_code="NO-EXISTE"))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "LOTE_NOT_FOUND")


# ---------------------------------------------------------------------------
# ControlProcesoPacking
# ---------------------------------------------------------------------------

class RegistrarControlProcesoPackingTests(TestCase):

    def _setup(self):
        make_lote()
        registrar_ingreso_packing(base_payload(lote_code="LOT-001"))

    def test_crea_registro_y_evento(self):
        self._setup()
        result = registrar_control_proceso_packing(base_payload(lote_code="LOT-001"))
        self.assertTrue(result.ok)
        self.assertEqual(result.code, "CONTROL_PROCESO_PACKING_REGISTERED")
        self.assertEqual(ControlProcesoPacking.objects.count(), 1)

    def test_permite_multiples_registros(self):
        self._setup()
        registrar_control_proceso_packing(base_payload(lote_code="LOT-001"))
        registrar_control_proceso_packing(base_payload(lote_code="LOT-001"))
        self.assertEqual(ControlProcesoPacking.objects.count(), 2)

    def test_rechaza_sin_ingreso_packing_previo(self):
        make_lote()
        result = registrar_control_proceso_packing(base_payload(lote_code="LOT-001"))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "INGRESO_PACKING_REQUIRED")
