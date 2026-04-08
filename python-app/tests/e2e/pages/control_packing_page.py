"""
Page Object para /operaciones/control/packing/

Planilla de calidad packing citricos (defectos, condicion y calibre por pallet).

Estructura de formulario (segun template control_calidad_packing.html):
  - select (sin ID) + onchange → #pallet-id-hidden
  - #pallet-id-hidden → input hidden con el UUID del pallet seleccionado
  - Campos del form: [name='field_name'] (Django form rendering)
  - Boton submit: 'Guardar Planilla Packing'
  - Mensajes: div.alert (con clases alert-success o alert-error)

Nota: el selector de pallet usa el UUID (pallet.id) como value, no el pallet_code.
"""
from __future__ import annotations

from playwright.sync_api import Page, expect


class ControlPackingPage:
    URL_PATH = "/operaciones/control/packing/"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def navigate(self) -> None:
        self.page.goto(f"{self.base_url}{self.URL_PATH}")

    def select_pallet(self, pallet_id: str) -> None:
        """
        Selecciona el pallet por su UUID (pallet.id).
        El template usa onchange para setear #pallet-id-hidden.
        """
        self.page.get_by_role("combobox").select_option(value=pallet_id)

    def fill_identification_fields(
        self,
        *,
        productor: str = "",
        variedad: str = "",
        trazabilidad: str = "",
        cod_sdp: str = "",
        cuartel: str = "",
        sector: str = "",
        nombre_control: str = "",
        supervisor: str = "",
        tipo_fruta: str = "",
        color: str = "",
        fecha_cosecha: str = "",
        fecha_despacho: str = "",
    ) -> None:
        if productor:
            self.page.locator("[name='productor']").fill(productor)
        if variedad:
            self.page.locator("[name='variedad']").fill(variedad)
        if trazabilidad:
            self.page.locator("[name='trazabilidad']").fill(trazabilidad)
        if cod_sdp:
            self.page.locator("[name='cod_sdp']").fill(cod_sdp)
        if cuartel:
            self.page.locator("[name='cuartel']").fill(cuartel)
        if sector:
            self.page.locator("[name='sector']").fill(sector)
        if nombre_control:
            self.page.locator("[name='nombre_control']").fill(nombre_control)
        if supervisor:
            self.page.locator("[name='supervisor']").fill(supervisor)
        if tipo_fruta:
            self.page.locator("[name='tipo_fruta']").fill(tipo_fruta)
        if color:
            self.page.locator("[name='color']").fill(color)
        if fecha_cosecha:
            self.page.locator("[name='fecha_cosecha']").fill(fecha_cosecha)
        if fecha_despacho:
            self.page.locator("[name='fecha_despacho']").fill(fecha_despacho)

    def fill_quality_fields(
        self,
        *,
        n_frutos_muestreados: str = "",
        brix: str = "",
        temperatura: str = "",
        humedad: str = "",
        pre_calibre: str = "",
        sobre_calibre: str = "",
    ) -> None:
        if n_frutos_muestreados:
            self.page.locator("[name='n_frutos_muestreados']").fill(n_frutos_muestreados)
        if brix:
            self.page.locator("[name='brix']").fill(brix)
        if temperatura:
            self.page.locator("[name='temperatura']").fill(temperatura)
        if humedad:
            self.page.locator("[name='humedad']").fill(humedad)
        if pre_calibre:
            self.page.locator("[name='pre_calibre']").fill(pre_calibre)
        if sobre_calibre:
            self.page.locator("[name='sobre_calibre']").fill(sobre_calibre)

    def fill_defect_field(self, field_name: str, value: str) -> None:
        """Llena un campo de defecto por su name HTML."""
        self.page.locator(f"[name='{field_name}']").fill(value)

    def fill_multiple_defects(self, defects: dict[str, str]) -> None:
        """
        Llena multiples campos de defecto.
        defects: {"deformes": "3", "manchas": "5", "total_defectos_pct": "8.0", ...}
        """
        for field_name, value in defects.items():
            self.fill_defect_field(field_name, value)

    def submit(self) -> None:
        self.page.get_by_role("button", name="Guardar Planilla Packing").click()

    # ------------------------------------------------------------------
    # Assertions
    # ------------------------------------------------------------------

    def expect_success_message(self) -> None:
        expect(self.page.locator(".alert-success")).to_be_visible()

    def expect_error_message(self, text: str = "") -> None:
        locator = self.page.locator(".alert-error")
        expect(locator).to_be_visible()
        if text:
            expect(locator).to_contain_text(text)

    def expect_pallet_selector_visible(self) -> None:
        expect(self.page.get_by_role("combobox")).to_be_visible()
