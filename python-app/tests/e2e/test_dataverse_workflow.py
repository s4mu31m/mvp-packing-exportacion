from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from playwright.sync_api import expect

from tests.e2e.dataverse_support import (
    TEMPORADA,
    assert_dataverse_entity_set_published,
    seed_closed_lote,
    seed_lote_in_process,
    seed_lote_with_desverdizado,
    seed_lote_with_ingreso_packing,
    seed_pallet_from_lote,
    wait_for,
)
from tests.e2e.pages.camaras_page import CamarasPage
from tests.e2e.pages.consulta_page import ConsultaPage
from tests.e2e.pages.desverdizado_page import DesverdizadoPage
from tests.e2e.pages.ingreso_packing_page import IngresoPackingPage
from tests.e2e.pages.paletizado_page import PaletizadoPage
from tests.e2e.pages.proceso_page import ProcesoPage


pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]


@pytest.fixture(autouse=True)
def _require_dataverse(test_backend):
    if test_backend != "dataverse":
        pytest.skip("Esta suite solo valida E2E contra Dataverse real.")


@pytest.fixture()
def login_as_role(page, make_user, login):
    def _login(role: str) -> str:
        slug = role.lower().replace(" ", "_")
        username = f"e2e_{slug}_{uuid4().hex[:8]}"
        make_user(username, role, nombrecompleto=f"E2E {role}")
        login(username)
        return username

    return _login


def _assert_filled(record, *fields: str) -> None:
    missing = [field for field in fields if getattr(record, field) in (None, "")]
    assert not missing, f"{record.__class__.__name__} quedo con campos vacios: {', '.join(missing)}"


def _wait_for_stage(repositories, lote_code: str, expected_stage: str):
    def _load():
        lote = repositories.lotes.find_by_code(TEMPORADA, lote_code)
        if lote and lote.etapa_actual == expected_stage:
            return lote
        return None

    return wait_for(f"etapa {expected_stage} de {lote_code}", _load)


def test_dataverse_desverdizado_flow_validates_required_fields_conditionals_and_persistence(
    page,
    live_server,
    login_as_role,
    repositories,
):
    login_as_role("Desverdizado")
    lote = seed_closed_lote(
        repositories,
        requiere_desverdizado=True,
        disponibilidad="no_disponible",
        roja=True,
    )
    desverdizado = DesverdizadoPage(page, live_server.url)

    desverdizado.navigate()
    desverdizado.fill_mantencion_form(
        camara_numero="CM-NEG-01",
        fecha_ingreso=lote.fecha_cosecha,
        hora_ingreso="09:00",
    )
    desverdizado.submit_mantencion_form()
    desverdizado.expect_error_message("Campo requerido: lote_code")

    desverdizado.select_lote(lote.lote_code)
    desverdizado.expect_context(
        productor=lote.productor,
        variedad=lote.variedad,
        color=lote.color,
        bins=1,
        kilos_neto=lote.kilos_neto,
    )
    desverdizado.expect_tab_visible("mantencion")
    desverdizado.expect_tab_hidden("desverdizado")

    desverdizado.fill_mantencion_form(
        camara_numero="CM-E2E-01",
        fecha_ingreso=lote.fecha_cosecha,
        hora_ingreso="09:15",
        temperatura_camara="12.5",
        humedad_relativa="84.0",
        observaciones=f"Mantencion {lote.token}",
    )
    desverdizado.submit_mantencion_form()
    desverdizado.expect_success_message()

    mantencion = wait_for(
        f"camara mantencion de {lote.lote_code}",
        lambda: repositories.camara_mantencions.find_by_lote(lote.lote_id),
    )
    _assert_filled(
        mantencion,
        "camara_numero",
        "fecha_ingreso",
        "hora_ingreso",
        "temperatura_camara",
        "humedad_relativa",
    )
    _wait_for_stage(repositories, lote.lote_code, "Mantencion")

    repositories.lotes.update(lote.lote_id, {"disponibilidad_camara_desverdizado": "disponible"})

    desverdizado.navigate()
    desverdizado.select_lote(lote.lote_code)
    desverdizado.expect_tab_visible("desverdizado")
    desverdizado.expect_context(
        productor=lote.productor,
        variedad=lote.variedad,
        color=lote.color,
        bins=1,
        kilos_neto=lote.kilos_neto,
    )

    desverdizado.fill_desv_form(
        fecha=lote.fecha_cosecha,
        hora="10:00",
        color="4",
        horas_desverdizado="72",
        kilos_enviados=str(lote.kilos_neto),
        kilos_recepcionados=str(lote.kilos_neto - 5),
    )
    desverdizado.submit_desv_form()
    desverdizado.expect_success_message()

    registro = wait_for(
        f"desverdizado de {lote.lote_code}",
        lambda: repositories.desverdizados.find_by_lote(lote.lote_id),
    )
    _assert_filled(
        registro,
        "fecha_ingreso",
        "hora_ingreso",
        "color_salida",
        "proceso",
        "kilos_enviados_terreno",
        "kilos_recepcionados",
    )
    assert str(registro.proceso).startswith("72"), "horas_desverdizado no se persistio en el campo proceso"
    _wait_for_stage(repositories, lote.lote_code, "Desverdizado")


