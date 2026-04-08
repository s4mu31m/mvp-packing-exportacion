from playwright.sync_api import Page, expect


class DashboardPage:
    URL_PATH = "/operaciones/"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def navigate(self) -> None:
        self.page.goto(f"{self.base_url}{self.URL_PATH}")

    def get_kpi_value(self, label_text: str) -> str:
        """Devuelve el valor numérico del KPI cuya etiqueta coincide con label_text."""
        kpi_card = self.page.locator(f"text={label_text}").locator("..")
        return kpi_card.locator("div").first.inner_text()

    def expect_lotes_table_visible(self) -> None:
        expect(self.page.locator("table.table")).to_be_visible()

    def expect_empty_state(self) -> None:
        expect(self.page.locator(".empty-state")).to_be_visible()

    def click_ver_todos(self) -> None:
        self.page.get_by_role("link", name="Ver todos →").click()
