import re
from operaciones.application.exceptions import PayloadValidationError
from operaciones.services.normalizers import normalize_code, normalize_temporada, normalize_operator_code


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def require_fields(payload: dict, fields: list[str]) -> None:
    errors = []
    for field in fields:
        if payload.get(field) in [None, ""]:
            errors.append(f"Campo requerido: {field}")
    if errors:
        raise PayloadValidationError(errors)


def _validate_hora(value: str, field_name: str, errors: list) -> None:
    """Valida formato HH:mm."""
    if value and not re.match(r"^\d{2}:\d{2}$", value):
        errors.append(f"{field_name} debe tener formato HH:mm (ej: 08:30)")


def _validate_neto_bruto(neto, bruto, campo_neto: str, campo_bruto: str, errors: list) -> None:
    """Valida que neto <= bruto cuando ambos estan presentes."""
    if neto is not None and bruto is not None:
        try:
            if float(neto) > float(bruto):
                errors.append(
                    f"{campo_neto} no puede superar {campo_bruto}"
                )
        except (TypeError, ValueError):
            pass


def _validate_pct(value, campo: str, errors: list) -> None:
    """Valida que el porcentaje este en rango 0-100."""
    if value is not None:
        try:
            v = float(value)
            if not (0 <= v <= 100):
                errors.append(f"{campo} debe estar en rango 0-100")
        except (TypeError, ValueError):
            errors.append(f"{campo} debe ser un numero")


def _payload_values(payload: dict) -> dict:
    """
    Compatibilidad entre payloads legacy (campos top-level) y payloads de las
    vistas web que encapsulan los datos operativos dentro de payload["extra"].
    """
    values = {}
    extra = payload.get("extra")
    if isinstance(extra, dict):
        values.update(extra)
    values.update(payload)
    return values


# ---------------------------------------------------------------------------
# Entidades base
# ---------------------------------------------------------------------------

def validate_bin_payload(payload: dict) -> dict:
    require_fields(payload, ["temporada"])

    errors = []
    _validate_hora(payload.get("hora_recepcion", ""), "hora_recepcion", errors)
    _validate_neto_bruto(
        payload.get("kilos_neto_ingreso"), payload.get("kilos_bruto_ingreso"),
        "kilos_neto_ingreso", "kilos_bruto_ingreso", errors
    )
    if errors:
        raise PayloadValidationError(errors)

    # bin_code es opcional: si no se provee, el use case lo genera automaticamente
    bin_code_raw = payload.get("bin_code", "")
    return {
        "temporada": normalize_temporada(payload["temporada"]),
        "bin_code": normalize_code(bin_code_raw) if bin_code_raw else "",
        "operator_code": normalize_operator_code(payload.get("operator_code", "")),
        "source_system": payload.get("source_system", "local").strip() or "local",
        "source_event_id": payload.get("source_event_id", "").strip(),
        # Campos opcionales del bin
        "extra": {
            k: payload[k]
            for k in [
                "fecha_cosecha", "codigo_productor", "nombre_productor",
                "variedad_fruta", "numero_cuartel", "nombre_cuartel",
                "predio", "sector", "lote_productor", "color", "estado_fisico",
                "a_o_r", "n_guia", "transporte", "capataz", "codigo_contratista",
                "nombre_contratista", "hora_recepcion",
                "kilos_bruto_ingreso", "kilos_neto_ingreso",
                "n_cajas_campo", "observaciones", "rol",
            ]
            if k in payload and payload[k] not in [None, ""]
        },
    }


