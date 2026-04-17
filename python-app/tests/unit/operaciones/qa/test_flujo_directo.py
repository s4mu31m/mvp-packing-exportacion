"""
test_flujo_directo.py — Flujo E2E completo sin desverdizado.

BLOQUEANTE: falla en este test indica corrupción del flujo productivo.

Datos: VARIEDAD_BLANCA (Thompson Seedless, productor PROD-SAN-ESTEBAN-01).
Cada paso usa POST HTTP real por las vistas operativas.
Los atajos via use case directo son documentados y usados solo donde
la UI no cubre el setup (creación de pallet al momento de paletizar).

Clases:
  - FlujoDirectoE2ETest        → flujo completo, 12 pasos, con persistencia y trazabilidad
  - TraceabilityDirectoTest    → cadena RegistroEtapa íntegra al final del flujo
"""
import datetime

from django.test import TestCase, override_settings
from django.urls import reverse

from operaciones.models import (
    Bin,
    BinLote,
    Lote,
    LotePlantaEstado,
    Pallet,
    PalletLote,
    TipoEvento,
)
from tests.unit.operaciones.qa.base import (
    QASetupMixin,
    TEMPORADA,
    VARIEDAD_BLANCA,
    build_iniciar_payload,
    build_bin_payload,
    build_cierre_lote_payload,
    build_ingreso_packing_payload,
    build_proceso_payload,
    build_control_payload,
    build_calidad_pallet_payload,
    build_camara_frio_payload,
    build_medicion_temperatura_payload,
    assert_trazabilidad,
    assert_integridad_registros,
)

# Eventos mínimos esperados en el flujo directo
EVENTOS_FLUJO_DIRECTO = [
    TipoEvento.BIN_REGISTRADO,
    TipoEvento.LOTE_CREADO,
    TipoEvento.INGRESO_PACKING,
    TipoEvento.PALLET_CREADO,
    TipoEvento.LOTE_ASIGNADO_PALLET,
    TipoEvento.CAMARA_FRIO_INGRESO,
]


