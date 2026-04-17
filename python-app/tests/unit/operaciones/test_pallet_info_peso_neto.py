"""Test para verificar que _pallet_info obtiene el peso neto del IngresoAPacking."""
from decimal import Decimal
from django.test import TestCase
from django.conf import settings

from operaciones.models import Bin, Lote, BinLote, Pallet, PalletLote, IngresoAPacking
from operaciones.views import _pallet_info

# Forzar SQLite para estos tests
settings.PERSISTENCE_BACKEND = "sqlite"


class PalletInfoPesoNetoTests(TestCase):
    def setUp(self):
        self.temporada = "2026"
        self.bin = Bin.objects.create(temporada=self.temporada, bin_code="BIN-001")
        self.lote = Lote.objects.create(temporada=self.temporada, lote_code="LOT-001")
        BinLote.objects.create(bin=self.bin, lote=self.lote)
        self.pallet = Pallet.objects.create(
            temporada=self.temporada,
            pallet_code="PAL-001",
            peso_total_kg=Decimal("1000.00"),
        )
        PalletLote.objects.create(pallet=self.pallet, lote=self.lote)

    def test_pallet_info_sin_ingreso_packing(self):
        """Sin IngresoAPacking, debe usar peso_total_kg del pallet."""
        info = _pallet_info(self.temporada, "PAL-001")
        self.assertEqual(info["peso_total"], 1000.0)

    def test_pallet_info_con_ingreso_packing(self):
        """Con IngresoAPacking, debe usar kilos_neto_ingreso_packing."""
        ingreso = IngresoAPacking.objects.create(
            lote=self.lote,
            kilos_bruto_ingreso_packing=Decimal("1000.00"),
            kilos_neto_ingreso_packing=Decimal("950.50"),
        )
        info = _pallet_info(self.temporada, "PAL-001")
        self.assertEqual(info["peso_total"], 950.5)

    def test_pallet_info_ingreso_packing_sin_neto(self):
        """IngresoAPacking sin neto debe usar peso_total_kg del pallet."""
        ingreso = IngresoAPacking.objects.create(
            lote=self.lote,
            kilos_bruto_ingreso_packing=Decimal("1000.00"),
        )
        info = _pallet_info(self.temporada, "PAL-001")
        self.assertEqual(info["peso_total"], 1000.0)
