from playwright.sync_api import Page, expect


class ConsultaPage:
    URL_PATH = "/operaciones/consulta/"
    EXPORT_URL_PATH = "/operaciones/consulta/exportar/"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def navigate(self) -> None:
        self.page.goto(f"{self.base_url}{self.URL_PATH}")

    def filter_by_productor(self, text: str) -> None:
        self.page.get_by_placeholder("Filtrar por productor...").fill(text)
        self.page.get_by_role("button", name="Filtrar").click()

    def filter_by_estado(self, estado_value: str) -> None:
        self.page.locator('[name="estado"]').select_option(value=estado_value)
        self.page.get_by_role("button", name="Filtrar").click()

    def clear_filters(self) -> None:
        self.page.get_by_role("link", name="Limpiar").click()

    def click_export_csv(self):
        """Retorna el objeto Download de Playwright."""
        with self.page.expect_download() as dl:
            self.page.get_by_role("link", name="Exportar CSV").click()
        return dl.value

    def expect_lote_in_table(self, lote_code: str) -> None:
        expect(self.page.locator(f"td:has-text('{lote_code}')")).to_be_visible()

    def expect_empty_state(self) -> None:
        expect(self.page.locator(".empty-state")).to_be_visible()

    def expect_active_filters_indicator(self) -> None:
        expect(self.page.get_by_text("Filtros activos")).to_be_visible()
