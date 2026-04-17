"""
base.py — Capa común reutilizable de la suite QA.

Contiene:
  - QASetupMixin: creación de usuarios, clientes y sesiones por rol
  - FIELD_DATA: datasets realistas de campo (dos variedades)
  - Payload builders: uno por etapa del flujo
  - Assert helpers: trazabilidad, integridad, acceso, HTTP
"""
import datetime

from django.contrib.auth import get_user_model
from django.test import Client
from django.test import override_settings

from usuarios.permissions import SESSION_KEY_ROL, SESSION_KEY_CODIGO_OPERADOR

User = get_user_model()
TEMPORADA = str(datetime.date.today().year)


# ---------------------------------------------------------------------------
# Configuración de roles
# ---------------------------------------------------------------------------

ROLES = {
    "recepcion":    ("qa_recepcion",     "Recepcion",       False, False, "QA-001"),
    "desverdizado": ("qa_desverdizado",  "Desverdizado",    False, False, "QA-002"),
    "ing_packing":  ("qa_ing_packing",   "Ingreso Packing", False, False, "QA-003"),
    "proceso":      ("qa_proceso",       "Proceso",         False, False, "QA-004"),
    "control":      ("qa_control",       "Control",         False, False, "QA-005"),
    "paletizado":   ("qa_paletizado",    "Paletizado",      False, False, "QA-006"),
    "camaras":      ("qa_camaras",       "Camaras",         False, False, "QA-007"),
    "jefatura":     ("qa_jefatura",      "Jefatura",        True,  False, "QA-008"),
    "administrador":("qa_administrador", "Administrador",   True,  True,  "QA-009"),
}

# Mapeo módulo operativo → URL name
MODULO_URL = {
    "dashboard":      "operaciones:dashboard",
    "recepcion":      "operaciones:recepcion",
    "desverdizado":   "operaciones:desverdizado",
    "ingreso_packing":"operaciones:ingreso_packing",
    "proceso":        "operaciones:proceso",
    "control":        "operaciones:control",
    "paletizado":     "operaciones:paletizado",
    "camaras":        "operaciones:camaras",
    "consulta":       "operaciones:consulta",
}


# ---------------------------------------------------------------------------
# QASetupMixin
# ---------------------------------------------------------------------------

class QASetupMixin:
    """
    Mixin para TestCase y TransactionTestCase.

    Uso en TestCase (setUpTestData — clase):
        @classmethod
        def setUpTestData(cls):
            cls.clients = QASetupMixin.build_all_clients()

    Uso en TransactionTestCase (setUp — instancia):
        def setUp(self):
            self.clients = QASetupMixin.build_all_clients()
    """

    @staticmethod
    def make_role_client(username, rol_str, is_staff=False, is_superuser=False,
                         operator_code="QA-XXX", suffix=""):
        """
        Crea un User Django, hace force_login e inyecta SESSION_KEY_ROL
        y crf21_codigooperador en la sesión. Devuelve (client, user).
        """
        uname = username + suffix if suffix else username
        user = User.objects.create_user(
            username=uname,
            password="qa_test_pw_2026",
            is_staff=is_staff,
            is_superuser=is_superuser,
        )
        c = Client()
        c.force_login(user)
        session = c.session
        session[SESSION_KEY_ROL] = rol_str
        session[SESSION_KEY_CODIGO_OPERADOR] = operator_code
        session.save()
        return c, user

    @classmethod
    def build_all_clients(cls, suffix=""):
        """
        Construye un client para cada rol definido en ROLES.
        Devuelve dict: {rol_key: (client, user)}
        """
        result = {}
        for key, (username, rol_str, is_staff, is_superuser, op_code) in ROLES.items():
            result[key] = cls.make_role_client(
                username, rol_str, is_staff, is_superuser, op_code, suffix=suffix
            )
        return result

    @staticmethod
    def get_lote_code_from_session(client):
        """Lee el lote_code que RecepcionView escribe en sesión."""
        return client.session.get("lote_activo_code")


# ---------------------------------------------------------------------------
# Datasets realistas de campo
# ---------------------------------------------------------------------------

VARIEDAD_BLANCA = {
    "codigo_productor": "PROD-SAN-ESTEBAN-01",
    "tipo_cultivo":     "Uva de mesa",
    "variedad_fruta":   "Thompson Seedless",
    "color":            "2",
    "fecha_cosecha":    "2026-03-15",
    "numero_cuartel":   "C-04",
    "nombre_cuartel":   "Cuartel Norte",
    "codigo_sag_csg":   "CSG-001",
    "codigo_sag_csp":   "CSP-001",
    "codigo_sdp":       "SDP-001",
    "lote_productor":   "Lote Campo 1",
    "hora_recepcion":   "08:30",
    "kilos_bruto_ingreso": "520",
    "kilos_neto_ingreso":  "498",
    "a_o_r":            "aprobado",
    "observaciones":    "",
}

