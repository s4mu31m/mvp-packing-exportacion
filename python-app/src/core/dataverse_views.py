
"""
Vistas de prueba para la conexión con Dataverse.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from infrastructure.dataverse.client import DataverseClient, DataverseAPIError
from infrastructure.dataverse.auth import DataverseAuthError
import logging

logger = logging.getLogger(__name__)

@require_http_methods(["GET"])
def check_tables_available(request):
    """
    Endpoint para verificar si las 14 tablas del modelo están accesibles y obtener un sample_count de cada una.
    GET /api/dataverse/check_tables/
    """
    try:
        client = DataverseClient()
        tables_to_check = [
            "crf21_bins",
            "crf21_calidad_desverdizados",
            "crf21_camara_mantencions",
            "crf21_lote_plantas",
            "crf21_bin_lote_plantas",
            "crf21_calidad_pallets",
            "crf21_camara_frios",
            "crf21_control_proceso_packings",
            "crf21_desverdizados",
            "crf21_ingreso_packings",
            "crf21_lote_planta_pallets",
            "crf21_medicion_temperatura_salidas",
            "crf21_pallets",
            "crf21_registro_packings"
        ]
        results = {}
        for table in tables_to_check:
            try:
                data = client.list_rows(entity_set_name=table, top=1)
                sample_count = len(data.get("value", []))
                pk_value = None
                sample_record = None
                if sample_count > 0:
                    logical_name = table[:-1] if table.endswith('s') else table
                    pk_field = f"{logical_name}id"
                    pk_value = data["value"][0].get(pk_field)
                    if table in ["crf21_bins", "crf21_bin_lote_plantas", 
                                "crf21_lote_plantas", 
                                "crf21_camara_mantencions", 
                                "crf21_desverdizados" , 
                                "crf21_calidad_desverdizados" , 
                                "crf21_ingreso_packings" , 
                                "crf21_registro_packings" , 
                                "crf21_control_proceso_packings" ,
                                "crf21_pallets", 
                                "crf21_lote_planta_pallets" , 
                                "crf21_calidad_pallets" , 
                                "crf21_camara_frios" , 
                                "crf21_medicion_temperatura_salidas" ]:
                        sample_record = data["value"][0]
                result = {
                    "accessible": True,
                    "sample_count": sample_count,
                    "pk": pk_value
                }
                if table in ["crf21_bins", 
                            "crf21_bin_lote_plantas", 
                            "crf21_lote_plantas", 
                            "crf21_camara_mantencions" , 
                            "crf21_desverdizados" , 
                            "crf21_calidad_desverdizados" , 
                            "crf21_ingreso_packings" , 
                            "crf21_registro_packings" , 
                            "crf21_control_proceso_packings" , 
                            "crf21_pallets" , 
                            "crf21_lote_planta_pallets" , 
                            "crf21_calidad_pallets" , 
                            "crf21_camara_frios" , 
                            "crf21_medicion_temperatura_salidas" ]:
                    result["sample_record"] = sample_record
                results[table] = result
            except Exception as e:
                results[table] = {
                    "accessible": False,
                    "error": str(e)
                }
        return JsonResponse({
            "status": "success",
            "tables": results
        })
    except Exception as e:
        logger.error(f"Error en check_tables_available: {e}")
        return JsonResponse({
            "status": "error",
            "message": "Error al verificar tablas",
            "details": str(e)
        }, status=500)


@require_http_methods(["GET"])
def ping_dataverse(request):
    """
    Endpoint para probar la conexión básica con Dataverse.
    
    GET /api/dataverse/ping/
    """
    try:
        client = DataverseClient()
        
        # Prueba simple: obtener información del usuario actual
        user_info = client.whoami()
        
        return JsonResponse({
            "status": "success",
            "message": "Conexión exitosa a Dataverse",
            "user_id": user_info.get("UserId"),
            "organization_id": user_info.get("OrganizationId"),
            "business_unit_id": user_info.get("BusinessUnitId")
        })
        
    except DataverseAuthError as e:
        logger.error(f"Error de autenticación Dataverse: {e}")
        return JsonResponse({
            "status": "error",
            "message": "Error de autenticación con Dataverse",
            "details": str(e)
        }, status=401)
        
    except DataverseAPIError as e:
        logger.error(f"Error de API Dataverse: {e}")
        return JsonResponse({
            "status": "error",
            "message": "Error en la API de Dataverse",
            "details": str(e)
        }, status=500)
        
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return JsonResponse({
            "status": "error",
            "message": "Error inesperado",
            "details": str(e)
        }, status=500)
    
@require_http_methods(["POST"])
def save_first_bin_code(request):
    """
    Guarda el valor de bin_code del primer registro de la tabla crf21_bins en un archivo local.
    POST /api/dataverse/save_first_bin_code/
    """
    try:
        client = DataverseClient()
        data = client.list_rows(entity_set_name="crf21_bins", top=1)
        if data.get("value"):
            bin_code = data["value"][0].get("crf21_bin_code")
            if bin_code:
                mensaje = f"El bin code de bin es: {bin_code}"
                return JsonResponse({"status": "success", "bin_code": bin_code, "mensaje": mensaje})
            else:
                return JsonResponse({"status": "error", "message": "No se encontró el campo crf21_bin_code en el primer registro."}, status=404)
        else:
            return JsonResponse({"status": "error", "message": "No se encontraron registros en crf21_bins."}, status=404)
    except Exception as e:
        logger.error(f"Error en save_first_bin_code: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
    
@require_http_methods(["GET"])
def get_first_bin_code(request):
    """
    Devuelve el valor de bin_code del primer registro de la tabla crf21_bins en JSON.
    GET /api/dataverse/get_first_bin_code/
    """
    try:
        client = DataverseClient()
        data = client.list_rows(entity_set_name="crf21_bins", top=1)
        if data.get("value"):
            bin_code = data["value"][0].get("crf21_bin_code")
            if bin_code:
                return JsonResponse({"bin_code": bin_code})
            else:
                return JsonResponse({"error": "No se encontró el campo crf21_bin_code en el primer registro."}, status=404)
        else:
            return JsonResponse({"error": "No se encontraron registros en crf21_bins."}, status=404)
    except Exception as e:
        logger.error(f"Error en get_first_bin_code: {e}")
        return JsonResponse({"error": str(e)}, status=500)

