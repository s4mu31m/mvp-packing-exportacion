from playwright.sync_api import Page, expect


class ControlPage:
    """Pagina indice de control de calidad con links a las planillas visibles."""

    URL_PATH = "/operaciones/control/"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def navigate(self) -> None:
        self.page.goto(f"{self.base_url}{self.URL_PATH}")

    def expect_all_planillas_visible(self) -> None:
        expect(self.page.locator("a[href$='/operaciones/control/desverdizado/']")).to_be_visible()
        expect(self.page.locator("a[href$='/operaciones/control/packing/']")).to_be_visible()
        expect(self.page.locator("a[href$='/operaciones/control/camaras/']")).to_be_visible()
        expect(self.page.locator("a[href$='/operaciones/control/proceso/']")).to_be_visible()

    def go_to_desverdizado(self) -> None:
        self.page.locator("a[href$='/operaciones/control/desverdizado/']").click()

    def go_to_packing(self) -> None:
        self.page.locator("a[href$='/operaciones/control/packing/']").click()

    def go_to_camaras(self) -> None:
        self.page.locator("a[href$='/operaciones/control/camaras/']").click()

    def go_to_proceso(self) -> None:
        self.page.locator("a[href$='/operaciones/control/proceso/']").click()
