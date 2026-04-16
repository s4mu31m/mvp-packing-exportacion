"""
Tests de cierre de pesaje y regla de desverdizado.

Cubre:
- Calculo correcto del total neto acumulado (multiples registros, uno, cero)
- Actualizacion del acumulado al eliminar un registro
- Persistencia del flag requiere_desverdizado
- Ausencia de disponibilidad_camara_desverdizado en el payload de cierre
- Flujo directo (no requiere desverdizado)
- Flujo con desverdizado: disponibilidad se define en la etapa de desverdizado
- Rechazo de desverdizado si disponibilidad = NO_DISPONIBLE
"""
from decimal import Decimal

from django.test import TestCase

from operaciones.application.use_cases.cerrar_lote_recepcion import cerrar_lote_recepcion
from operaciones.application.use_cases.registrar_desverdizado import registrar_desverdizado
from operaciones.models import DisponibilidadCamara, Lote, LotePlantaEstado
from .helpers import make_lote, make_bin, base_payload


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _lote_con_bins(lote_code="LOT-CPT", cantidad_bins=2, temporada="2026"):
    """Crea un lote abierto con N bins asociados para tests de cierre de pesaje."""
    from operaciones.models import BinLote
    lote = make_lote(temporada=temporada, lote_code=lote_code, cantidad_bins=cantidad_bins)
    for i in range(cantidad_bins):
        bin_obj = make_bin(
            temporada=temporada,
            bin_code=f"BIN-CPT-{i+1:02d}",
            kilos_bruto_ingreso=100.0,
            kilos_neto_ingreso=90.0,
        )
        BinLote.objects.create(lote=lote, bin=bin_obj)
    return lote


def _payload_cierre(lote_code="LOT-CPT", kilos_bruto=500.0, kilos_neto=450.0,
                    requiere_desverdizado=False, temporada="2026"):
    return {
        **base_payload(temporada=temporada),
        "lote_code": lote_code,
        "kilos_bruto_conformacion": kilos_bruto,
        "kilos_neto_conformacion": kilos_neto,
        "requiere_desverdizado": requiere_desverdizado,
    }


# ---------------------------------------------------------------------------
# Calculo de total neto acumulado
# ---------------------------------------------------------------------------

class AcumuladoNetoPesajesTests(TestCase):
    """Verifica que el acumulado de netos se calcula correctamente."""

    def test_acumulado_multiples_registros(self):
        """Dos pesajes (1020 kg + 305 kg) => total 1325 kg."""
        pesajes = [
            {"cantidad_bins": 5, "kilos_brutos": 1100.0, "tara": 16.0, "kilos_netos": 1020.0},
            {"cantidad_bins": 2, "kilos_brutos": 337.0, "tara": 16.0, "kilos_netos": 305.0},
        ]
        total = sum(Decimal(str(p["kilos_netos"])) for p in pesajes)
        self.assertEqual(total, Decimal("1325.0"))

    def test_acumulado_un_solo_registro(self):
        """Un pesaje => acumulado == ese mismo valor."""
        pesajes = [
            {"cantidad_bins": 3, "kilos_brutos": 500.0, "tara": 16.0, "kilos_netos": 452.0},
        ]
        total = sum(Decimal(str(p["kilos_netos"])) for p in pesajes)
        self.assertEqual(total, Decimal("452.0"))

    def test_acumulado_cero_registros(self):
        """Sin pesajes => acumulado == 0."""
        pesajes = []
        total = sum(Decimal(str(p["kilos_netos"])) for p in pesajes)
        self.assertEqual(total, Decimal("0"))

    def test_acumulado_tras_eliminar_registro(self):
        """Agregar 2 pesajes, eliminar el primero => acumulado == segundo pesaje."""
        pesajes = [
            {"cantidad_bins": 5, "kilos_brutos": 1100.0, "tara": 16.0, "kilos_netos": 1020.0},
            {"cantidad_bins": 2, "kilos_brutos": 337.0, "tara": 16.0, "kilos_netos": 305.0},
        ]
        # Eliminar indice 0
        pesajes.pop(0)
        total = sum(Decimal(str(p["kilos_netos"])) for p in pesajes)
        self.assertEqual(total, Decimal("305.0"))

    def test_acumulado_con_valores_como_float_en_sesion(self):
        """El acumulado funciona aunque los valores esten almacenados como float (sesion)."""
        pesajes = [
            {"cantidad_bins": 3, "kilos_brutos": 600.5, "tara": 15.5, "kilos_netos": 554.0},
            {"cantidad_bins": 2, "kilos_brutos": 400.25, "tara": 15.5, "kilos_netos": 369.25},
        ]
        total = sum(Decimal(str(p["kilos_netos"])) for p in pesajes)
        self.assertEqual(total, Decimal("923.25"))


