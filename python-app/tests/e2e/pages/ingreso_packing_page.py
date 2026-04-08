from playwright.sync_api import Page, expect


class IngresoPackingPage:
    URL_PATH = "/operaciones/ingreso-packing/"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def navigate(self) -> None:
        self.page.goto(f"{self.base_url}{self.URL_PATH}")

    def set_lote_code(self, lote_code: str) -> None:
        self.page.locator("#lote-code-input").fill(lote_code)

    def fill_form(
        self,
        fecha: str,
        hora: str,
        kilos_bruto: str = "",
        kilos_neto: str = "",
    ) -> None:
        self.page.get_by_label("Fecha ingreso").fill(fecha)
        self.page.get_by_label("Hora ingreso").fill(hora)
        if kilos_bruto:
            self.page.get_by_label("Kilos bruto ingreso packing").fill(kilos_bruto)
        if kilos_neto:
            self.page.get_by_label("Kilos neto ingreso packing").fill(kilos_neto)

    def submit(self) -> None:
        self.page.get_by_role("button", name="Registrar ingreso").click()

    def expect_success_message(self) -> None:
        expect(self.page.locator(".alert-success")).to_be_visible()
