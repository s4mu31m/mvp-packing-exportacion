from playwright.sync_api import Page, expect


class CamarasPage:
    URL_PATH = "/operaciones/camaras/"

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

    def fill_camara_form(
        self,
        *,
        camara_numero: str,
        temperatura_camara: str,
        humedad_relativa: str,
        fecha_ingreso: str,
        hora_ingreso: str,
        destino_despacho: str,
    ) -> None:
        self.page.locator("[name='camara_numero']").fill(camara_numero)
        self.page.locator("[name='temperatura_camara']").fill(temperatura_camara)
        self.page.locator("[name='humedad_relativa']").fill(humedad_relativa)
        self.page.locator("[name='fecha_ingreso']").fill(fecha_ingreso)
        self.page.locator("[name='hora_ingreso']").fill(hora_ingreso)
        self.page.locator("[name='destino_despacho']").fill(destino_despacho)

    def submit_ingreso(self) -> None:
        self.page.get_by_role("button", name="Registrar Ingreso").click()

    def expect_control_link_visible(self) -> None:
        expect(self.page.locator("a[href$='/operaciones/control/camaras/']")).to_be_visible()

    def expect_success_message(self) -> None:
        expect(self.page.locator(".alert-success")).to_be_visible()

    def expect_error_message(self, text: str) -> None:
        expect(self.page.locator(".alert-error")).to_contain_text(text)
