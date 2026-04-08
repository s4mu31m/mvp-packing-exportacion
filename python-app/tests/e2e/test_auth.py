"""
Fase 1 — Autenticación E2E

Cubre: login OK, credenciales incorrectas, usuario inactivo, usuario bloqueado,
logout, y redirección cuando no hay sesión activa.
"""
import pytest
from tests.e2e.pages.login_page import LoginPage

pytestmark = pytest.mark.e2e


# ─── Login exitoso ──────────────────────────────────────────────────────────

def test_login_success_redirects_to_portal(page, make_user, live_server):
    make_user("operador_ok", "Recepcion")
    lp = LoginPage(page, live_server.url)
    lp.navigate()
    lp.login("operador_ok", "CaliPro2026!")
    lp.expect_at_portal()


def test_login_page_has_csrf_token(page, live_server):
    """El formulario debe incluir el token CSRF."""
    page.goto(f"{live_server.url}/usuarios/login/")
    assert page.locator('[name="csrfmiddlewaretoken"]').count() == 1


# ─── Credenciales inválidas ──────────────────────────────────────────────────

def test_login_wrong_password_shows_error(page, make_user, live_server):
    make_user("operador_pw", "Recepcion")
    lp = LoginPage(page, live_server.url)
    lp.navigate()
    lp.login("operador_pw", "wrong_password")
    lp.expect_error_visible()
    lp.expect_still_at_login()


def test_login_wrong_username_shows_error(page, live_server):
    lp = LoginPage(page, live_server.url)
    lp.navigate()
    lp.login("usuario_que_no_existe", "CaliPro2026!")
    lp.expect_error_visible()


# ─── Usuarios inactivo / bloqueado ──────────────────────────────────────────

def test_login_inactive_user_rejected(page, make_user, live_server):
    make_user("inactivo_e2e", "Recepcion", activo=False)
    lp = LoginPage(page, live_server.url)
    lp.navigate()
    lp.login("inactivo_e2e", "CaliPro2026!")
    lp.expect_error_visible()
    lp.expect_still_at_login()


def test_login_blocked_user_rejected(page, make_user, live_server):
    make_user("bloqueado_e2e", "Recepcion", bloqueado=True)
    lp = LoginPage(page, live_server.url)
    lp.navigate()
    lp.login("bloqueado_e2e", "CaliPro2026!")
    lp.expect_error_visible()
    lp.expect_still_at_login()


# ─── Logout ─────────────────────────────────────────────────────────────────

def test_logout_redirects_to_login(as_recepcion, live_server):
    """Después del logout, el usuario debe aterrizar en login."""
    page = as_recepcion
    page.goto(f"{live_server.url}/usuarios/portal/")
    page.get_by_role("button", name="Cerrar sesión").click()
    # Debe redirigir a login (puede ser /usuarios/login/ o /)
    assert "/login" in page.url or page.url == f"{live_server.url}/"


# ─── Redirecciones sin sesión ────────────────────────────────────────────────

@pytest.mark.parametrize("path", [
    "/operaciones/",
    "/operaciones/recepcion/",
    "/operaciones/desverdizado/",
    "/operaciones/ingreso-packing/",
    "/operaciones/proceso/",
    "/operaciones/control/",
    "/operaciones/paletizado/",
    "/operaciones/camaras/",
])
def test_unauthenticated_access_redirects_to_login(page, live_server, path):
    """Todas las rutas operativas deben redirigir a login si no hay sesión."""
    page.goto(f"{live_server.url}{path}")
    assert "/login" in page.url
