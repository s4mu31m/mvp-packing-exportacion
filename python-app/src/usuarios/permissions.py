"""
Módulo central de permisos basados en roles de negocio (crf21_rol).

Fuente de verdad: crf21_rol almacenado en sesión Django post-login.
Toda verificación de acceso debe pasar por estas funciones.
No duplicar lógica en views, templates ni context processors.
"""
from __future__ import annotations

# Roles válidos del sistema
ROLES_VALIDOS = [
    "Recepcion",
    "Pesaje",
    "Desverdizado",
    "Ingreso Packing",
    "Proceso",
    "Control",
    "Paletizado",
    "Camaras",
    "Jefatura",
    "Administrador",
]

# Claves de sesión para datos del perfil operativo
SESSION_KEY_ROL              = "crf21_rol"
SESSION_KEY_CODIGO_OPERADOR  = "crf21_codigooperador"
SESSION_KEY_USUARIO_ID       = "crf21_usuariooperativoid"
SESSION_KEY_ACTIVO           = "crf21_activo"
SESSION_KEY_BLOQUEADO        = "crf21_bloqueado"

# Mapeo módulo → roles requeridos (vacío = cualquier usuario autenticado)
MODULO_ROL_MAP: dict[str, list[str]] = {
    "dashboard":        [],               # cualquier usuario autenticado
    "recepcion":        ["Recepcion"],
    "pesaje":           ["Pesaje"],
    "desverdizado":     ["Desverdizado"],
    "ingreso_packing":  ["Ingreso Packing"],
    "proceso":          ["Proceso"],
    "control":          ["Control"],
    "paletizado":       ["Paletizado"],
    "camaras":          ["Camaras"],
    "consulta":         ["Jefatura"],
    "gestion_usuarios": ["Administrador"],
}


# ---------------------------------------------------------------------------
# Parseo y normalización de roles
# ---------------------------------------------------------------------------

def parsear_roles(rol_str: str) -> list[str]:
    """Convierte 'Recepcion, Pesaje' → ['Recepcion', 'Pesaje']."""
    if not rol_str:
        return []
    return [r.strip() for r in rol_str.split(",") if r.strip()]


def normalizar_roles(roles: list[str]) -> str:
    """Convierte ['Recepcion', 'Pesaje'] → 'Recepcion, Pesaje'."""
    return ", ".join(r.strip() for r in roles if r.strip())


# ---------------------------------------------------------------------------
# Consulta de roles desde sesión
# ---------------------------------------------------------------------------

def get_roles(request) -> list[str]:
    """
    Retorna los roles del usuario autenticado desde la sesión.

    Si no hay roles en sesión (ej: usuario Django nativo sin UsuarioProfile),
    usa is_superuser/is_staff como fallback de compatibilidad.
    """
    if not request.user.is_authenticated:
        return []
    rol_str = request.session.get(SESSION_KEY_ROL, "")
    if rol_str:
        return parsear_roles(rol_str)
    # Fallback de compatibilidad para usuarios Django nativos
    user = request.user
    if user.is_superuser:
        return ["Administrador"]
    if user.is_staff:
        return ["Jefatura"]
    return []


# ---------------------------------------------------------------------------
# Verificaciones de acceso
# ---------------------------------------------------------------------------

def is_admin(request) -> bool:
    """True si el usuario tiene rol Administrador."""
    return "Administrador" in get_roles(request)


def is_jefatura(request) -> bool:
    """True si el usuario tiene rol Jefatura o Administrador."""
    roles = get_roles(request)
    return "Administrador" in roles or "Jefatura" in roles


def has_role(request, *roles: str) -> bool:
    """True si el usuario tiene al menos uno de los roles dados, o es Administrador."""
    user_roles = get_roles(request)
    if "Administrador" in user_roles:
        return True
    return any(r in user_roles for r in roles)


def puede_acceder_modulo(request, modulo: str) -> bool:
    """
    Determina si el usuario puede acceder a un módulo operativo.
    Siempre True para Administrador.
    """
    if not request.user.is_authenticated:
        return False
    user_roles = get_roles(request)
    if "Administrador" in user_roles:
        return True
    requeridos = MODULO_ROL_MAP.get(modulo)
    if requeridos is None:
        return True   # módulo desconocido: permisivo
    if not requeridos:
        return True   # sin restricción de rol
    return any(r in user_roles for r in requeridos)
