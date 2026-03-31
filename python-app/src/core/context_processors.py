# src/core/context_processors.py

from django.urls import reverse


def CaliPro_context(request):
    """
    Inyecta en todos los templates:
    - planta_seleccionada
    - exportador_activo
    - nav_sections  (sidebar, diferenciado por rol)
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
        "nav_sections": _nav_sections(request.user),
        "mobile_nav_items": _mobile_nav(),
    }


def _safe_reverse(url_name):
    try:
        return reverse(url_name)
    except Exception:
        return "#"


def _nav_sections(user):
    sections = [
        {
            "label": "Flujo Operativo",
            "items": [
                {"name": "Dashboard",       "icon": "T", "url": _safe_reverse("operaciones:dashboard"),       "url_name": "dashboard"},
                {"name": "Recepcion",       "icon": "R", "url": _safe_reverse("operaciones:recepcion"),       "url_name": "recepcion"},
                {"name": "Conformar Lote",  "icon": "L", "url": _safe_reverse("operaciones:pesaje"),          "url_name": "pesaje"},
                {"name": "Desverdizado",    "icon": "D", "url": _safe_reverse("operaciones:desverdizado"),    "url_name": "desverdizado"},
                {"name": "Ingreso Packing", "icon": "I", "url": _safe_reverse("operaciones:ingreso_packing"), "url_name": "ingreso_packing"},
                {"name": "Proceso Packing", "icon": "P", "url": _safe_reverse("operaciones:proceso"),         "url_name": "proceso"},
                {"name": "Control Proceso", "icon": "C", "url": _safe_reverse("operaciones:control"),         "url_name": "control"},
                {"name": "Paletizado",      "icon": "X", "url": _safe_reverse("operaciones:paletizado"),      "url_name": "paletizado"},
                {"name": "Camaras Frio",    "icon": "F", "url": _safe_reverse("operaciones:camaras"),         "url_name": "camaras"},
            ],
        },
    ]

    # Sección Gestión — jefatura y administradores
    if user.is_staff or user.is_superuser:
        gestion_items = [
            {"name": "Consulta Jefatura", "icon": "J", "url": _safe_reverse("operaciones:consulta"), "url_name": "consulta"},
        ]
        # Gestión de usuarios — solo administradores
        if user.is_superuser:
            gestion_items.append(
                {"name": "Usuarios", "icon": "U", "url": _safe_reverse("usuarios:gestion_usuarios"), "url_name": "gestion_usuarios"},
            )
        sections.append({"label": "Gestion", "items": gestion_items})

    return sections


def _mobile_nav():
    return [
        {"name": "Dashboard", "icon": "T", "url": _safe_reverse("operaciones:dashboard"), "url_name": "dashboard"},
        {"name": "Recepcion", "icon": "R", "url": _safe_reverse("operaciones:recepcion"), "url_name": "recepcion"},
        {"name": "Lote",      "icon": "L", "url": _safe_reverse("operaciones:pesaje"),    "url_name": "pesaje"},
        {"name": "Packing",   "icon": "P", "url": _safe_reverse("operaciones:proceso"),   "url_name": "proceso"},
        {"name": "Consulta",  "icon": "J", "url": _safe_reverse("operaciones:consulta"),  "url_name": "consulta"},
    ]