def test_dataverse_ingreso_packing_flow_validates_inherited_context_and_persistence(
    page,
    live_server,
    login_as_role,
    repositories,
):
    login_as_role("Ingreso Packing")
    lote = seed_lote_with_desverdizado(repositories)
    ingreso = IngresoPackingPage(page, live_server.url)

    ingreso.navigate()
    ingreso.fill_form(lote.fecha_cosecha, "11:00", kilos_bruto="590", kilos_neto="575")
    ingreso.submit()
    ingreso.expect_error_message("Campo requerido: lote_code")

    ingreso.select_lote(lote.lote_code)
    ingreso.expect_context(
        lote_code=lote.lote_code,
        productor=lote.productor,
        variedad=lote.variedad,
        color=lote.color,
        via_desverdizado=True,
        kilos_neto=lote.kilos_neto,
    )
    ingreso.fill_form(lote.fecha_cosecha, "11:15", kilos_bruto="590", kilos_neto="575")
    ingreso.submit()
    ingreso.expect_success_message()

    registro = wait_for(
        f"ingreso packing de {lote.lote_code}",
        lambda: repositories.ingresos_packing.find_by_lote(lote.lote_id),
    )
    _assert_filled(
        registro,
        "fecha_ingreso",
        "hora_ingreso",
        "kilos_bruto_ingreso_packing",
        "kilos_neto_ingreso_packing",
    )
    assert registro.via_desverdizado is True, "via_desverdizado no se propago al ingreso a packing"
    _wait_for_stage(repositories, lote.lote_code, "Ingreso Packing")


def test_dataverse_proceso_flow_validates_required_fields_context_and_persistence(
    page,
    live_server,
    login_as_role,
    repositories,
):
    login_as_role("Proceso")
    lote = seed_lote_with_ingreso_packing(repositories, via_desverdizado=True)
    proceso = ProcesoPage(page, live_server.url)

    proceso.navigate()
    proceso.fill_form(
        fecha=lote.fecha_cosecha,
        hora_inicio="12:00",
        linea_proceso="LINEA-1",
        categoria_calidad="Extra",
        calibre="XL",
        tipo_envase="Caja 8.2kg",
        cantidad_cajas="60",
        merma_pct="3.5",
    )
    proceso.submit()
    proceso.expect_error_message("Campo requerido: lote_code")

    proceso.select_lote(lote.lote_code)
    proceso.expect_context(
        productor=lote.productor,
        variedad=lote.variedad,
        color=lote.color,
        kilos_neto=lote.kilos_neto,
    )
    proceso.fill_form(
        fecha=lote.fecha_cosecha,
        hora_inicio="12:10",
        linea_proceso="LINEA-1",
        categoria_calidad="Extra",
        calibre="XL",
        tipo_envase="Caja 8.2kg",
        cantidad_cajas="60",
        merma_pct="3.5",
    )
    proceso.submit()
    proceso.expect_success_message()

    registros = wait_for(
        f"registro packing de {lote.lote_code}",
        lambda: repositories.registros_packing.list_by_lote(lote.lote_id),
    )
    registro = registros[-1]
    _assert_filled(
        registro,
        "fecha",
        "hora_inicio",
        "linea_proceso",
        "categoria_calidad",
        "calibre",
        "tipo_envase",
        "cantidad_cajas_producidas",
        "merma_seleccion_pct",
    )
    _wait_for_stage(repositories, lote.lote_code, "Packing / Proceso")


