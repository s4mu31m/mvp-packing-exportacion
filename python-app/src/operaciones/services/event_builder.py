"""
Utilidades puras para construcción de event keys.

La creación del RegistroEtapa en base de datos (antes aquí como create_registro_etapa)
fue movida a los repositorios de infraestructura para mantener la separación de
responsabilidades entre lógica de dominio y persistencia.
"""


def build_event_key(*parts: str) -> str:
    """
    Construye una clave idempotente concatenando partes normalizadas con guión.

    Ejemplo:
        build_event_key("2026", "BIN", "B-001", "BIN_REGISTRADO")
        → "2026-BIN-B-001-BIN_REGISTRADO"
    """
    clean_parts = [str(p).strip().upper() for p in parts if str(p).strip()]
    return "-".join(clean_parts)
