"""
Management command: dataverse_add_timestamp_field

Agrega el campo crf21_ultimo_cambio_estado_at (DateTime, TimeZoneIndependent)
a las tablas crf21_lote_plantas y crf21_pallets en Dataverse.

Este campo es la fuente de verdad para la fecha del ultimo cambio real de etapa
en el flujo operativo. Se requiere una vez por entorno Dataverse.

Uso:
    # Verificar si los campos ya existen
    python manage.py dataverse_add_timestamp_field --check-only

    # Crear los campos (idempotente — no falla si ya existen)
    python manage.py dataverse_add_timestamp_field --create

Requiere que el App Registration tenga rol 'System Customizer' o
'System Administrator' en el entorno Dataverse.

Referencia Metadata API:
    https://learn.microsoft.com/en-us/power-apps/developer/data-platform/webapi/create-update-column-definitions-using-web-api
"""
from __future__ import annotations

import sys

from django.core.management.base import BaseCommand

from infrastructure.dataverse.client import DataverseClient, DataverseAPIError

LANG_ES = 3082  # Espanol

# Entidades objetivo
TARGETS = [
    {
        "entity_logical": "crf21_lote_planta",
        "entity_set":     "crf21_lote_plantas",
        "display_name":   "Lote Planta",
    },
    {
        "entity_logical": "crf21_pallet",
        "entity_set":     "crf21_pallets",
        "display_name":   "Pallet",
    },
]

FIELD_LOGICAL = "crf21_ultimo_cambio_estado_at"
FIELD_SCHEMA  = "crf21_UltimoCambioEstadoAt"
FIELD_LABEL   = "Ultimo Cambio Estado"


# ---------------------------------------------------------------------------
# Helpers
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


def _req_level_none() -> dict:
    return {
        "Value": "None",
        "CanBeChanged": True,
        "ManagedPropertyLogicalName": "canmodifyrequirementlevelsettings",
    }


def _field_payload() -> dict:
    """
    Payload Metadata API para DateTimeAttributeMetadata.

    Format:           DateAndTime  — almacena fecha + hora completa
    DateTimeBehavior: TimeZoneIndependent — el valor se almacena tal cual (UTC)
                      sin conversion por timezone del usuario. Ideal para timestamps.
    """
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.DateTimeAttributeMetadata",
        "SchemaName":       FIELD_SCHEMA,
        "LogicalName":      FIELD_LOGICAL,
        "DisplayName":      _label(FIELD_LABEL),
        "Description":      _label(
            "Timestamp UTC del ultimo cambio real de etapa operativa. "
            "Fuente oficial para dashboard, consulta jefatura, filtros y exportaciones."
        ),
        "RequiredLevel":    _req_level_none(),
        "Format":           "DateAndTime",
        "DateTimeBehavior": {"Value": "TimeZoneIndependent"},
    }


def field_exists(client: DataverseClient, entity_logical: str) -> bool:
    """Retorna True si crf21_ultimo_cambio_estado_at ya existe en la entidad."""
    try:
        result = client._request(
            "GET",
            f"EntityDefinitions(LogicalName='{entity_logical}')/Attributes",
            params={"$select": "LogicalName", "$filter": f"LogicalName eq '{FIELD_LOGICAL}'"},
        )
        return bool((result or {}).get("value"))
    except DataverseAPIError as exc:
        err = str(exc)
        if "404" in err or "Does Not Exist" in err:
            return False
        raise


def create_field(client: DataverseClient, entity_logical: str) -> None:
    """
    Crea crf21_ultimo_cambio_estado_at en la entidad.
    Silencioso si ya existe (idempotente).
    """
    base = f"EntityDefinitions(LogicalName='{entity_logical}')/Attributes"
    try:
        client._request("POST", base, json=_field_payload())
    except DataverseAPIError as exc:
        err = str(exc)
        if "already exists" in err.lower() or "0x80048418" in err:
            return  # Ya existe — OK
        raise


def publish_entity(client: DataverseClient, entity_logical: str) -> None:
    """Publica los cambios para que el campo quede disponible de inmediato."""
    xml = (
        "<importexportxml><entities>"
        f"<entity>{entity_logical}</entity>"
        "</entities></importexportxml>"
    )
    try:
        client._request("POST", "PublishXml", json={"ParameterXml": xml})
    except DataverseAPIError:
        pass  # Fallo de publicacion no es critico


# ---------------------------------------------------------------------------
# Management Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = (
        "Agrega crf21_ultimo_cambio_estado_at (DateTime/TimeZoneIndependent) "
        "a crf21_lote_plantas y crf21_pallets en Dataverse."
    )

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--check-only",
            action="store_true",
            help="Solo verificar si el campo existe en ambas tablas (no crea nada).",
        )
        group.add_argument(
            "--create",
            action="store_true",
            help="Crear el campo en las tablas donde falte (idempotente).",
        )

    def handle(self, *args, **options):
        check_only: bool = options["check_only"]
        do_create:  bool = options["create"]

        client = DataverseClient(timeout=120)

        # --- Verificar conectividad ---
        try:
            who = client.whoami()
            user_id = who.get("UserId", "?")
            self.stdout.write(f"Conectado a Dataverse (UserId: {user_id})")
        except DataverseAPIError as exc:
            self.stderr.write(self.style.ERROR(f"No se pudo conectar a Dataverse: {exc}"))
            sys.exit(1)

        self.stdout.write(f"\nCampo objetivo: {FIELD_LOGICAL}")
        self.stdout.write(f"Tipo:           DateAndTime / TimeZoneIndependent\n")

        any_missing = False

        for target in TARGETS:
            entity = target["entity_logical"]
            label  = target["display_name"]

            self.stdout.write(f"[{label}] {entity} ...", ending=" ")

            exists = field_exists(client, entity)

            if exists:
                self.stdout.write(self.style.SUCCESS("campo ya existe — OK"))
                continue

            any_missing = True
            self.stdout.write(self.style.WARNING("campo FALTANTE"))

            if check_only:
                continue

            # --- Crear campo ---
            self.stdout.write(f"  → Creando {FIELD_LOGICAL} en {entity} ...")
            try:
                create_field(client, entity)
                self.stdout.write(f"  → Publicando {entity} ...")
                publish_entity(client, entity)
                self.stdout.write(
                    self.style.SUCCESS(f"  → Campo creado y publicado en {entity}")
                )
            except DataverseAPIError as exc:
                self.stderr.write(
                    self.style.ERROR(f"  ERROR creando campo en {entity}: {exc}")
                )
                sys.exit(1)

        # --- Resumen ---
        self.stdout.write("")
        if check_only:
            if any_missing:
                self.stderr.write(
                    self.style.WARNING(
                        "Hay campos faltantes. Ejecuta con --create para crearlos."
                    )
                )
                sys.exit(1)
            else:
                self.stdout.write(
                    self.style.SUCCESS("Verificacion OK — campo presente en ambas tablas.")
                )
        else:
            if any_missing:
                self.stdout.write(
                    self.style.SUCCESS("Campos creados correctamente.")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        "Nada que hacer — campo ya existia en ambas tablas."
                    )
                )