def validate_lote_payload(payload: dict) -> dict:
    require_fields(payload, ["temporada"])

    errors = []
    _validate_neto_bruto(
        payload.get("kilos_neto_conformacion"), payload.get("kilos_bruto_conformacion"),
        "kilos_neto_conformacion", "kilos_bruto_conformacion", errors
    )
    if errors:
        raise PayloadValidationError(errors)

    lote_code_raw = payload.get("lote_code", "")
    return {
        "temporada": normalize_temporada(payload["temporada"]),
        "lote_code": normalize_code(lote_code_raw) if lote_code_raw else "",
        "operator_code": normalize_operator_code(payload.get("operator_code", "")),
        "source_system": payload.get("source_system", "local").strip() or "local",
        "source_event_id": payload.get("source_event_id", "").strip(),
        "extra": {
            k: payload[k]
            for k in [
                "fecha_conformacion", "cantidad_bins",
                "kilos_bruto_conformacion", "kilos_neto_conformacion",
                "requiere_desverdizado", "disponibilidad_camara_desverdizado",
                "rol",
            ]
            if k in payload and payload[k] not in [None, ""]
        },
    }


def validate_pallet_payload(payload: dict) -> dict:
    require_fields(payload, ["temporada"])
    pallet_code_raw = payload.get("pallet_code", "")
    return {
        "temporada": normalize_temporada(payload["temporada"]),
        "pallet_code": normalize_code(pallet_code_raw) if pallet_code_raw else "",
        "operator_code": normalize_operator_code(payload.get("operator_code", "")),
        "source_system": payload.get("source_system", "local").strip() or "local",
        "source_event_id": payload.get("source_event_id", "").strip(),
        "extra": {
            k: payload[k]
            for k in ["fecha", "hora", "tipo_caja", "cajas_por_pallet",
                      "peso_total_kg", "destino_mercado", "rol"]
            if k in payload and payload[k] not in [None, ""]
        },
    }


# ---------------------------------------------------------------------------
# Nuevas entidades del flujo
# ---------------------------------------------------------------------------

def validate_camara_mantencion_payload(payload: dict) -> dict:
    values = _payload_values(payload)
    require_fields(values, ["temporada", "lote_code"])
    errors = []
    _validate_hora(values.get("hora_ingreso", ""), "hora_ingreso", errors)
    _validate_hora(values.get("hora_salida", ""), "hora_salida", errors)
    if errors:
        raise PayloadValidationError(errors)
    return {
        "temporada": normalize_temporada(values["temporada"]),
        "lote_code": normalize_code(values["lote_code"]),
        "operator_code": normalize_operator_code(values.get("operator_code", "")),
        "source_system": values.get("source_system", "local").strip() or "local",
        "extra": {
            k: values[k]
            for k in ["camara_numero", "fecha_ingreso", "hora_ingreso",
                      "fecha_salida", "hora_salida", "temperatura_camara",
                      "humedad_relativa", "observaciones", "rol"]
            if k in values and values[k] not in [None, ""]
        },
    }


def validate_desverdizado_payload(payload: dict) -> dict:
    values = _payload_values(payload)
    require_fields(values, ["temporada", "lote_code"])
    errors = []
    _validate_hora(values.get("hora_ingreso", ""), "hora_ingreso", errors)
    _validate_hora(values.get("hora_salida", ""), "hora_salida", errors)
    _validate_neto_bruto(
        values.get("kilos_neto_salida"), values.get("kilos_bruto_salida"),
        "kilos_neto_salida", "kilos_bruto_salida", errors
    )
    if errors:
        raise PayloadValidationError(errors)
    extra = {
        k: values[k]
        for k in [
            "fecha_ingreso", "hora_ingreso", "fecha_salida", "hora_salida",
            "kilos_enviados_terreno", "kilos_recepcionados", "kilos_procesados",
            "kilos_bruto_salida", "kilos_neto_salida",
            "color_salida", "proceso", "fecha_proceso", "sector", "cuartel", "rol",
        ]
        if k in values and values[k] not in [None, ""]
    }
    if "proceso" not in extra and values.get("horas_desverdizado") not in [None, ""]:
        extra["proceso"] = str(values["horas_desverdizado"])
    return {
        "temporada": normalize_temporada(values["temporada"]),
        "lote_code": normalize_code(values["lote_code"]),
        "operator_code": normalize_operator_code(values.get("operator_code", "")),
        "source_system": values.get("source_system", "local").strip() or "local",
        "extra": extra,
    }


