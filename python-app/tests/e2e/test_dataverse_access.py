from __future__ import annotations

from uuid import uuid4

import pytest
from playwright.sync_api import expect

from tests.e2e.pages.control_page import ControlPage


pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]


@pytest.fixture(autouse=True)
def _require_dataverse(test_backend):
    if test_backend != "dataverse":
        pytest.skip("Esta suite solo valida E2E contra Dataverse real.")


@pytest.fixture()
def login_as_role(page, make_user, login):
    def _login(role: str) -> str:
        slug = role.lower().replace(" ", "_")
        username = f"e2e_{slug}_{uuid4().hex[:8]}"
        make_user(username, role, nombrecompleto=f"E2E {role}")
        login(username)
        return username

    return _login


def _goto(page, live_server, path: str):
    response = page.goto(f"{live_server.url}{path}")
    assert response is not None, f"No hubo respuesta HTTP al navegar a {path}"
    return response


@pytest.mark.parametrize(
    ("role", "path", "title_fragment"),
    [
        ("Desverdizado", "/operaciones/desverdizado/", "Desverdizado"),
        ("Ingreso Packing", "/operaciones/ingreso-packing/", "Ingreso a Packing"),
        ("Proceso", "/operaciones/proceso/", "Proceso Packing"),
        ("Control", "/operaciones/control/", "Control de Calidad"),
        ("Paletizado", "/operaciones/paletizado/", "Paletizado"),
        ("Camaras", "/operaciones/camaras/", "Camaras"),
    ],
)
def test_dataverse_role_can_access_its_priority_module(
    page,
    live_server,
    login_as_role,
    role: str,
    path: str,
    title_fragment: str,
):
    login_as_role(role)

    response = _goto(page, live_server, path)

    assert response.status == 200, f"{role} no pudo abrir {path}: HTTP {response.status}"
    expect(page.locator(".page-title")).to_contain_text(title_fragment)


@pytest.mark.parametrize(
    ("role", "path"),
    [
        ("Recepcion", "/operaciones/desverdizado/"),
        ("Desverdizado", "/operaciones/ingreso-packing/"),
        ("Ingreso Packing", "/operaciones/proceso/"),
        ("Proceso", "/operaciones/control/"),
        ("Control", "/operaciones/paletizado/"),
        ("Paletizado", "/operaciones/camaras/"),
    ],
)
def test_dataverse_wrong_role_gets_403_on_priority_operational_module(
    page,
    live_server,
    login_as_role,
    role: str,
    path: str,
):
    login_as_role(role)

    response = _goto(page, live_server, path)

    assert response.status == 403, f"{role} debio ser rechazado en {path}, pero recibio HTTP {response.status}"


def test_dataverse_non_jefatura_is_redirected_from_consulta(
    page,
    live_server,
    login_as_role,
):
    login_as_role("Proceso")

    _goto(page, live_server, "/operaciones/consulta/")

    page.wait_for_url(f"{live_server.url}/usuarios/portal/")
    assert page.url == f"{live_server.url}/usuarios/portal/"


def test_dataverse_jefatura_can_access_consulta(page, live_server, login_as_role):
    login_as_role("Jefatura")

    response = _goto(page, live_server, "/operaciones/consulta/")

    assert response.status == 200, f"Jefatura no pudo abrir consulta: HTTP {response.status}"
    expect(page.locator(".page-title")).to_contain_text("Consulta Jefatura")


def test_dataverse_control_index_exposes_navigation_to_visible_planillas(
    page,
    live_server,
    login_as_role,
):
    login_as_role("Control")
    control = ControlPage(page, live_server.url)

    control.navigate()
    control.expect_all_planillas_visible()

    control.go_to_proceso()
    page.wait_for_url(f"{live_server.url}/operaciones/control/proceso/")
    expect(page.locator(".page-title")).to_contain_text("Proceso")

    control.navigate()
    control.go_to_camaras()
    page.wait_for_url(f"{live_server.url}/operaciones/control/camaras/")
    expect(page.locator(".page-title")).to_contain_text("Control")
