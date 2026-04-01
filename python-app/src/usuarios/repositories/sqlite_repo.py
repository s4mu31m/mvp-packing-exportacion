"""
Implementación SQLite del repositorio de usuarios.

Usa UsuarioProfile (Django ORM) para simular el contrato de crf21_usuariooperativos.
La convención de codigooperador es:
    ADM-NNN → usuarios con rol Administrador
    JEF-NNN → usuarios con rol Jefatura (sin Administrador)
    OPE-NNN → todos los demás
donde NNN es un contador secuencial por prefijo, zero-padded a 3 dígitos.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from usuarios.repositories import UsuarioRecord, UsuarioRepository


def _prefix_for_rol(rol_str: str) -> str:
    """Determina prefijo de codigooperador según rol primario."""
    if "Administrador" in rol_str:
        return "ADM"
    if "Jefatura" in rol_str:
        return "JEF"
    return "OPE"


def _generar_codigo_operador(rol_str: str) -> str:
    """Genera código único inmutable tipo ADM-001."""
    from usuarios.models import UsuarioProfile
    prefix = _prefix_for_rol(rol_str)
    count = UsuarioProfile.objects.filter(codigooperador__startswith=prefix + "-").count()
    return f"{prefix}-{count + 1:03d}"


def _profile_to_record(profile) -> UsuarioRecord:
    return UsuarioRecord(
        id=profile.pk,
        dataverse_id=profile.dataverse_id,
        usernamelogin=profile.usernamelogin,
        nombrecompleto=profile.nombrecompleto,
        correo=profile.correo,
        passwordhash=profile.passwordhash,
        rol=profile.rol,
        activo=profile.activo,
        bloqueado=profile.bloqueado,
        codigooperador=profile.codigooperador,
    )


class SQLiteUsuarioRepository(UsuarioRepository):

    def get_by_username(self, username: str) -> Optional[UsuarioRecord]:
        from usuarios.models import UsuarioProfile
        try:
            return _profile_to_record(UsuarioProfile.objects.get(usernamelogin=username))
        except UsuarioProfile.DoesNotExist:
            return None

    def get_by_id(self, usuario_id: Any) -> Optional[UsuarioRecord]:
        from usuarios.models import UsuarioProfile
        try:
            return _profile_to_record(UsuarioProfile.objects.get(pk=usuario_id))
        except UsuarioProfile.DoesNotExist:
            return None

    def list_all(self) -> list[UsuarioRecord]:
        from usuarios.models import UsuarioProfile
        return [_profile_to_record(p) for p in UsuarioProfile.objects.all().order_by("usernamelogin")]

    def create(self, *, usernamelogin: str, nombrecompleto: str, correo: str,
               passwordhash: str, rol: str,
               activo: bool = True, bloqueado: bool = False) -> UsuarioRecord:
        from usuarios.models import UsuarioProfile
        codigooperador = _generar_codigo_operador(rol)
        profile = UsuarioProfile.objects.create(
            dataverse_id=str(uuid.uuid4()),
            usernamelogin=usernamelogin,
            nombrecompleto=nombrecompleto,
            correo=correo,
            passwordhash=passwordhash,
            rol=rol,
            activo=activo,
            bloqueado=bloqueado,
            codigooperador=codigooperador,
        )
        return _profile_to_record(profile)

    def update(self, usuario_id: Any, fields: dict) -> UsuarioRecord:
        from usuarios.models import UsuarioProfile
        profile = UsuarioProfile.objects.get(pk=usuario_id)
        fields.pop("codigooperador", None)   # inmutable
        for key, value in fields.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        profile.save()
        return _profile_to_record(profile)

    def toggle_activo(self, usuario_id: Any) -> UsuarioRecord:
        from usuarios.models import UsuarioProfile
        profile = UsuarioProfile.objects.get(pk=usuario_id)
        profile.activo = not profile.activo
        profile.save(update_fields=["activo"])
        return _profile_to_record(profile)
