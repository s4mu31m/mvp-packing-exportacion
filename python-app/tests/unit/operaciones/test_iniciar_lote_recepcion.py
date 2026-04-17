"""
Tests para el nuevo flujo de recepcion con lote abierto:
  iniciar_lote_recepcion → agregar_bin_a_lote_abierto → cerrar_lote_recepcion
"""
from django.test import TestCase

from operaciones.application.use_cases import (
    iniciar_lote_recepcion,
    agregar_bin_a_lote_abierto,
    cerrar_lote_recepcion,
)
from operaciones.models import Lote, LotePlantaEstado
from tests.unit.operaciones.helpers import base_payload


class IniciarLoteRecepcionTest(TestCase):

    def test_crea_lote_abierto_con_lote_code_autogenerado(self):
        payload = base_payload(temporada="2026", temporada_codigo="2025-2026")
        result = iniciar_lote_recepcion(payload)

        self.assertTrue(result.ok, result.errors)
        self.assertIn("lote_id", result.data)
        lote_code = result.data["lote_code"]
        self.assertTrue(lote_code.startswith("LP-2025-2026-"), lote_code)
        self.assertEqual(result.data["estado"], LotePlantaEstado.ABIERTO)

    def test_lote_queda_en_bd_con_estado_abierto(self):
        payload = base_payload(temporada="2026", temporada_codigo="2025-2026")
        result = iniciar_lote_recepcion(payload)

        lote = Lote.objects.get(pk=result.data["lote_id"])
        self.assertEqual(lote.estado, LotePlantaEstado.ABIERTO)
        self.assertEqual(lote.temporada_codigo, "2025-2026")
        self.assertEqual(lote.correlativo_temporada, 1)

    def test_correlativos_de_temporada_ascienden(self):
        payload = base_payload(temporada="2026", temporada_codigo="2025-2026")
        r1 = iniciar_lote_recepcion(payload)
        r2 = iniciar_lote_recepcion(payload)

        self.assertTrue(r1.ok)
        self.assertTrue(r2.ok)
        c1 = r1.data["correlativo_temporada"]
        c2 = r2.data["correlativo_temporada"]
        self.assertEqual(c1, 1)
        self.assertEqual(c2, 2)

    def test_temporadas_distintas_correlativos_independientes(self):
        r1 = iniciar_lote_recepcion(base_payload(temporada="2026", temporada_codigo="2025-2026"))
        r2 = iniciar_lote_recepcion(base_payload(temporada="2027", temporada_codigo="2026-2027"))

        self.assertEqual(r1.data["correlativo_temporada"], 1)
        self.assertEqual(r2.data["correlativo_temporada"], 1)

    def test_sin_temporada_falla(self):
        result = iniciar_lote_recepcion({})
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "INVALID_PAYLOAD")


class AgregarBinALoteAbiertoTest(TestCase):

    def setUp(self):
        payload = base_payload(temporada="2026", temporada_codigo="2025-2026")
        result = iniciar_lote_recepcion(payload)
        self.lote_code = result.data["lote_code"]

    def test_agrega_bin_y_retorna_bin_code(self):
        payload = base_payload(
            temporada="2026",
            lote_code=self.lote_code,
            fecha_cosecha="2026-03-29",
            variedad_fruta="Thompson Seedless",
        )
        result = agregar_bin_a_lote_abierto(payload)

        self.assertTrue(result.ok, result.errors)
        bin_code = result.data["bin_code"]
        self.assertIn("290326", bin_code)  # DDMMYY format per Excel "Codigo de barra"

    def test_bin_code_se_genera_automaticamente(self):
        payload = base_payload(temporada="2026", lote_code=self.lote_code)
        result = agregar_bin_a_lote_abierto(payload)
        self.assertTrue(result.ok, result.errors)
        self.assertIsNotNone(result.data.get("bin_code"))

    def test_multiples_bins_incrementan_correlativo(self):
        p = base_payload(temporada="2026", lote_code=self.lote_code, fecha_cosecha="2026-03-29")
        r1 = agregar_bin_a_lote_abierto(p)
        r2 = agregar_bin_a_lote_abierto(p)
        n1 = int(r1.data["bin_code"].split("-")[-1])
        n2 = int(r2.data["bin_code"].split("-")[-1])
        self.assertEqual(n2, n1 + 1)

    def test_falla_si_lote_no_existe(self):
        payload = base_payload(temporada="2026", lote_code="LP-INEXISTENTE-000099")
        result = agregar_bin_a_lote_abierto(payload)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "LOTE_NOT_FOUND")

    def test_falla_si_lote_ya_cerrado(self):
        # Cerrar primero el lote
        p_bin = base_payload(temporada="2026", lote_code=self.lote_code)
        agregar_bin_a_lote_abierto(p_bin)
        cerrar_lote_recepcion(base_payload(temporada="2026", lote_code=self.lote_code))

        # Intentar agregar al lote cerrado
        result = agregar_bin_a_lote_abierto(p_bin)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "LOTE_NOT_OPEN")


