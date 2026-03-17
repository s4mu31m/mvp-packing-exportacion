from django.test import TestCase

from operaciones.models import Bin, Lote, BinLote, Pallet, PalletLote, RegistroEtapa
from operaciones.application.use_cases.cerrar_pallet import cerrar_pallet


class CerrarPalletTests(TestCase):
    def setUp(self):
        self.bin_1 = Bin.objects.create(temporada="2026", bin_code="BIN-001")
        self.lote_1 = Lote.objects.create(
            temporada="2026", lote_code="LOT-001")
        BinLote.objects.create(bin=self.bin_1, lote=self.lote_1)

    def test_cierra_pallet_con_lote_existente(self):
        result = cerrar_pallet({
            "temporada": "2026",
            "pallet_code": "PAL-001",
            "lote_codes": ["LOT-001"],
            "operator_code": "OP-03",
        })

        self.assertTrue(result.ok)
        self.assertEqual(result.code, "PALLET_CLOSED")
        self.assertEqual(Pallet.objects.count(), 1)
        self.assertEqual(PalletLote.objects.count(), 1)
        self.assertEqual(RegistroEtapa.objects.count(), 1)