def validate_calidad_desverdizado_payload(payload: dict) -> dict:
    values = _payload_values(payload)
    require_fields(values, ["temporada", "lote_code"])
    errors = []
    _validate_hora(values.get("hora", ""), "hora", errors)
    if errors:
        raise PayloadValidationError(errors)
    return {
        "temporada": normalize_temporada(values["temporada"]),
        "lote_code": normalize_code(values["lote_code"]),
        "operator_code": normalize_operator_code(values.get("operator_code", "")),
        "source_system": values.get("source_system", "local").strip() or "local",
        "extra": {
            k: values[k]
            for k in [
                "fecha", "hora", "temperatura_fruta", "color_evaluado",
                "estado_visual", "presencia_defectos", "descripcion_defectos",
                "aprobado", "observaciones", "rol",
            ]
            if k in values and values[k] not in [None, ""]
        },
    }


def validate_ingreso_packing_payload(payload: dict) -> dict:
    values = _payload_values(payload)
    require_fields(values, ["temporada", "lote_code"])
    errors = []
    _validate_hora(values.get("hora_ingreso", ""), "hora_ingreso", errors)
    _validate_neto_bruto(
        values.get("kilos_neto_ingreso_packing"),
        values.get("kilos_bruto_ingreso_packing"),
        "kilos_neto_ingreso_packing", "kilos_bruto_ingreso_packing", errors
    )
    if errors:
        raise PayloadValidationError(errors)
    return {
        "temporada": normalize_temporada(values["temporada"]),
        "lote_code": normalize_code(values["lote_code"]),
        "operator_code": normalize_operator_code(values.get("operator_code", "")),
        "source_system": values.get("source_system", "local").strip() or "local",
        "extra": {
            k: values[k]
            for k in [
                "fecha_ingreso", "hora_ingreso",
                "kilos_bruto_ingreso_packing", "kilos_neto_ingreso_packing",
                "via_desverdizado", "observaciones", "rol",
            ]
            if k in values and values[k] not in [None, ""]
        },
    }


def validate_registro_packing_payload(payload: dict) -> dict:
    values = _payload_values(payload)
    require_fields(values, ["temporada", "lote_code"])
    errors = []
    _validate_hora(values.get("hora_inicio", ""), "hora_inicio", errors)
    _validate_pct(values.get("merma_seleccion_pct"), "merma_seleccion_pct", errors)
    if errors:
        raise PayloadValidationError(errors)
    return {
        "temporada": normalize_temporada(values["temporada"]),
        "lote_code": normalize_code(values["lote_code"]),
        "operator_code": normalize_operator_code(values.get("operator_code", "")),
        "source_system": values.get("source_system", "local").strip() or "local",
        "extra": {
            k: values[k]
            for k in [
                "fecha", "hora_inicio", "linea_proceso", "categoria_calidad",
                "calibre", "tipo_envase", "cantidad_cajas_producidas",
                "peso_promedio_caja_kg", "merma_seleccion_pct",
                "merma_seleccion_kg", "kilos_fruta_comercial", "kilos_descarte_local",
                "rol",
            ]
            if k in values and values[k] not in [None, ""]
        },
    }


