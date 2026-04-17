"""
Tests para generacion dinamica de codigos y correlativos por temporada.
Cubre: season.py, sequences.py, code_generators.py
"""
import datetime
from django.test import TestCase

from operaciones.services.season import resolve_temporada_codigo
from operaciones.services.sequences import get_next_sequence
from operaciones.services.code_generators import (
    build_bin_code,
    build_lote_code,
    build_pallet_code,
    next_lote_correlativo,
)


class ResolveTemporadaCodigoTest(TestCase):

    def test_mes_octubre_inicia_nueva_temporada(self):
        fecha = datetime.date(2025, 10, 1)
        self.assertEqual(resolve_temporada_codigo(fecha), "2025-2026")

    def test_mes_enero_pertenece_temporada_anterior(self):
        fecha = datetime.date(2026, 1, 15)
        self.assertEqual(resolve_temporada_codigo(fecha), "2025-2026")

    def test_mes_septiembre_pertenece_temporada_anterior(self):
        fecha = datetime.date(2026, 9, 30)
        self.assertEqual(resolve_temporada_codigo(fecha), "2025-2026")

    def test_mes_octubre_siguiente_ano_nueva_temporada(self):
        fecha = datetime.date(2026, 10, 1)
        self.assertEqual(resolve_temporada_codigo(fecha), "2026-2027")

    def test_string_fecha_valida(self):
        self.assertEqual(resolve_temporada_codigo("2025-11-01"), "2025-2026")

    def test_string_fecha_invalida_usa_hoy(self):
        # No debe lanzar excepcion
        result = resolve_temporada_codigo("no-es-fecha")
        self.assertIn("-", result)

    def test_none_usa_hoy(self):
        result = resolve_temporada_codigo(None)
        self.assertIn("-", result)


class GetNextSequenceTest(TestCase):

    def test_primer_correlativo_es_uno(self):
        val = get_next_sequence("lote", "2025-2026")
        self.assertEqual(val, 1)

    def test_segundo_correlativo_es_dos(self):
        get_next_sequence("lote", "2025-2026")
        val = get_next_sequence("lote", "2025-2026")
        self.assertEqual(val, 2)

    def test_distintas_dimensiones_son_independientes(self):
        v1 = get_next_sequence("lote", "2025-2026")
        v2 = get_next_sequence("lote", "2026-2027")
        self.assertEqual(v1, 1)
        self.assertEqual(v2, 1)

    def test_distintas_entidades_son_independientes(self):
        v_lote   = get_next_sequence("lote", "20260329")
        v_bin    = get_next_sequence("bin",  "20260329")
        v_pallet = get_next_sequence("pallet", "20260329")
        self.assertEqual(v_lote, 1)
        self.assertEqual(v_bin, 1)
        self.assertEqual(v_pallet, 1)

    def test_correlativo_nunca_regresa_a_cero(self):
        for _ in range(5):
            get_next_sequence("lote", "2025-2026")
        val = get_next_sequence("lote", "2025-2026")
        self.assertEqual(val, 6)


