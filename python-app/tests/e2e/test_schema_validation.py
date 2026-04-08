"""
Smoke tests de schema Dataverse.

Validan que todas las entidades y campos requeridos existan en el entorno
Dataverse real. Solo corren con CALIPRO_TEST_BACKEND=dataverse.

Si fallan, ejecutar:
    PERSISTENCE_BACKEND=dataverse python manage.py dataverse_ensure_schema --check-only
    PERSISTENCE_BACKEND=dataverse python manage.py dataverse_ensure_schema --create
"""
from __future__ import annotations

import pytest

from infrastructure.dataverse.schema_definition import (
    REQUIRED_SCHEMA,
    NEW_ENTITIES,
    EntitySpec,
)

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]


@pytest.fixture(autouse=True)
def _require_dataverse(test_backend):
    if test_backend != "dataverse":
        pytest.skip("Esta suite solo valida schema contra Dataverse real.")


@pytest.fixture(scope="module")
def dv_client():
    """Cliente Dataverse compartido para todos los tests de schema (ahorra tokens OAuth)."""
    from infrastructure.dataverse.client import DataverseClient
    return DataverseClient(timeout=60)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_entity_attr_names(client, logical_name: str) -> set[str]:
    """Retorna todos los nombres logicos de atributos de la entidad."""
    from infrastructure.dataverse.client import DataverseAPIError
    try:
        result = client._request(
            "GET",
            f"EntityDefinitions(LogicalName='{logical_name}')/Attributes",
            params={"$select": "LogicalName"},
        )
        return {attr["LogicalName"] for attr in (result or {}).get("value", [])}
    except DataverseAPIError:
        return set()


# ---------------------------------------------------------------------------
# Test 1: Todas las entity sets son accesibles via OData
# ---------------------------------------------------------------------------

def test_all_entity_sets_are_accessible(dv_client):
    """
    Verifica que los 20 entity sets se pueden consultar via OData ($top=1).
    Acumula todos los fallos y los reporta de una vez.
    """
    from infrastructure.dataverse.client import DataverseAPIError

    failures: list[str] = []

    for spec in REQUIRED_SCHEMA:
        try:
            dv_client._request(
                "GET",
                spec.entity_set_name,
                params={"$top": "1", "$select": "createdon"},
            )
        except DataverseAPIError as exc:
            failures.append(f"{spec.entity_set_name}: {exc}")
        except Exception as exc:
            failures.append(f"{spec.entity_set_name}: error inesperado — {exc}")

    if failures:
        msg = (
            f"{len(failures)}/{len(REQUIRED_SCHEMA)} entity sets inaccesibles:\n"
            + "\n".join(f"  - {f}" for f in failures)
            + "\n\nSolucion: PERSISTENCE_BACKEND=dataverse python manage.py dataverse_ensure_schema --create"
        )
        pytest.fail(msg)


# ---------------------------------------------------------------------------
# Test 2: Campos criticos existen en cada entidad
# ---------------------------------------------------------------------------

def test_critical_fields_exist_per_entity(dv_client):
    """
    Para cada entidad, verifica que todos los campos listados en schema_definition
    existan como Attributes en Dataverse.

    Excluye campos de lectura OData (prefijados con '_') y campos Lookup
    (que se verifican via su nombre de atributo, no el alias de lectura).
    """
    gaps: dict[str, list[str]] = {}

    for spec in REQUIRED_SCHEMA:
        required_field_names = [
            f.logical_name
            for f in spec.fields
            if not f.logical_name.startswith("_")
        ]
        if not required_field_names:
            continue

        current_attrs = _get_entity_attr_names(dv_client, spec.logical_name)
        if not current_attrs:
            # La entidad no existe — ya cubierto por test_all_entity_sets_are_accessible
            continue

        missing = [fn for fn in required_field_names if fn not in current_attrs]
        if missing:
            gaps[spec.logical_name] = missing

    if gaps:
        lines = []
        for entity, fields in gaps.items():
            lines.append(f"  {entity}:")
            for fn in fields:
                lines.append(f"    - {fn}")
        msg = (
            f"Campos faltantes en {len(gaps)} entidad(es):\n"
            + "\n".join(lines)
            + "\n\nSolucion: PERSISTENCE_BACKEND=dataverse python manage.py "
            + "dataverse_ensure_schema --create"
        )
        pytest.fail(msg)


# ---------------------------------------------------------------------------
# Test 3: Las 4 planillas nuevas estan completamente provisionadas
# ---------------------------------------------------------------------------

def test_new_planilla_tables_are_fully_provisioned(dv_client):
    """
    Foco especifico en las 4 planillas de control de calidad recientemente agregadas.
    Valida accesibilidad OData + todos los campos.

    Si falla, indica el comando exacto para crear la tabla faltante.
    """
    from infrastructure.dataverse.client import DataverseAPIError

    failures: list[str] = []

    for spec in NEW_ENTITIES:
        # Verificar accesibilidad OData
        try:
            dv_client._request(
                "GET",
                spec.entity_set_name,
                params={"$top": "1", "$select": "createdon"},
            )
        except DataverseAPIError as exc:
            failures.append(
                f"ENTITY MISSING: {spec.entity_set_name} — {exc}\n"
                f"  → Crear con: python manage.py dataverse_ensure_schema "
                f"--create --table {spec.logical_name}"
            )
            continue  # Sin entidad no podemos verificar campos

        # Verificar campos
        current_attrs = _get_entity_attr_names(dv_client, spec.logical_name)
        required = [
            f.logical_name
            for f in spec.fields
            if not f.logical_name.startswith("_")
        ]
        missing = [fn for fn in required if fn not in current_attrs]
        if missing:
            failures.append(
                f"MISSING FIELDS in {spec.logical_name} ({len(missing)} campos):\n"
                + "\n".join(f"    - {fn}" for fn in missing)
                + f"\n  → Crear con: python manage.py dataverse_ensure_schema "
                f"--create --table {spec.logical_name}"
            )

    if failures:
        pytest.fail(
            f"{len(failures)} planilla(s) con gaps:\n\n"
            + "\n\n".join(failures)
        )


# ---------------------------------------------------------------------------
# Test 4: Campos JSON (Memo) para almacenamiento de datos estructurados
# ---------------------------------------------------------------------------

def test_json_memo_fields_exist(dv_client):
    """
    Verifica que los campos Memo usados para almacenar JSON existan.
    Son criticos para el funcionamiento de planillas con datos complejos.
    """
    json_fields = [
        ("crf21_planilla_desv_calibre", "crf21_calibres_grupos"),
        ("crf21_planilla_desv_semillas", "crf21_frutas_data"),
        ("crf21_planilla_calidad_camara", "crf21_mediciones"),
    ]

    missing: list[str] = []
    for entity_logical, field_logical in json_fields:
        attrs = _get_entity_attr_names(dv_client, entity_logical)
        if attrs and field_logical not in attrs:
            missing.append(f"{entity_logical}.{field_logical}")

    if missing:
        pytest.fail(
            "Campos JSON (Memo) faltantes — sin ellos las planillas no pueden "
            "almacenar datos estructurados:\n"
            + "\n".join(f"  - {m}" for m in missing)
        )
