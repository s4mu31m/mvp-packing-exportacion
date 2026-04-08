from playwright.sync_api import Page, expect


class ControlPage:
    """Página índice de Control de Calidad con links a las 4 planillas."""
    URL_PATH = "/operaciones/control/"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def navigate(self) -> None:
        self.page.goto(f"{self.base_url}{self.URL_PATH}")

    def expect_all_planillas_visible(self) -> None:
        expect(self.page.get_by_text("Calidad Desverdizado")).to_be_visible()
        expect(self.page.get_by_text("Calidad Packing Cítricos")).to_be_visible()
        expect(self.page.get_by_text("Control Cámaras")).to_be_visible()
        expect(self.page.get_by_text("Parámetros Proceso")).to_be_visible()

    def go_to_desverdizado(self) -> None:
        self.page.get_by_text("Calidad Desverdizado").click()

    def go_to_packing(self) -> None:
        self.page.get_by_text("Calidad Packing Cítricos").click()

    def go_to_camaras(self) -> None:
        self.page.get_by_text("Control Cámaras").click()

    def go_to_proceso(self) -> None:
        self.page.get_by_text("Parámetros Proceso").click()
