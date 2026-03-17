from django.core.management.base import BaseCommand

from infrastructure.dataverse.client import DataverseClient


class Command(BaseCommand):
    help = "Valida autenticación y conectividad básica con Dataverse"

    def handle(self, *args, **options):
        client = DataverseClient()

        whoami = client.whoami()

        self.stdout.write(self.style.SUCCESS("Conexión Dataverse OK"))
        self.stdout.write(f"BusinessUnitId: {whoami.get('BusinessUnitId')}")
        self.stdout.write(f"OrganizationId: {whoami.get('OrganizationId')}")
        self.stdout.write(f"UserId: {whoami.get('UserId')}")