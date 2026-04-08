"""
Page Object para /operaciones/control/desverdizado/

Cubre las dos planillas:
  - Planilla 1 — Calibres (tab: calibres)
  - Planilla 2 — Semillas (tab: semillas)

Estructura de formulario (segun template control_calidad_desverdizado.html):
  - #lote-selector → select del lote activo
  - #tab-btn-calibres / #tab-btn-semillas → botones de pestana
  - Formulario calibres: action=calibres, campos con name='supervisor', name='oleocelosis', etc.
    y grupos de calibres con name='grupo_N_color', name='grupo_N_cal_CAL', name='grupo_N_obs'
  - Formulario semillas: action=semillas, campos por fruta: name='gG_fF_semillas' (G=1-5, F=1-10)
  - Botones de submit: 'Guardar Planilla Calibres' / 'Guardar Planilla Semillas'
  - Mensajes: div.alert (con clases alert-success o alert-error)
"""
from __future__ import annotations

from playwright.sync_api import Page, expect


class ControlDesvPage:
    URL_PATH = "/operaciones/control/desverdizado/"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def navigate(self) -> None:
        self.page.goto(f"{self.base_url}{self.URL_PATH}")

    def select_lote(self, lote_code: str) -> None:
        self.page.locator("#lote-selector").select_option(value=lote_code)

    # ------------------------------------------------------------------
    # Tab navigation
    # ------------------------------------------------------------------

    def go_to_tab_calibres(self) -> None:
        self.page.locator("#tab-btn-calibres").click()

    def go_to_tab_semillas(self) -> None:
        self.page.locator("#tab-btn-semillas").click()

    # ------------------------------------------------------------------
    # Planilla 1 — Calibres
    # ------------------------------------------------------------------

    def fill_calibres_header(
        self,
        *,
        supervisor: str = "",
        productor: str = "",
        variedad: str = "",
        trazabilidad: str = "",
        cod_sdp: str = "",
        fecha_cosecha: str = "",
        fecha_despacho: str = "",
        cuartel: str = "",
        sector: str = "",
    ) -> None:
        tab = self.page.locator("#tab-calibres")
        if supervisor:
            tab.locator("[name='supervisor']").fill(supervisor)
        if productor:
            tab.locator("[name='productor']").fill(productor)
        if variedad:
            tab.locator("[name='variedad']").fill(variedad)
        if trazabilidad:
            tab.locator("[name='trazabilidad']").fill(trazabilidad)
        if cod_sdp:
            tab.locator("[name='cod_sdp']").fill(cod_sdp)
        if fecha_cosecha:
            tab.locator("[name='fecha_cosecha']").fill(fecha_cosecha)
        if fecha_despacho:
            tab.locator("[name='fecha_despacho']").fill(fecha_despacho)
        if cuartel:
            tab.locator("[name='cuartel']").fill(cuartel)
        if sector:
            tab.locator("[name='sector']").fill(sector)

    def fill_defect_fields(self, defects: dict[str, str]) -> None:
        """
        Llena campos de defecto en la planilla calibres.
        defects: {"oleocelosis": "5.2", "rugoso": "3.1", ...}
        """
        tab = self.page.locator("#tab-calibres")
        for field_name, value in defects.items():
            tab.locator(f"[name='{field_name}']").fill(value)

    def fill_calibres_group(
        self,
        group_index: int,
        color: str,
        calibres: dict[str, str | int],
        obs: str = "",
    ) -> None:
        """
        Llena un grupo de calibres.
        group_index: 1, 2 o 3
        calibres: {"XL": "10", "L": "25", ...}
        """
        tab = self.page.locator("#tab-calibres")
        tab.locator(f"[name='grupo_{group_index}_color']").fill(color)
        for cal_name, value in calibres.items():
            tab.locator(f"[name='grupo_{group_index}_cal_{cal_name}']").fill(str(value))
        if obs:
            tab.locator(f"[name='grupo_{group_index}_obs']").fill(obs)

    def submit_calibres(self) -> None:
        self.page.locator("#tab-calibres").get_by_role(
            "button", name="Guardar Planilla Calibres"
        ).click()

    # ------------------------------------------------------------------
    # Planilla 2 — Semillas
    # ------------------------------------------------------------------

    def fill_semillas_header(
        self,
        *,
        supervisor: str = "",
        productor: str = "",
        variedad: str = "",
        color: str = "",
        trazabilidad: str = "",
        cod_sdp: str = "",
        cuartel: str = "",
        sector: str = "",
        fecha: str = "",
    ) -> None:
        tab = self.page.locator("#tab-semillas")
        if supervisor:
            tab.locator("[name='supervisor']").fill(supervisor)
        if productor:
            tab.locator("[name='productor']").fill(productor)
        if variedad:
            tab.locator("[name='variedad']").fill(variedad)
        if color:
            tab.locator("[name='color']").fill(color)
        if trazabilidad:
            tab.locator("[name='trazabilidad']").fill(trazabilidad)
        if cod_sdp:
            tab.locator("[name='cod_sdp']").fill(cod_sdp)
        if cuartel:
            tab.locator("[name='cuartel']").fill(cuartel)
        if sector:
            tab.locator("[name='sector']").fill(sector)
        if fecha:
            tab.locator("[name='fecha']").fill(fecha)

    def fill_fruit_seed_count(self, fruit_n: int, semillas: int) -> None:
        """
        Llena el conteo de semillas para un fruto especifico.
        fruit_n: 1..50 (el template organiza 5 grupos × 10 frutas)
        semillas: 0..20
        """
        group = ((fruit_n - 1) // 10) + 1    # 1..5
        fruit_in_group = ((fruit_n - 1) % 10) + 1  # 1..10
        self.page.locator(f"[name='g{group}_f{fruit_in_group}_semillas']").fill(str(semillas))

    def fill_fruit_seed_counts(self, counts: dict[int, int]) -> None:
        """
        Llena multiples conteos de semillas a la vez.
        counts: {1: 0, 2: 3, 3: 1, ...}
        """
        for fruit_n, semillas in counts.items():
            self.fill_fruit_seed_count(fruit_n, semillas)

    def submit_semillas(self) -> None:
        self.page.locator("#tab-semillas").get_by_role(
            "button", name="Guardar Planilla Semillas"
        ).click()

    # ------------------------------------------------------------------
    # Assertions
    # ------------------------------------------------------------------

    def expect_success_message(self) -> None:
        expect(self.page.locator(".alert-success")).to_be_visible()

    def expect_error_message(self, text: str = "") -> None:
        locator = self.page.locator(".alert-error")
        expect(locator).to_be_visible()
        if text:
            expect(locator).to_contain_text(text)

    def expect_context_visible(self) -> None:
        expect(self.page.locator("#lote-context-panel")).to_be_visible()

    def expect_context(
        self,
        *,
        productor: str = "",
        variedad: str = "",
        color: str = "",
    ) -> None:
        expect(self.page.locator("#lote-context-panel")).to_be_visible()
        if productor:
            expect(self.page.locator("#ctx-productor")).to_have_text(productor)
        if variedad:
            expect(self.page.locator("#ctx-variedad")).to_have_text(variedad)
        if color:
            expect(self.page.locator("#ctx-color")).to_have_text(color)
