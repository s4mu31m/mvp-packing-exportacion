"""
Management command: dataverse_ensure_schema

Verifica y/o crea el esquema Dataverse requerido para el funcionamiento
completo de la app (20 entidades).

Uso:
    # Solo verificar (exit 1 si hay gaps)
    python manage.py dataverse_ensure_schema --check-only

    # Verificar y crear lo que falte
    python manage.py dataverse_ensure_schema --create

    # Apuntar a una tabla especifica
    python manage.py dataverse_ensure_schema --check-only --table crf21_planilla_desv_calibre
    python manage.py dataverse_ensure_schema --create --table crf21_planilla_calidad_camara

Requiere que el App Registration tenga rol 'System Customizer' o
'System Administrator' en el entorno Dataverse.

Timeout extendido a 180s porque la Metadata API de Dataverse puede tardar
entre 30 y 120 segundos para crear una entidad.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Optional

from django.core.management.base import BaseCommand

from infrastructure.dataverse.client import DataverseClient, DataverseAPIError
from infrastructure.dataverse.schema_definition import (
    REQUIRED_SCHEMA,
    EntitySpec,
    FieldSpec,
    LOGICAL_NAME_INDEX,
)

LANG_ES = 3082  # Espanol


# ---------------------------------------------------------------------------
# Helpers de construccion de payload Metadata API
# ---------------------------------------------------------------------------

def _label(text: str) -> dict:
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.Label",
        "LocalizedLabels": [{
            "@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
            "Label": text,
            "LanguageCode": LANG_ES,
        }],
        "UserLocalizedLabel": {
            "@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
            "Label": text,
            "LanguageCode": LANG_ES,
        },
    }


def _req_level(value: str = "None") -> dict:
    return {
        "Value": value,
        "CanBeChanged": True,
        "ManagedPropertyLogicalName": "canmodifyrequirementlevelsettings",
    }


# ---------------------------------------------------------------------------
# Operaciones de verificacion (solo lectura)
# ---------------------------------------------------------------------------

def entity_exists(client: DataverseClient, logical_name: str) -> bool:
    """Retorna True si la entidad existe en Dataverse."""
    try:
        client._request(
            "GET",
            f"EntityDefinitions(LogicalName='{logical_name}')",
            params={"$select": "LogicalName"},
        )
        return True
    except DataverseAPIError as exc:
        err = str(exc)
        if "404" in err or "0x80040217" in err or "Does Not Exist" in err:
            return False
        raise


def get_entity_attribute_names(client: DataverseClient, logical_name: str) -> set[str]:
    """
    Retorna el conjunto de nombres logicos de todos los atributos de la entidad.
    Retorna set() si la entidad no existe.
    """
    try:
        result = client._request(
            "GET",
            f"EntityDefinitions(LogicalName='{logical_name}')/Attributes",
            params={"$select": "LogicalName"},
        )
        return {attr["LogicalName"] for attr in (result or {}).get("value", [])}
    except DataverseAPIError as exc:
        err = str(exc)
        if "404" in err or "0x80040217" in err or "Does Not Exist" in err:
            return set()
        raise


@dataclass
class EntityGapReport:
    logical_name: str
    entity_exists: bool
    missing_fields: list[str] = field(default_factory=list)
    present_fields: list[str] = field(default_factory=list)

    @property
    def has_gaps(self) -> bool:
        return not self.entity_exists or bool(self.missing_fields)


def check_schema(
    client: DataverseClient,
    specs: list[EntitySpec],
) -> dict[str, EntityGapReport]:
    """
    Verifica el schema Dataverse contra las specs dadas.
    Retorna un dict logical_name → EntityGapReport.
    """
    reports: dict[str, EntityGapReport] = {}

    for spec in specs:
        exists = entity_exists(client, spec.logical_name)
        report = EntityGapReport(logical_name=spec.logical_name, entity_exists=exists)

        if exists:
            current_attrs = get_entity_attribute_names(client, spec.logical_name)
            for f_spec in spec.fields:
                # Los campos Lookup se verifican por el nombre del atributo lookup
                # (no por el campo de lectura _*_value que es un OData alias)
                if f_spec.logical_name.startswith("_"):
                    continue
                if f_spec.logical_name in current_attrs:
                    report.present_fields.append(f_spec.logical_name)
                else:
                    report.missing_fields.append(f_spec.logical_name)

        reports[spec.logical_name] = report

    return reports


# ---------------------------------------------------------------------------
# Operaciones de creacion
# ---------------------------------------------------------------------------

def create_entity(client: DataverseClient, spec: EntitySpec) -> None:
    """Crea la entidad (tabla) en Dataverse con su atributo primario."""
    payload = {
        "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
        "SchemaName": spec.schema_name,
        "DisplayName": _label(spec.display_label),
        "DisplayCollectionName": _label(spec.display_collection_label),
        "Description": _label(f"Entidad {spec.display_label} — CaliPro packing exportacion"),
        "OwnershipType": "UserOwned",
        "HasActivities": False,
        "HasNotes": False,
        "IsActivity": False,
        "Attributes": [{
            "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
            "SchemaName": "crf21_nombre",
            "IsPrimaryName": True,
            "DisplayName": _label("Nombre"),
            "Description": _label("Nombre auto-generado del registro"),
            "RequiredLevel": _req_level("None"),
            "MaxLength": 100,
        }],
    }
    client._request("POST", "EntityDefinitions", json=payload)


def create_field(
    client: DataverseClient,
    entity_logical: str,
    spec: FieldSpec,
) -> None:
    """
    Crea un campo (Attribute) en la entidad.
    Para Lookup usa create_lookup_relationship en su lugar.
    Captura 'already exists' silenciosamente.
    """
    base = f"EntityDefinitions(LogicalName='{entity_logical}')/Attributes"

    if spec.field_type == "String":
        payload = {
            "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
            "SchemaName": spec.schema_name,
            "LogicalName": spec.logical_name,
            "DisplayName": _label(spec.display_label),
            "RequiredLevel": _req_level("None"),
            "MaxLength": spec.max_length,
        }
    elif spec.field_type == "Memo":
        payload = {
            "@odata.type": "Microsoft.Dynamics.CRM.MemoAttributeMetadata",
            "SchemaName": spec.schema_name,
            "LogicalName": spec.logical_name,
            "DisplayName": _label(spec.display_label),
            "RequiredLevel": _req_level("None"),
            "MaxLength": spec.max_length_memo,
        }
    elif spec.field_type == "Decimal":
        payload = {
            "@odata.type": "Microsoft.Dynamics.CRM.DecimalAttributeMetadata",
            "SchemaName": spec.schema_name,
            "LogicalName": spec.logical_name,
            "DisplayName": _label(spec.display_label),
            "RequiredLevel": _req_level("None"),
            "Precision": spec.precision,
            "MinValue": spec.min_value_decimal,
            "MaxValue": spec.max_value_decimal,
        }
    elif spec.field_type == "Integer":
        payload = {
            "@odata.type": "Microsoft.Dynamics.CRM.IntegerAttributeMetadata",
            "SchemaName": spec.schema_name,
            "LogicalName": spec.logical_name,
            "DisplayName": _label(spec.display_label),
            "RequiredLevel": _req_level("None"),
            "Format": "None",
            "MinValue": spec.min_value_int,
            "MaxValue": spec.max_value_int,
        }
    elif spec.field_type == "Boolean":
        payload = {
            "@odata.type": "Microsoft.Dynamics.CRM.BooleanAttributeMetadata",
            "SchemaName": spec.schema_name,
            "LogicalName": spec.logical_name,
            "DisplayName": _label(spec.display_label),
            "RequiredLevel": _req_level("None"),
            "OptionSet": {
                "@odata.type": "Microsoft.Dynamics.CRM.BooleanOptionSetMetadata",
                "TrueOption": {"Value": 1, "Label": _label("Si")},
                "FalseOption": {"Value": 0, "Label": _label("No")},
            },
        }
    elif spec.field_type == "DateTime":
        payload = {
            "@odata.type": "Microsoft.Dynamics.CRM.DateTimeAttributeMetadata",
            "SchemaName": spec.schema_name,
            "LogicalName": spec.logical_name,
            "DisplayName": _label(spec.display_label),
            "RequiredLevel": _req_level("None"),
            "Format": "DateOnly",
            "DateTimeBehavior": {"Value": "DateOnly"},
        }
    else:
        raise ValueError(f"Tipo de campo no soportado: {spec.field_type}")

    try:
        client._request("POST", base, json=payload)
    except DataverseAPIError as exc:
        err = str(exc)
        if "already exists" in err.lower() or "0x80048418" in err:
            return  # Ya existe, silencioso
        raise


def create_lookup_relationship(
    client: DataverseClient,
    entity_logical: str,
    spec: FieldSpec,
) -> None:
    """
    Crea un campo Lookup via RelationshipDefinitions (OneToMany en la entidad referenciada).
    Captura 'already exists' silenciosamente.
    """
    payload = {
        "@odata.type": "Microsoft.Dynamics.CRM.OneToManyRelationshipMetadata",
        "SchemaName": spec.lookup_relationship_schema,
        "ReferencedEntity": spec.lookup_target_entity,
        "ReferencingEntity": entity_logical,
        "Lookup": {
            "@odata.type": "Microsoft.Dynamics.CRM.LookupAttributeMetadata",
            "SchemaName": spec.schema_name,
            "DisplayName": _label(spec.display_label),
            "RequiredLevel": _req_level("None"),
        },
        "AssociatedMenuConfiguration": {
            "Behavior": "UseCollectionName",
            "Group": "Details",
            "Label": _label(spec.display_label),
            "Order": 10000,
        },
        "CascadeConfiguration": {
            "Assign": "NoCascade",
            "Delete": "RemoveLink",
            "Merge": "NoCascade",
            "Reparent": "NoCascade",
            "Share": "NoCascade",
            "Unshare": "NoCascade",
        },
    }
    try:
        client._request("POST", "RelationshipDefinitions", json=payload)
    except DataverseAPIError as exc:
        err = str(exc)
        if "already exists" in err.lower() or "0x80048418" in err:
            return
        raise


def publish_entity(client: DataverseClient, logical_name: str) -> None:
    """
    Publica los cambios de la entidad en Dataverse.
    Fallo silencioso (WARNING) porque en entornos managed puede no ser necesario.
    """
    xml = (
        "<importexportxml><entities>"
        f"<entity>{logical_name}</entity>"
        "</entities></importexportxml>"
    )
    client._request("POST", "PublishXml", json={"ParameterXml": xml})


# ---------------------------------------------------------------------------
# Management Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = "Verifica y/o crea el esquema Dataverse requerido (20 entidades)"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--check-only",
            action="store_true",
            help="Solo verificar: imprime reporte y retorna exit 1 si hay gaps.",
        )
        group.add_argument(
            "--create",
            action="store_true",
            help="Verificar y crear tablas/campos faltantes en Dataverse.",
        )
        parser.add_argument(
            "--table",
            type=str,
            default=None,
            metavar="LOGICAL_NAME",
            help=(
                "Limitar la operacion a una sola entidad (por logical_name). "
                "Ej: --table crf21_planilla_desv_calibre"
            ),
        )

    def handle(self, *args, **options):
        check_only: bool = options["check_only"]
        do_create: bool = options["create"]
        table_filter: Optional[str] = options.get("table")

        # Seleccionar specs a procesar
        if table_filter:
            if table_filter not in LOGICAL_NAME_INDEX:
                self.stderr.write(
                    self.style.ERROR(
                        f"Entidad '{table_filter}' no encontrada en REQUIRED_SCHEMA. "
                        f"Nombres validos: {', '.join(sorted(LOGICAL_NAME_INDEX))}"
                    )
                )
                sys.exit(1)
            specs = [LOGICAL_NAME_INDEX[table_filter]]
        else:
            specs = REQUIRED_SCHEMA

        # Construir cliente con timeout extendido (creacion de entidad puede tardar 60-120s)
        try:
            client = DataverseClient(timeout=180)
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"No se pudo crear DataverseClient: {exc}"))
            sys.exit(1)

        self.stdout.write(f"\nVerificando {len(specs)} entidad(es) en Dataverse...")
        self.stdout.write("-" * 60)

        # Verificar schema actual
        try:
            reports = check_schema(client, specs)
        except DataverseAPIError as exc:
            self.stderr.write(self.style.ERROR(f"Error accediendo a Metadata API: {exc}"))
            sys.exit(1)

        # Imprimir reporte
        total_gaps = 0
        for logical_name, report in reports.items():
            if not report.has_gaps:
                self.stdout.write(self.style.SUCCESS(f"  OK  {logical_name}"))
            else:
                total_gaps += 1
                if not report.entity_exists:
                    self.stdout.write(
                        self.style.ERROR(f"  MISSING ENTITY  {logical_name}")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  MISSING FIELDS  {logical_name} "
                            f"({len(report.missing_fields)} campos)"
                        )
                    )
                    for fname in report.missing_fields:
                        self.stdout.write(f"      - {fname}")

        self.stdout.write("-" * 60)
        self.stdout.write(
            f"Resultado: {len(reports) - total_gaps}/{len(reports)} entidades OK, "
            f"{total_gaps} con gaps."
        )

        if check_only:
            if total_gaps > 0:
                self.stderr.write(
                    self.style.ERROR(
                        f"\n{total_gaps} gap(s) encontrados. "
                        f"Ejecute con --create para crearlos."
                    )
                )
                sys.exit(1)
            else:
                self.stdout.write(self.style.SUCCESS("\nSchema completo. Sin gaps."))
            return

        # --create: crear lo que falta
        if total_gaps == 0:
            self.stdout.write(self.style.SUCCESS("\nSchema ya completo. Nada que crear."))
            return

        self.stdout.write(f"\nCreando elementos faltantes...")
        self.stdout.write("-" * 60)

        created_entities = 0
        created_fields = 0
        warnings = 0

        for logical_name, report in reports.items():
            if not report.has_gaps:
                continue

            spec = LOGICAL_NAME_INDEX[logical_name]

            # 1. Crear entidad si no existe
            if not report.entity_exists:
                self.stdout.write(f"  Creando entidad {logical_name}...")
                try:
                    create_entity(client, spec)
                    self.stdout.write(self.style.SUCCESS(f"    Entidad {logical_name} creada OK"))
                    created_entities += 1
                    # Ahora todos sus campos son "faltantes"
                    report.missing_fields = [
                        f.logical_name for f in spec.fields
                        if not f.logical_name.startswith("_")
                    ]
                except DataverseAPIError as exc:
                    err = str(exc)
                    if "already exists" in err.lower() or "0x80048418" in err:
                        self.stdout.write(
                            self.style.WARNING(f"    Entidad {logical_name} ya existe (OK)")
                        )
                    else:
                        self.stderr.write(
                            self.style.ERROR(f"    ERROR creando entidad {logical_name}: {exc}")
                        )
                        self.stderr.write("    Causas posibles:")
                        self.stderr.write("      - App Registration sin rol 'System Customizer'")
                        self.stderr.write("      - Publisher prefix 'crf21_' no configurado")
                        self.stderr.write("      - Cuota de entidades custom alcanzada")
                        warnings += 1
                        continue

            # 2. Crear campos faltantes
            fields_by_name = {f.logical_name: f for f in spec.fields}
            for field_name in report.missing_fields:
                if field_name.startswith("_"):
                    continue
                f_spec = fields_by_name.get(field_name)
                if not f_spec:
                    continue

                try:
                    if f_spec.field_type == "Lookup":
                        if not f_spec.lookup_target_entity or not f_spec.lookup_relationship_schema:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"    SKIP lookup {field_name}: "
                                    f"faltan lookup_target_entity / lookup_relationship_schema"
                                )
                            )
                            warnings += 1
                            continue
                        self.stdout.write(f"    Creando lookup {field_name}...")
                        create_lookup_relationship(client, logical_name, f_spec)
                    else:
                        self.stdout.write(f"    Creando campo {field_name}...")
                        create_field(client, logical_name, f_spec)
                    self.stdout.write(self.style.SUCCESS(f"    {field_name} OK"))
                    created_fields += 1
                except DataverseAPIError as exc:
                    self.stderr.write(
                        self.style.WARNING(f"    WARN {field_name}: {exc}")
                    )
                    warnings += 1

            # 3. Publicar entidad
            self.stdout.write(f"  Publicando {logical_name}...")
            try:
                publish_entity(client, logical_name)
                self.stdout.write(self.style.SUCCESS(f"  Publicacion de {logical_name} OK"))
            except DataverseAPIError as exc:
                self.stdout.write(
                    self.style.WARNING(
                        f"  WARN publicacion {logical_name}: {exc} "
                        f"(puede requerir publicacion manual desde Power Apps)"
                    )
                )
                warnings += 1

        self.stdout.write("-" * 60)
        self.stdout.write(
            self.style.SUCCESS(
                f"Listo: {created_entities} entidades creadas, "
                f"{created_fields} campos creados, "
                f"{warnings} advertencias."
            )
        )
        if warnings > 0:
            self.stdout.write(
                self.style.WARNING(
                    "Ejecute --check-only para verificar el estado final."
                )
            )
