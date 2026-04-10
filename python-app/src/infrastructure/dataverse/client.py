from __future__ import annotations

from typing import Any, Optional

import requests
from django.conf import settings

from .auth import DataverseTokenProvider


class DataverseAPIError(RuntimeError):
    """Error de llamada HTTP o semántico contra Dataverse Web API."""


class DataverseClient:
    def __init__(
        self,
        token_provider: Optional[DataverseTokenProvider] = None,
        base_url: Optional[str] = None,
        api_version: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> None:
        self.token_provider = token_provider or DataverseTokenProvider()
        self.base_url = (base_url or settings.DATAVERSE_URL).rstrip("/")
        self.api_version = api_version or settings.DATAVERSE_API_VERSION
        self.timeout = timeout or settings.DATAVERSE_TIMEOUT

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json; charset=utf-8",
                "OData-MaxVersion": "4.0",
                "OData-Version": "4.0",
            }
        )

    @property
    def api_root(self) -> str:
        return f"{self.base_url}/api/data/{self.api_version}"

    def _build_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self.api_root}/{path.lstrip('/')}"

    def _authorized_headers(self, extra_headers: Optional[dict[str, str]] = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.token_provider.get_access_token()}",
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> Any:
        url = self._build_url(path)

        def send(auth_headers: dict[str, str]) -> requests.Response:
            return self.session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                headers=auth_headers,
                timeout=(6.1, self.timeout),
            )

        auth_headers = self._authorized_headers(headers)
        response = send(auth_headers)

        if response.status_code == 401:
            refreshed_headers = {
                "Authorization": f"Bearer {self.token_provider.get_access_token(force_refresh=True)}"
            }
            if headers:
                refreshed_headers.update(headers)
            response = send(refreshed_headers)

        if not response.ok:
            try:
                error_detail = response.json()
            except ValueError:
                error_detail = response.text

            raise DataverseAPIError(
                f"Dataverse devolvió {response.status_code} en {method} {url}: {error_detail}"
            )

        if response.status_code == 204 or not response.text:
            return None

        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return response.json()

        return response.text

    def whoami(self) -> dict[str, Any]:
        return self._request("GET", "WhoAmI()")

    def get_entity_definition(self, logical_name: str) -> dict[str, Any]:
        path = f"EntityDefinitions(LogicalName='{logical_name}')"
        params = {"$select": "LogicalName,EntitySetName,DisplayName"}
        return self._request("GET", path, params=params)

    def list_rows(
        self,
        entity_set_name: str,
        *,
        select: Optional[list[str]] = None,
        filter_expr: Optional[str] = None,
        top: int = 50,
        orderby: Optional[str] = None,
        expand: Optional[str] = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}

        if select:
            params["$select"] = ",".join(select)
        if filter_expr:
            params["$filter"] = filter_expr
        if top:
            params["$top"] = top
        if orderby:
            params["$orderby"] = orderby
        if expand:
            params["$expand"] = expand

        return self._request("GET", entity_set_name, params=params)

    def create_row(self, entity_set_name: str, payload: dict[str, Any]) -> Any:
        return self._request(
            "POST",
            entity_set_name,
            json=payload,
            headers={"Prefer": "return=representation"},
        )

    def update_row(
        self,
        entity_set_name: str,
        row_id: str,
        payload: dict[str, Any],
        *,
        return_representation: bool = False,
    ) -> Optional[dict[str, Any]]:
        extra = {"Prefer": "return=representation"} if return_representation else None
        return self._request(
            "PATCH",
            f"{entity_set_name}({row_id})",
            json=payload,
            headers=extra,
        )

    def delete_row(self, entity_set_name: str, row_id: str) -> None:
        self._request("DELETE", f"{entity_set_name}({row_id})")