def test_dataverse_control_proceso_flow_persists_visible_parameters(
    page,
    live_server,
    login_as_role,
    repositories,
):
    login_as_role("Control")
    lote = seed_lote_with_ingreso_packing(repositories, via_desverdizado=False)

    page.goto(f"{live_server.url}/operaciones/control/proceso/")
    page.locator("[name='fecha']").fill(lote.fecha_cosecha)
    page.locator("[name='hora']").fill("12:30")
    page.locator("[name='n_bins_procesados']").fill("4")
    page.locator("[name='temp_agua_tina']").fill("4.8")
    page.locator("[name='ph_agua']").fill("6.9")
    page.locator("[name='rendimiento_lote_pct']").fill("91.5")
    page.locator("[name='observaciones_generales']").fill(f"Control {lote.token}")
    page.locator("#form-control button[type='submit']").click()
    expect(page.locator(".alert-error")).to_contain_text("Campo requerido: lote_code")

    page.locator("#lote-selector").select_option(value=lote.lote_code)
    expect(page.locator("#ctx-productor")).to_have_text(lote.productor)
    expect(page.locator("#ctx-variedad")).to_have_text(lote.variedad)
    page.locator("[name='fecha']").fill(lote.fecha_cosecha)
    page.locator("[name='hora']").fill("12:45")
    page.locator("[name='n_bins_procesados']").fill("4")
    page.locator("[name='temp_agua_tina']").fill("4.8")
    page.locator("[name='ph_agua']").fill("6.9")
    page.locator("[name='rendimiento_lote_pct']").fill("91.5")
    page.locator("[name='observaciones_generales']").fill(f"Control {lote.token}")
    page.locator("#form-control button[type='submit']").click()
    expect(page.locator(".alert-success")).to_be_visible()

    registros = wait_for(
        f"control proceso de {lote.lote_code}",
        lambda: repositories.control_proceso_packings.list_by_lote(lote.lote_id),
    )
    registro = registros[-1]
    _assert_filled(
        registro,
        "fecha",
        "hora",
        "n_bins_procesados",
        "temp_agua_tina",
        "ph_agua",
        "rendimiento_lote_pct",
    )
    assert registro.observaciones_generales == f"Control {lote.token}"


def test_dataverse_paletizado_flow_validates_inherited_context_and_quality_persistence(
    page,
    live_server,
    login_as_role,
    repositories,
):
    login_as_role("Paletizado")
    lote = seed_lote_in_process(repositories, via_desverdizado=True)
    pallet = seed_pallet_from_lote(repositories, lote)
    paletizado = PaletizadoPage(page, live_server.url)

    paletizado.navigate()
    paletizado.fill_quality_form(
        fecha=lote.fecha_cosecha,
        hora="13:00",
        temperatura_fruta="7.4",
        peso_caja_muestra="8.200",
        estado_visual_fruta="Uniforme",
        observaciones="Sin hallazgos",
    )
    paletizado.submit_quality()
    paletizado.expect_error_message("Campo requerido: pallet_code")

    paletizado.select_pallet(pallet.pallet_code)
    paletizado.expect_context(
        lote_code=lote.lote_code,
        productor=lote.productor,
        variedad=lote.variedad,
        color=lote.color,
    )
    paletizado.open_close_tab()
    paletizado.expect_close_lote_code(lote.lote_code)

    page.locator("#tab-btn-calidad").click()
    paletizado.fill_quality_form(
        fecha=lote.fecha_cosecha,
        hora="13:10",
        temperatura_fruta="7.4",
        peso_caja_muestra="8.200",
        estado_visual_fruta="Uniforme",
        observaciones="Sin hallazgos",
    )
    paletizado.add_sample(
        index=1,
        temperatura_fruta="7.1",
        peso_caja_muestra="8.100",
        n_frutos="42",
        observaciones="Muestra 1",
    )
    paletizado.submit_quality()
    paletizado.expect_success_message()

    calidad = wait_for(
        f"calidad pallet de {pallet.pallet_code}",
        lambda: repositories.calidad_pallets.list_by_pallet(pallet.pallet_id),
    )[-1]
    _assert_filled(
        calidad,
        "fecha",
        "hora",
        "temperatura_fruta",
        "peso_caja_muestra",
        "estado_visual_fruta",
    )

    muestras = wait_for(
        f"muestras de calidad de {pallet.pallet_code}",
        lambda: repositories.calidad_pallet_muestras.list_by_pallet(pallet.pallet_id),
    )
    muestra = muestras[-1]
    _assert_filled(muestra, "numero_muestra", "temperatura_fruta", "peso_caja_muestra", "n_frutos")
    _wait_for_stage(repositories, lote.lote_code, "Calidad Pallet")


