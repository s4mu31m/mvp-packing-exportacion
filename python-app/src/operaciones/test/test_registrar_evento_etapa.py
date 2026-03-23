from django.test import TestCase

from operaciones.models import Lote, RegistroEtapa, TipoEvento
from operaciones.application.use_cases.registrar_evento_etapa import registrar_evento_etapa


class RegistrarEventoEtapaTests(TestCase):
    def setUp(self):
        self.temporada = "2026"
        self.lote = Lote.objects.create(
            temporada=self.temporada,
            lote_code="LOTE-001",
            operator_code="OP-01",
            source_system="local",
            source_event_id="seed-001",
        )

    def test_registra_pesaje_correctamente(self):
        result = registrar_evento_etapa({
            "temporada": self.temporada,
            "tipo_evento": TipoEvento.PESAJE,
            "lote_code": "LOTE-001",
            "datos": {"peso_kg": 320},
        })

        self.assertTrue(result.ok)
        self.assertEqual(result.code, "EVENTO_REGISTRADO")
        registro = RegistroEtapa.objects.get(id=result.data["registro_id"])
        self.assertEqual(registro.tipo_evento, TipoEvento.PESAJE)
        self.assertEqual(registro.payload["peso_kg"], 320)
        self.assertEqual(registro.lote, self.lote)

    def test_registra_desverdizado_ingreso(self):
        result = registrar_evento_etapa({
            "temporada": self.temporada,
            "tipo_evento": TipoEvento.DESVERDIZADO_INGRESO,
            "lote_code": "LOTE-001",
        })

        self.assertTrue(result.ok)
        self.assertEqual(result.code, "EVENTO_REGISTRADO")
        registro = RegistroEtapa.objects.get(id=result.data["registro_id"])
        self.assertEqual(registro.tipo_evento, TipoEvento.DESVERDIZADO_INGRESO)

    def test_registra_control_calidad(self):
        result = registrar_evento_etapa({
            "temporada": self.temporada,
            "tipo_evento": TipoEvento.CONTROL_CALIDAD,
            "lote_code": "LOTE-001",
            "datos": {"resultado": "aprobado", "observacion": "sin defectos"},
        })

        self.assertTrue(result.ok)
        self.assertEqual(result.code, "EVENTO_REGISTRADO")
        registro = RegistroEtapa.objects.get(id=result.data["registro_id"])
        self.assertEqual(registro.tipo_evento, TipoEvento.CONTROL_CALIDAD)
        self.assertEqual(registro.payload["resultado"], "aprobado")
        self.assertEqual(registro.payload["observacion"], "sin defectos")

    def test_rechaza_tipo_evento_invalido(self):
        result = registrar_evento_etapa({
            "temporada": self.temporada,
            "tipo_evento": "EVENTO_INEXISTENTE",
            "lote_code": "LOTE-001",
        })

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "INVALID_TIPO_EVENTO")
