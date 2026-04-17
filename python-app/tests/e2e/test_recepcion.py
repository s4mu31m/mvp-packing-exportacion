"""
Fase 1 - Recepcion de bins E2E

Cubre: iniciar lote, agregar bins, campos base bloqueados tras primer bin
y cierre de lote.
"""
import pytest
from playwright.sync_api import expect

from tests.e2e.pages.recepcion_page import RecepcionPage

pytestmark = pytest.mark.e2e


@pytest.fixture()
def recepcion(as_recepcion, live_server):
    """RecepcionPage ya autenticado como operador de recepcion."""
    page = RecepcionPage(as_recepcion, live_server.url)
    page.navigate()
    return page


def test_recepcion_page_loads_with_iniciar_form(recepcion):
    """Sin lote activo debe mostrar el formulario de inicio."""
    recepcion.expect_iniciar_form_visible()


def test_iniciar_lote_creates_active_state(recepcion):
    """Al iniciar un lote aparece el formulario de bins."""
    recepcion.iniciar_lote()
    recepcion.expect_bin_form_visible()


def test_iniciar_lote_shows_badge_with_lote_code(recepcion):
    """Al iniciar un lote el header muestra el codigo del lote activo."""
    recepcion.iniciar_lote()
    recepcion.expect_lote_activo_badge()


def test_add_first_bin_shows_success_message(recepcion):
    recepcion.iniciar_lote()
    recepcion.fill_bin_base_fields(
        codigo_productor="PROD-001",
        variedad="Clementina",
        color="3",
    )
    recepcion.fill_bin_variable_fields(kilos_bruto="520", kilos_neto="510")
    recepcion.agregar_bin()
    recepcion.expect_success_message()


def test_add_bin_appears_in_sidebar(recepcion):
    """El bin recien agregado aparece en el panel lateral."""
    recepcion.iniciar_lote()
    recepcion.fill_bin_base_fields("PROD-002", "Mandarina", "2")
    recepcion.fill_bin_variable_fields(kilos_bruto="480", kilos_neto="460")
    recepcion.agregar_bin()
    bins_items = recepcion.page.locator("#bins-list div[style*='border-bottom']")
    expect(bins_items.first).to_be_visible()


def test_base_fields_become_readonly_after_first_bin(recepcion):
    """Tras agregar el primer bin los campos base deben quedar readonly."""
    recepcion.iniciar_lote()
    recepcion.fill_bin_base_fields("PROD-003", "Thompson", "1")
    recepcion.agregar_bin()
    readonly_inputs = recepcion.page.locator('[name="codigo_productor"][readonly]')
    expect(readonly_inputs).to_be_visible()


def test_cerrar_lote_button_disabled_with_zero_bins(recepcion):
    """El boton Cerrar Lote debe estar deshabilitado si no hay bins."""
    recepcion.iniciar_lote()
    cerrar_btn = recepcion.page.get_by_role("button", name="Cerrar Lote")
    expect(cerrar_btn).to_be_disabled()


def test_cerrar_lote_after_adding_bin(recepcion):
    """Despues de agregar un bin, cerrar el lote debe mostrar exito."""
    recepcion.iniciar_lote()
    recepcion.fill_bin_base_fields("PROD-004", "Navel", "4")
    recepcion.fill_bin_variable_fields(kilos_bruto="600", kilos_neto="580")
    recepcion.agregar_bin()
    recepcion.fill_cerrar_form(kilos_bruto="600", kilos_neto="580")
    recepcion.cerrar_lote()
    recepcion.expect_success_message()


def test_cerrar_lote_returns_to_iniciar_form(recepcion):
    """Al cerrar el lote debe volver al estado inicial (sin lote activo)."""
    recepcion.iniciar_lote()
    recepcion.fill_bin_base_fields("PROD-005", "Satsuma", "2")
    recepcion.fill_bin_variable_fields(kilos_bruto="500", kilos_neto="480")
    recepcion.agregar_bin()
    recepcion.fill_cerrar_form()
    recepcion.cerrar_lote()
    recepcion.expect_iniciar_form_visible()
