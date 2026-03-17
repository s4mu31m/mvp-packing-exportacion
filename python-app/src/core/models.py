from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditSourceModel(TimeStampedModel):
    source_system = models.CharField(
        max_length=50,
        blank=True,
        default="local",
        help_text="Sistema origen del registro: local, dataverse, import, api, etc."
    )
    source_event_id = models.CharField(
        max_length=120,
        blank=True,
        default="",
        db_index=True,
        help_text="Identificador externo del evento o registro origen."
    )
    operator_code = models.CharField(
        max_length=50,
        blank=True,
        default="",
        db_index=True,
        help_text="Código del operador responsable de la acción."
    )

    class Meta:
        abstract = True