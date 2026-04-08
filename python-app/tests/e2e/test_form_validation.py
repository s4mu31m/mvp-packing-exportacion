"""
Fase 3 — Validaciones de formularios E2E

Cubre: campos requeridos, rangos numéricos, contraseñas que no coinciden.
"""
import pytest
from playwright.sync_api import expect
from tests.e2e.pages.recepcion_page import RecepcionPage

pytestmark = pytest.mark.e2e


# ─── BinForm ─────────────────────────────────────────────────────────────────

def test_bin_form_required_codigo_productor(as_recepcion, live_server):
    """Enviar sin código de productor debe mostrar error de validación HTML5."""
    rec = RecepcionPage(as_recepcion, live_server.url)
    rec.navigate()
    rec.iniciar_lote()
    # Nota: iniciar_lote() muestra su propio .alert-success ("Lote ... iniciado").
    # No podemos verificar ausencia de .alert-success porque ese mensaje ya está.
    # En cambio, verificamos que el formulario sigue visible y que no se agregó
    # ningún bin (la validación HTML5 de `required` impide el envío).

    # No rellenamos codigo_productor — el campo tiene required en el template
    rec.page.get_by_label("Variedad").fill("Clementina")
    rec.page.get_by_label("Color (numero)").fill("3")
    rec.agregar_bin()

    # Formulario de bin sigue visible (HTML5 impidió el envío) y 0 bins en sidebar
    rec.expect_bin_form_visible()
    assert rec.get_bins_count() == 0


def test_bin_form_required_variedad(as_recepcion, live_server):
    rec = RecepcionPage(as_recepcion, live_server.url)
    rec.navigate()
    rec.iniciar_lote()

    rec.page.get_by_label("Codigo productor / agricultor").fill("PROD-001")
    rec.page.get_by_label("Color (numero)").fill("3")
    # Variedad vacía
    rec.agregar_bin()

    rec.expect_bin_form_visible()
    assert rec.get_bins_count() == 0


def test_bin_form_required_color(as_recepcion, live_server):
    rec = RecepcionPage(as_recepcion, live_server.url)
    rec.navigate()
    rec.iniciar_lote()

    rec.page.get_by_label("Codigo productor / agricultor").fill("PROD-001")
    rec.page.get_by_label("Variedad").fill("Clementina")
    # Color vacío
    rec.agregar_bin()

    rec.expect_bin_form_visible()
    assert rec.get_bins_count() == 0


# ─── CerrarLoteForm ───────────────────────────────────────────────────────────

def test_cerrar_lote_button_disabled_without_bins(as_recepcion, live_server):
    """El botón de cerrar lote debe estar deshabilitado con 0 bins."""
    rec = RecepcionPage(as_recepcion, live_server.url)
    rec.navigate()
    rec.iniciar_lote()

    cerrar_btn = rec.page.get_by_role("button", name="Cerrar Lote")
    expect(cerrar_btn).to_be_disabled()


# ─── UsuarioCreacionForm ──────────────────────────────────────────────────────

def test_create_user_password_mismatch(as_admin, live_server):
    """Contraseñas distintas deben mostrar error al crear usuario."""
    as_admin.goto(f"{live_server.url}/usuarios/gestion/")
    as_admin.locator('[name="usernamelogin"]').fill("mismatch_user")
    as_admin.locator('[name="password"]').fill("Password1!")
    as_admin.locator('[name="password_confirm"]').fill("Diferente2!")
    # role-chip oculta el <input> → clic en el <label> que lo envuelve
    as_admin.locator('label:has([name="roles"][value="Recepcion"])').click()
    as_admin.get_by_role("button", name="Crear usuario").click()
    expect(as_admin.locator(".alert-danger")).to_be_visible()


def test_create_user_missing_username(as_admin, live_server):
    """Sin username el formulario no debe enviar."""
    as_admin.goto(f"{live_server.url}/usuarios/gestion/")
    # username vacío
    as_admin.locator('[name="password"]').fill("Password1!")
    as_admin.locator('[name="password_confirm"]').fill("Password1!")
    # role-chip oculta el <input> → clic en el <label> que lo envuelve
    as_admin.locator('label:has([name="roles"][value="Recepcion"])').click()
    as_admin.get_by_role("button", name="Crear usuario").click()
    # El campo requerido HTML5 impide el envío; seguimos en la misma página
    assert "/gestion" in as_admin.url


def test_create_user_no_roles_selected(as_admin, live_server):
    """Sin roles seleccionados debe mostrar error."""
    as_admin.goto(f"{live_server.url}/usuarios/gestion/")
    as_admin.locator('[name="usernamelogin"]').fill("sin_roles")
    as_admin.locator('[name="password"]').fill("Password1!")
    as_admin.locator('[name="password_confirm"]').fill("Password1!")
    # No seleccionamos roles
    as_admin.get_by_role("button", name="Crear usuario").click()
    expect(as_admin.locator(".alert-danger")).to_be_visible()
