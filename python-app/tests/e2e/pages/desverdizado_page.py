from playwright.sync_api import Page, expect


class DesverdizadoPage:
    URL_PATH = "/operaciones/desverdizado/"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def navigate(self) -> None:
        self.page.goto(f"{self.base_url}{self.URL_PATH}")

    def set_lote_code(self, lote_code: str) -> None:
        self.page.locator("#lote-code-input").fill(lote_code)

    def select_lote(self, lote_code: str) -> None:
        self.page.locator("#lote-selector").select_option(label=lote_code)

    def fill_desv_form(
        self,
        fecha: str,
        hora: str,
        horas_desverdizado: str = "24",
    ) -> None:
        self.page.get_by_label("Fecha ingreso").fill(fecha)
        self.page.get_by_label("Hora ingreso").fill(hora)
        self.page.get_by_label("Horas de desverdizado").fill(horas_desverdizado)

    def submit_desv_form(self) -> None:
        self.page.get_by_role("button", name="Registrar desverdizado").click()

    def expect_no_lotes_pendientes(self) -> None:
        expect(
            self.page.get_by_text("No hay lotes cerrados pendientes")
        ).to_be_visible()

    def expect_success_message(self) -> None:
        expect(self.page.locator(".alert-success")).to_be_visible()
