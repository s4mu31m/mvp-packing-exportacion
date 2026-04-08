from playwright.sync_api import Page, expect


class ProcesoPage:
    URL_PATH = "/operaciones/proceso/"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def navigate(self) -> None:
        self.page.goto(f"{self.base_url}{self.URL_PATH}")

    def set_lote_code(self, lote_code: str) -> None:
        self.page.locator("#lote-code-input").fill(lote_code)

    def select_lote(self, lote_code: str) -> None:
        self.page.locator("#lote-selector").select_option(value=lote_code)

    def fill_form(
        self,
        *,
        fecha: str,
        hora_inicio: str,
        linea_proceso: str,
        categoria_calidad: str,
        calibre: str,
        tipo_envase: str,
        cantidad_cajas: str,
        merma_pct: str,
    ) -> None:
        self.page.locator("[name='fecha']").fill(fecha)
        self.page.locator("[name='hora_inicio']").fill(hora_inicio)
        self.page.locator("[name='linea_proceso']").fill(linea_proceso)
        self.page.locator("[name='categoria_calidad']").fill(categoria_calidad)
        self.page.locator("[name='calibre']").fill(calibre)
        self.page.locator("[name='tipo_envase']").fill(tipo_envase)
        self.page.locator("[name='cantidad_cajas_producidas']").fill(cantidad_cajas)
        self.page.locator("[name='merma_seleccion_pct']").fill(merma_pct)

    def submit(self) -> None:
        self.page.get_by_role("button", name="Guardar Registro").click()

    def expect_success_message(self) -> None:
        expect(self.page.locator(".alert-success")).to_be_visible()

    def expect_error_message(self, text: str) -> None:
        expect(self.page.locator(".alert-error")).to_contain_text(text)

    def expect_context(
        self,
        *,
        productor: str,
        variedad: str,
        color: str,
        kilos_neto: int | None = None,
    ) -> None:
        expect(self.page.locator("#lote-context-panel")).to_be_visible()
        expect(self.page.locator("#ctx-productor")).to_have_text(productor)
        expect(self.page.locator("#ctx-variedad")).to_have_text(variedad)
        expect(self.page.locator("#ctx-color")).to_have_text(color)
        if kilos_neto is not None:
            expect(self.page.locator("#ctx-kg")).to_contain_text(f"{kilos_neto}")
