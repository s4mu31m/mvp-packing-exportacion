from playwright.sync_api import Page, expect


class GestionUsuariosPage:
    URL_PATH = "/usuarios/gestion/"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def navigate(self) -> None:
        self.page.goto(f"{self.base_url}{self.URL_PATH}")

    def fill_new_user_form(
        self,
        username: str,
        password: str,
        roles: list[str],
        nombre: str = "",
        correo: str = "",
        activo: bool = True,
        bloqueado: bool = False,
    ) -> None:
        # Los labels en el template no tienen `for` con id de Django form;
        # usamos name= directamente porque el HTML los define así.
        self.page.locator('[name="usernamelogin"]').fill(username)
        self.page.locator('[name="nombrecompleto"]').fill(nombre)
        self.page.locator('[name="correo"]').fill(correo)
        self.page.locator('[name="password"]').fill(password)
        self.page.locator('[name="password_confirm"]').fill(password)

        # Los roles usan la clase CSS `role-chip`: el <input> queda hidden vía CSS
        # y el <label> es el elemento visible. Hacemos click en el <label> que
        # envuelve el checkbox; eso activa el input sin necesidad de force.
        for role in roles:
            self.page.locator(f'label:has([name="roles"][value="{role}"])').click()

        # Los checkboxes activo/bloqueado usan `toggle-inline`.
        # Igual que con roles: click en el <label> contenedor para activarlos.
        activo_cb = self.page.locator('[name="activo"]')
        if activo and not activo_cb.is_checked():
            self.page.locator('label:has([name="activo"])').click()
        elif not activo and activo_cb.is_checked():
            self.page.locator('label:has([name="activo"])').click()

        if bloqueado:
            self.page.locator('label:has([name="bloqueado"])').click()

    def submit_create_user(self) -> None:
        self.page.get_by_role("button", name="Crear usuario").click()

    def toggle_user(self, username: str) -> None:
        """Hace click en Activar/Desactivar para el usuario indicado."""
        row = self.page.locator(f"td:has-text('{username}')").locator("..")
        row.get_by_role("button").click()

    def expect_user_in_table(self, username: str) -> None:
        expect(self.page.locator(f"td:has-text('{username}')")).to_be_visible()

    def expect_success_message(self) -> None:
        expect(self.page.locator(".alert-success")).to_be_visible()

    def expect_error_message(self) -> None:
        expect(self.page.locator(".alert-danger")).to_be_visible()
