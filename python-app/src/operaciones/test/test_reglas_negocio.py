"""
Tests de reglas de negocio y validaciones de payload.
Cubre: formato hora, kilos neto <= bruto, rangos %, restricciones del flujo.
"""
from django.test import TestCase

from operaciones.application.use_cases import (
    registrar_bin_recibido,
    registrar_camara_mantencion,
    registrar_desverdizado,
    registrar_ingreso_packing,
    registrar_registro_packing,
    registrar_control_proceso_packing,
)
from .helpers import make_lote, make_lote_con_desverdizado, base_payload


# ---------------------------------------------------------------------------
# Validacion de formato hora
# ---------------------------------------------------------------------------

class ValidacionHoraTests(TestCase):

    def test_hora_invalida_bin(self):
        result = registrar_bin_recibido({
            "temporada": "2026",
            "bin_code": "BIN-001",
            "hora_recepcion": "8:30",  # falta 0 inicial
        })
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "INVALID_PAYLOAD")
        self.assertTrue(any("hora_recepcion" in e for e in result.errors))

    def test_hora_valida_bin(self):
        result = registrar_bin_recibido({
            "temporada": "2026",
            "bin_code": "BIN-001",
            "hora_recepcion": "08:30",
        })
        self.assertTrue(result.ok)

    def test_hora_invalida_camara_mantencion(self):
        make_lote_con_desverdizado(disponible=False)
        result = registrar_camara_mantencion(base_payload(
            lote_code="LOT-001",
            hora_ingreso="9:00",  # invalido
        ))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "INVALID_PAYLOAD")


# ---------------------------------------------------------------------------
# Validacion kilos neto <= bruto
# ---------------------------------------------------------------------------

class ValidacionKilosTests(TestCase):

    def test_kilos_neto_mayor_bruto_bin_rechazado(self):
        result = registrar_bin_recibido({
            "temporada": "2026",
            "bin_code": "BIN-001",
            "kilos_bruto_ingreso": "100",
            "kilos_neto_ingreso": "110",  # neto > bruto
        })
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "INVALID_PAYLOAD")
        self.assertTrue(any("kilos_neto_ingreso" in e for e in result.errors))

    def test_kilos_neto_igual_bruto_aceptado(self):
        result = registrar_bin_recibido({
            "temporada": "2026",
            "bin_code": "BIN-001",
            "kilos_bruto_ingreso": "100",
            "kilos_neto_ingreso": "100",
        })
        self.assertTrue(result.ok)

    def test_kilos_neto_menor_bruto_aceptado(self):
        result = registrar_bin_recibido({
            "temporada": "2026",
            "bin_code": "BIN-001",
            "kilos_bruto_ingreso": "100",
            "kilos_neto_ingreso": "95",
        })
        self.assertTrue(result.ok)

    def test_kilos_neto_mayor_bruto_desverdizado_rechazado(self):
        make_lote_con_desverdizado(disponible=True)
        result = registrar_desverdizado(base_payload(
            lote_code="LOT-001",
            kilos_bruto_salida="100",
            kilos_neto_salida="110",
        ))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "INVALID_PAYLOAD")


# ---------------------------------------------------------------------------
# Validacion porcentajes
# ---------------------------------------------------------------------------

class ValidacionPorcentajesTests(TestCase):

    def _setup_lote_con_ingreso(self):
        make_lote()
        registrar_ingreso_packing(base_payload(lote_code="LOT-001"))

    def test_merma_fuera_rango_rechazado(self):
        self._setup_lote_con_ingreso()
        result = registrar_registro_packing(base_payload(
            lote_code="LOT-001",
            merma_seleccion_pct="150",  # > 100
        ))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "INVALID_PAYLOAD")

    def test_rendimiento_fuera_rango_rechazado(self):
        self._setup_lote_con_ingreso()
        result = registrar_control_proceso_packing(base_payload(
            lote_code="LOT-001",
            rendimiento_lote_pct="-5",  # < 0
        ))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "INVALID_PAYLOAD")

    def test_merma_en_rango_aceptado(self):
        self._setup_lote_con_ingreso()
        result = registrar_registro_packing(base_payload(
            lote_code="LOT-001",
            merma_seleccion_pct="12.5",
        ))
        self.assertTrue(result.ok)


# ---------------------------------------------------------------------------
# Campos requeridos
# ---------------------------------------------------------------------------

class CamposRequeridosTests(TestCase):

    def test_bin_sin_temporada_rechazado(self):
        result = registrar_bin_recibido({"bin_code": "BIN-001"})
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "INVALID_PAYLOAD")

    def test_bin_sin_bin_code_se_genera_automaticamente(self):
        # bin_code es opcional: si no se provee, se genera en backend
        result = registrar_bin_recibido({"temporada": "2026"})
        self.assertTrue(result.ok)
        self.assertIsNotNone(result.data.get("bin_code"))

    def test_camara_mantencion_sin_lote_code_rechazado(self):
        result = registrar_camara_mantencion({"temporada": "2026"})
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "INVALID_PAYLOAD")


# ---------------------------------------------------------------------------
# Restriccion 1:1
# ---------------------------------------------------------------------------

class Restriccion1a1Tests(TestCase):

    def test_camara_mantencion_1a1(self):
        make_lote_con_desverdizado(disponible=False)
        r1 = registrar_camara_mantencion(base_payload(lote_code="LOT-001"))
        r2 = registrar_camara_mantencion(base_payload(lote_code="LOT-001"))
        self.assertTrue(r1.ok)
        self.assertFalse(r2.ok)
        self.assertEqual(r2.code, "CAMARA_MANTENCION_ALREADY_EXISTS")

    def test_desverdizado_1a1(self):
        make_lote_con_desverdizado(disponible=True)
        r1 = registrar_desverdizado(base_payload(lote_code="LOT-001"))
        r2 = registrar_desverdizado(base_payload(lote_code="LOT-001"))
        self.assertTrue(r1.ok)
        self.assertFalse(r2.ok)
        self.assertEqual(r2.code, "DESVERDIZADO_ALREADY_EXISTS")

    def test_ingreso_packing_1a1(self):
        make_lote()
        r1 = registrar_ingreso_packing(base_payload(lote_code="LOT-001"))
        r2 = registrar_ingreso_packing(base_payload(lote_code="LOT-001"))
        self.assertTrue(r1.ok)
        self.assertFalse(r2.ok)
        self.assertEqual(r2.code, "INGRESO_PACKING_ALREADY_EXISTS")
