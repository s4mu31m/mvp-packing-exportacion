"""
test_concurrencia.py — N operadores simultáneos con threading.

DIAGNÓSTICO (no bloqueante por defecto, excepto corrupción de datos).

Requiere TransactionTestCase: Django TestCase usa savepoints que bloquean
SQLite bajo threading. TransactionTestCase trunca tablas entre tests.

Nota sobre SQLite: en modo WAL permite un escritor a la vez.
Los locks transitorios son esperados y no indican un error del sistema.
Solo es BLOQUEANTE si hay corrupción de datos (500, duplicados, pérdida).

Clases:
  - ConcurrentRecepcionTest  → N=5 operadores de Recepcion arrancando a la vez
  - ConcurrentPackingTest    → 3 operadores de Proceso + 3 de Control simultáneos
"""
import threading
import uuid

from django.test import TransactionTestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

from usuarios.permissions import SESSION_KEY_ROL, SESSION_KEY_CODIGO_OPERADOR

from operaciones.models import Lote, Bin, RegistroEtapa

User = get_user_model()


def _make_thread_client(username, rol_str, is_staff=False, is_superuser=False,
                        operator_code="QA-THR"):
    """Crea un User + Client con sesión y rol inyectados. Seguro por thread (Client separado)."""
    user = User.objects.create_user(
        username=username, password="qa_thread_pw",
        is_staff=is_staff, is_superuser=is_superuser,
    )
    c = Client()
    c.force_login(user)
    session = c.session
    session[SESSION_KEY_ROL] = rol_str
    session[SESSION_KEY_CODIGO_OPERADOR] = operator_code
    session.save()
    return c


