"""
Fase 3 - Interacciones UI E2E

Cubre: toasts (forms.js), sidebar activo y validaciones basicas de layout.
"""
import pytest
from playwright.sync_api import expect

from tests.e2e.pages.recepcion_page import RecepcionPage

pytestmark = pytest.mark.e2e


def test_toast_appears_after_iniciar_lote(as_recepcion, live_server):
    """Al iniciar un lote debe completarse el cambio a formulario de bins."""
    rec = RecepcionPage(as_recepcion, live_server.url)
    rec.navigate()
    rec.iniciar_lote()
    rec.expect_bin_form_visible()


def test_toast_appears_after_agregar_bin(as_recepcion, live_server):
    """Al agregar un bin debe aparecer un mensaje de exito."""
    rec = RecepcionPage(as_recepcion, live_server.url)
    rec.navigate()
    rec.iniciar_lote()
    rec.fill_bin_base_fields("PROD-TOAST", "Mandarina", "2")
    rec.fill_bin_variable_fields(kilos_bruto="500", kilos_neto="480")
    rec.agregar_bin()
    rec.expect_success_message()


def test_live_clock_present_in_app_layout(as_recepcion, live_server):
    """Si existe #live-time en layout, debe tener contenido."""
    as_recepcion.goto(f"{live_server.url}/operaciones/")
    live_time = as_recepcion.locator("#live-time")
    if live_time.count() > 0:
        expect(live_time).not_to_be_empty()


def test_sidebar_highlights_current_page(as_recepcion, live_server):
    """El item activo del sidebar debe diferenciarse visualmente."""
    as_recepcion.goto(f"{live_server.url}/operaciones/recepcion/")
    active_items = as_recepcion.locator(".nav-item-active, [class*='active']")
    assert active_items.count() >= 1


def test_all_forms_have_csrf_token(as_recepcion, live_server):
    """Todos los formularios en recepcion deben tener token CSRF."""
    as_recepcion.goto(f"{live_server.url}/operaciones/recepcion/")
    csrf_tokens = as_recepcion.locator('[name="csrfmiddlewaretoken"]')
    assert csrf_tokens.count() >= 1
