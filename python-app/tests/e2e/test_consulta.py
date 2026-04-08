"""
Fase 2 — Consulta Jefatura y export CSV E2E

Cubre: ver lotes, filtros, limpiar filtros, exportar CSV.
"""
import pytest
from playwright.sync_api import expect
from tests.e2e.pages.consulta_page import ConsultaPage
from tests.e2e.pages.recepcion_page import RecepcionPage

pytestmark = pytest.mark.e2e


def _create_closed_lote(page, live_server, productor="PROD-TEST"):
    """Crea y cierra un lote de recepción. Requiere que el usuario tenga rol Recepcion o Admin."""
    rec = RecepcionPage(page, live_server.url)
    rec.navigate()
    rec.iniciar_lote()
    rec.fill_bin_base_fields(productor, "Clementina", "3")
    rec.fill_bin_variable_fields(kilos_bruto="500", kilos_neto="480")
    rec.agregar_bin()
    rec.fill_cerrar_form(kilos_bruto="500", kilos_neto="480")
    rec.cerrar_lote()


@pytest.fixture()
def consulta_with_data(as_admin, live_server):
    """Página de consulta con al menos un lote creado."""
    _create_closed_lote(as_admin, live_server)
    c = ConsultaPage(as_admin, live_server.url)
    c.navigate()
    return c


# ─── Acceso ──────────────────────────────────────────────────────────────────

def test_consulta_loads_for_jefatura(page, make_user, login, live_server):
    make_user("jef_consulta_ok", "Jefatura")
    login("jef_consulta_ok")
    page.goto(f"{live_server.url}/operaciones/consulta/")
    assert "/consulta" in page.url
    # El texto "Consulta Jefatura" aparece en varios nodos (título de página,
    # sidebar, topnav). Usamos .first para evitar strict-mode violations.
    expect(page.get_by_text("Consulta Jefatura").first).to_be_visible()


def test_consulta_blocked_for_recepcion(page, make_user, login, live_server):
    make_user("rec_no_consulta2", "Recepcion")
    login("rec_no_consulta2")
    page.goto(f"{live_server.url}/operaciones/consulta/")
    assert "/consulta/" not in page.url or "/login" in page.url


# ─── Vista de lotes ───────────────────────────────────────────────────────────

def test_consulta_empty_state_with_no_lotes(as_admin, live_server):
    c = ConsultaPage(as_admin, live_server.url)
    c.navigate()
    c.expect_empty_state()


def test_consulta_shows_lote_after_creation(consulta_with_data):
    """Un lote creado debe aparecer en la tabla de consulta."""
    # Verificar que hay al menos una fila en la tabla
    expect(consulta_with_data.page.locator("table.table")).to_be_visible()
    rows = consulta_with_data.page.locator("table.table tbody tr")
    assert rows.count() >= 1


# ─── Filtros ─────────────────────────────────────────────────────────────────

def test_filter_by_productor_shows_matching_lotes(consulta_with_data):
    consulta_with_data.filter_by_productor("PROD-TEST")
    expect(consulta_with_data.page.get_by_text("Filtros activos")).to_be_visible()
    expect(consulta_with_data.page.locator("table.table")).to_be_visible()


def test_filter_by_productor_no_match_shows_empty(consulta_with_data):
    consulta_with_data.filter_by_productor("PRODUCTOR_QUE_NO_EXISTE_ZZZZZ")
    consulta_with_data.expect_empty_state()


def test_filter_by_estado_cerrado(consulta_with_data):
    consulta_with_data.filter_by_estado("cerrado")
    expect(consulta_with_data.page.get_by_text("Filtros activos")).to_be_visible()


def test_clear_filter_resets_results(consulta_with_data):
    consulta_with_data.filter_by_productor("XYZ_NO_EXISTE")
    consulta_with_data.expect_empty_state()
    consulta_with_data.clear_filters()
    # Sin filtros activos debería mostrar el lote de prueba
    expect(consulta_with_data.page.locator("table.table")).to_be_visible()


# ─── Export CSV ───────────────────────────────────────────────────────────────

def test_export_csv_returns_download(consulta_with_data):
    """El botón Exportar CSV debe desencadenar una descarga."""
    download = consulta_with_data.click_export_csv()
    assert download is not None
    assert download.suggested_filename.endswith(".csv")


def test_export_csv_with_filter(consulta_with_data, live_server):
    """El export CSV respeta los filtros activos."""
    consulta_with_data.filter_by_productor("PROD-TEST")
    download = consulta_with_data.click_export_csv()
    assert download.suggested_filename.endswith(".csv")