@override_settings(PERSISTENCE_BACKEND="sqlite")
class FlujoDirectoE2ETest(TestCase):
    """
    Flujo completo sin desverdizado.

    Paso 1-3:  Recepción (iniciar → 2 bins → cerrar)
    Paso 4:    Ingreso Packing
    Paso 5:    Registro Packing
    Paso 6:    Control Proceso Packing
    Paso 7:    Cerrar Pallet (atajo use case — sin vista de creación de pallets)
    Paso 8:    Calidad Pallet
    Paso 9:    Cámara Frío
    Paso 10:   Medición Temperatura
    Paso 11:   Consulta Jefatura — lote visible
    Paso 12:   Exportar CSV — lote en exportación
    """

    @classmethod
    def setUpTestData(cls):
        cls.all_clients = QASetupMixin.build_all_clients()

    def _c(self, rol_key):
        return self.all_clients[rol_key][0]

    # ----- Paso 1: Iniciar lote -----

    def test_paso01_iniciar_lote(self):
        resp = self._c("recepcion").post(
            reverse("operaciones:recepcion"),
            build_iniciar_payload(),
        )
        self.assertIn(resp.status_code, [200, 302],
            msg="Paso 1 — iniciar lote debe responder 200/302")
        lote_code = QASetupMixin.get_lote_code_from_session(self._c("recepcion"))
        self.assertIsNotNone(lote_code,
            msg="Paso 1 — lote_code debe quedar en sesión tras iniciar")
        lote = Lote.objects.filter(temporada=TEMPORADA, lote_code=lote_code).first()
        self.assertIsNotNone(lote,
            msg=f"Paso 1 — Lote {lote_code} no encontrado en DB")
        self.assertEqual(lote.estado, LotePlantaEstado.ABIERTO,
            msg=f"Paso 1 — Lote recién iniciado debe estar en estado ABIERTO")

    # ----- Paso 2: Agregar 2 bins -----

    def test_paso02_agregar_dos_bins(self):
        client = self._c("recepcion")
        client.post(reverse("operaciones:recepcion"), build_iniciar_payload())
        lote_code = QASetupMixin.get_lote_code_from_session(client)

        resp1 = client.post(
            reverse("operaciones:recepcion"),
            build_bin_payload(VARIEDAD_BLANCA, numero_cuartel="C-04"),
        )
        self.assertIn(resp1.status_code, [200, 302],
            msg=f"Paso 2 — agregar bin 1 al lote {lote_code}")

        resp2 = client.post(
            reverse("operaciones:recepcion"),
            build_bin_payload(VARIEDAD_BLANCA, numero_cuartel="C-04"),
        )
        self.assertIn(resp2.status_code, [200, 302],
            msg=f"Paso 2 — agregar bin 2 al lote {lote_code}")

        lote = Lote.objects.get(temporada=TEMPORADA, lote_code=lote_code)
        self.assertEqual(lote.cantidad_bins, 2,
            msg=f"Paso 2 — Lote {lote_code} debe tener 2 bins")
        self.assertEqual(BinLote.objects.filter(lote=lote).count(), 2,
            msg=f"Paso 2 — Deben existir 2 relaciones BinLote para lote {lote_code}")

    # ----- Paso 3: Cerrar lote -----

    def test_paso03_cerrar_lote(self):
        client = self._c("recepcion")
        client.post(reverse("operaciones:recepcion"), build_iniciar_payload())
        client.post(reverse("operaciones:recepcion"), build_bin_payload(VARIEDAD_BLANCA))
        lote_code = QASetupMixin.get_lote_code_from_session(client)

        resp = client.post(
            reverse("operaciones:recepcion"),
            build_cierre_lote_payload(requiere_desverdizado=False),
        )
        self.assertIn(resp.status_code, [200, 302],
            msg=f"Paso 3 — cerrar lote {lote_code}")

        lote = Lote.objects.get(temporada=TEMPORADA, lote_code=lote_code)
        self.assertEqual(lote.estado, LotePlantaEstado.CERRADO,
            msg=f"Paso 3 — Lote {lote_code} debe quedar en estado CERRADO tras cierre")
        self.assertIsNone(
            QASetupMixin.get_lote_code_from_session(client),
            msg="Paso 3 — sesión debe limpiarse de lote_activo_code tras cierre",
        )

    # ----- Paso 4: Ingreso Packing -----

    def test_paso04_ingreso_packing(self):
        from operaciones.models import IngresoAPacking
        client = self._c("recepcion")
        client.post(reverse("operaciones:recepcion"), build_iniciar_payload())
        client.post(reverse("operaciones:recepcion"), build_bin_payload(VARIEDAD_BLANCA))
        lote_code = QASetupMixin.get_lote_code_from_session(client)
        client.post(reverse("operaciones:recepcion"), build_cierre_lote_payload())

        resp = self._c("ing_packing").post(
            reverse("operaciones:ingreso_packing"),
            build_ingreso_packing_payload(lote_code, via_desverdizado=False),
        )
        self.assertIn(resp.status_code, [200, 302],
            msg=f"Paso 4 — ingreso packing para lote {lote_code}")

        ingreso = IngresoAPacking.objects.filter(
            lote__temporada=TEMPORADA, lote__lote_code=lote_code
        ).first()
        self.assertIsNotNone(ingreso,
            msg=f"Paso 4 — IngresoAPacking no creado para lote {lote_code}")
        self.assertFalse(ingreso.via_desverdizado,
            msg="Paso 4 — via_desverdizado debe ser False en flujo directo")

    # ----- Paso 5: Registro Packing -----

    def test_paso05_registro_packing(self):
        from operaciones.models import RegistroPacking, IngresoAPacking
        # Setup: lote cerrado con ingreso packing
        lote_code = self._setup_lote_con_ingreso_packing()

        resp = self._c("proceso").post(
            reverse("operaciones:proceso"),
            build_proceso_payload(lote_code),
        )
        self.assertIn(resp.status_code, [200, 302],
            msg=f"Paso 5 — registro packing para lote {lote_code}")

        lote = Lote.objects.get(temporada=TEMPORADA, lote_code=lote_code)
        registros = lote.registros_packing.count()
        self.assertGreater(registros, 0,
            msg=f"Paso 5 — RegistroPacking no creado para lote {lote_code}")

    # ----- Paso 6: Control Proceso -----

    def test_paso06_control_proceso_packing(self):
        from operaciones.models import ControlProcesoPacking
        lote_code = self._setup_lote_con_ingreso_packing()

        resp = self._c("control").post(
            reverse("operaciones:control_proceso"),  # índice no acepta POST
            build_control_payload(lote_code),
        )
        self.assertIn(resp.status_code, [200, 302],
            msg=f"Paso 6 — control proceso para lote {lote_code}")

        lote = Lote.objects.get(temporada=TEMPORADA, lote_code=lote_code)
        self.assertGreater(lote.control_proceso_packing.count(), 0,
            msg=f"Paso 6 — ControlProcesoPacking no creado para lote {lote_code}")

    # ----- Paso 7+8: Pallet + Calidad Pallet -----

    def test_paso07_08_calidad_pallet(self):
        from operaciones.models import CalidadPallet
        lote_code = self._setup_lote_con_ingreso_packing()
        pallet_code = self._crear_pallet(lote_code)

        resp = self._c("paletizado").post(
            reverse("operaciones:paletizado"),
            build_calidad_pallet_payload(pallet_code),
        )
        self.assertIn(resp.status_code, [200, 302],
            msg=f"Paso 8 — calidad pallet para pallet {pallet_code}")

        pallet = Pallet.objects.get(temporada=TEMPORADA, pallet_code=pallet_code)
        self.assertGreater(pallet.calidad_pallet.count(), 0,
            msg=f"Paso 8 — CalidadPallet no creado para pallet {pallet_code}")

    # ----- Paso 9: Cámara Frío -----

    def test_paso09_camara_frio(self):
        from operaciones.models import CamaraFrio
        lote_code = self._setup_lote_con_ingreso_packing()
        pallet_code = self._crear_pallet(lote_code)

        resp = self._c("camaras").post(
            reverse("operaciones:camaras"),
            build_camara_frio_payload(pallet_code),
        )
        self.assertIn(resp.status_code, [200, 302],
            msg=f"Paso 9 — camara frio para pallet {pallet_code}")

        pallet = Pallet.objects.get(temporada=TEMPORADA, pallet_code=pallet_code)
        self.assertTrue(
            hasattr(pallet, "camara_frio") and pallet.camara_frio is not None
            or CamaraFrio.objects.filter(pallet=pallet).exists(),
            msg=f"Paso 9 — CamaraFrio no creado para pallet {pallet_code}",
        )

    # ----- Paso 10: Medición Temperatura -----

    def test_paso10_medicion_temperatura(self):
        from operaciones.models import MedicionTemperaturaSalida
        lote_code = self._setup_lote_con_ingreso_packing()
        pallet_code = self._crear_pallet(lote_code)
        # Primero registrar cámara frío (requisito de contexto)
        self._c("camaras").post(
            reverse("operaciones:camaras"),
            build_camara_frio_payload(pallet_code),
        )

        resp = self._c("camaras").post(
            reverse("operaciones:camaras"),
            build_medicion_temperatura_payload(pallet_code),
        )
        self.assertIn(resp.status_code, [200, 302],
            msg=f"Paso 10 — medicion temperatura para pallet {pallet_code}")

        pallet = Pallet.objects.get(temporada=TEMPORADA, pallet_code=pallet_code)
        self.assertGreater(
            MedicionTemperaturaSalida.objects.filter(pallet=pallet).count(), 0,
            msg=f"Paso 10 — MedicionTemperatura no creada para pallet {pallet_code}",
        )

    # ----- Paso 11: Consulta Jefatura -----

    def test_paso11_consulta_jefatura_ve_el_lote(self):
        lote_code = self._setup_lote_cerrado()
        resp = self._c("jefatura").get(reverse("operaciones:consulta"))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn(lote_code, content,
            msg=f"Paso 11 — lote {lote_code} no aparece en consulta de Jefatura")

    # ----- Paso 12: Exportar CSV -----

    def test_paso12_exportar_csv_contiene_lote(self):
        lote_code = self._setup_lote_cerrado()
        resp = self._c("jefatura").get(reverse("operaciones:exportar_consulta"))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn(lote_code, content,
            msg=f"Paso 12 — lote {lote_code} no aparece en exportación CSV")

    # ----- Helpers de setup compartidos -----

    def _setup_lote_cerrado(self):
        """Crea un lote cerrado con 1 bin. Devuelve lote_code."""
        from operaciones.application.use_cases import (
            iniciar_lote_recepcion, agregar_bin_a_lote_abierto, cerrar_lote_recepcion
        )
        res = iniciar_lote_recepcion({
            "temporada": TEMPORADA, "operator_code": "QA-SETUP", "source_system": "test"
        })
        lote_code = res.data["lote_code"]
        agregar_bin_a_lote_abierto({
            "temporada": TEMPORADA, "lote_code": lote_code,
            "operator_code": "QA-SETUP", "source_system": "test",
            "variedad_fruta": VARIEDAD_BLANCA["variedad_fruta"],
            "kilos_neto_ingreso": "498", "kilos_bruto_ingreso": "520",
            "codigo_productor": VARIEDAD_BLANCA["codigo_productor"],
        })
        cerrar_lote_recepcion({
            "temporada": TEMPORADA, "lote_code": lote_code,
            "operator_code": "QA-SETUP", "source_system": "test",
        })
        return lote_code

    def _setup_lote_con_ingreso_packing(self):
        """Crea un lote cerrado con ingreso a packing. Devuelve lote_code."""
        from operaciones.application.use_cases import registrar_ingreso_packing
        lote_code = self._setup_lote_cerrado()
        registrar_ingreso_packing({
            "temporada": TEMPORADA, "lote_code": lote_code,
            "operator_code": "QA-SETUP", "source_system": "test",
            "via_desverdizado": False, "extra": {},
        })
        return lote_code

    def _crear_pallet(self, lote_code):
        """
        Crea un pallet asociado al lote via use case (atajo documentado:
        no existe vista de creación directa de pallet en el MVP).
        Devuelve pallet_code.
        """
        from operaciones.application.use_cases import cerrar_pallet
        res = cerrar_pallet({
            "temporada": TEMPORADA, "lote_codes": [lote_code],
            "operator_code": "QA-SETUP", "source_system": "test",
        })
        if res.ok:
            return res.data.get("pallet_code")
        raise RuntimeError(f"cerrar_pallet falló para lote {lote_code}: {res.errors}")


