from django.test import TestCase

from operaciones.models import Bin, RegistroEtapa, TipoEvento
from operaciones.application.use_cases.registrar_bin_recibido import registrar_bin_recibido


class RegistrarBinRecibidoTests(TestCase):
    def test_crea_bin_y_registra_evento(self):
        result = registrar_bin_recibido({
            "temporada": "2026",
            "bin_code": "BIN-001",
            "operator_code": "OP-01",
            "source_system": "local",
            "source_event_id": "evt-001",
        })

        self.assertTrue(result.ok)
        self.assertEqual(result.code, "BIN_REGISTERED")
        self.assertEqual(Bin.objects.count(), 1)
        self.assertEqual(
            Bin.objects.filter(temporada="2026", bin_code="BIN-001").count(),
            1,
        )
        self.assertEqual(
            RegistroEtapa.objects.filter(
                tipo_evento=TipoEvento.BIN_REGISTRADO).count(),
            1,
        )

    def test_rechaza_bin_duplicado(self):
        Bin.objects.create(
            temporada="2026",
            bin_code="BIN-001",
            operator_code="OP-01",
            source_system="local",
            source_event_id="seed-001",
        )

        result = registrar_bin_recibido({
            "temporada": "2026",
            "bin_code": "BIN-001",
            "operator_code": "OP-02",
        })

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "BIN_ALREADY_EXISTS")
        self.assertEqual(Bin.objects.count(), 1)
