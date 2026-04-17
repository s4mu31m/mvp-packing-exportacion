# src/core/context_processors.py

from django.urls import reverse


def CaliPro_context(request):
    """
    Inyecta en todos los templates:
    - planta_seleccionada
    - exportador_activo
    - nav_sections  (sidebar, filtrado por roles de negocio)
    - mobile_nav_items
    """
    if not request.user.is_authenticated:
        return {}

    return {
        "planta_seleccionada": request.session.get("planta_seleccionada", {
            "id": 10,
            "nombre": "CaliPro",
        }),
        "exportador_activo": request.session.get("exportador_activo", {
            "id": 39,
            "nombre": "Exportadora CaliPro S.A.",
        }),
        "nav_sections": _nav_sections(request),
        "mobile_nav_items": _mobile_nav(),
        "codigo_operador": request.session.get("crf21_codigooperador", ""),
    }


def _safe_reverse(url_name):
    try:
        return reverse(url_name)
    except Exception:
        return "#"


def _nav_sections(request):
    from usuarios.permissions import is_admin, is_jefatura, puede_acceder_modulo

    _all_op_items = [
        {"name": "Dashboard",          "icon": "🏠", "url": _safe_reverse("operaciones:dashboard"),       "url_name": "dashboard",       "modulo": "dashboard"},
        {"name": "Recepción",          "icon": "📥", "url": _safe_reverse("operaciones:recepcion"),       "url_name": "recepcion",       "modulo": "recepcion"},
        {"name": "Desverdizado",       "icon": "🌿", "url": _safe_reverse("operaciones:desverdizado"),    "url_name": "desverdizado",    "modulo": "desverdizado"},
        {"name": "Ingreso Packing",    "icon": "📦", "url": _safe_reverse("operaciones:ingreso_packing"), "url_name": "ingreso_packing", "modulo": "ingreso_packing"},
        {"name": "Parámetros Proceso", "icon": "⚙️", "url": _safe_reverse("operaciones:control_proceso"),  "url_name": "control_proceso", "modulo": "control"},
        {"name": "Proceso Packing",    "icon": "🏭", "url": _safe_reverse("operaciones:proceso"),         "url_name": "proceso",         "modulo": "proceso"},
        {"name": "Paletizado",         "icon": "🪵", "url": _safe_reverse("operaciones:paletizado"),      "url_name": "paletizado",      "modulo": "paletizado"},
        {"name": "Cámaras Frío",       "icon": "🧊", "url": _safe_reverse("operaciones:camaras"),         "url_name": "camaras",         "modulo": "camaras"},
    ]
    op_items = [
        {k: v for k, v in item.items() if k != "modulo"}
        for item in _all_op_items
        if puede_acceder_modulo(request, item["modulo"])
    ]

    sections = [
        {"label": "Flujo Operativo", "items": op_items},
    ]

    # Sección Gestión — jefatura y administradores (verificado por roles de negocio)
    if is_jefatura(request):
        gestion_items = [
            {"name": "Control de Calidad", "icon": "✅", "url": _safe_reverse("operaciones:control"), "url_name": "control"},
            {"name": "Control de Gestión", "icon": "📊", "url": _safe_reverse("operaciones:consulta"), "url_name": "consulta"},
        ]
        if is_admin(request):
            gestion_items.append(
                {"name": "Usuarios", "icon": "👥", "url": _safe_reverse("usuarios:gestion_usuarios"), "url_name": "gestion_usuarios"},
            )
        sections.append({"label": "Gestión", "items": gestion_items})

    return sections


def _mobile_nav():
    return [
        {"name": "Dashboard",  "icon": "🏠", "url": _safe_reverse("operaciones:dashboard"), "url_name": "dashboard"},
        {"name": "Recepción",  "icon": "📥", "url": _safe_reverse("operaciones:recepcion"), "url_name": "recepcion"},
        {"name": "Packing",    "icon": "🏭", "url": _safe_reverse("operaciones:proceso"),   "url_name": "proceso"},
        {"name": "Consulta",   "icon": "📊", "url": _safe_reverse("operaciones:consulta"),  "url_name": "consulta"},
    ]