def validate_control_proceso_packing_payload(payload: dict) -> dict:
    values = _payload_values(payload)
    require_fields(values, ["temporada", "lote_code"])
    errors = []
    _validate_hora(values.get("hora", ""), "hora", errors)
    for campo in ["rendimiento_lote_pct", "pct_calibre_export", "pct_calibres_menores"]:
        _validate_pct(values.get(campo), campo, errors)
    if errors:
        raise PayloadValidationError(errors)
    return {
        "temporada": normalize_temporada(values["temporada"]),
        "lote_code": normalize_code(values["lote_code"]),
        "operator_code": normalize_operator_code(values.get("operator_code", "")),
        "source_system": values.get("source_system", "local").strip() or "local",
        "extra": {
            k: values[k]
            for k in [
                "fecha", "hora", "n_bins_procesados", "velocidad_volcador",
                "obs_volcador", "temp_agua_tina", "cloro_libre_ppm", "ph_agua",
                "tiempo_inmersion_seg", "recambio_agua", "temp_aire_secado",
                "velocidad_ventiladores", "fruta_sale_seca", "tipo_cera",
                "dosis_cera_ml_min", "temp_cera", "cobertura_uniforme",
                "n_operarios_seleccion", "fruta_dano_condicion_kg",
                "fruta_dano_calidad_kg", "fruta_pudricion_kg",
                "merma_total_seleccion_kg", "equipo_calibrador",
                "calibre_predominante", "pct_calibre_export", "pct_calibres_menores",
                "tipo_caja", "peso_promedio_caja_kg", "n_cajas_producidas",
                "rendimiento_lote_pct", "observaciones_generales", "rol",
            ]
            if k in values and values[k] not in [None, ""]
        },
    }


def validate_calidad_pallet_payload(payload: dict) -> dict:
    values = _payload_values(payload)
    require_fields(values, ["temporada", "pallet_code"])
    errors = []
    _validate_hora(values.get("hora", ""), "hora", errors)
    if errors:
        raise PayloadValidationError(errors)
    return {
        "temporada": normalize_temporada(values["temporada"]),
        "pallet_code": normalize_code(values["pallet_code"]),
        "operator_code": normalize_operator_code(values.get("operator_code", "")),
        "source_system": values.get("source_system", "local").strip() or "local",
        "extra": {
            k: values[k]
            for k in [
                "fecha", "hora", "temperatura_fruta", "peso_caja_muestra",
                "estado_embalaje", "estado_visual_fruta", "presencia_defectos",
                "descripcion_defectos", "aprobado", "observaciones", "rol",
            ]
            if k in values and values[k] not in [None, ""]
        },
    }


def validate_camara_frio_payload(payload: dict) -> dict:
    values = _payload_values(payload)
    require_fields(values, ["temporada", "pallet_code"])
    errors = []
    _validate_hora(values.get("hora_ingreso", ""), "hora_ingreso", errors)
    _validate_hora(values.get("hora_salida", ""), "hora_salida", errors)
    if errors:
        raise PayloadValidationError(errors)
    return {
        "temporada": normalize_temporada(values["temporada"]),
        "pallet_code": normalize_code(values["pallet_code"]),
        "operator_code": normalize_operator_code(values.get("operator_code", "")),
        "source_system": values.get("source_system", "local").strip() or "local",
        "extra": {
            k: values[k]
            for k in [
                "camara_numero", "temperatura_camara", "humedad_relativa",
                "fecha_ingreso", "hora_ingreso", "fecha_salida", "hora_salida",
                "destino_despacho", "rol",
            ]
            if k in values and values[k] not in [None, ""]
        },
    }


def validate_medicion_temperatura_payload(payload: dict) -> dict:
    values = _payload_values(payload)
    require_fields(values, ["temporada", "pallet_code"])
    errors = []
    _validate_hora(values.get("hora", ""), "hora", errors)
    if errors:
        raise PayloadValidationError(errors)
    return {
        "temporada": normalize_temporada(values["temporada"]),
        "pallet_code": normalize_code(values["pallet_code"]),
        "operator_code": normalize_operator_code(values.get("operator_code", "")),
        "source_system": values.get("source_system", "local").strip() or "local",
        "extra": {
            k: values[k]
            for k in [
                "fecha", "hora", "temperatura_pallet", "punto_medicion",
                "dentro_rango", "observaciones", "rol",
            ]
            if k in values and values[k] not in [None, ""]
        },
    }
