"""
Fase 2 — Gestión de usuarios E2E

Cubre: crear usuario, roles asignados, toggle activo/inactivo,
validaciones de contraseña, bloqueo a no-administradores.
"""
import pytest
from playwright.sync_api import expect
from tests.e2e.pages.gestion_usuarios_page import GestionUsuariosPage

pytestmark = pytest.mark.e2e


@pytest.fixture()
def gestion(as_admin, live_server):
    g = GestionUsuariosPage(as_admin, live_server.url)
    g.navigate()
    return g


# ─── Acceso ──────────────────────────────────────────────────────────────────

def test_gestion_page_loads_for_admin(gestion):
    """La página de gestión debe cargarse para un Administrador."""
    expect(gestion.page.get_by_text("Gestión de Usuarios")).to_be_visible()


def test_gestion_blocked_for_jefatura(page, make_user, login, live_server):
    make_user("jef_blocked", "Jefatura")
    login("jef_blocked")
    page.goto(f"{live_server.url}/usuarios/gestion/")
    assert "/gestion/" not in page.url or "/login" in page.url


# ─── Crear usuario ────────────────────────────────────────────────────────────

def test_create_user_with_single_role(gestion, live_server):
    gestion.fill_new_user_form(
        username="nuevo_rec",
        password="Segura2026!",
        roles=["Recepcion"],
        nombre="Nuevo Recepcionista",
    )
    gestion.submit_create_user()
    gestion.expect_success_message()
    gestion.expect_user_in_table("nuevo_rec")


def test_create_user_with_multiple_roles(gestion):
    gestion.fill_new_user_form(
        username="multi_rol",
        password="Segura2026!",
        roles=["Recepcion", "Control"],
        nombre="Operador Multirol",
    )
    gestion.submit_create_user()
    gestion.expect_success_message()
    gestion.expect_user_in_table("multi_rol")


def test_create_admin_user(gestion):
    gestion.fill_new_user_form(
        username="nuevo_admin",
        password="Admin2026!!",
        roles=["Administrador"],
    )
    gestion.submit_create_user()
    gestion.expect_success_message()
    gestion.expect_user_in_table("nuevo_admin")


def test_created_user_can_login(page, make_user, login, as_admin, live_server):
    """Un usuario creado desde la UI puede iniciar sesión."""
    # Crear usuario desde la UI de gestión
    from tests.e2e.pages.gestion_usuarios_page import GestionUsuariosPage
    g = GestionUsuariosPage(as_admin, live_server.url)
    g.navigate()
    g.fill_new_user_form(
        username="user_login_test",
        password="Login2026!",
        roles=["Recepcion"],
    )
    g.submit_create_user()
    g.expect_success_message()

    # Abrir una sesión totalmente nueva (contexto propio, sin cookies del admin)
    # para verificar que el usuario recién creado puede autenticarse.
    # Si usamos as_admin.context.new_page(), la nueva pestaña hereda las cookies
    # del admin y Django redirige /login/ → /portal/ antes de mostrar el form.
    fresh_context = as_admin.context.browser.new_context()
    try:
        new_page = fresh_context.new_page()
        new_page.goto(f"{live_server.url}/usuarios/login/")
        new_page.get_by_label("Usuario").fill("user_login_test")
        new_page.get_by_label("Contraseña").fill("Login2026!")
        new_page.get_by_role("button", name="Acceder").click()
        assert "/portal" in new_page.url
    finally:
        fresh_context.close()


# ─── Validaciones ─────────────────────────────────────────────────────────────

def test_create_user_password_mismatch_shows_error(gestion):
    gestion.page.locator('[name="usernamelogin"]').fill("bad_pwd_user")
    gestion.page.locator('[name="password"]').fill("Password1!")
    gestion.page.locator('[name="password_confirm"]').fill("OtraPassword!")
    # role-chip oculta el <input> → clic en el <label> que lo envuelve
    gestion.page.locator('label:has([name="roles"][value="Recepcion"])').click()
    gestion.submit_create_user()
    gestion.expect_error_message()


def test_create_duplicate_username_shows_error(gestion, make_user):
    make_user("duplicado", "Recepcion")
    gestion.fill_new_user_form(
        username="duplicado",
        password="Pass2026!",
        roles=["Recepcion"],
    )
    gestion.submit_create_user()
    gestion.expect_error_message()


# ─── Toggle activo ────────────────────────────────────────────────────────────

def test_toggle_user_inactive(gestion, make_user):
    make_user("toggle_user", "Recepcion")
    gestion.navigate()  # refrescar para ver el usuario recién creado
    gestion.toggle_user("toggle_user")
    # Después del toggle la fila debe mostrar "No" en la columna Activo
    row = gestion.page.locator("td:has-text('toggle_user')").locator("..")
    expect(row.get_by_text("No").first).to_be_visible()


def test_cannot_toggle_self(gestion):
    """El administrador no debe poder desactivarse a sí mismo."""
    # La fila del usuario propio muestra "—" en vez del botón toggle
    row = gestion.page.locator("td:has-text('admin_e2e')").locator("..")
    expect(row.get_by_role("button")).not_to_be_visible()