VARIEDAD_ROJA = {
    "codigo_productor": "PROD-LIMARI-07",
    "tipo_cultivo":     "Uva de mesa",
    "variedad_fruta":   "Red Globe",
    "color":            "5",
    "fecha_cosecha":    "2026-03-12",
    "numero_cuartel":   "C-11",
    "nombre_cuartel":   "Cuartel Sur",
    "codigo_sag_csg":   "CSG-101",
    "codigo_sag_csp":   "CSP-101",
    "codigo_sdp":       "SDP-101",
    "lote_productor":   "Lote Campo 11",
    "hora_recepcion":   "09:45",
    "kilos_bruto_ingreso": "610",
    "kilos_neto_ingreso":  "585",
    "a_o_r":            "objetado",
    "observaciones":    "Manchas leves en epidermis, aceptado condicionado",
}


# ---------------------------------------------------------------------------
# Payload builders — uno por etapa
# ---------------------------------------------------------------------------

def build_iniciar_payload(temporada=TEMPORADA, **kwargs):
    data = {"action": "iniciar", "temporada": temporada}
    data.update(kwargs)
    return data


def build_bin_payload(variedad=None, temporada=TEMPORADA, **kwargs):
    if variedad is None:
        variedad = VARIEDAD_BLANCA
    data = {"action": "agregar_bin", "temporada": temporada}
    data.update(variedad)
    data.update(kwargs)
    return data


def build_cierre_lote_payload(
    requiere_desverdizado=False,
    temporada=TEMPORADA,
    **kwargs,
):
    data = {
        "action": "cerrar",
        "temporada": temporada,
        "requiere_desverdizado": "on" if requiere_desverdizado else "",
        "kilos_bruto_conformacion": "520",
        "kilos_neto_conformacion":  "498",
    }
    data.update(kwargs)
    return data


def build_mantencion_payload(lote_code, temporada=TEMPORADA, **kwargs):
    data = {
        "action": "mantencion",
        "temporada": temporada,
        "lote_code": lote_code,
        "camara_numero": "CM-1",
        "fecha_ingreso": "2026-03-15",
        "hora_ingreso":  "09:00",
        "temperatura_camara": "12.0",
        "humedad_relativa":   "85.0",
        "observaciones": "En espera de camara desverdizado",
    }
    data.update(kwargs)
    return data


def build_desverdizado_payload(lote_code, temporada=TEMPORADA, **kwargs):
    data = {
        "action": "desverdizado",
        "temporada": temporada,
        "lote_code": lote_code,
        "fecha_ingreso": "2026-03-15",
        "hora_ingreso":  "12:00",
        "color":  "4",
        "horas_desverdizado": "72",
        "kilos_enviados_terreno": "480",
        "kilos_recepcionados":    "475",
    }
    data.update(kwargs)
    return data


def build_ingreso_packing_payload(lote_code, via_desverdizado=False,
                                   temporada=TEMPORADA, **kwargs):
    data = {
        "temporada":  temporada,
        "lote_code":  lote_code,
        "fecha_ingreso": "2026-03-15",
        "hora_ingreso":  "10:15",
        "kilos_bruto_ingreso_packing": "498",
        "kilos_neto_ingreso_packing":  "482",
        "via_desverdizado": "on" if via_desverdizado else "",
        "observaciones": "Ingreso QA",
    }
    data.update(kwargs)
    return data


def build_proceso_payload(lote_code, temporada=TEMPORADA, **kwargs):
    data = {
        "temporada":  temporada,
        "lote_code":  lote_code,
        "fecha":      "2026-03-15",
        "hora_inicio": "10:30",
        "linea_proceso":         "L1",
        "categoria_calidad":     "Extra",
        "calibre":               "XL",
        "tipo_envase":           "Caja 8.2kg",
        "cantidad_cajas_producidas": "60",
        "merma_seleccion_pct":   "3.5",
    }
    data.update(kwargs)
    return data


def build_control_payload(lote_code, temporada=TEMPORADA, **kwargs):
    data = {
        "temporada":  temporada,
        "lote_code":  lote_code,
        "fecha":      "2026-03-15",
        "hora":       "11:00",
        "n_bins_procesados": "4",
        "temp_agua_tina":    "4.5",
        "ph_agua":           "6.8",
        "recambio_agua":     "True",
        "rendimiento_lote_pct": "92.0",
        "observaciones_generales": "Proceso normal QA",
    }
    data.update(kwargs)
    return data


