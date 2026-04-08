from playwright.sync_api import Page, expect


class DesverdizadoPage:
    URL_PATH = "/operaciones/desverdizado/"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def navigate(self) -> None:
        self.page.goto(f"{self.base_url}{self.URL_PATH}")

    def set_lote_code(self, lote_code: str) -> None:
        self.page.locator("#lote-code-input").fill(lote_code)

    def select_lote(self, lote_code: str) -> None:
        self.page.locator("#lote-selector").select_option(value=lote_code)

    def fill_mantencion_form(
        self,
        *,
        camara_numero: str = "CM-E2E-01",
        fecha_ingreso: str = "",
        hora_ingreso: str = "",
        temperatura_camara: str = "",
        humedad_relativa: str = "",
        observaciones: str = "",
    ) -> None:
        form = self.page.locator("#form-mantencion")
        form.locator("[name='camara_numero']").fill(camara_numero)
        if fecha_ingreso:
            form.locator("[name='fecha_ingreso']").fill(fecha_ingreso)
        if hora_ingreso:
            form.locator("[name='hora_ingreso']").fill(hora_ingreso)
        if temperatura_camara:
            form.locator("[name='temperatura_camara']").fill(temperatura_camara)
        if humedad_relativa:
            form.locator("[name='humedad_relativa']").fill(humedad_relativa)
        if observaciones:
            form.locator("[name='observaciones']").fill(observaciones)

    def submit_mantencion_form(self) -> None:
        self.page.locator("#form-mantencion").get_by_role("button", name="Registrar Camara").click()

    def fill_desv_form(
        self,
        fecha: str,
        hora: str,
        color: str = "4",
        horas_desverdizado: str = "24",
        kilos_enviados: str = "",
        kilos_recepcionados: str = "",
    ) -> None:
        form = self.page.locator("#form-desverdizado")
        form.locator("[name='fecha_ingreso']").fill(fecha)
        form.locator("[name='hora_ingreso']").fill(hora)
        form.locator("[name='color']").fill(color)
        form.locator("[name='horas_desverdizado']").fill(horas_desverdizado)
        if kilos_enviados:
            form.locator("[name='kilos_enviados_terreno']").fill(kilos_enviados)
        if kilos_recepcionados:
            form.locator("[name='kilos_recepcionados']").fill(kilos_recepcionados)

    def submit_desv_form(self) -> None:
        self.page.locator("#form-desverdizado").get_by_role("button", name="Registrar Desverdizado").click()

    def expect_no_lotes_pendientes(self) -> None:
        expect(self.page.get_by_text("No hay lotes cerrados pendientes")).to_be_visible()

    def expect_success_message(self) -> None:
        expect(self.page.locator(".alert-success")).to_be_visible()

    def expect_error_message(self, text: str) -> None:
        expect(self.page.locator(".alert-error")).to_contain_text(text)

    def expect_context(
        self,
        *,
        productor: str,
        variedad: str,
        color: str,
        bins: int | None = None,
        kilos_neto: int | None = None,
    ) -> None:
        expect(self.page.locator("#lote-context-panel")).to_be_visible()
        expect(self.page.locator("#ctx-productor")).to_have_text(productor)
        expect(self.page.locator("#ctx-variedad")).to_have_text(variedad)
        expect(self.page.locator("#ctx-color")).to_have_text(color)
        if bins is not None:
            expect(self.page.locator("#ctx-bins")).to_have_text(str(bins))
        if kilos_neto is not None:
            expect(self.page.locator("#ctx-kg")).to_contain_text(f"{kilos_neto}")

    def expect_tab_visible(self, name: str) -> None:
        expect(self.page.locator(f"#tab-{name}")).to_be_visible()

    def expect_tab_hidden(self, name: str) -> None:
        expect(self.page.locator(f"#tab-{name}")).to_be_hidden()