def test_dataverse_camaras_flow_validates_inherited_context_link_and_persistence(
    page,
    live_server,
    login_as_role,
    repositories,
):
    login_as_role("Camaras")
    lote = seed_lote_in_process(repositories, via_desverdizado=False)
    pallet = seed_pallet_from_lote(repositories, lote)
    camaras = CamarasPage(page, live_server.url)

    camaras.navigate()
    camaras.fill_camara_form(
        camara_numero="CF-NEG-01",
        temperatura_camara="-0.8",
        humedad_relativa="92",
        fecha_ingreso=lote.fecha_cosecha,
        hora_ingreso="14:00",
        destino_despacho="Valparaiso",
    )
    camaras.submit_ingreso()
    camaras.expect_error_message("Campo requerido: pallet_code")

    camaras.select_pallet(pallet.pallet_code)
    camaras.expect_context(
        lote_code=lote.lote_code,
        productor=lote.productor,
        variedad=lote.variedad,
        color=lote.color,
    )
    camaras.expect_control_link_visible()
    camaras.fill_camara_form(
        camara_numero="CF-01",
        temperatura_camara="-0.8",
        humedad_relativa="92",
        fecha_ingreso=lote.fecha_cosecha,
        hora_ingreso="14:10",
        destino_despacho="Valparaiso",
    )
    camaras.submit_ingreso()
    camaras.expect_success_message()

    registro = wait_for(
        f"camara frio de {pallet.pallet_code}",
        lambda: repositories.camara_frios.find_by_pallet(pallet.pallet_id),
    )
    _assert_filled(
        registro,
        "camara_numero",
        "temperatura_camara",
        "humedad_relativa",
        "fecha_ingreso",
        "hora_ingreso",
        "destino_despacho",
    )
    _wait_for_stage(repositories, lote.lote_code, "Camara Frio")


def test_dataverse_control_camaras_planilla_persists_measurements(
    page,
    live_server,
    login_as_role,
    repositories,
):
    login_as_role("Control")
    lote = seed_lote_in_process(repositories, via_desverdizado=False)
    pallet = seed_pallet_from_lote(repositories, lote)

    page.goto(f"{live_server.url}/operaciones/control/camaras/")
    assert_dataverse_entity_set_published("crf21_planilla_calidad_camaras")
    page.locator("select").first.select_option(value=str(pallet.pallet_id))
    page.locator("[name='fecha_control']").fill(lote.fecha_cosecha)
    page.locator("[name='tipo_proceso']").fill("Frio exportacion")
    page.locator("[name='zona_planta']").fill("Zona 1")
    page.locator("[name='tunel_camara']").fill("Tunel 2")
    page.locator("[name='capacidad_maxima']").fill("18 pallets")
    page.locator("[name='temperatura_equipos']").fill("-1C")
    page.locator("[name='codigo_envases']").fill("ENV-42")
    page.locator("[name='cantidad_pallets']").fill("1")
    page.locator("[name='especie']").fill(lote.tipo_cultivo)
    page.locator("[name='variedad']").fill(lote.variedad)
    page.locator("[name='fecha_embalaje']").fill(lote.fecha_cosecha)
    page.locator("[name='estiba']").fill("Alta")
    page.locator("[name='tipo_inversion']").fill("Simple")
    page.locator("[name='med_0_hora']").fill("15:00")
    page.locator("[name='med_0_ambiente']").fill("-0.5")
    page.locator("[name='med_0_pulpa_ext_entrada']").fill("3.1")
    page.locator("[name='med_0_pulpa_ext_medio']").fill("2.8")
    page.locator("[name='med_0_pulpa_ext_salida']").fill("2.3")
    page.locator("[name='med_0_pulpa_int_entrada']").fill("4.0")
    page.locator("[name='med_0_pulpa_int_media']").fill("3.6")
    page.locator("[name='med_0_pulpa_int_salida']").fill("3.0")
    page.locator("[name='observaciones']").fill(f"Planilla {lote.token}")
    page.locator("#form-camaras button[type='submit']").click()
    expect(page.locator(".alert-success")).to_be_visible()

    planillas = wait_for(
        f"planilla de control camaras de {pallet.pallet_code}",
        lambda: repositories.planillas_calidad_camara.list_by_pallet(pallet.pallet_id),
    )
    planilla = planillas[-1]
    _assert_filled(planilla, "fecha_control", "tipo_proceso", "tunel_camara", "mediciones_json")
    mediciones = json.loads(planilla.mediciones_json or "[]")
    assert mediciones, "La planilla de control camaras no persistio las mediciones horarias"
    assert mediciones[0]["hora"] == "15:00"


def test_dataverse_consulta_jefatura_filters_and_exports_enriched_fields(
    page,
    live_server,
    login_as_role,
    repositories,
):
    login_as_role("Jefatura")
    lote = seed_lote_with_ingreso_packing(repositories, via_desverdizado=False)
    consulta = ConsultaPage(page, live_server.url)

    consulta.navigate()
    consulta.filter_by_productor(lote.productor)
    consulta.expect_active_filters_indicator()
    consulta.expect_lote_in_table(lote.lote_code)
    expect(page.locator(f"td:has-text('{lote.variedad}')")).to_be_visible()

    download = consulta.click_export_csv()
    csv_content = Path(download.path()).read_text(encoding="utf-8-sig")
    assert lote.lote_code in csv_content, "El CSV exportado no incluyo el lote filtrado"
    assert lote.productor in csv_content, "El CSV exportado no incluyo el productor heredado"
