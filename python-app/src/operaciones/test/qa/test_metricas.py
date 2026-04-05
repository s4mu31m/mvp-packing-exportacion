"""
test_metricas.py — Rendimiento y observabilidad.

DIAGNÓSTICO: no bloqueante por defecto. Imprime resumen de tiempos al final.
Los thresholds son referencias, no criterios duros de release — el entorno
local con SQLite no equivale a producción.

Clases:
  - ThroughputBaselineTest → mide tiempos por etapa y throughput del flujo completo
  - LatenciaEtapasTest     → identifica etapas outlier y compara flujo directo vs desverdizado
"""
import time
import threading
from collections import defaultdict

from django.test import TransactionTestCase, override_settings
from django.urls import reverse

from operaciones.test.qa.base import (
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
)


# ---------------------------------------------------------------------------
# Colector de tiempos — thread-safe
# ---------------------------------------------------------------------------

class TimingCollector:
    """Acumula tiempos de respuesta (ms) por etapa. Thread-safe."""

    def __init__(self):
        self._lock = threading.Lock()
        self._times: dict = defaultdict(list)

    def record(self, label: str, elapsed_ms: float):
        with self._lock:
            self._times[label].append(elapsed_ms)

    def summary(self) -> dict:
        """Devuelve dict {label: {n, mean_ms, max_ms, min_ms}}."""
        return {
            label: {
                "n":        len(times),
                "mean_ms":  sum(times) / len(times),
                "max_ms":   max(times),
                "min_ms":   min(times),
            }
            for label, times in self._times.items()
            if times
        }

    def print_report(self, title="Métricas de tiempos"):
        summary = self.summary()
        print(f"\n{'='*60}")
        print(f"[MÉTRICAS] {title}")
        print(f"{'='*60}")
        print(f"{'Etapa':<35} {'n':>4} {'mean_ms':>9} {'max_ms':>9} {'min_ms':>9}")
        print(f"{'-'*35} {'-'*4} {'-'*9} {'-'*9} {'-'*9}")
        for label, m in sorted(summary.items()):
            print(f"{label:<35} {m['n']:>4} {m['mean_ms']:>9.1f} {m['max_ms']:>9.1f} {m['min_ms']:>9.1f}")
        print(f"{'='*60}")

    def check_soft_thresholds(self, max_mean_ms=500.0):
        """
        Imprime advertencias para etapas que superan el threshold blando.
        No lanza excepciones — solo registra como observación.
        """
        warnings = []
        for label, m in self.summary().items():
            if m["mean_ms"] > max_mean_ms:
                warnings.append(
                    f"  OBSERVACIÓN: '{label}' mean={m['mean_ms']:.1f}ms > {max_mean_ms}ms"
                )
        if warnings:
            print("\n[MÉTRICAS] Etapas sobre threshold blando (no bloqueante):")
            for w in warnings:
                print(w)
        return warnings


def _timed_post(client, url, payload, collector, label):
    """Ejecuta POST y registra elapsed_ms. Devuelve response."""
    t0 = time.perf_counter()
    resp = client.post(url, payload)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    collector.record(label, elapsed_ms)
    return resp


def _timed_get(client, url, collector, label, **params):
    """Ejecuta GET y registra elapsed_ms."""
    t0 = time.perf_counter()
    resp = client.get(url, params)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    collector.record(label, elapsed_ms)
    return resp


