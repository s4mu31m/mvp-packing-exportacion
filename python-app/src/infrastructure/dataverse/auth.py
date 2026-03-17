from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import requests
from django.conf import settings


class DataverseAuthError(RuntimeError):
    """Error de autenticación contra Microsoft Entra / Dataverse."""


@dataclass
class DataverseTokenProvider:
    tenant_id: str = settings.DATAVERSE_TENANT_ID
    client_id: str = settings.DATAVERSE_CLIENT_ID
    client_secret: str = settings.DATAVERSE_CLIENT_SECRET
    resource_url: str = settings.DATAVERSE_URL
    timeout: int = settings.DATAVERSE_TIMEOUT

    _access_token: Optional[str] = field(default=None, init=False)
    _expires_at: float = field(default=0, init=False)

    @property
    def token_url(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"

    @property
    def scope(self) -> str:
        return f"{self.resource_url}/.default"

    def _validate_config(self) -> None:
        missing = [
            name
            for name, value in {
                "DATAVERSE_URL": self.resource_url,
                "DATAVERSE_TENANT_ID": self.tenant_id,
                "DATAVERSE_CLIENT_ID": self.client_id,
                "DATAVERSE_CLIENT_SECRET": self.client_secret,
            }.items()
            if not value
        ]
        if missing:
            raise DataverseAuthError(
                f"Faltan variables de configuración Dataverse: {', '.join(missing)}"
            )

    def get_access_token(self, force_refresh: bool = False) -> str:
        self._validate_config()

        now = time.time()
        if (
            not force_refresh
            and self._access_token
            and now < (self._expires_at - 60)
        ):
            return self._access_token

        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": self.scope,
        }

        response = requests.post(
            self.token_url,
            data=payload,
            timeout=(6.1, self.timeout),
        )

        if not response.ok:
            raise DataverseAuthError(
                f"No se pudo obtener token ({response.status_code}): {response.text}"
            )

        data = response.json()
        access_token = data.get("access_token")
        expires_in = int(data.get("expires_in", 3599))

        if not access_token:
            raise DataverseAuthError("La respuesta de autenticación no incluyó access_token.")

        self._access_token = access_token
        self._expires_at = now + expires_in
        return access_token