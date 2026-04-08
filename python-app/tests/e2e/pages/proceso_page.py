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

    def expect_success_message(self) -> None:
        expect(self.page.locator(".alert-success")).to_be_visible()
