from playwright.sync_api import Page, expect


class RecepcionPage:
    URL_PATH = "/operaciones/recepcion/"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def navigate(self) -> None:
        self.page.goto(f"{self.base_url}{self.URL_PATH}")

    # ── Estado sin lote ──────────────────────────────────────────────────────

    def expect_iniciar_form_visible(self) -> None:
        expect(self.page.locator("#form-iniciar")).to_be_visible()

    def iniciar_lote(self) -> None:
        self.page.get_by_role("button", name="Iniciar Lote").click()

    # ── Estado con lote activo ───────────────────────────────────────────────

    def expect_bin_form_visible(self) -> None:
        expect(self.page.locator("#form-bin")).to_be_visible()

    def fill_bin_base_fields(
        self,
        codigo_productor: str,
        variedad: str,
        color: str,
        tipo_cultivo: str = "",
    ) -> None:
        """Rellena los campos base del lote (se bloquean tras el primer bin)."""
        self.page.get_by_label("Codigo productor / agricultor").fill(codigo_productor)
        if tipo_cultivo:
            self.page.get_by_label("Tipo cultivo (especie)").fill(tipo_cultivo)
        self.page.get_by_label("Variedad").fill(variedad)
        self.page.get_by_label("Color (numero)").fill(color)

    def fill_bin_variable_fields(
        self,
        kilos_bruto: str = "",
        kilos_neto: str = "",
        cuartel: str = "",
    ) -> None:
        """Rellena los campos variables por bin."""
        if kilos_bruto:
            self.page.get_by_label("Kilos bruto ingreso").fill(kilos_bruto)
        if kilos_neto:
            self.page.get_by_label("Kilos neto ingreso").fill(kilos_neto)
        if cuartel:
            self.page.get_by_label("Cuartel").fill(cuartel)

    def agregar_bin(self) -> None:
        self.page.get_by_role("button", name="Agregar Bin").click()

    def simular_scan(self, code: str) -> None:
        """Simula la lectura de un escáner de código de barras usando scan.js."""
        self.page.evaluate("code => window.simularScan(code)", code)

    def cerrar_lote(self) -> None:
        # El texto del botón incluye la cantidad de bins: "Cerrar Lote (N bins)"
        self.page.get_by_role("button", name="Cerrar Lote").click()

    def fill_cerrar_form(
        self,
        kilos_bruto: str = "1000",
        kilos_neto: str = "950",
        requiere_desverdizado: bool = False,
    ) -> None:
        self.page.get_by_label("Kilos bruto total lote").fill(kilos_bruto)
        self.page.get_by_label("Kilos neto total lote").fill(kilos_neto)
        if requiere_desverdizado:
            self.page.get_by_label("Requiere desverdizado").check()

    # ── Sidebar de bins ──────────────────────────────────────────────────────

    def get_bins_count(self) -> int:
        """Cuenta los bins en el panel lateral."""
        items = self.page.locator("#bins-list [style*='border-bottom']").all()
        return len(items)

    def expect_bin_in_sidebar(self, bin_code: str) -> None:
        expect(self.page.locator("#bins-list").get_by_text(bin_code)).to_be_visible()

    def expect_empty_bins_list(self) -> None:
        expect(self.page.locator("#bins-list .empty-state")).to_be_visible()

    # ── Mensajes ─────────────────────────────────────────────────────────────

    def expect_success_message(self) -> None:
        """Verifica que aparezca un mensaje de éxito (Django messages → alert-success)."""
        expect(self.page.locator(".alert-success")).to_be_visible()

    def expect_lote_activo_badge(self) -> None:
        """Verifica que el badge de lote activo sea visible en el header.

        Excluimos .badge-dot porque el topnav siempre muestra una pastilla
        'En línea' que también tiene class badge-teal badge-dot.
        El badge de lote activo NO tiene badge-dot → usamos :not(.badge-dot).
        """
        expect(self.page.locator(".badge-teal:not(.badge-dot)")).to_be_visible()
