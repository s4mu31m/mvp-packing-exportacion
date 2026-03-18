"""
Vistas de prueba para la conexión con Dataverse.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from infrastructure.dataverse.client import DataverseClient, DataverseAPIError
from infrastructure.dataverse.auth import DataverseAuthError
import logging

logger = logging.getLogger(__name__)


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


@require_http_methods(["GET"])
def test_accounts(request):
    """
    Endpoint para consultar las cuentas (accounts) de Dataverse.
    
    GET /api/dataverse/accounts/
    """
    try:
        client = DataverseClient()
        
        # Consultar las primeras 5 cuentas
        accounts = client.list_rows(
            entity_set_name="accounts",
            select=["accountid", "name", "accountnumber", "createdon"],
            top=5
        )
        
        return JsonResponse({
            "status": "success",
            "message": "Consulta exitosa de cuentas",
            "data": accounts.get("value", []),
            "count": len(accounts.get("value", []))
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


@require_http_methods(["GET"])  
def test_entities(request):
    """
    Endpoint para listar algunas entidades disponibles en Dataverse.
    
    GET /api/dataverse/entities/
    """
    try:
        client = DataverseClient()
        
        # Lista de entidades comunes para probar
        test_entities = ["accounts", "contacts", "systemusers"]
        results = {}
        
        for entity in test_entities:
            try:
                # Intentar obtener solo 1 registro de cada entidad
                data = client.list_rows(
                    entity_set_name=entity,
                    top=1
                )
                results[entity] = {
                    "exists": True,
                    "sample_count": len(data.get("value", [])),
                    "message": "Entidad accesible"
                }
            except Exception as e:
                results[entity] = {
                    "exists": False,
                    "error": str(e),
                    "message": "Entidad no accesible o no existe"
                }
        
        return JsonResponse({
            "status": "success", 
            "message": "Prueba de entidades completada",
            "entities": results
        })
        
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return JsonResponse({
            "status": "error",
            "message": "Error inesperado",
            "details": str(e)
        }, status=500)