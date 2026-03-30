"""
Factory de repositorios configurable por variable de entorno.

Uso:
    from infrastructure.repository_factory import get_repositories

    repos = get_repositories()
    bin_record = repos.bins.create(temporada="2026", bin_code="B001")

El backend se selecciona mediante PERSISTENCE_BACKEND en el archivo .env:

    PERSISTENCE_BACKEND=sqlite      → Django ORM local (por defecto)
    PERSISTENCE_BACKEND=dataverse   → Microsoft Dataverse Web API

Los repositorios Dataverse se instancian solo cuando se solicita ese backend,
evitando errores de configuración en modo sqlite cuando las variables DATAVERSE_*
no están presentes o son inválidas.
"""
from __future__ import annotations

from django.conf import settings

from domain.repositories.base import Repositories


def get_repositories() -> Repositories:
    """
    Retorna el conjunto de repositorios apropiado según PERSISTENCE_BACKEND.

    Raises:
        ValueError: Si el valor de PERSISTENCE_BACKEND no es reconocido.
    """
    backend = getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip()

    if backend == "sqlite":
        return _get_sqlite_repositories()

    if backend == "dataverse":
        return _get_dataverse_repositories()

    raise ValueError(
        f"PERSISTENCE_BACKEND='{backend}' no es válido. "
        "Valores aceptados: 'sqlite', 'dataverse'."
    )


def _get_sqlite_repositories() -> Repositories:
    from infrastructure.sqlite.repositories import build_sqlite_repositories
    return build_sqlite_repositories()


def _get_dataverse_repositories() -> Repositories:
    from infrastructure.dataverse.repositories import build_dataverse_repositories
    return build_dataverse_repositories()