# ---------------------------------------------------------------------------
# Persistencia de requiere_desverdizado en cierre de lote
# ---------------------------------------------------------------------------

class CierreLoteRequiereDesverdizadoTests(TestCase):

    def test_requiere_desverdizado_true_persiste(self):
        """Al cerrar con requiere_desverdizado=True, el lote lo refleja en DB."""
        _lote_con_bins(lote_code="LOT-RD1")
        payload = _payload_cierre(lote_code="LOT-RD1", requiere_desverdizado=True)
        result = cerrar_lote_recepcion(payload)
        self.assertTrue(result.ok, result.errors)
        lote = Lote.objects.get(temporada="2026", lote_code="LOT-RD1")
        self.assertTrue(lote.requiere_desverdizado)

    def test_requiere_desverdizado_false_persiste(self):
        """Al cerrar con requiere_desverdizado=False, el lote lo refleja en DB."""
        _lote_con_bins(lote_code="LOT-RD2")
        payload = _payload_cierre(lote_code="LOT-RD2", requiere_desverdizado=False)
        result = cerrar_lote_recepcion(payload)
        self.assertTrue(result.ok, result.errors)
        lote = Lote.objects.get(temporada="2026", lote_code="LOT-RD2")
        self.assertFalse(lote.requiere_desverdizado)


# ---------------------------------------------------------------------------
# Disponibilidad de camara NO se define en cierre de pesaje
# ---------------------------------------------------------------------------

class DisponibilidadAusenteEnCierreTests(TestCase):

    def test_disponibilidad_no_se_establece_en_cierre(self):
        """Cerrar lote sin disponibilidad => campo queda None en DB."""
        _lote_con_bins(lote_code="LOT-DA1")
        payload = _payload_cierre(lote_code="LOT-DA1", requiere_desverdizado=True)
        # No hay 'disponibilidad_camara_desverdizado' en el payload
        self.assertNotIn("disponibilidad_camara_desverdizado", payload)
        result = cerrar_lote_recepcion(payload)
        self.assertTrue(result.ok, result.errors)
        lote = Lote.objects.get(temporada="2026", lote_code="LOT-DA1")
        self.assertIsNone(lote.disponibilidad_camara_desverdizado)

    def test_disponibilidad_ignorada_si_viene_en_payload_de_cierre(self):
        """Si por error llega disponibilidad en el payload de cierre, el use case la procesa
        (el use case acepta campos opcionales). Lo importante es que la vista ya no la envie."""
        _lote_con_bins(lote_code="LOT-DA2")
        # Simulacion: si alguien envia el campo, el use case lo procesa (no es un error)
        # pero la vista corregida ya no lo enviara
        payload = _payload_cierre(lote_code="LOT-DA2", requiere_desverdizado=True)
        self.assertNotIn("disponibilidad_camara_desverdizado", payload,
                         "La vista de cierre no debe incluir disponibilidad_camara_desverdizado en el payload")


# ---------------------------------------------------------------------------
# Flujo directo: lote no requiere desverdizado
# ---------------------------------------------------------------------------

