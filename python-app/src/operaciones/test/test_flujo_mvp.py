from django.test import TestCase

from operaciones.models import Bin, Lote, Pallet, BinLote, PalletLote, RegistroEtapa
from operaciones.application.use_cases.registrar_bin_recibido import registrar_bin_recibido
from operaciones.application.use_cases.crear_lote_recepcion import crear_lote_recepcion
from operaciones.application.use_cases.cerrar_pallet import cerrar_pallet


class FlujoMVPTests(TestCase):
    def test_flujo_completo(self):
        r1 = registrar_bin_recibido({"temporada": "2026", "bin_code": "BIN-001"})
        r2 = registrar_bin_recibido({"temporada": "2026", "bin_code": "BIN-002"})
        r3 = crear_lote_recepcion({
            "temporada": "2026",
            "lote_code": "LOT-001",
            "bin_codes": ["BIN-001", "BIN-002"],
        })
        r4 = cerrar_pallet({
            "temporada": "2026",
            "pallet_code": "PAL-001",
            "lote_codes": ["LOT-001"],
        })

        self.assertTrue(r1.ok)
        self.assertTrue(r2.ok)
        self.assertTrue(r3.ok)
        self.assertTrue(r4.ok)

        self.assertEqual(Bin.objects.count(), 2)
        self.assertEqual(Lote.objects.count(), 1)
        self.assertEqual(Pallet.objects.count(), 1)
        self.assertEqual(BinLote.objects.count(), 2)
        self.assertEqual(PalletLote.objects.count(), 1)
        self.assertGreaterEqual(RegistroEtapa.objects.count(), 3)