def build_calidad_pallet_payload(pallet_code, temporada=TEMPORADA, **kwargs):
    data = {
        "action":       "calidad",
        "temporada":    temporada,
        "pallet_code":  pallet_code,
        "fecha":        "2026-03-15",
        "hora":         "13:00",
        "temperatura_fruta":   "4.2",
        "peso_caja_muestra":   "8.150",
        "estado_visual_fruta": "Buena",
        "presencia_defectos":  "",
        "aprobado":            "True",
        "observaciones":       "Pallet QA aprobado",
    }
    data.update(kwargs)
    return data


def build_camara_frio_payload(pallet_code, temporada=TEMPORADA, **kwargs):
    data = {
        "action":       "camara",
        "temporada":    temporada,
        "pallet_code":  pallet_code,
        "camara_numero":     "CF-3",
        "temperatura_camara": "-0.5",
        "humedad_relativa":   "92.0",
        "fecha_ingreso":  "2026-03-15",
        "hora_ingreso":   "14:00",
        "destino_despacho": "USA-Export",
    }
    data.update(kwargs)
    return data


def build_medicion_temperatura_payload(pallet_code, temporada=TEMPORADA, **kwargs):
    data = {
        "action":       "medicion",
        "temporada":    temporada,
        "pallet_code":  pallet_code,
        "fecha":        "2026-03-16",
        "hora":         "06:00",
        "temperatura_pallet":  "-0.8",
        "punto_medicion": "Centro pallet nivel 2",
        "dentro_rango":   "True",
        "observaciones":  "Temperatura optima para despacho",
    }
    data.update(kwargs)
    return data


# ---------------------------------------------------------------------------
# Assert helpers compartidos
# ---------------------------------------------------------------------------

def assert_trazabilidad(test_case, lote, pallet, eventos_esperados, msg_prefix=""):
    """
    Verifica que todos los TipoEvento esperados están registrados
    en RegistroEtapa para el lote y pallet dados.
    """
    from operaciones.models import RegistroEtapa
    tipos_presentes = set(
        RegistroEtapa.objects.filter(temporada=TEMPORADA)
        .values_list("tipo_evento", flat=True)
    )
    for tipo in eventos_esperados:
        test_case.assertIn(
            tipo, tipos_presentes,
            msg=f"{msg_prefix}Falta RegistroEtapa de tipo '{tipo}' — "
                f"presentes: {sorted(tipos_presentes)}",
        )


def assert_integridad_registros(test_case, temporada=TEMPORADA):
    """
    Verifica la integridad de la cadena de trazabilidad:
      1. Sin registros huérfanos (sin bin, lote ni pallet).
      2. event_key único (idempotencia).
    """
    from operaciones.models import RegistroEtapa
    qs = RegistroEtapa.objects.filter(temporada=temporada)

    huerfanos = qs.filter(bin__isnull=True, lote__isnull=True, pallet__isnull=True)
    test_case.assertEqual(
        huerfanos.count(), 0,
        msg=f"Hay {huerfanos.count()} RegistroEtapa huérfanos (sin entidad asociada)",
    )

    total = qs.count()
    distintos = qs.values("event_key").distinct().count()
    test_case.assertEqual(
        total, distintos,
        msg=f"Duplicados en event_key: {total} registros pero solo {distintos} keys distintos",
    )


def assert_post_ok(test_case, client, url, payload, allowed=(200, 302), msg=""):
    """POST a url con payload; verifica que el status esté en allowed."""
    resp = client.post(url, payload)
    test_case.assertIn(
        resp.status_code, allowed,
        msg=msg or f"POST {url} → HTTP {resp.status_code} (esperado {allowed})",
    )
    return resp


def assert_acceso_bloqueado(test_case, client, url, msg=""):
    """GET a url; verifica que el status sea 403."""
    resp = client.get(url)
    test_case.assertEqual(
        resp.status_code, 403,
        msg=msg or f"GET {url} debería devolver 403, obtuvo {resp.status_code}",
    )
    return resp


def assert_no_form_fields_in_403(test_case, resp, field_names):
    """
    Verifica que en una respuesta 403 no aparecen los campos de formulario
    del módulo protegido — previene exponer UI a rol incorrecto.
    """
    content = resp.content.decode()
    for name in field_names:
        test_case.assertNotIn(
            f'name="{name}"', content,
            msg=f"Campo '{name}' expuesto en respuesta 403 — posible leak de UI",
        )