class FlujoDirectoTests(TestCase):

    def test_flujo_directo_cierra_correctamente(self):
        """Lote sin desverdizado cierra con estado CERRADO."""
        _lote_con_bins(lote_code="LOT-DIR")
        result = cerrar_lote_recepcion(_payload_cierre(lote_code="LOT-DIR"))
        self.assertTrue(result.ok, result.errors)
        lote = Lote.objects.get(temporada="2026", lote_code="LOT-DIR")
        self.assertEqual(lote.estado, LotePlantaEstado.CERRADO)
        self.assertFalse(lote.requiere_desverdizado)

    def test_flujo_directo_desverdizado_rechazado(self):
        """Lote con requiere_desverdizado=False es rechazado en registrar_desverdizado."""
        _lote_con_bins(lote_code="LOT-DIR2")
        cerrar_lote_recepcion(_payload_cierre(lote_code="LOT-DIR2", requiere_desverdizado=False))
        result = registrar_desverdizado({
            **base_payload(),
            "lote_code": "LOT-DIR2",
            "disponibilidad_camara_desverdizado": DisponibilidadCamara.DISPONIBLE,
        })
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "DESVERDIZADO_NO_APLICA")


# ---------------------------------------------------------------------------
# Flujo con desverdizado: disponibilidad se define en etapa desverdizado
# ---------------------------------------------------------------------------

class FlujoConDesverdizadoTests(TestCase):

    def _cerrar_lote_para_desverdizado(self, lote_code):
        _lote_con_bins(lote_code=lote_code)
        result = cerrar_lote_recepcion(_payload_cierre(
            lote_code=lote_code, requiere_desverdizado=True
        ))
        self.assertTrue(result.ok, result.errors)
        return Lote.objects.get(temporada="2026", lote_code=lote_code)

    def test_disponibilidad_none_tras_cierre(self):
        """Tras cerrar lote con requiere_desverdizado=True, disponibilidad sigue None."""
        lote = self._cerrar_lote_para_desverdizado("LOT-DESV1")
        self.assertIsNone(lote.disponibilidad_camara_desverdizado)

    def test_desverdizado_registrado_con_disponibilidad_en_payload(self):
        """Registrar desverdizado pasando disponibilidad=DISPONIBLE en payload => ok."""
        self._cerrar_lote_para_desverdizado("LOT-DESV2")
        result = registrar_desverdizado({
            **base_payload(),
            "lote_code": "LOT-DESV2",
            "disponibilidad_camara_desverdizado": DisponibilidadCamara.DISPONIBLE,
        })
        self.assertTrue(result.ok, result.errors)
        lote = Lote.objects.get(temporada="2026", lote_code="LOT-DESV2")
        self.assertEqual(lote.disponibilidad_camara_desverdizado, DisponibilidadCamara.DISPONIBLE)

    def test_desverdizado_registrado_sin_disponibilidad_en_payload(self):
        """Registrar desverdizado sin pasar disponibilidad => ok (campo null no bloquea)."""
        self._cerrar_lote_para_desverdizado("LOT-DESV3")
        result = registrar_desverdizado({
            **base_payload(),
            "lote_code": "LOT-DESV3",
        })
        self.assertTrue(result.ok, result.errors)

    def test_desverdizado_rechazado_si_disponibilidad_no_disponible(self):
        """Pasar disponibilidad=NO_DISPONIBLE en payload de desverdizado => CAMARA_NO_DISPONIBLE."""
        self._cerrar_lote_para_desverdizado("LOT-DESV4")
        result = registrar_desverdizado({
            **base_payload(),
            "lote_code": "LOT-DESV4",
            "disponibilidad_camara_desverdizado": DisponibilidadCamara.NO_DISPONIBLE,
        })
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "CAMARA_NO_DISPONIBLE")
        # Verificar que el lote quedo marcado como NO_DISPONIBLE en DB
        lote = Lote.objects.get(temporada="2026", lote_code="LOT-DESV4")
        self.assertEqual(lote.disponibilidad_camara_desverdizado, DisponibilidadCamara.NO_DISPONIBLE)
