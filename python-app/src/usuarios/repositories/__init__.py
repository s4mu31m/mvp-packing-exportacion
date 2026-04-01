"""
Interfaz de repositorio de usuarios operativos.

Contrato equivalente a crf21_usuariooperativos en Dataverse.
Las implementaciones concretas (SQLite / Dataverse) deben cumplir este contrato.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class UsuarioRecord:
    """
    Representa un usuario operativo según el esquema de Dataverse.

    Campos mapeados a crf21_usuariooperativos:
        id              → PK local (int en SQLite, UUID str en Dataverse)
        dataverse_id    → crf21_usuariooperativoid
        usernamelogin   → crf21_usernamelogin
        nombrecompleto  → crf21_nombrecompleto
        correo          → crf21_correo
        passwordhash    → crf21_passwordhash
        rol             → crf21_rol (texto separado por coma)
        activo          → crf21_activo
        bloqueado       → crf21_bloqueado
        codigooperador  → crf21_codigooperador (inmutable, generado en backend)
    """
    id: Any
    dataverse_id: Optional[str]
    usernamelogin: str
    nombrecompleto: str
    correo: str
    passwordhash: str
    rol: str           # ej. "Recepcion, Pesaje" o "Administrador"
    activo: bool
    bloqueado: bool
    codigooperador: str


class UsuarioRepository(ABC):
    """Contrato de acceso a usuarios operativos (implementado por SQLite y Dataverse)."""

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[UsuarioRecord]:
        """Busca un usuario por crf21_usernamelogin. None si no existe."""

    @abstractmethod
    def get_by_id(self, usuario_id: Any) -> Optional[UsuarioRecord]:
        """Busca un usuario por PK. None si no existe."""

    @abstractmethod
    def list_all(self) -> list[UsuarioRecord]:
        """Lista todos los usuarios."""

    @abstractmethod
    def create(self, *, usernamelogin: str, nombrecompleto: str, correo: str,
               passwordhash: str, rol: str,
               activo: bool = True, bloqueado: bool = False) -> UsuarioRecord:
        """
        Crea un nuevo usuario.
        codigooperador se genera internamente: no es un parámetro.
        """

    @abstractmethod
    def update(self, usuario_id: Any, fields: dict) -> UsuarioRecord:
        """
        Actualiza campos de un usuario existente.
        codigooperador es ignorado si se incluye en fields.
        """

    @abstractmethod
    def toggle_activo(self, usuario_id: Any) -> UsuarioRecord:
        """Alterna crf21_activo del usuario."""


def get_usuario_repository() -> UsuarioRepository:
    """
    Factory: retorna el repositorio correcto según PERSISTENCE_BACKEND.

        sqlite    → SQLiteUsuarioRepository  (UsuarioProfile Django ORM)
        dataverse → DataverseUsuarioRepository (crf21_usuariooperativos OData v4)
    """
    from django.conf import settings
    backend = getattr(settings, "PERSISTENCE_BACKEND", "sqlite").lower().strip()
    if backend == "dataverse":
        from usuarios.repositories.dataverse_repo import DataverseUsuarioRepository
        return DataverseUsuarioRepository()
    from usuarios.repositories.sqlite_repo import SQLiteUsuarioRepository
    return SQLiteUsuarioRepository()
