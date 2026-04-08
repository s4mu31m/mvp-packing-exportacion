"""
Fase 1 — Recepción de bins E2E

Cubre: iniciar lote, agregar bins, campos base bloqueados tras primer bin,
simulación de escáner, cerrar lote.
"""
import pytest
from playwright.sync_api import expect
from tests.e2e.pages.recepcion_page import RecepcionPage

pytestmark = pytest.mark.e2e


@pytest.fixture()
def recepcion(as_recepcion, live_server):
    """RecepcionPage ya autenticado como operador de Recepcion."""
    page = RecepcionPage(as_recepcion, live_server.url)
    page.navigate()
    return page


# ─── Estado inicial ──────────────────────────────────────────────────────────

def test_recepcion_page_loads_with_iniciar_form(recepcion):
    """Sin lote activo debe mostrar el formulario de inicio."""
    recepcion.expect_iniciar_form_visible()


def test_iniciar_lote_creates_active_state(recepcion):
    """Al iniciar un lote aparece el formulario de bins."""
    recepcion.iniciar_lote()
    recepcion.expect_bin_form_visible()


def test_iniciar_lote_shows_badge_with_lote_code(recepcion):
    """Al iniciar un lote el header muestra el código del lote activo."""
    recepcion.iniciar_lote()
    recepcion.expect_lote_activo_badge()


# ─── Agregar bins ────────────────────────────────────────────────────────────

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
    """El bin recién agregado aparece en el panel lateral."""
    recepcion.iniciar_lote()
    recepcion.fill_bin_base_fields("PROD-002", "Mandarina", "2")
    recepcion.fill_bin_variable_fields(kilos_bruto="480", kilos_neto="460")
    recepcion.agregar_bin()
    # El sidebar debe mostrar al menos 1 bin (código generado automáticamente)
    page = recepcion.page
    bins_items = page.locator("#bins-list div[style*='border-bottom']")
    expect(bins_items.first).to_be_visible()


def test_base_fields_become_readonly_after_first_bin(recepcion):
    """Tras agregar el primer bin los campos base deben quedar como readonly."""
    recepcion.iniciar_lote()
    recepcion.fill_bin_base_fields("PROD-003", "Thompson", "1")
    recepcion.agregar_bin()

    # Verificar que los campos base ahora son readonly
    page = recepcion.page
    readonly_inputs = page.locator('[name="codigo_productor"][readonly]')
    expect(readonly_inputs).to_be_visible()


# ─── Escáner de códigos ──────────────────────────────────────────────────────

def test_scanner_simulation_available(recepcion):
    """window.simularScan debe estar disponible en la página de recepción."""
    recepcion.iniciar_lote()
    # Verificar que la función existe en el contexto JS
    result = recepcion.page.evaluate("typeof window.simularScan")
    assert result == "function"


# ─── Cerrar lote ─────────────────────────────────────────────────────────────

def test_cerrar_lote_button_disabled_with_zero_bins(recepcion):
    """El botón Cerrar Lote debe estar deshabilitado si no hay bins."""
    recepcion.iniciar_lote()
    cerrar_btn = recepcion.page.get_by_role("button", name="Cerrar Lote")
    expect(cerrar_btn).to_be_disabled()


def test_cerrar_lote_after_adding_bin(recepcion):
    """Después de agregar un bin, cerrar el lote debe mostrar éxito."""
    recepcion.iniciar_lote()
    recepcion.fill_bin_base_fields("PROD-004", "Navel", "4")
    recepcion.fill_bin_variable_fields(kilos_bruto="600", kilos_neto="580")
    recepcion.agregar_bin()

    # Rellenar form de cierre
    recepcion.fill_cerrar_form(kilos_bruto="600", kilos_neto="580")
    recepcion.cerrar_lote()

    recepcion.expect_success_message()


def test_cerrar_lote_returns_to_iniciar_form(recepcion):
    """Al cerrar el lote la página debe volver al estado inicial (sin lote activo)."""
    recepcion.iniciar_lote()
    recepcion.fill_bin_base_fields("PROD-005", "Satsuma", "2")
    recepcion.fill_bin_variable_fields(kilos_bruto="500", kilos_neto="480")
    recepcion.agregar_bin()
    recepcion.fill_cerrar_form()
    recepcion.cerrar_lote()

    # Después de cerrar debe estar de vuelta en el formulario de inicio
    recepcion.expect_iniciar_form_visible()