class CerrarLoteRecepcionTest(TestCase):

    def setUp(self):
        payload = base_payload(temporada="2026", temporada_codigo="2025-2026")
        result = iniciar_lote_recepcion(payload)
        self.lote_code = result.data["lote_code"]
        # Agregar un bin para poder cerrar
        agregar_bin_a_lote_abierto(
            base_payload(temporada="2026", lote_code=self.lote_code)
        )

    def test_cierra_lote_correctamente(self):
        payload = base_payload(temporada="2026", lote_code=self.lote_code)
        result = cerrar_lote_recepcion(payload)
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.data["estado"], LotePlantaEstado.CERRADO)

    def test_lote_queda_cerrado_en_bd(self):
        cerrar_lote_recepcion(base_payload(temporada="2026", lote_code=self.lote_code))
        lote = Lote.objects.get(lote_code=self.lote_code)
        self.assertEqual(lote.estado, LotePlantaEstado.CERRADO)

    def test_no_se_puede_cerrar_dos_veces(self):
        cerrar_lote_recepcion(base_payload(temporada="2026", lote_code=self.lote_code))
        result = cerrar_lote_recepcion(base_payload(temporada="2026", lote_code=self.lote_code))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "LOTE_NOT_OPEN")

    def test_no_se_puede_cerrar_sin_bins(self):
        # Crear un lote nuevo sin bins
        r = iniciar_lote_recepcion(base_payload(temporada="2026", temporada_codigo="2025-2026"))
        lote_code_nuevo = r.data["lote_code"]
        result = cerrar_lote_recepcion(base_payload(temporada="2026", lote_code=lote_code_nuevo))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "LOTE_SIN_BINS")

    def test_falla_si_lote_no_existe(self):
        result = cerrar_lote_recepcion(base_payload(temporada="2026", lote_code="LP-INEXISTENTE-000099"))
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "LOTE_NOT_FOUND")


class FlujoCompletoRecepcionTest(TestCase):
    """Test del flujo completo: iniciar → agregar bins → cerrar."""

    def test_flujo_completo(self):
        temporada = "2026"
        temporada_codigo = "2025-2026"

        # 1. Iniciar lote
        r_inicio = iniciar_lote_recepcion(
            base_payload(temporada=temporada, temporada_codigo=temporada_codigo)
        )
        self.assertTrue(r_inicio.ok)
        lote_code = r_inicio.data["lote_code"]

        # 2. Agregar 3 bins
        bin_codes = []
        for _ in range(3):
            r = agregar_bin_a_lote_abierto(
                base_payload(temporada=temporada, lote_code=lote_code,
                             fecha_cosecha="2026-03-01")
            )
            self.assertTrue(r.ok, r.errors)
            bin_codes.append(r.data["bin_code"])

        # Todos los bin codes son distintos
        self.assertEqual(len(set(bin_codes)), 3)

        # 3. Cerrar lote
        r_cierre = cerrar_lote_recepcion(
            base_payload(temporada=temporada, lote_code=lote_code)
        )
        self.assertTrue(r_cierre.ok, r_cierre.errors)
        self.assertEqual(r_cierre.data["cantidad_bins"], 3)

        # 4. Verificar que ya no se pueden agregar bins
        r_extra = agregar_bin_a_lote_abierto(
            base_payload(temporada=temporada, lote_code=lote_code)
        )
        self.assertFalse(r_extra.ok)
        self.assertEqual(r_extra.code, "LOTE_NOT_OPEN")