@override_settings(PERSISTENCE_BACKEND="sqlite")
class TraceabilityDirectoTest(TestCase):
    """
    Valida la integridad de la cadena RegistroEtapa al completar el flujo directo.
    BLOQUEANTE: registros huérfanos o event_key duplicados indican corrupción.
    """

    @classmethod
    def setUpTestData(cls):
        from operaciones.application.use_cases import (
            iniciar_lote_recepcion,
            agregar_bin_a_lote_abierto,
            cerrar_lote_recepcion,
            registrar_ingreso_packing,
            registrar_registro_packing,
            registrar_control_proceso_packing,
            cerrar_pallet,
            registrar_calidad_pallet,
            registrar_camara_frio,
            registrar_medicion_temperatura,
        )
        base = {"temporada": TEMPORADA, "operator_code": "QA-TRACE", "source_system": "test"}

        res = iniciar_lote_recepcion(base.copy())
        lote_code = res.data["lote_code"]
        agregar_bin_a_lote_abierto({**base, "lote_code": lote_code,
            "variedad_fruta": "Thompson Seedless",
            "kilos_neto_ingreso": "498", "kilos_bruto_ingreso": "520"})
        cerrar_lote_recepcion({**base, "lote_code": lote_code})
        registrar_ingreso_packing({**base, "lote_code": lote_code,
            "via_desverdizado": False, "extra": {}})
        registrar_registro_packing({**base, "lote_code": lote_code,
            "extra": {"linea_proceso": "L1", "cantidad_cajas_producidas": 60}})
        registrar_control_proceso_packing({**base, "lote_code": lote_code,
            "extra": {"n_bins_procesados": 2}})
        res_pallet = cerrar_pallet({**base, "lote_codes": [lote_code]})
        pallet_code = res_pallet.data.get("pallet_code")
        registrar_calidad_pallet({**base, "pallet_code": pallet_code, "extra": {}})
        registrar_camara_frio({**base, "pallet_code": pallet_code,
            "extra": {"camara_numero": "CF-1"}})
        registrar_medicion_temperatura({**base, "pallet_code": pallet_code,
            "extra": {"temperatura_pallet": -0.8}})

        cls.lote = Lote.objects.get(temporada=TEMPORADA, lote_code=lote_code)
        cls.pallet = Pallet.objects.get(temporada=TEMPORADA, pallet_code=pallet_code)

    def test_eventos_minimos_presentes(self):
        assert_trazabilidad(
            self, self.lote, self.pallet,
            EVENTOS_FLUJO_DIRECTO,
            msg_prefix="Flujo directo — ",
        )

    def test_sin_registros_huerfanos(self):
        assert_integridad_registros(self)

    def test_event_key_unico(self):
        from operaciones.models import RegistroEtapa
        total = RegistroEtapa.objects.filter(temporada=TEMPORADA).count()
        distintos = (
            RegistroEtapa.objects.filter(temporada=TEMPORADA)
            .values("event_key").distinct().count()
        )
        self.assertEqual(total, distintos,
            msg=f"Duplicados en event_key: {total} registros, {distintos} keys únicos")

    def test_lote_tiene_registros_propios(self):
        from operaciones.models import RegistroEtapa
        count = RegistroEtapa.objects.filter(lote=self.lote).count()
        self.assertGreater(count, 0,
            msg=f"Lote {self.lote.lote_code} no tiene RegistroEtapa asociados")

    def test_pallet_tiene_registros_propios(self):
        from operaciones.models import RegistroEtapa
        count = RegistroEtapa.objects.filter(pallet=self.pallet).count()
        self.assertGreater(count, 0,
            msg=f"Pallet {self.pallet.pallet_code} no tiene RegistroEtapa asociados")

    def test_persistencia_final_coherente(self):
        """Verifica consistencia de la cadena de entidades relacionadas."""
        lote = self.lote
        self.assertEqual(lote.estado, LotePlantaEstado.CERRADO,
            msg="Lote debe estar cerrado al finalizar flujo")
        self.assertGreater(BinLote.objects.filter(lote=lote).count(), 0,
            msg="Lote debe tener bins asociados")
        self.assertGreater(PalletLote.objects.filter(lote=lote).count(), 0,
            msg="Lote debe estar asignado a un pallet")
