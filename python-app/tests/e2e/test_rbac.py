"""
Fase 1 — Control de acceso por rol (RBAC) E2E

Verifica que cada rol llega a las páginas que le corresponden
y es redirigido desde las que no le corresponden.
"""
import pytest
from tests.e2e.pages.portal_page import PortalPage

pytestmark = pytest.mark.e2e


# ─── Badge de rol en portal ──────────────────────────────────────────────────

def test_admin_badge_in_portal(as_admin, live_server):
    portal = PortalPage(as_admin, live_server.url)
    portal.navigate()
    portal.expect_badge("Administrador")


def test_jefatura_badge_in_portal(page, make_user, login, live_server):
    make_user("jef_badge", "Jefatura")
    login("jef_badge")
    portal = PortalPage(page, live_server.url)
    portal.navigate()
    portal.expect_badge("Jefatura")


def test_operador_badge_in_portal(as_recepcion, live_server):
    portal = PortalPage(as_recepcion, live_server.url)
    portal.navigate()
    portal.expect_badge("Operador")


# ─── Acceso a rutas por rol ───────────────────────────────────────────────────

@pytest.mark.parametrize("path,rol", [
    ("/operaciones/recepcion/",      "Recepcion"),
    ("/operaciones/desverdizado/",   "Desverdizado"),
    ("/operaciones/ingreso-packing/","Ingreso Packing"),
    ("/operaciones/proceso/",        "Proceso"),
    ("/operaciones/control/",        "Control"),
    ("/operaciones/paletizado/",     "Paletizado"),
    ("/operaciones/camaras/",        "Camaras"),
])
def test_role_can_access_own_module(page, make_user, login, live_server, path, rol):
    username = f"usr_{rol.lower().replace(' ', '_')}"
    make_user(username, rol)
    login(username)
    page.goto(f"{live_server.url}{path}")
    # No debe redirigir a login ni a portal (403 o redirect por rol)
    assert path in page.url or live_server.url + path == page.url


def test_jefatura_can_access_consulta(page, make_user, login, live_server):
    make_user("jef_consulta", "Jefatura")
    login("jef_consulta")
    page.goto(f"{live_server.url}/operaciones/consulta/")
    assert "/consulta" in page.url


def test_recepcion_cannot_access_consulta(page, make_user, login, live_server):
    """Un operador de Recepcion no debe poder acceder a Consulta Jefatura."""
    make_user("rec_no_consulta", "Recepcion")
    login("rec_no_consulta")
    page.goto(f"{live_server.url}/operaciones/consulta/")
    # Debe redirigir a portal u otra página — no quedarse en /consulta/
    assert "/consulta/" not in page.url or "/login" in page.url


# ─── Admin bypass ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", [
    "/operaciones/recepcion/",
    "/operaciones/desverdizado/",
    "/operaciones/ingreso-packing/",
    "/operaciones/proceso/",
    "/operaciones/control/",
    "/operaciones/paletizado/",
    "/operaciones/camaras/",
    "/operaciones/consulta/",
    "/usuarios/gestion/",
])
def test_admin_can_access_all_routes(as_admin, live_server, path):
    page = as_admin
    page.goto(f"{live_server.url}{path}")
    # Admin nunca debe ser redirigido a login
    assert "/login" not in page.url


def test_non_admin_cannot_access_gestion_usuarios(page, make_user, login, live_server):
    """Solo Administrador accede a /usuarios/gestion/."""
    make_user("jef_no_gestion", "Jefatura")
    login("jef_no_gestion")
    page.goto(f"{live_server.url}/usuarios/gestion/")
    assert "/gestion/" not in page.url or "/login" in page.url
