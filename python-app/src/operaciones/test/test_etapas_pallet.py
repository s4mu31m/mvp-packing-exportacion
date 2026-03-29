"""
Tests para los use cases de etapas asociadas a Pallet:
- registrar_calidad_pallet
- registrar_camara_frio
- registrar_medicion_temperatura
"""
from django.test import TestCase

from operaciones.models import (
    CalidadPallet, CamaraFrio, MedicionTemperaturaSalida,
    RegistroEtapa, TipoEvento,
)
from operaciones.application.use_cases import (
    registrar_calidad_pallet,
    registrar_camara_frio,
    registrar_medicion_temperatura,
)
from .helpers import make_pallet, base_payload


class RegistrarCalidadPalletTests(TestCase):

    def test_crea_registro_y_evento(self):
        make_pallet()
        result = registrar_calidad_pallet(base_payload(pallet_code="PAL-001"))
        self.assertTrue(result.ok)
        self.assertEqual(result.code, "CALIDAD_PALLET_REGISTERED")
        self.assertEqual(CalidadPallet.objects.count(), 1)
        self.assertEqual(
            RegistroEtapa.objects.filter(tipo_evento=TipoEvento.CALIDAD_PALLET).count(), 1
        )

    def test_permite_multiples_registros(self):
        make_pallet()
        registrar_calidad_pallet(base_payload(pallet_code="PAL-001"))
        registrar_calidad_pallet(base_payload(pallet_code="PAL-001"))
        self.assertEqual(CalidadPallet.objects.count(), 2)

    def test_rechaza_pallet_inexistente(self):
        result = registrar_calidad_pallet(base_payload(pallet_code="NO-EXISTE"))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "PALLET_NOT_FOUND")

    def test_devuelve_campo_aprobado(self):
        make_pallet()
        result = registrar_calidad_pallet(base_payload(pallet_code="PAL-001"))
        self.assertIn("aprobado", result.data)


class RegistrarCamaraFrioTests(TestCase):

    def test_crea_registro_y_evento(self):
        make_pallet()
        result = registrar_camara_frio(base_payload(pallet_code="PAL-001"))
        self.assertTrue(result.ok)
        self.assertEqual(result.code, "CAMARA_FRIO_REGISTERED")
        self.assertEqual(CamaraFrio.objects.count(), 1)
        self.assertEqual(
            RegistroEtapa.objects.filter(tipo_evento=TipoEvento.CAMARA_FRIO_INGRESO).count(), 1
        )

    def test_rechaza_pallet_inexistente(self):
        result = registrar_camara_frio(base_payload(pallet_code="NO-EXISTE"))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "PALLET_NOT_FOUND")

    def test_rechaza_duplicado(self):
        make_pallet()
        registrar_camara_frio(base_payload(pallet_code="PAL-001"))
        result = registrar_camara_frio(base_payload(pallet_code="PAL-001"))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "CAMARA_FRIO_ALREADY_EXISTS")
        self.assertEqual(CamaraFrio.objects.count(), 1)

    def test_idempotencia_evento(self):
        make_pallet()
        registrar_camara_frio(base_payload(pallet_code="PAL-001"))
        self.assertEqual(
            RegistroEtapa.objects.filter(tipo_evento=TipoEvento.CAMARA_FRIO_INGRESO).count(), 1
        )


class RegistrarMedicionTemperaturaTests(TestCase):

    def _setup(self):
        make_pallet()
        registrar_camara_frio(base_payload(pallet_code="PAL-001"))

    def test_crea_registro_y_evento(self):
        self._setup()
        result = registrar_medicion_temperatura(base_payload(pallet_code="PAL-001"))
        self.assertTrue(result.ok)
        self.assertEqual(result.code, "MEDICION_TEMPERATURA_REGISTERED")
        self.assertEqual(MedicionTemperaturaSalida.objects.count(), 1)
        self.assertEqual(
            RegistroEtapa.objects.filter(tipo_evento=TipoEvento.CONTROL_TEMPERATURA).count(), 1
        )

    def test_permite_multiples_mediciones(self):
        self._setup()
        registrar_medicion_temperatura(base_payload(pallet_code="PAL-001"))
        registrar_medicion_temperatura(base_payload(pallet_code="PAL-001"))
        self.assertEqual(MedicionTemperaturaSalida.objects.count(), 2)

    def test_rechaza_pallet_inexistente(self):
        result = registrar_medicion_temperatura(base_payload(pallet_code="NO-EXISTE"))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "PALLET_NOT_FOUND")

    def test_rechaza_sin_camara_frio_previa(self):
        make_pallet()
        result = registrar_medicion_temperatura(base_payload(pallet_code="PAL-001"))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "CAMARA_FRIO_REQUIRED")

    def test_devuelve_campo_dentro_rango(self):
        self._setup()
        result = registrar_medicion_temperatura(base_payload(pallet_code="PAL-001"))
        self.assertIn("dentro_rango", result.data)