@override_settings(PERSISTENCE_BACKEND="sqlite")
class ThroughputBaselineTest(TransactionTestCase):
    """
    Mide tiempo de respuesta por etapa del flujo directo completo.
    Reporta throughput (operaciones/segundo) al final.

    Threshold blando: mean_ms > 500 → observación (no bloquea release).
    """

    def test_flujo_directo_completo_con_metricas(self):
        collector = TimingCollector()
        all_clients = QASetupMixin.build_all_clients()

        def c(rol_key):
            return all_clients[rol_key][0]

        t_flujo_inicio = time.perf_counter()

        # --- Recepción ---
        _timed_post(c("recepcion"), reverse("operaciones:recepcion"),
                    build_iniciar_payload(), collector, "01_recepcion_iniciar")

        lote_code = QASetupMixin.get_lote_code_from_session(c("recepcion"))
        self.assertIsNotNone(lote_code,
            msg="[Métricas] Lote no iniciado — test de métricas no puede continuar")

        _timed_post(c("recepcion"), reverse("operaciones:recepcion"),
                    build_bin_payload(VARIEDAD_BLANCA), collector, "02_recepcion_agregar_bin")
        _timed_post(c("recepcion"), reverse("operaciones:recepcion"),
                    build_cierre_lote_payload(), collector, "03_recepcion_cerrar")

        # --- Ingreso Packing ---
        _timed_post(c("ing_packing"), reverse("operaciones:ingreso_packing"),
                    build_ingreso_packing_payload(lote_code), collector, "04_ingreso_packing")

        # --- Proceso ---
        _timed_post(c("proceso"), reverse("operaciones:proceso"),
                    build_proceso_payload(lote_code), collector, "05_registro_packing")

        # --- Control ---
        _timed_post(c("control"), reverse("operaciones:control"),
                    build_control_payload(lote_code), collector, "06_control_proceso")

        # --- Pallet (atajo use case) ---
        t0 = time.perf_counter()
        from operaciones.application.use_cases import cerrar_pallet
        res_pallet = cerrar_pallet({
            "temporada": TEMPORADA, "lote_codes": [lote_code],
            "operator_code": "QA-METRICS", "source_system": "test",
        })
        collector.record("07_cerrar_pallet_usecase", (time.perf_counter() - t0) * 1000)
        pallet_code = res_pallet.data.get("pallet_code") if res_pallet.ok else None
        self.assertIsNotNone(pallet_code,
            msg="[Métricas] Pallet no creado — flujo de métricas incompleto")

        # --- Calidad Pallet ---
        _timed_post(c("paletizado"), reverse("operaciones:paletizado"),
                    build_calidad_pallet_payload(pallet_code), collector, "08_calidad_pallet")

        # --- Cámara Frío ---
        _timed_post(c("camaras"), reverse("operaciones:camaras"),
                    build_camara_frio_payload(pallet_code), collector, "09_camara_frio")

        # --- Medición Temperatura ---
        _timed_post(c("camaras"), reverse("operaciones:camaras"),
                    build_medicion_temperatura_payload(pallet_code), collector, "10_medicion_temp")

        # --- Consulta Jefatura ---
        _timed_get(c("jefatura"), reverse("operaciones:consulta"),
                   collector, "11_consulta_jefatura")

        t_flujo_total = (time.perf_counter() - t_flujo_inicio) * 1000
        collector.record("00_FLUJO_COMPLETO", t_flujo_total)

        # ----- Reporte -----
        collector.print_report("Flujo Directo Completo")

        # ----- Throughput -----
        n_operaciones = 10  # 10 etapas medidas
        throughput = n_operaciones / (t_flujo_total / 1000)
        print(f"\n[MÉTRICAS] Throughput flujo completo: {throughput:.2f} ops/s "
              f"({t_flujo_total:.0f}ms total)")

        # Threshold blando (observación, no fallo duro)
        collector.check_soft_thresholds(max_mean_ms=500.0)

        if throughput < 2.0:
            print(f"[MÉTRICAS] OBSERVACIÓN: throughput {throughput:.2f} ops/s < 2.0 ops/s — "
                  f"revisar si persiste en staging (SQLite local no refleja producción)")

        # Única assertion dura: el flujo completo no tomó más de 60 segundos
        self.assertLess(t_flujo_total, 60_000,
            msg=f"Flujo completo tardó {t_flujo_total:.0f}ms — umbral máximo: 60s")


