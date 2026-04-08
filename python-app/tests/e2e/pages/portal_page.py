from playwright.sync_api import Page, expect


class PortalPage:
    URL_PATH = "/usuarios/portal/"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def navigate(self) -> None:
        self.page.goto(f"{self.base_url}{self.URL_PATH}")

    def expect_badge(self, badge_text: str) -> None:
        """Verifica que aparezca el badge de rol (Administrador / Jefatura / Operador).

        El template coloca el badge dentro de una etiqueta <p> como <span>.
        Acotamos el locator para evitar strict-mode violations cuando 'Administrador'
        aparece también en otros nodos del DOM (p.ej. sidebar de base.html).
        """
        expect(self.page.locator("p > span").filter(has_text=badge_text)).to_be_visible()

    def expect_module_available(self, module_name: str) -> None:
        """El módulo está visible y tiene el link 'Entrar' habilitado."""
        card = self.page.locator(f"h2:has-text('{module_name}')").locator("..")
        expect(card.get_by_role("link", name="Entrar")).to_be_visible()

    def expect_module_not_available(self, module_name: str) -> None:
        """El módulo aparece pero sin link Entrar (solo botón 'Próximamente')."""
        card = self.page.locator(f"h2:has-text('{module_name}')").locator("..")
        expect(card.get_by_role("link", name="Entrar")).not_to_be_visible()

    def enter_module(self, module_name: str) -> None:
        card = self.page.locator(f"h2:has-text('{module_name}')").locator("..")
        card.get_by_role("link", name="Entrar").click()

    def logout(self) -> None:
        self.page.get_by_role("button", name="Cerrar sesión").click()
