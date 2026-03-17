from operaciones.application.exceptions import PayloadValidationError
from operaciones.services.normalizers import normalize_code, normalize_temporada, normalize_operator_code


def require_fields(payload: dict, fields: list[str]) -> None:
    errors = []
    for field in fields:
        if payload.get(field) in [None, ""]:
            errors.append(f"Campo requerido: {field}")

    if errors:
        raise PayloadValidationError(errors)


def validate_bin_payload(payload: dict) -> dict:
    require_fields(payload, ["temporada", "bin_code"])

    return {
        "temporada": normalize_temporada(payload["temporada"]),
        "bin_code": normalize_code(payload["bin_code"]),
        "operator_code": normalize_operator_code(payload.get("operator_code", "")),
        "source_system": payload.get("source_system", "local").strip() or "local",
        "source_event_id": payload.get("source_event_id", "").strip(),
    }


def validate_lote_payload(payload: dict) -> dict:
    require_fields(payload, ["temporada", "lote_code"])

    return {
        "temporada": normalize_temporada(payload["temporada"]),
        "lote_code": normalize_code(payload["lote_code"]),
        "operator_code": normalize_operator_code(payload.get("operator_code", "")),
        "source_system": payload.get("source_system", "local").strip() or "local",
        "source_event_id": payload.get("source_event_id", "").strip(),
    }


def validate_pallet_payload(payload: dict) -> dict:
    require_fields(payload, ["temporada", "pallet_code"])

    return {
        "temporada": normalize_temporada(payload["temporada"]),
        "pallet_code": normalize_code(payload["pallet_code"]),
        "operator_code": normalize_operator_code(payload.get("operator_code", "")),
        "source_system": payload.get("source_system", "local").strip() or "local",
        "source_event_id": payload.get("source_event_id", "").strip(),
    }