@override_settings(PERSISTENCE_BACKEND="sqlite")
class LatenciaEtapasTest(TransactionTestCase):
    """
    Compara latencia entre flujo directo y flujo con desverdizado.
    Identifica etapas outlier.
    """

    def test_comparacion_flujo_directo_vs_desverdizado(self):
        from operaciones.application.use_cases import (
            iniciar_lote_recepcion, agregar_bin_a_lote_abierto,
            cerrar_lote_recepcion, registrar_camara_mantencion,
            registrar_desverdizado, registrar_ingreso_packing,
        )
        from operaciones.models import DisponibilidadCamara
        base = {"temporada": TEMPORADA, "source_system": "test"}

        collector_directo = TimingCollector()
        collector_desv = TimingCollector()

        # --- Flujo directo (solo recepción y cierre) ---
        t0 = time.perf_counter()
        r1 = iniciar_lote_recepcion({**base, "operator_code": "QA-LAT-D"})
        collector_directo.record("iniciar_lote", (time.perf_counter() - t0) * 1000)

        lc1 = r1.data["lote_code"]
        t0 = time.perf_counter()
        agregar_bin_a_lote_abierto({**base, "lote_code": lc1, "operator_code": "QA-LAT-D",
            "variedad_fruta": "Thompson Seedless",
            "kilos_neto_ingreso": "498", "kilos_bruto_ingreso": "520"})
        collector_directo.record("agregar_bin", (time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        cerrar_lote_recepcion({**base, "lote_code": lc1, "operator_code": "QA-LAT-D"})
        collector_directo.record("cerrar_lote", (time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        registrar_ingreso_packing({**base, "lote_code": lc1, "operator_code": "QA-LAT-D",
            "via_desverdizado": False, "extra": {}})
        collector_directo.record("ingreso_packing", (time.perf_counter() - t0) * 1000)

        # --- Flujo con desverdizado ---
        r2 = iniciar_lote_recepcion({**base, "operator_code": "QA-LAT-V"})
        lc2 = r2.data["lote_code"]
        agregar_bin_a_lote_abierto({**base, "lote_code": lc2, "operator_code": "QA-LAT-V",
            "variedad_fruta": "Red Globe",
            "kilos_neto_ingreso": "585", "kilos_bruto_ingreso": "610"})
        cerrar_lote_recepcion({**base, "lote_code": lc2, "operator_code": "QA-LAT-V",
            "requiere_desverdizado": True,
            "disponibilidad_camara_desverdizado": DisponibilidadCamara.NO_DISPONIBLE})

        t0 = time.perf_counter()
        registrar_camara_mantencion({**base, "lote_code": lc2, "operator_code": "QA-LAT-V",
            "extra": {"camara_numero": "CM-4"}})
        collector_desv.record("camara_mantencion", (time.perf_counter() - t0) * 1000)

        from operaciones.models import Lote
        Lote.objects.filter(temporada=TEMPORADA, lote_code=lc2).update(
            disponibilidad_camara_desverdizado=DisponibilidadCamara.DISPONIBLE
        )

        t0 = time.perf_counter()
        registrar_desverdizado({**base, "lote_code": lc2, "operator_code": "QA-LAT-V",
            "extra": {"horas_desverdizado": 72, "color_salida": "4"}})
        collector_desv.record("desverdizado", (time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        registrar_ingreso_packing({**base, "lote_code": lc2, "operator_code": "QA-LAT-V",
            "via_desverdizado": True, "extra": {}})
        collector_desv.record("ingreso_packing_via_desv", (time.perf_counter() - t0) * 1000)

        # Reportes
        collector_directo.print_report("Flujo Directo — use cases")
        collector_desv.print_report("Flujo Desverdizado — etapas adicionales")

        # Validación: ambos flujos deben completar cada use case en < 5 segundos
        for collector, nombre in [(collector_directo, "directo"),
                                   (collector_desv, "desverdizado")]:
            for label, m in collector.summary().items():
                self.assertLess(m["max_ms"], 5_000,
                    msg=f"[{nombre}] '{label}' tardó {m['max_ms']:.0f}ms — "
                        f"un solo use case no debe tardar más de 5s")
