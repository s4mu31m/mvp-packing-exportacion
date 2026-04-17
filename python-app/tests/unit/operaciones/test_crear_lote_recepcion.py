from django.test import TestCase

from operaciones.models import Bin, Lote, BinLote, RegistroEtapa
from operaciones.application.use_cases.crear_lote_recepcion import crear_lote_recepcion


class CrearLoteRecepcionTests(TestCase):
    def setUp(self):
        Bin.objects.create(temporada="2026", bin_code="BIN-001")
        Bin.objects.create(temporada="2026", bin_code="BIN-002")

    def test_crea_lote_y_relaciones(self):
        result = crear_lote_recepcion({
            "temporada": "2026",
            "lote_code": "LOT-001",
            "bin_codes": ["BIN-001", "BIN-002"],
            "operator_code": "OP-01",
        })

        self.assertTrue(result.ok)
        self.assertEqual(result.code, "LOTE_CREATED")
        self.assertEqual(Lote.objects.count(), 1)
        self.assertEqual(BinLote.objects.count(), 2)
        self.assertEqual(RegistroEtapa.objects.count(), 1)

    def test_rechaza_si_falta_un_bin(self):
        result = crear_lote_recepcion({
            "temporada": "2026",
            "lote_code": "LOT-001",
            "bin_codes": ["BIN-001", "BIN-999"],
        })

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "BINS_NOT_FOUND")
        self.assertEqual(Lote.objects.count(), 0)
        self.assertEqual(BinLote.objects.count(), 0)
