"""
Fase 1 — Happy path del pipeline MVP (Fase 1: solo recepción completa y dashboard)

Cubre el flujo principal end-to-end:
  Login → Recepción (iniciar lote + agregar bin + cerrar) → Dashboard con KPIs actualizados.

Los tests de etapas posteriores (Desverdizado, Packing, etc.) se agregan en Fase 2
una vez que el scaffolding base sea estable.
"""
import pytest
from playwright.sync_api import expect
from tests.e2e.pages.dashboard_page import DashboardPage
from tests.e2e.pages.recepcion_page import RecepcionPage

pytestmark = pytest.mark.e2e


def _complete_reception(page, live_server):
    """Helper: completa una recepción con un bin y cierra el lote.
    Devuelve la RecepcionPage después del cierre exitoso.
    """
    rec = RecepcionPage(page, live_server.url)
    rec.navigate()
    rec.iniciar_lote()
    rec.fill_bin_base_fields(
        codigo_productor="PROD-MVP",
        variedad="Clementina Oroval",
        color="3",
    )
    rec.fill_bin_variable_fields(kilos_bruto="520", kilos_neto="500")
    rec.agregar_bin()
    rec.fill_cerrar_form(kilos_bruto="520", kilos_neto="500")
    rec.cerrar_lote()
    return rec


def test_dashboard_loads_for_authenticated_user(as_admin, live_server):
    """El dashboard debe cargar sin errores para cualquier usuario autenticado."""
    dash = DashboardPage(as_admin, live_server.url)
    dash.navigate()
    # La página debe mostrar el título de la sección.
    # "Dashboard" aparece en sidebar, topnav y page-title → acotamos a .page-title
    # para evitar strict-mode violation.
    expect(as_admin.locator(".page-title")).to_be_visible()


def test_dashboard_shows_empty_state_with_no_lotes(as_admin, live_server):
    """Con BD vacía el dashboard debe mostrar el empty state."""
    dash = DashboardPage(as_admin, live_server.url)
    dash.navigate()
    dash.expect_empty_state()


def test_reception_creates_lote_visible_in_dashboard(page, make_user, login, live_server):
    """Después de crear y cerrar un lote, éste aparece en el dashboard."""
    make_user("mvp_admin", "Administrador")
    login("mvp_admin")

    _complete_reception(page, live_server)

    # Ir al dashboard y verificar que ya no está el empty state
    dash = DashboardPage(page, live_server.url)
    dash.navigate()
    dash.expect_lotes_table_visible()


def test_dashboard_ver_todos_goes_to_consulta(page, make_user, login, live_server):
    """El link 'Ver todos →' del dashboard lleva a la página de consulta."""
    make_user("mvp_jef", "Administrador")
    login("mvp_jef")

    # Crear un lote para que aparezca la tabla
    _complete_reception(page, live_server)

    dash = DashboardPage(page, live_server.url)
    dash.navigate()
    dash.click_ver_todos()
    assert "/consulta" in page.url


def test_full_reception_pipeline(page, make_user, login, live_server):
    """Pipeline completo de recepción: login → iniciar → agregar bin → cerrar → lote visible."""
    make_user("pipeline_rec", "Recepcion")
    login("pipeline_rec")

    rec = RecepcionPage(page, live_server.url)

    # 1. Iniciar lote
    rec.navigate()
    rec.expect_iniciar_form_visible()
    rec.iniciar_lote()
    rec.expect_bin_form_visible()
    rec.expect_lote_activo_badge()

    # 2. Agregar bin
    rec.fill_bin_base_fields("PROD-FULL", "Thompson Seedless", "2")
    rec.fill_bin_variable_fields(kilos_bruto="480", kilos_neto="460")
    rec.agregar_bin()
    rec.expect_success_message()

    # 3. Cerrar lote
    rec.fill_cerrar_form(kilos_bruto="480", kilos_neto="460")
    rec.cerrar_lote()
    rec.expect_success_message()
    rec.expect_iniciar_form_visible()
