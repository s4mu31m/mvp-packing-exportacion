"""
Implementación Dataverse del repositorio de usuarios.

Accede a crf21_usuariooperativos vía DataverseClient (OData v4).
No usa UsuarioProfile (modelo SQLite); opera directamente contra la API.
"""
from __future__ import annotations

from typing import Any, Optional

from usuarios.repositories import UsuarioRecord, UsuarioRepository

ENTITY_SET = "crf21_usuariooperativos"
PK_FIELD   = "crf21_usuariooperativoid"

# Lista de campos para $select (list[str] — requerido por DataverseClient.list_rows)
SELECT_FIELDS: list[str] = [
    "crf21_usuariooperativoid",
    "crf21_usernamelogin",
    "crf21_nombrecompleto",
    "crf21_correo",
    "crf21_passwordhash",
    "crf21_rol",
    "crf21_activo",
    "crf21_bloqueado",
    "crf21_codigooperador",
]

# Mapeo dominio → nombre de campo Dataverse (para update)
FIELD_MAP = {
    "usernamelogin":   "crf21_usernamelogin",
    "nombrecompleto":  "crf21_nombrecompleto",
    "correo":          "crf21_correo",
    "passwordhash":    "crf21_passwordhash",
    "rol":             "crf21_rol",
    "activo":          "crf21_activo",
    "bloqueado":       "crf21_bloqueado",
    # codigooperador excluido intencionalmente (inmutable)
}


def _row_to_record(row: dict) -> UsuarioRecord:
    dv_id = row.get("crf21_usuariooperativoid")
    return UsuarioRecord(
        id=dv_id,
        dataverse_id=dv_id,
        usernamelogin=row.get("crf21_usernamelogin", ""),
        nombrecompleto=row.get("crf21_nombrecompleto", ""),
        correo=row.get("crf21_correo", ""),
        passwordhash=row.get("crf21_passwordhash", ""),
        rol=row.get("crf21_rol", ""),
        activo=bool(row.get("crf21_activo", True)),
        bloqueado=bool(row.get("crf21_bloqueado", False)),
        codigooperador=row.get("crf21_codigooperador", ""),
    )


def _prefix_for_rol(rol_str: str) -> str:
    if "Administrador" in rol_str:
        return "ADM"
    if "Jefatura" in rol_str:
        return "JEF"
    return "OPE"


class DataverseUsuarioRepository(UsuarioRepository):

    def _client(self):
        from infrastructure.dataverse.client import DataverseClient
        return DataverseClient()

    def get_by_username(self, username: str) -> Optional[UsuarioRecord]:
        client = self._client()
        safe = username.replace("'", "''")
        data = client.list_rows(
            ENTITY_SET,
            select=SELECT_FIELDS,
            filter_expr=f"crf21_usernamelogin eq '{safe}'",
            top=1,
        )
        rows = data.get("value", [])
        return _row_to_record(rows[0]) if rows else None

    def get_by_id(self, usuario_id: Any) -> Optional[UsuarioRecord]:
        """
        Obtiene un usuario por PK (UUID).
        Usa list_rows con filtro por PK — DataverseClient no tiene get_row.
        """
        client = self._client()
        try:
            # OData v4: GUIDs se comparan sin comillas
            data = client.list_rows(
                ENTITY_SET,
                select=SELECT_FIELDS,
                filter_expr=f"crf21_usuariooperativoid eq {usuario_id}",
                top=1,
            )
            rows = data.get("value", [])
            return _row_to_record(rows[0]) if rows else None
        except Exception:
            return None

    def list_all(self) -> list[UsuarioRecord]:
        client = self._client()
        data = client.list_rows(ENTITY_SET, select=SELECT_FIELDS)
        return [_row_to_record(r) for r in data.get("value", [])]

    def create(self, *, usernamelogin: str, nombrecompleto: str, correo: str,
               passwordhash: str, rol: str,
               activo: bool = True, bloqueado: bool = False) -> UsuarioRecord:
        client = self._client()
        # Generar código de operador contando registros con mismo prefijo
        prefix = _prefix_for_rol(rol)
        safe_prefix = prefix.replace("'", "''")
        existing = client.list_rows(
            ENTITY_SET,
            select=["crf21_codigooperador"],
            filter_expr=f"startswith(crf21_codigooperador, '{safe_prefix}-')",
        )
        count = len(existing.get("value", []))
        codigooperador = f"{prefix}-{count + 1:03d}"

        payload = {
            "crf21_usernamelogin":  usernamelogin,
            "crf21_nombrecompleto": nombrecompleto,
            "crf21_correo":         correo,
            "crf21_passwordhash":   passwordhash,
            "crf21_rol":            rol,
            "crf21_activo":         activo,
            "crf21_bloqueado":      bloqueado,
            "crf21_codigooperador": codigooperador,
        }
        created_id = client.create_row(ENTITY_SET, payload)
        return UsuarioRecord(
            id=created_id,
            dataverse_id=created_id,
            usernamelogin=usernamelogin,
            nombrecompleto=nombrecompleto,
            correo=correo,
            passwordhash=passwordhash,
            rol=rol,
            activo=activo,
            bloqueado=bloqueado,
            codigooperador=codigooperador,
        )

    def update(self, usuario_id: Any, fields: dict) -> UsuarioRecord:
        client = self._client()
        fields.pop("codigooperador", None)   # inmutable
        payload = {FIELD_MAP[k]: v for k, v in fields.items() if k in FIELD_MAP}
        if payload:
            client.update_row(ENTITY_SET, str(usuario_id), payload)
        return self.get_by_id(usuario_id)

    def toggle_activo(self, usuario_id: Any) -> UsuarioRecord:
        current = self.get_by_id(usuario_id)
        if current is None:
            raise ValueError(f"Usuario {usuario_id} no encontrado en Dataverse")
        client = self._client()
        client.update_row(ENTITY_SET, str(usuario_id), {"crf21_activo": not current.activo})
        return self.get_by_id(usuario_id)