class BuildBinCodeTest(TestCase):
    """
    Formato: {codigo_productor}-{tipo_cultivo}-{variedad_fruta}-{numero_cuartel}-{DDMMYY}-{correlativo:03d}
    Ejemplo: AG01-LM-Eur-C05-120326-001
    """

    def _kwargs(self, fecha="2026-03-12"):
        return dict(
            codigo_productor="AG01",
            tipo_cultivo="LM",
            variedad_fruta="Eur",
            numero_cuartel="C05",
            fecha_cosecha=fecha,
        )

    def test_formato_correcto(self):
        codigo = build_bin_code(**self._kwargs())
        # AG01-LM-Eur-C05-120326-001
        partes = codigo.split("-")
        self.assertEqual(partes[0], "AG01")
        self.assertEqual(partes[1], "LM")
        self.assertEqual(partes[2], "Eur")
        self.assertEqual(partes[3], "C05")
        self.assertEqual(partes[4], "120326")   # DDMMYY
        self.assertEqual(partes[5], "001")

    def test_fecha_en_formato_ddmmyy(self):
        codigo = build_bin_code(**self._kwargs(fecha="2026-03-29"))
        self.assertIn("290326", codigo)

    def test_correlativo_incrementa_mismo_conjunto(self):
        c1 = build_bin_code(**self._kwargs())
        c2 = build_bin_code(**self._kwargs())
        n1 = int(c1.split("-")[-1])
        n2 = int(c2.split("-")[-1])
        self.assertEqual(n2, n1 + 1)

    def test_distintos_productores_correlativos_independientes(self):
        c1 = build_bin_code(codigo_productor="AG01", tipo_cultivo="LM", variedad_fruta="Eur",
                            numero_cuartel="C05", fecha_cosecha="2026-03-12")
        c2 = build_bin_code(codigo_productor="AG02", tipo_cultivo="LM", variedad_fruta="Eur",
                            numero_cuartel="C05", fecha_cosecha="2026-03-12")
        n1 = int(c1.split("-")[-1])
        n2 = int(c2.split("-")[-1])
        self.assertEqual(n1, 1)
        self.assertEqual(n2, 1)

    def test_distintas_fechas_correlativos_independientes(self):
        c1 = build_bin_code(**self._kwargs(fecha="2026-03-12"))
        c2 = build_bin_code(**self._kwargs(fecha="2026-03-13"))
        n1 = int(c1.split("-")[-1])
        n2 = int(c2.split("-")[-1])
        self.assertEqual(n1, 1)
        self.assertEqual(n2, 1)

    def test_campos_vacios_usan_placeholder(self):
        codigo = build_bin_code(fecha_cosecha="2026-03-12")
        self.assertIn("XX", codigo)

    def test_sin_fecha_usa_hoy(self):
        codigo = build_bin_code(codigo_productor="AG01", tipo_cultivo="LM",
                                variedad_fruta="Eur", numero_cuartel="C05")
        self.assertIsNotNone(codigo)
        self.assertIn("-", codigo)


class BuildLoteCodeTest(TestCase):

    def test_formato_correcto(self):
        codigo = build_lote_code("2025-2026", 1)
        self.assertEqual(codigo, "LP-2025-2026-000001")

    def test_correlativo_padded_6_digitos(self):
        codigo = build_lote_code("2025-2026", 257)
        self.assertEqual(codigo, "LP-2025-2026-000257")

    def test_temporada_en_codigo(self):
        codigo = build_lote_code("2026-2027", 1)
        self.assertIn("2026-2027", codigo)


class BuildPalletCodeTest(TestCase):

    def test_formato_correcto(self):
        codigo = build_pallet_code(fecha=datetime.date(2026, 3, 29))
        partes = codigo.split("-")
        self.assertEqual(partes[0], "PA")
        self.assertEqual(partes[1], "20260329")
        self.assertEqual(len(partes[2]), 4)

    def test_correlativo_diario_incrementa(self):
        c1 = build_pallet_code(fecha=datetime.date(2026, 3, 29))
        c2 = build_pallet_code(fecha=datetime.date(2026, 3, 29))
        n1 = int(c1.split("-")[2])
        n2 = int(c2.split("-")[2])
        self.assertEqual(n2, n1 + 1)


class NextLoteCorrelativoTest(TestCase):

    def test_devuelve_lote_code_y_correlativo(self):
        lote_code, correlativo = next_lote_correlativo("2025-2026")
        self.assertEqual(lote_code, "LP-2025-2026-000001")
        self.assertEqual(correlativo, 1)

    def test_correlativo_sube_dentro_temporada(self):
        _, c1 = next_lote_correlativo("2025-2026")
        _, c2 = next_lote_correlativo("2025-2026")
        _, c3 = next_lote_correlativo("2025-2026")
        self.assertEqual(c1, 1)
        self.assertEqual(c2, 2)
        self.assertEqual(c3, 3)

    def test_nueva_temporada_reinicia_correlativo(self):
        _, c_a = next_lote_correlativo("2025-2026")
        _, c_b = next_lote_correlativo("2026-2027")
        self.assertEqual(c_a, 1)
        self.assertEqual(c_b, 1)
