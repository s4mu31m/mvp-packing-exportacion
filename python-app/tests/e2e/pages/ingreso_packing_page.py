from playwright.sync_api import Page, expect


class IngresoPackingPage:
    URL_PATH = "/operaciones/ingreso-packing/"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def navigate(self) -> None:
        self.page.goto(f"{self.base_url}{self.URL_PATH}")

    def set_lote_code(self, lote_code: str) -> None:
        self.page.locator("#lote-code-display").fill(lote_code)

    def select_lote(self, lote_code: str) -> None:
        self.page.locator("#lote-selector").select_option(value=lote_code)

    def fill_form(
        self,
        fecha: str,
        hora: str,
        kilos_bruto: str = "",
        kilos_neto: str = "",
    ) -> None:
        self.page.locator("[name='fecha_ingreso']").fill(fecha)
        self.page.locator("[name='hora_ingreso']").fill(hora)
        if kilos_bruto:
            self.page.locator("[name='kilos_bruto_ingreso_packing']").fill(kilos_bruto)
        if kilos_neto:
            self.page.locator("[name='kilos_neto_ingreso_packing']").fill(kilos_neto)

    def submit(self) -> None:
        self.page.locator("#form-ingreso").get_by_role("button", name="Registrar Ingreso").click()

    def expect_success_message(self) -> None:
        expect(self.page.locator(".alert-success")).to_be_visible()

    def expect_error_message(self, text: str) -> None:
        expect(self.page.locator(".alert-error")).to_contain_text(text)

    def expect_context(
        self,
        *,
        lote_code: str,
        productor: str,
        variedad: str,
        color: str,
        via_desverdizado: bool,
        kilos_neto: int | None = None,
    ) -> None:
        expect(self.page.locator("#lote-context-panel")).to_be_visible()
        expect(self.page.locator("#ctx-lote")).to_have_text(lote_code)
        expect(self.page.locator("#ctx-productor")).to_have_text(productor)
        expect(self.page.locator("#ctx-variedad")).to_have_text(variedad)
        expect(self.page.locator("#ctx-color")).to_have_text(color)
        expect(self.page.locator("#ctx-via-desv")).not_to_have_text("")
        if kilos_neto is not None:
            expect(self.page.locator("#ctx-kg-neto")).to_contain_text(f"{kilos_neto}")
        self.expect_hidden_via_desverdizado(via_desverdizado)

    def expect_hidden_via_desverdizado(self, expected: bool) -> None:
        expect(self.page.locator("#via-desverdizado-hidden")).to_have_value("on" if expected else "")
