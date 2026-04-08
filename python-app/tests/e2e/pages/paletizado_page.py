from playwright.sync_api import Page, expect


class PaletizadoPage:
    URL_PATH = "/operaciones/paletizado/"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def navigate(self) -> None:
        self.page.goto(f"{self.base_url}{self.URL_PATH}")

    def select_pallet(self, pallet_code: str) -> None:
        self.page.locator("#pallet-selector").select_option(value=pallet_code)

    def expect_context(
        self,
        *,
        lote_code: str,
        productor: str,
        variedad: str,
        color: str,
    ) -> None:
        expect(self.page.locator("#pallet-context-panel")).to_be_visible()
        expect(self.page.locator("#ctx-lote")).to_have_text(lote_code)
        expect(self.page.locator("#ctx-productor")).to_have_text(productor)
        expect(self.page.locator("#ctx-variedad")).to_have_text(variedad)
        expect(self.page.locator("#ctx-color")).to_have_text(color)

    def fill_quality_form(
        self,
        *,
        fecha: str,
        hora: str,
        temperatura_fruta: str,
        peso_caja_muestra: str,
        estado_visual_fruta: str,
        observaciones: str = "",
    ) -> None:
        self.page.locator("[name='fecha']").fill(fecha)
        self.page.locator("[name='hora']").fill(hora)
        self.page.locator("[name='temperatura_fruta']").fill(temperatura_fruta)
        self.page.locator("[name='peso_caja_muestra']").fill(peso_caja_muestra)
        self.page.locator("[name='estado_visual_fruta']").fill(estado_visual_fruta)
        if observaciones:
            self.page.locator("[name='observaciones']").fill(observaciones)

    def add_sample(
        self,
        *,
        index: int,
        temperatura_fruta: str,
        peso_caja_muestra: str,
        n_frutos: str,
        observaciones: str = "",
    ) -> None:
        self.page.locator("#btn-add-muestra").click()
        self.page.locator(f"[name='muestra_{index}_temperatura_fruta']").fill(temperatura_fruta)
        self.page.locator(f"[name='muestra_{index}_peso_caja_muestra']").fill(peso_caja_muestra)
        self.page.locator(f"[name='muestra_{index}_n_frutos']").fill(n_frutos)
        if observaciones:
            self.page.locator(f"[name='muestra_{index}_observaciones']").fill(observaciones)

    def submit_quality(self) -> None:
        self.page.get_by_role("button", name="Registrar Calidad").click()

    def open_close_tab(self) -> None:
        self.page.locator("#tab-btn-cerrar").click()

    def submit_close(self) -> None:
        self.page.get_by_role("button", name="Cerrar Pallet").click()

    def expect_close_lote_code(self, lote_code: str) -> None:
        expect(self.page.locator("#lote-code-display")).to_have_value(lote_code)

    def expect_success_message(self) -> None:
        expect(self.page.locator(".alert-success")).to_be_visible()

    def expect_error_message(self, text: str) -> None:
        expect(self.page.locator(".alert-error")).to_contain_text(text)
