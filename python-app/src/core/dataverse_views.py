"""
Vistas internas de diagnostico Dataverse.

Estas rutas solo deben habilitarse en entornos de desarrollo mediante
`ENABLE_DEV_DIAGNOSTICS=true` y su uso queda restringido a superusuarios.
"""
import logging

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from infrastructure.dataverse.auth import DataverseAuthError
from infrastructure.dataverse.client import DataverseAPIError, DataverseClient

logger = logging.getLogger(__name__)

_TABLES_TO_CHECK = (
    "crf21_bins",
    "crf21_calidad_desverdizados",
    "crf21_camara_mantencions",
    "crf21_lote_plantas",
    "crf21_bin_lote_plantas",
    "crf21_calidad_pallets",
    "crf21_calidad_pallet_muestras",
    "crf21_camara_frios",
    "crf21_control_proceso_packings",
    "crf21_desverdizados",
    "crf21_ingreso_packings",
    "crf21_lote_planta_pallets",
    "crf21_medicion_temperatura_salidas",
    "crf21_pallets",
    "crf21_registro_packings",
    "crf21_usuariooperativos",
)


def _is_superuser(user) -> bool:
    return bool(user and user.is_authenticated and user.is_superuser)


def _safe_error(message: str, status: int = 500) -> JsonResponse:
    return JsonResponse({"status": "error", "message": message}, status=status)


def _mask_value(value: str | None) -> str:
    if not value:
        return ""
    raw = str(value).strip()
    if len(raw) <= 4:
        return "*" * len(raw)
    return f"{raw[:3]}{'*' * (len(raw) - 5)}{raw[-2:]}"


@login_required
@user_passes_test(_is_superuser)
@require_http_methods(["GET"])
def check_tables_available(request):
    """
    Verifica accesibilidad basica de tablas del modelo en Dataverse.
    GET /api/dataverse/check_tables/
    """
    try:
        client = DataverseClient()
        available = 0
        unavailable = 0
        sampled_rows = 0
        for table in _TABLES_TO_CHECK:
            try:
                data = client.list_rows(entity_set_name=table, top=1)
                available += 1
                sampled_rows += len(data.get("value", []))
            except Exception as exc:
                unavailable += 1
                logger.warning("Entidad de diagnostico no disponible: %s (%s)", table, exc)

        return JsonResponse(
            {
                "status": "success",
                "message": "Verificacion completada.",
                "summary": {
                    "checked_entities": len(_TABLES_TO_CHECK),
                    "available_entities": available,
                    "unavailable_entities": unavailable,
                    "sampled_rows": sampled_rows,
                },
            }
        )
    except Exception as exc:
        logger.error("Error en check_tables_available: %s", exc)
        return _safe_error("No fue posible verificar el esquema.", status=500)


@login_required
@user_passes_test(_is_superuser)
@require_http_methods(["GET"])
def ping_dataverse(request):
    """
    Prueba conectividad basica con Dataverse.
    GET /api/dataverse/ping/
    """
    try:
        client = DataverseClient()
        user_info = client.whoami()

        return JsonResponse(
            {
                "status": "success",
                "message": "Conectividad validada.",
                "diagnostic_context": {
                    "user_id": _mask_value(user_info.get("UserId")),
                    "organization_id": _mask_value(user_info.get("OrganizationId")),
                    "business_unit_id": _mask_value(user_info.get("BusinessUnitId")),
                },
            }
        )

    except DataverseAuthError as exc:
        logger.error("Error de autenticacion Dataverse: %s", exc)
        return _safe_error("No fue posible autenticar contra el servicio.", status=401)

    except DataverseAPIError as exc:
        logger.error("Error de API Dataverse: %s", exc)
        return _safe_error("El servicio no respondio correctamente.", status=500)

    except Exception as exc:
        logger.error("Error inesperado en ping_dataverse: %s", exc)
        return _safe_error("No fue posible validar conectividad.", status=500)


@login_required
@user_passes_test(_is_superuser)
@require_http_methods(["POST"])
def save_first_bin_code(request):
    """
    Endpoint legacy de apoyo para diagnostico de lectura de bins.
    POST /api/dataverse/save_first_bin_code/
    """
    try:
        client = DataverseClient()
        data = client.list_rows(entity_set_name="crf21_bins", top=1)
        if data.get("value"):
            bin_code = data["value"][0].get("crf21_bin_code")
            if bin_code:
                return JsonResponse(
                    {
                        "status": "success",
                        "bin_code": _mask_value(bin_code),
                    }
                )
            return _safe_error("No se encontro un codigo valido en el primer registro.", status=404)
        return _safe_error("No se encontraron registros de bins.", status=404)
    except Exception as exc:
        logger.error("Error en save_first_bin_code: %s", exc)
        return _safe_error("No fue posible consultar el primer bin.", status=500)


@login_required
@user_passes_test(_is_superuser)
@require_http_methods(["GET"])
def get_first_bin_code(request):
    """
    Endpoint legacy de apoyo para diagnostico de lectura de bins.
    GET /api/dataverse/get_first_bin_code/
    """
    try:
        client = DataverseClient()
        data = client.list_rows(entity_set_name="crf21_bins", top=1)
        if data.get("value"):
            bin_code = data["value"][0].get("crf21_bin_code")
            if bin_code:
                return JsonResponse(
                    {
                        "status": "success",
                        "bin_code": _mask_value(bin_code),
                    }
                )
            return _safe_error("No se encontro un codigo valido en el primer registro.", status=404)
        return _safe_error("No se encontraron registros de bins.", status=404)
    except Exception as exc:
        logger.error("Error en get_first_bin_code: %s", exc)
        return _safe_error("No fue posible consultar el primer bin.", status=500)
