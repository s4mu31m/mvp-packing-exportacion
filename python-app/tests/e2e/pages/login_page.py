from playwright.sync_api import Page, expect


class LoginPage:
    URL_PATH = "/usuarios/login/"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def navigate(self) -> None:
        self.page.goto(f"{self.base_url}{self.URL_PATH}")

    def login(self, username: str, password: str) -> None:
        self.page.get_by_label("Usuario").fill(username)
        self.page.get_by_label("Contraseña").fill(password)
        self.page.get_by_role("button", name="Acceder").click()

    def expect_error_visible(self) -> None:
        expect(self.page.locator(".alert-danger")).to_be_visible()

    def expect_at_portal(self) -> None:
        expect(self.page).to_have_url(f"{self.base_url}/usuarios/portal/")

    def expect_still_at_login(self) -> None:
        expect(self.page).to_have_url(f"{self.base_url}{self.URL_PATH}")