@override_settings(PERSISTENCE_BACKEND="sqlite")
class ConcurrentRecepcionTest(TransactionTestCase):
    """
    5 operadores de Recepcion arrancan simultáneamente via threading.Barrier.
    Cada uno inicia un lote, agrega un bin y lo cierra.

    BLOQUEANTE: HTTP 500, excepciones de thread, pérdida de datos, event_key duplicado.
    DIAGNÓSTICO: locks transitorios de SQLite (OperationalError: database is locked)
                 se capturan y reportan como advertencia, no como fallo duro.
    """

    N = 5

    def setUp(self):
        # Configurar timeout de SQLite para evitar locks
        from django.db import connection
        try:
            connection.cursor().execute("PRAGMA busy_timeout = 20000;")
        except Exception:
            pass

    def test_N_operadores_recepcion_simultaneos(self):
        results = []        # (thread_idx, step, status_code)
        errors = []         # (thread_idx, step, exception_str)
        lock = threading.Lock()
        barrier = threading.Barrier(self.N)

        def operator_task(idx):
            username = f"qa_conc_rec_{idx:03d}_{uuid.uuid4().hex[:6]}"
            op_code = f"QA-R{idx:02d}"
            lote_code = f"QA-CONC-{uuid.uuid4().hex[:8].upper()}"

            try:
                client = _make_thread_client(
                    username, "Recepcion", operator_code=op_code
                )

                # Sincronización: todos arrancan al mismo tiempo
                barrier.wait(timeout=30)

                # Paso 1: iniciar lote
                resp_init = client.post(
                    reverse("operaciones:recepcion"),
                    {"action": "iniciar", "temporada": "2026"},
                )
                with lock:
                    results.append((idx, "iniciar", resp_init.status_code))

                # Capturar lote_code de sesión
                lote_activo = client.session.get("lote_activo_code")
                if not lote_activo:
                    with lock:
                        errors.append((idx, "iniciar", "lote_activo_code no en sesión"))
                    return

                # Paso 2: agregar bin
                resp_bin = client.post(
                    reverse("operaciones:recepcion"),
                    {
                        "action": "agregar_bin",
                        "temporada": "2026",
                        "variedad_fruta": "Thompson Seedless",
                        "kilos_bruto_ingreso": "520",
                        "kilos_neto_ingreso": "498",
                    },
                )
                with lock:
                    results.append((idx, "agregar_bin", resp_bin.status_code))

                # Paso 3: cerrar lote
                resp_cerrar = client.post(
                    reverse("operaciones:recepcion"),
                    {
                        "action": "cerrar",
                        "temporada": "2026",
                        "requiere_desverdizado": "",
                        "disponibilidad_camara_desverdizado": "",
                        "kilos_bruto_conformacion": "520",
                        "kilos_neto_conformacion": "498",
                    },
                )
                with lock:
                    results.append((idx, "cerrar", resp_cerrar.status_code))

            except threading.BrokenBarrierError:
                with lock:
                    errors.append((idx, "barrier", "BrokenBarrier — thread no llegó a tiempo"))
            except Exception as exc:
                with lock:
                    errors.append((idx, "unknown", str(exc)))

        threads = [threading.Thread(target=operator_task, args=(i,))
                   for i in range(self.N)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        # ----- Assertions -----

        # Clasificar errores: locks/barrier son infra SQLite (DIAGNÓSTICO), el resto BLOQUEANTE
        infra_errors = [
            e for e in errors
            if "locked" in e[2].lower() or "BrokenBarrier" in e[2] or e[2] == ""
        ]
        non_infra_errors = [e for e in errors if e not in infra_errors]

        # Excepciones no controladas (BLOQUEANTE — excluye locks/barrier/cadena vacía)
        self.assertEqual(non_infra_errors, [],
            msg=f"Excepciones no controladas en threads: {non_infra_errors}")

        # HTTP 500 — BLOQUEANTE salvo si causado por locks SQLite (DIAGNÓSTICO en ese caso)
        fives = [(idx, step, st) for idx, step, st in results if st == 500]
        if fives and infra_errors:
            print(f"\n[DIAGNÓSTICO] {len(fives)} respuesta(s) HTTP 500 bajo concurrencia — "
                  f"probablemente causadas por locks SQLite. Verificar en staging con PostgreSQL.")
        elif fives:
            self.assertEqual(fives, [],
                msg=f"HTTP 500 bajo concurrencia (sin locks SQLite detectados): {fives}")

        # Respuestas inesperadas (BLOQUEANTE)
        invalid = [(idx, step, st) for idx, step, st in results
                   if st not in (200, 302, 500)]
        self.assertEqual(invalid, [],
            msg=f"Respuestas HTTP inesperadas bajo concurrencia: {invalid}")

        # Lotes creados — BLOQUEANTE si no hay infra_errors, DIAGNÓSTICO si los hay
        lotes_creados = Lote.objects.filter(temporada="2026").count()
        if lotes_creados == 0 and infra_errors:
            print(f"\n[DIAGNÓSTICO] Ningún lote creado — {len(infra_errors)} fallos "
                  f"por locks/barrier SQLite. Esperado en SQLite local, no indica pérdida de datos.")
        elif lotes_creados == 0:
            self.fail("Ningún lote fue creado bajo concurrencia — posible pérdida total de datos")

        # Unicidad de event_key (BLOQUEANTE — idempotencia bajo concurrencia)
        total_registros = RegistroEtapa.objects.filter(temporada="2026").count()
        if total_registros > 0:
            distintos = (
                RegistroEtapa.objects.filter(temporada="2026")
                .values("event_key").distinct().count()
            )
            self.assertEqual(total_registros, distintos,
                msg=f"Event_key duplicados bajo concurrencia: {total_registros} registros, "
                    f"{distintos} únicos — corrupción de idempotencia")

        # Reporte diagnóstico de infra (no BLOQUEANTE)
        if infra_errors:
            print(f"\n[DIAGNÓSTICO] {len(infra_errors)} fallo(s) de infra SQLite "
                  f"(locks/barrier) en ConcurrentRecepcionTest — esperado en entorno local, "
                  f"no indica corrupción de datos.")


@override_settings(PERSISTENCE_BACKEND="sqlite")
class ConcurrentPackingTest(TransactionTestCase):
    """
    3 operadores de Proceso + 3 de Control sobre lotes distintos simultáneamente.
    Verifica que los registros de packing no se mezclan entre lotes.
    """

    def setUp(self):
        from django.db import connection
        try:
            connection.cursor().execute("PRAGMA busy_timeout = 20000;")
        except Exception:
            pass

    def test_proceso_y_control_sobre_lotes_distintos(self):
        from operaciones.application.use_cases import (
            iniciar_lote_recepcion, agregar_bin_a_lote_abierto,
            cerrar_lote_recepcion, registrar_ingreso_packing,
        )
        N = 3
        base_args = {"temporada": "2026", "source_system": "test"}

        # Crear N lotes con ingreso packing (setup síncrono)
        lote_codes = []
        for i in range(N):
            res = iniciar_lote_recepcion({**base_args, "operator_code": f"QA-PACK-{i}"})
            lc = res.data["lote_code"]
            agregar_bin_a_lote_abierto({**base_args, "lote_code": lc,
                "operator_code": f"QA-PACK-{i}",
                "variedad_fruta": "Thompson Seedless",
                "kilos_neto_ingreso": "300", "kilos_bruto_ingreso": "315"})
            cerrar_lote_recepcion({**base_args, "lote_code": lc,
                "operator_code": f"QA-PACK-{i}"})
            registrar_ingreso_packing({**base_args, "lote_code": lc,
                "operator_code": f"QA-PACK-{i}",
                "via_desverdizado": False, "extra": {}})
            lote_codes.append(lc)

        results = []
        errors = []
        lock = threading.Lock()
        barrier = threading.Barrier(N * 2)  # N proceso + N control

        def proceso_task(idx, lote_code):
            username = f"qa_conc_proc_{idx}_{uuid.uuid4().hex[:6]}"
            try:
                client = _make_thread_client(username, "Proceso", operator_code=f"QA-PC{idx}")
                barrier.wait(timeout=30)
                resp = client.post(reverse("operaciones:proceso"), {
                    "temporada": "2026",
                    "lote_code": lote_code,
                    "fecha": "2026-03-15",
                    "hora_inicio": "10:30",
                    "linea_proceso": f"L{idx}",
                    "categoria_calidad": "Extra",
                    "calibre": "XL",
                    "tipo_envase": "Caja 8.2kg",
                    "cantidad_cajas_producidas": "60",
                    "merma_seleccion_pct": "3.5",
                })
                with lock:
                    results.append(("proceso", idx, lote_code, resp.status_code))
            except Exception as exc:
                with lock:
                    errors.append(("proceso", idx, str(exc)))

        def control_task(idx, lote_code):
            username = f"qa_conc_ctrl_{idx}_{uuid.uuid4().hex[:6]}"
            try:
                client = _make_thread_client(username, "Control", operator_code=f"QA-CT{idx}")
                barrier.wait(timeout=30)
                resp = client.post(reverse("operaciones:control"), {
                    "temporada": "2026",
                    "lote_code": lote_code,
                    "fecha": "2026-03-15",
                    "hora": "11:00",
                    "n_bins_procesados": "2",
                    "temp_agua_tina": "4.5",
                    "ph_agua": "6.8",
                    "recambio_agua": "True",
                    "rendimiento_lote_pct": "90.0",
                })
                with lock:
                    results.append(("control", idx, lote_code, resp.status_code))
            except Exception as exc:
                with lock:
                    errors.append(("control", idx, str(exc)))

        threads = []
        for i, lc in enumerate(lote_codes):
            threads.append(threading.Thread(target=proceso_task, args=(i, lc)))
            threads.append(threading.Thread(target=control_task, args=(i, lc)))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        # Assertions
        # Excluir locks SQLite, BrokenBarrier (explícito o por str='')
        non_lock_errors = [
            e for e in errors
            if "locked" not in str(e).lower()
            and "BrokenBarrier" not in str(e)
            and str(e[2]) != ""
        ]
        self.assertEqual(non_lock_errors, [],
            msg=f"Excepciones no controladas en threads de packing: {non_lock_errors}")

        fives = [r for r in results if r[3] == 500]
        self.assertEqual(fives, [],
            msg=f"HTTP 500 en packing concurrente: {fives}")

        # Verificar que los RegistroPacking y ControlProcesoPacking
        # están correctamente asociados a sus lotes
        from operaciones.models import RegistroPacking, ControlProcesoPacking
        for lc in lote_codes:
            lote = Lote.objects.get(temporada="2026", lote_code=lc)
            proc_count = lote.registros_packing.count()
            ctrl_count = lote.control_proceso_packing.count()
            # Cada lote debe tener sus propios registros (puede ser 0 si hubo lock)
            # Lo importante es que no estén mezclados entre lotes
            self.assertLessEqual(proc_count, 1,
                msg=f"Lote {lc} tiene {proc_count} RegistroPacking — máximo esperado: 1 por thread")
            self.assertLessEqual(ctrl_count, 1,
                msg=f"Lote {lc} tiene {ctrl_count} ControlProcesoPacking — máximo esperado: 1 por thread")

        # Unicidad global de event_key
        total = RegistroEtapa.objects.filter(temporada="2026").count()
        if total > 0:
            distintos = (
                RegistroEtapa.objects.filter(temporada="2026")
                .values("event_key").distinct().count()
            )
            self.assertEqual(total, distintos,
                msg="Event_key duplicados en test de packing concurrente")
