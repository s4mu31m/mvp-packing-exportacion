# src/core/context_processors.py

from django.urls import reverse


def cfn_context(request):
    """

    Inyecta en todos los templates:

    - planta_seleccionada

    - exportador_activo

    - nav_sections  (sidebar)

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

        "nav_sections": _nav_sections(),

        "mobile_nav_items": _mobile_nav(),

    }


def _nav_sections():

    return [

        {

            "label": "Flujo Operativo",

            "items": [

                {"name": "Dashboard",      "icon": "📋", "url": reverse(
                    "operaciones:dashboard"),    "url_name": "dashboard"},

                {"name": "Recepción",      "icon": "📥", "url": reverse(
                    "operaciones:recepcion"),    "url_name": "recepcion"},

                {"name": "Pesaje",         "icon": "⚖️",  "url": reverse(
                    "operaciones:pesaje"),       "url_name": "pesaje"},

                {"name": "Desverdizado",   "icon": "🍋", "url": reverse(
                    "operaciones:desverdizado"), "url_name": "desverdizado"},

                {"name": "Proceso Packing", "icon": "⚙️",  "url": reverse(
                    "operaciones:proceso"),      "url_name": "proceso"},

                {"name": "Control Proceso", "icon": "🔍", "url": reverse(
                    "operaciones:control"),      "url_name": "control"},

                {"name": "Paletizado",     "icon": "📦", "url": reverse(
                    "operaciones:paletizado"),   "url_name": "paletizado"},

                {"name": "Cámaras Frío",   "icon": "❄️",  "url": reverse(
                    "operaciones:camaras"),      "url_name": "camaras"},

            ],

        },

        {

            "label": "Gestión",

            "items": [

                {"name": "Consulta Jefatura", "icon": "📊", "url": reverse(
                    "operaciones:consulta"), "url_name": "consulta"},

            ],

        },

    ]


def _mobile_nav():

    return [

        {"name": "Dashboard",  "icon": "📋", "url": reverse(
            "operaciones:dashboard"),  "url_name": "dashboard"},

        {"name": "Recepción",  "icon": "📥", "url": reverse(
            "operaciones:recepcion"),  "url_name": "recepcion"},

        {"name": "Pesaje",     "icon": "⚖️",  "url": reverse(
            "operaciones:pesaje"),     "url_name": "pesaje"},

        {"name": "Packing",    "icon": "⚙️",  "url": reverse(
            "operaciones:proceso"),    "url_name": "proceso"},

        {"name": "Consulta",   "icon": "📊", "url": reverse(
            "operaciones:consulta"),   "url_name": "consulta"},

    ]
