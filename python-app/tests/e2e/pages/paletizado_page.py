from playwright.sync_api import Page, expect


class PaletizadoPage:
    URL_PATH = "/operaciones/paletizado/"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def navigate(self) -> None:
        self.page.goto(f"{self.base_url}{self.URL_PATH}")

    def expect_success_message(self) -> None:
        expect(self.page.locator(".alert-success")).to_be_visible()
