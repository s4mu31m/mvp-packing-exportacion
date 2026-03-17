from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from core.models import AuditSourceModel


class TipoEvento(models.TextChoices):
    BIN_REGISTRADO = "BIN_REGISTRADO", "Bin registrado"
    LOTE_CREADO = "LOTE_CREADO", "Lote creado"
    BIN_ASIGNADO_LOTE = "BIN_ASIGNADO_LOTE", "Bin asignado a lote"
    LOTE_INGRESO_CAMARA = "LOTE_INGRESO_CAMARA", "Lote ingresa a cámara"
    LOTE_SALIDA_CAMARA = "LOTE_SALIDA_CAMARA", "Lote sale de cámara"
    PALLET_CREADO = "PALLET_CREADO", "Pallet creado"
    LOTE_ASIGNADO_PALLET = "LOTE_ASIGNADO_PALLET", "Lote asignado a pallet"
    ETAPA_REGISTRADA = "ETAPA_REGISTRADA", "Etapa registrada"


class MaestroOperacionalModel(AuditSourceModel):
    temporada = models.CharField(max_length=20, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    dataverse_id = models.CharField(
        max_length=120,
        null=True,
        blank=True,
        db_index=True,
        help_text="GUID o identificador equivalente en Dataverse."
    )

    class Meta:
        abstract = True


class Bin(MaestroOperacionalModel):
    bin_code = models.CharField(max_length=50)

    class Meta:
        db_table = "operaciones_bin"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["temporada", "bin_code"],
                name="uq_bin_temporada_code",
            ),
        ]
        indexes = [
            models.Index(fields=["temporada", "bin_code"],
                         name="ix_bin_temp_code"),
        ]

    def __str__(self):
        return f"{self.temporada} - {self.bin_code}"


class Lote(MaestroOperacionalModel):
    lote_code = models.CharField(max_length=50)

    class Meta:
        db_table = "operaciones_lote"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["temporada", "lote_code"],
                name="uq_lote_temporada_code",
            ),
        ]
        indexes = [
            models.Index(fields=["temporada", "lote_code"],
                         name="ix_lote_temp_code"),
        ]

    def __str__(self):
        return f"{self.temporada} - {self.lote_code}"


class Pallet(MaestroOperacionalModel):
    pallet_code = models.CharField(max_length=50)

    class Meta:
        db_table = "operaciones_pallet"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["temporada", "pallet_code"],
                name="uq_pallet_temporada_code",
            ),
        ]
        indexes = [
            models.Index(fields=["temporada", "pallet_code"],
                         name="ix_pallet_temp_code"),
        ]

    def __str__(self):
        return f"{self.temporada} - {self.pallet_code}"


class BinLote(AuditSourceModel):
    bin = models.ForeignKey(
        Bin,
        on_delete=models.PROTECT,
        related_name="bin_lotes",
    )
    lote = models.ForeignKey(
        Lote,
        on_delete=models.PROTECT,
        related_name="bin_lotes",
    )

    class Meta:
        db_table = "operaciones_bin_lote"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["bin", "lote"],
                name="uq_bin_lote_pair",
            ),
        ]
        indexes = [
            models.Index(fields=["bin", "lote"], name="ix_bin_lote_pair"),
            models.Index(fields=["lote"], name="ix_bin_lote_lote"),
        ]

    def __str__(self):
        return f"{self.bin} -> {self.lote}"


class PalletLote(AuditSourceModel):
    pallet = models.ForeignKey(
        Pallet,
        on_delete=models.PROTECT,
        related_name="pallet_lotes",
    )
    lote = models.ForeignKey(
        Lote,
        on_delete=models.PROTECT,
        related_name="pallet_lotes",
    )

    class Meta:
        db_table = "operaciones_pallet_lote"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["pallet", "lote"],
                name="uq_pallet_lote_pair",
            ),
        ]
        indexes = [
            models.Index(fields=["pallet", "lote"],
                         name="ix_pallet_lote_pair"),
            models.Index(fields=["lote"], name="ix_pallet_lote_lote"),
        ]

    def __str__(self):
        return f"{self.lote} -> {self.pallet}"


class RegistroEtapa(AuditSourceModel):
    temporada = models.CharField(max_length=20, db_index=True)
    event_key = models.CharField(
        max_length=120,
        unique=True,
        db_index=True,
        help_text="Clave idempotente única del evento."
    )
    tipo_evento = models.CharField(
        max_length=40,
        choices=TipoEvento.choices,
        db_index=True,
    )

    bin = models.ForeignKey(
        Bin,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="registros_etapa",
    )
    lote = models.ForeignKey(
        Lote,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="registros_etapa",
    )
    pallet = models.ForeignKey(
        Pallet,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="registros_etapa",
    )

    occurred_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Momento real del evento operacional."
    )
    payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Metadatos flexibles del evento."
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "operaciones_registro_etapa"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(bin__isnull=False) |
                    Q(lote__isnull=False) |
                    Q(pallet__isnull=False)
                ),
                name="ck_registro_etapa_target_present",
            ),
        ]
        indexes = [
            models.Index(fields=["temporada", "tipo_evento"],
                         name="ix_reg_temp_tipo"),
            models.Index(fields=["occurred_at"], name="ix_reg_occurred_at"),
            models.Index(fields=["bin"], name="ix_reg_bin"),
            models.Index(fields=["lote"], name="ix_reg_lote"),
            models.Index(fields=["pallet"], name="ix_reg_pallet"),
        ]

    def clean(self):
        if not any([self.bin_id, self.lote_id, self.pallet_id]):
            raise ValidationError(
                "RegistroEtapa debe referenciar al menos un Bin, Lote o Pallet."
            )

    def __str__(self):
        return f"{self.tipo_evento} - {self.event_key}"
