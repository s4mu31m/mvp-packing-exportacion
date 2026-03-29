"""
Tests de flujo completo extendido.
Verifica la cadena de use cases de principio a fin,
incluyendo la rama con y sin desverdizado.
"""
from django.test import TestCase

from operaciones.models import RegistroEtapa, CamaraFrio, IngresoAPacking
from operaciones.application.use_cases import (
    registrar_bin_recibido,
    crear_lote_recepcion,
    registrar_desverdizado,
    registrar_ingreso_packing,
    registrar_registro_packing,
    registrar_calidad_pallet,
    registrar_camara_frio,
    registrar_medicion_temperatura,
    cerrar_pallet,
)
from .helpers import make_lote_con_desverdizado, base_payload


class FlujoSinDesverdizadoTests(TestCase):
    """Flujo directo: recepcion → lote → ingreso packing → pallet → camara frio → medicion."""

    def test_flujo_directo_completo(self):
        # 1. Bins
        r1 = registrar_bin_recibido({"temporada": "2026", "bin_code": "B-001"})
        r2 = registrar_bin_recibido({"temporada": "2026", "bin_code": "B-002"})
        self.assertTrue(r1.ok)
        self.assertTrue(r2.ok)

        # 2. Lote
        r3 = crear_lote_recepcion({
            "temporada": "2026",
            "lote_code": "L-001",
            "bin_codes": ["B-001", "B-002"],
        })
        self.assertTrue(r3.ok)

        # 3. Ingreso packing (sin desverdizado)
        r4 = registrar_ingreso_packing(base_payload(lote_code="L-001"))
        self.assertTrue(r4.ok)
        self.assertFalse(r4.data["via_desverdizado"])

        # 4. Cerrar pallet
        r5 = cerrar_pallet({
            "temporada": "2026",
            "pallet_code": "P-001",
            "lote_codes": ["L-001"],
        })
        self.assertTrue(r5.ok)

        # 5. Calidad pallet
        r6 = registrar_calidad_pallet(base_payload(pallet_code="P-001"))
        self.assertTrue(r6.ok)

        # 6. Camara frio
        r7 = registrar_camara_frio(base_payload(pallet_code="P-001"))
        self.assertTrue(r7.ok)

        # 7. Medicion temperatura
        r8 = registrar_medicion_temperatura(base_payload(pallet_code="P-001"))
        self.assertTrue(r8.ok)

        # Al menos 6 eventos en auditoria
        self.assertGreaterEqual(RegistroEtapa.objects.count(), 6)


class FlujoConDesverdizadoTests(TestCase):
    """Flujo con desverdizado: lote configurado → desverdizado → ingreso packing."""

    def test_via_desverdizado_autodetectado(self):
        # Lote con camara disponible para desverdizado
        make_lote_con_desverdizado(lote_code="L-DESV", disponible=True)

        # Desverdizado
        r1 = registrar_desverdizado(base_payload(lote_code="L-DESV"))
        self.assertTrue(r1.ok)

        # Ingreso packing: via_desverdizado debe ser True automaticamente
        r2 = registrar_ingreso_packing(base_payload(lote_code="L-DESV"))
        self.assertTrue(r2.ok)
        self.assertTrue(r2.data["via_desverdizado"])

        ingreso = IngresoAPacking.objects.get()
        self.assertTrue(ingreso.via_desverdizado)


class FlujoMultiplesRegistrosTests(TestCase):
    """Verifica que entidades FK permiten multiples registros por lote/pallet."""

    def test_multiples_registros_packing_mismo_lote(self):
        from operaciones.models import RegistroPacking
        make_lote_con_desverdizado(disponible=True)

        registrar_ingreso_packing(base_payload(lote_code="LOT-001"))
        registrar_registro_packing(base_payload(lote_code="LOT-001"))
        registrar_registro_packing(base_payload(lote_code="LOT-001"))
        registrar_registro_packing(base_payload(lote_code="LOT-001"))

        self.assertEqual(RegistroPacking.objects.count(), 3)

    def test_multiples_mediciones_mismo_pallet(self):
        from operaciones.models import MedicionTemperaturaSalida
        from .helpers import make_pallet
        make_pallet()
        registrar_camara_frio(base_payload(pallet_code="PAL-001"))
        registrar_medicion_temperatura(base_payload(pallet_code="PAL-001"))
        registrar_medicion_temperatura(base_payload(pallet_code="PAL-001"))
        self.assertEqual(MedicionTemperaturaSalida.objects.count(), 2)


class BackendSwitchTests(TestCase):
    """
    Smoke test: el switch PERSISTENCE_BACKEND=sqlite debe funcionar
    para todos los use cases nuevos sin errores de importacion ni de repositorio.
    """

    def test_todos_los_use_cases_importan_correctamente(self):
        from operaciones.application.use_cases import (
            registrar_camara_mantencion,
            registrar_desverdizado,
            registrar_calidad_desverdizado,
            registrar_ingreso_packing,
            registrar_registro_packing,
            registrar_control_proceso_packing,
            registrar_calidad_pallet,
            registrar_camara_frio,
            registrar_medicion_temperatura,
        )
        use_cases = [
            registrar_camara_mantencion,
            registrar_desverdizado,
            registrar_calidad_desverdizado,
            registrar_ingreso_packing,
            registrar_registro_packing,
            registrar_control_proceso_packing,
            registrar_calidad_pallet,
            registrar_camara_frio,
            registrar_medicion_temperatura,
        ]
        for uc in use_cases:
            self.assertTrue(callable(uc), f"{uc.__name__} no es callable")

    def test_get_repositories_devuelve_todos_los_repos(self):
        from infrastructure.repository_factory import get_repositories
        repos = get_repositories()
        expected = [
            "bins", "lotes", "pallets", "bin_lotes", "pallet_lotes", "registros",
            "camara_mantencions", "desverdizados", "calidad_desverdizados",
            "ingresos_packing", "registros_packing", "control_proceso_packings",
            "calidad_pallets", "camara_frios", "mediciones_temperatura",
        ]
        for attr in expected:
            self.assertTrue(hasattr(repos, attr), f"repos.{attr} no existe")
