from django.urls import path
from operaciones.api.views import (
    api_registrar_bin, api_crear_lote,
    api_cerrar_pallet, api_trazabilidad
)

urlpatterns = [
    path("bins/", api_registrar_bin),
    path("lotes/", api_crear_lote),
    path("pallets/", api_cerrar_pallet),
    path("trazabilidad/", api_trazabilidad),
]