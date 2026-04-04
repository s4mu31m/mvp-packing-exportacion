# operaciones/api/views.py

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from operaciones.application.use_cases import (
    registrar_bin_recibido,
    crear_lote_recepcion,
    cerrar_pallet,
    registrar_evento_etapa,
)
from operaciones.models import Bin, Lote, Pallet, RegistroEtapa


@require_http_methods(["POST"])
def api_registrar_bin(request):
    payload = json.loads(request.body)
    result = registrar_bin_recibido(payload)
    return JsonResponse(
        {"ok": result.ok, "code": result.code, "message": result.message,
         "data": result.data, "errors": result.errors},
        status=200 if result.ok else 400
    )


@require_http_methods(["POST"])
def api_crear_lote(request):
    payload = json.loads(request.body)
    result = crear_lote_recepcion(payload)
    return JsonResponse(
        {"ok": result.ok, "code": result.code, "message": result.message,
         "data": result.data, "errors": result.errors},
        status=200 if result.ok else 400
    )


@require_http_methods(["POST"])
def api_cerrar_pallet(request):
    payload = json.loads(request.body)
    result = cerrar_pallet(payload)
    return JsonResponse(
        {"ok": result.ok, "code": result.code, "message": result.message,
         "data": result.data, "errors": result.errors},
        status=200 if result.ok else 400
    )


@require_http_methods(["POST"])
def api_registrar_evento(request):
    payload = json.loads(request.body)
    result = registrar_evento_etapa(payload)
    return JsonResponse(
        {"ok": result.ok, "code": result.code, "message": result.message,
         "data": result.data, "errors": result.errors},
        status=200 if result.ok else 400
    )


@require_http_methods(["GET"])
def api_trazabilidad(request):
    temporada = request.GET.get("temporada", "")
    qs = RegistroEtapa.objects.select_related("bin", "lote", "pallet")
    if temporada:
        qs = qs.filter(temporada=temporada)
    registros = [
        {
            "id": r.id,
            "tipo_evento": r.tipo_evento,
            "temporada": r.temporada,
            "bin": r.bin.bin_code if r.bin else None,
            "lote": r.lote.lote_code if r.lote else None,
            "pallet": r.pallet.pallet_code if r.pallet else None,
            "created_at": r.created_at.isoformat(),
        }
        for r in qs[:100]
    ]
    return JsonResponse({"ok": True, "data": registros})