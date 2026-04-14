from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from core.models import AuditSourceModel


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------

class TipoEvento(models.TextChoices):
    BIN_REGISTRADO           = "BIN_REGISTRADO",           "Bin registrado"
    LOTE_CREADO              = "LOTE_CREADO",              "Lote creado"
    PALLET_CREADO            = "PALLET_CREADO",            "Pallet creado"
    LOTE_ASIGNADO_PALLET     = "LOTE_ASIGNADO_PALLET",     "Lote asignado a pallet"
    PALLET_CERRADO           = "PALLET_CERRADO",           "Pallet cerrado"
    PESAJE                   = "PESAJE",                   "Pesaje y asignacion de lote"
    DESVERDIZADO_INGRESO     = "DESVERDIZADO_INGRESO",     "Ingreso a desverdizado"
    DESVERDIZADO_SALIDA      = "DESVERDIZADO_SALIDA",      "Salida de desverdizado"
    CAMARA_MANTENCION        = "CAMARA_MANTENCION",        "Ingreso a camara de mantencion"
    CAMARA_MANTENCION_SALIDA = "CAMARA_MANTENCION_SALIDA", "Salida de camara de mantencion"
    PACKING_PROCESO          = "PACKING_PROCESO",          "Proceso de packing"
    CONTROL_CALIDAD          = "CONTROL_CALIDAD",          "Control de calidad"
    INGRESO_PACKING          = "INGRESO_PACKING",          "Ingreso a proceso de packing"
    CAMARA_FRIO_INGRESO      = "CAMARA_FRIO_INGRESO",      "Ingreso a camara de frio"
    CONTROL_TEMPERATURA      = "CONTROL_TEMPERATURA",      "Control de temperatura en camara"
    CALIDAD_DESVERDIZADO     = "CALIDAD_DESVERDIZADO",     "Control de calidad posterior a desverdizado"
    CALIDAD_PALLET           = "CALIDAD_PALLET",           "Control de calidad posterior a pallet"


class LotePlantaEstado(models.TextChoices):
    ABIERTO    = "abierto",    "Abierto"
    EN_PROCESO = "en_proceso", "En proceso"
    CERRADO    = "cerrado",    "Cerrado"
    FINALIZADO = "finalizado", "Finalizado"
    ANULADO    = "anulado",    "Anulado"


class DisponibilidadCamara(models.TextChoices):
    """
    Semántica de tres estados para disponibilidad_camara_desverdizado.
    En Dataverse se implementa como Choice con tres opciones.
    Null en este campo equivale a 'no_aplica' (cuando requiere_desverdizado=False).
    """
    DISPONIBLE    = "disponible",    "Disponible"
    NO_DISPONIBLE = "no_disponible", "No disponible"
    NO_APLICA     = "no_aplica",     "No aplica"


class AOR(models.TextChoices):
    APROBADO  = "aprobado",  "Aprobado"
    OBJETADO  = "objetado",  "Objetado"
    RECHAZADO = "rechazado", "Rechazado"


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Bin
# ---------------------------------------------------------------------------

class Bin(MaestroOperacionalModel):
    """
    Unidad atomica del proceso. Llega preconstruido desde el modulo campo
    o se crea en recepcion. Identificador interno: id_bin (YYYYMMDD-0001).
    """
    # Identificacion interna
    id_bin = models.CharField(
        max_length=20, blank=True, default="",
        help_text="Codigo interno generado: YYYYMMDD-0001"
    )
    bin_code = models.CharField(
        max_length=50,
        help_text="Codigo de barras del bin (del modulo campo o formado en recepcion)"
    )
    contador_incremental = models.IntegerField(default=0)

    # Origen
    fecha_cosecha = models.DateField(null=True, blank=True)
    codigo_productor = models.CharField(max_length=50, blank=True, default="")
    nombre_productor = models.CharField(max_length=100, blank=True, default="")
    codigo_sag_csg = models.CharField(max_length=50, blank=True, default="")
    codigo_sag_csp = models.CharField(max_length=50, blank=True, default="")
    codigo_sdp = models.CharField(max_length=50, blank=True, default="")
    tipo_cultivo = models.CharField(max_length=50, blank=True, default="")
    variedad_fruta = models.CharField(max_length=100, blank=True, default="")
    numero_cuartel = models.CharField(max_length=20, blank=True, default="")
    nombre_cuartel = models.CharField(max_length=100, blank=True, default="")
    predio = models.CharField(max_length=100, blank=True, default="")
    sector = models.CharField(max_length=50, blank=True, default="")
    lote_productor = models.CharField(max_length=50, blank=True, default="")

    # Estado en recepcion
    color = models.CharField(max_length=30, blank=True, default="")
    estado_fisico = models.CharField(max_length=50, blank=True, default="")
    a_o_r = models.CharField(
        max_length=10,
        choices=AOR.choices,
        blank=True, default=""
    )
    n_guia = models.CharField(max_length=30, blank=True, default="")
    transporte = models.CharField(max_length=50, blank=True, default="")
    capataz = models.CharField(max_length=100, blank=True, default="")
    codigo_contratista = models.CharField(max_length=50, blank=True, default="")
    nombre_contratista = models.CharField(max_length=100, blank=True, default="")

    # Recepcion
    hora_recepcion = models.CharField(max_length=5, blank=True, default="",
        help_text="Formato HH:mm")
    kilos_bruto_ingreso = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    kilos_neto_ingreso = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    cantidad_bins_grupo = models.IntegerField(
        null=True, blank=True,
        help_text="Cantidad de bins del mismo tipo en el grupo pesado")
    tara_bin = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Tara especifica del tipo de bin (kg)")
    n_cajas_campo = models.IntegerField(null=True, blank=True)
    observaciones = models.TextField(blank=True, default="")

    # Rol
    rol = models.CharField(max_length=50, blank=True, default="",
        help_text="Perfil del usuario que registra")

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
            models.Index(fields=["temporada", "bin_code"], name="ix_bin_temp_code"),
            models.Index(fields=["fecha_cosecha"], name="ix_bin_fecha_cosecha"),
        ]

    def clean(self):
        if (self.kilos_neto_ingreso is not None
                and self.kilos_bruto_ingreso is not None
                and self.kilos_neto_ingreso > self.kilos_bruto_ingreso):
            raise ValidationError(
                "kilos_neto_ingreso no puede superar kilos_bruto_ingreso."
            )

    def __str__(self):
        return f"{self.temporada} - {self.bin_code}"


# ---------------------------------------------------------------------------
# Lote (LotePlanta en la especificacion)
# ---------------------------------------------------------------------------

class Lote(MaestroOperacionalModel):
    """
    Agrupacion interna generada en planta. Equivale a LotePlanta en la spec.
    Codigo de negocio: YYYYMMDD-L0001.
    """
    id_lote_planta = models.CharField(
        max_length=20, blank=True, default="",
        help_text="Codigo interno generado: YYYYMMDD-L0001"
    )
    lote_code = models.CharField(max_length=50)
    contador_incremental = models.IntegerField(default=0)
    fecha_conformacion = models.DateField(null=True, blank=True)
    cantidad_bins = models.IntegerField(default=0)
    kilos_bruto_conformacion = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    kilos_neto_conformacion = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    requiere_desverdizado = models.BooleanField(default=False)
    disponibilidad_camara_desverdizado = models.CharField(
        max_length=20,
        choices=DisponibilidadCamara.choices,
        null=True, blank=True,
        help_text=(
            "Nullable. Solo aplica si requiere_desverdizado=True. "
            "Tres estados: disponible / no_disponible / no_aplica"
        )
    )
    rol = models.CharField(max_length=50, blank=True, default="",
        help_text="Perfil del usuario que registra")

    # Generacion dinamica de codigo y estado
    estado = models.CharField(
        max_length=20,
        choices=LotePlantaEstado.choices,
        default=LotePlantaEstado.ABIERTO,
        db_index=True,
        help_text="Estado del lote planta (abierto → en_proceso → cerrado → finalizado/anulado)",
    )
    temporada_codigo = models.CharField(
        max_length=20, blank=True, default="",
        db_index=True,
        help_text="Codigo de temporada operativa. Ej: 2025-2026. Derivado automaticamente si no se provee.",
    )
    correlativo_temporada = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Correlativo ascendente dentro de la temporada. No se reutiliza si el lote es anulado.",
    )

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
            models.Index(fields=["temporada", "lote_code"], name="ix_lote_temp_code"),
        ]

    def clean(self):
        if (self.kilos_neto_conformacion is not None
                and self.kilos_bruto_conformacion is not None
                and self.kilos_neto_conformacion > self.kilos_bruto_conformacion):
            raise ValidationError(
                "kilos_neto_conformacion no puede superar kilos_bruto_conformacion."
            )

    def __str__(self):
        return f"{self.temporada} - {self.lote_code}"


# ---------------------------------------------------------------------------
# Pallet
# ---------------------------------------------------------------------------

class Pallet(MaestroOperacionalModel):
    """
    Unidad de agrupacion final. Codigo de negocio: YYYYMMDD-P0001.
    """
    id_pallet = models.CharField(
        max_length=20, blank=True, default="",
        help_text="Codigo interno generado: YYYYMMDD-P0001"
    )
    pallet_code = models.CharField(max_length=50)
    contador_incremental = models.IntegerField(default=0)
    fecha = models.DateField(null=True, blank=True)
    hora = models.CharField(max_length=5, blank=True, default="",
        help_text="Formato HH:mm")
    tipo_caja = models.CharField(max_length=50, blank=True, default="")
    cajas_por_pallet = models.IntegerField(null=True, blank=True)
    peso_total_kg = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    destino_mercado = models.CharField(max_length=100, blank=True, default="")
    rol = models.CharField(max_length=50, blank=True, default="",
        help_text="Perfil del usuario que registra")

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
            models.Index(fields=["temporada", "pallet_code"], name="ix_pallet_temp_code"),
        ]

    def __str__(self):
        return f"{self.temporada} - {self.pallet_code}"


# ---------------------------------------------------------------------------
# BinLote  (relacion Bin <-> Lote/LotePlanta)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# PalletLote  (relacion Pallet <-> Lote/LotePlanta)
# ---------------------------------------------------------------------------

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
            models.UniqueConstraint(
                fields=["lote"],
                name="uq_pallet_lote_lote_unico",
            ),
        ]
        indexes = [
            models.Index(fields=["pallet", "lote"], name="ix_pallet_lote_pair"),
            models.Index(fields=["lote"], name="ix_pallet_lote_lote"),
        ]

    def __str__(self):
        return f"{self.lote} -> {self.pallet}"


# ---------------------------------------------------------------------------
# CamaraMantencion
# ---------------------------------------------------------------------------

class CamaraMantencion(AuditSourceModel):
    """
    Etapa condicional pre-desverdizado.
    Solo se crea cuando requiere_desverdizado=True y disponibilidad_camara=no_disponible.
    Un lote tiene como maximo un registro.
    """
    lote = models.OneToOneField(
        Lote,
        on_delete=models.PROTECT,
        related_name="camara_mantencion",
    )
    camara_numero = models.CharField(max_length=20, blank=True, default="")
    fecha_ingreso = models.DateField(null=True, blank=True)
    hora_ingreso = models.CharField(max_length=5, blank=True, default="",
        help_text="Formato HH:mm")
    fecha_salida = models.DateField(null=True, blank=True)
    hora_salida = models.CharField(max_length=5, blank=True, default="",
        help_text="Nullable. Restriccion: no puede ser anterior a hora_ingreso")
    temperatura_camara = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="°C")
    humedad_relativa = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="%")
    observaciones = models.TextField(blank=True, default="")
    rol = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "operaciones_camara_mantencion"
        ordering = ["-created_at"]

    def clean(self):
        if (self.fecha_salida and self.fecha_ingreso
                and self.fecha_salida < self.fecha_ingreso):
            raise ValidationError(
                "fecha_salida no puede ser anterior a fecha_ingreso en CamaraMantencion."
            )

    def __str__(self):
        return f"CamaraMantencion - {self.lote}"


# ---------------------------------------------------------------------------
# Desverdizado
# ---------------------------------------------------------------------------

class Desverdizado(AuditSourceModel):
    """
    Etapa condicional. Un lote tiene como maximo un registro.
    Solo si requiere_desverdizado=True y camara disponible.
    """
    lote = models.OneToOneField(
        Lote,
        on_delete=models.PROTECT,
        related_name="desverdizado",
    )
    numero_camara = models.CharField(max_length=50, blank=True, default="")
    fecha_ingreso = models.DateField(null=True, blank=True)
    hora_ingreso = models.CharField(max_length=5, blank=True, default="",
        help_text="Formato HH:mm")
    fecha_salida = models.DateField(null=True, blank=True)
    hora_salida = models.CharField(max_length=5, blank=True, default="",
        help_text="Nullable. Restriccion: no puede ser anterior a hora_ingreso")
    kilos_enviados_terreno = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    kilos_recepcionados = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    kilos_procesados = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    kilos_bruto_salida = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    kilos_neto_salida = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    horas_desverdizado = models.IntegerField(
        null=True, blank=True,
        help_text="Horas planificadas de desverdizado. Reemplaza el campo proceso para este dato."
    )
    color_salida = models.CharField(max_length=30, blank=True, default="")
    proceso = models.CharField(max_length=100, blank=True, default="",
        help_text="Metodo de conservacion — texto libre. Valor legacy: horas en formato '72h'.")
    fecha_proceso = models.DateField(null=True, blank=True)
    sector = models.CharField(max_length=50, blank=True, default="")
    cuartel = models.CharField(max_length=50, blank=True, default="")
    rol = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "operaciones_desverdizado"
        ordering = ["-created_at"]

    def clean(self):
        if (self.fecha_salida and self.fecha_ingreso
                and self.fecha_salida < self.fecha_ingreso):
            raise ValidationError(
                "fecha_salida no puede ser anterior a fecha_ingreso en Desverdizado."
            )
        if (self.kilos_neto_salida is not None
                and self.kilos_bruto_salida is not None
                and self.kilos_neto_salida > self.kilos_bruto_salida):
            raise ValidationError(
                "kilos_neto_salida no puede superar kilos_bruto_salida."
            )

    def __str__(self):
        return f"Desverdizado - {self.lote}"


# ---------------------------------------------------------------------------
# CalidadDesverdizado
# ---------------------------------------------------------------------------

class CalidadDesverdizado(AuditSourceModel):
    """
    Control de calidad post-desverdizado. Solo aplica a lotes que pasaron
    por Desverdizado. Pueden registrarse multiples evaluaciones por lote.
    Campos propuestos — pendientes de validacion con cliente.
    """
    lote = models.ForeignKey(
        Lote,
        on_delete=models.PROTECT,
        related_name="calidad_desverdizado",
    )
    fecha = models.DateField(null=True, blank=True)
    hora = models.CharField(max_length=5, blank=True, default="",
        help_text="Formato HH:mm")
    temperatura_fruta = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="°C")
    color_evaluado = models.CharField(max_length=30, blank=True, default="")
    estado_visual = models.CharField(max_length=50, blank=True, default="")
    presencia_defectos = models.BooleanField(null=True, blank=True)
    descripcion_defectos = models.TextField(blank=True, default="")
    aprobado = models.BooleanField(null=True, blank=True,
        help_text="Aprobado para ingreso a packing")
    observaciones = models.TextField(blank=True, default="")
    rol = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "operaciones_calidad_desverdizado"
        ordering = ["-created_at"]

    def __str__(self):
        return f"CalidadDesv - {self.lote} ({self.fecha})"


# ---------------------------------------------------------------------------
# IngresoAPacking
# ---------------------------------------------------------------------------

class IngresoAPacking(AuditSourceModel):
    """
    Etapa obligatoria para todos los lotes. Un lote tiene exactamente un registro.
    Marca el cierre del flujo pre-packing.
    """
    lote = models.OneToOneField(
        Lote,
        on_delete=models.PROTECT,
        related_name="ingreso_packing",
    )
    fecha_ingreso = models.DateField(null=True, blank=True)
    hora_ingreso = models.CharField(max_length=5, blank=True, default="",
        help_text="Formato HH:mm")
    kilos_bruto_ingreso_packing = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    kilos_neto_ingreso_packing = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    via_desverdizado = models.BooleanField(default=False,
        help_text="True = llego desde desverdizado / False = directo")
    observaciones = models.TextField(blank=True, default="")
    rol = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "operaciones_ingreso_packing"
        ordering = ["-created_at"]

    def clean(self):
        if (self.kilos_neto_ingreso_packing is not None
                and self.kilos_bruto_ingreso_packing is not None
                and self.kilos_neto_ingreso_packing > self.kilos_bruto_ingreso_packing):
            raise ValidationError(
                "kilos_neto_ingreso_packing no puede superar kilos_bruto_ingreso_packing."
            )

    def __str__(self):
        return f"IngresoAPacking - {self.lote}"


# ---------------------------------------------------------------------------
# RegistroPacking
# ---------------------------------------------------------------------------

class RegistroPacking(AuditSourceModel):
    """
    Registra que se produjo. Multiples filas por lote segun combinacion
    de categoria, calibre y linea.
    """
    lote = models.ForeignKey(
        Lote,
        on_delete=models.PROTECT,
        related_name="registros_packing",
    )
    fecha = models.DateField(null=True, blank=True)
    hora_inicio = models.CharField(max_length=5, blank=True, default="",
        help_text="Formato HH:mm")
    linea_proceso = models.CharField(max_length=50, blank=True, default="",
        help_text="Texto libre — pendiente aclarar con cliente")
    categoria_calidad = models.CharField(max_length=50, blank=True, default="",
        help_text="Texto libre por ahora")
    calibre = models.CharField(max_length=20, blank=True, default="")
    tipo_envase = models.CharField(max_length=50, blank=True, default="")
    cantidad_cajas_producidas = models.IntegerField(null=True, blank=True)
    peso_promedio_caja_kg = models.DecimalField(
        max_digits=8, decimal_places=3, null=True, blank=True)
    merma_seleccion_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="(%) — deprecated, usar merma_seleccion_kg")
    merma_seleccion_kg = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Merma de seleccion en kilos")
    kilos_fruta_comercial = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Kilos disponibles para venta comercial")
    kilos_descarte_local = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Kilos descartados o destinados a consumo local")
    rol = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "operaciones_registro_packing"
        ordering = ["-created_at"]

    def clean(self):
        if (self.merma_seleccion_pct is not None
                and not (0 <= self.merma_seleccion_pct <= 100)):
            raise ValidationError(
                "merma_seleccion_pct debe estar en rango 0-100."
            )

    def __str__(self):
        return f"RegistroPacking - {self.lote} ({self.fecha})"


# ---------------------------------------------------------------------------
# ControlProcesoPacking
# ---------------------------------------------------------------------------

class ControlProcesoPacking(AuditSourceModel):
    """
    Registra como estaba configurada la linea. Multiples registros por lote
    si los parametros cambian en el turno.
    """
    lote = models.ForeignKey(
        Lote,
        on_delete=models.PROTECT,
        related_name="control_proceso_packing",
    )
    fecha = models.DateField(null=True, blank=True)
    hora = models.CharField(max_length=5, blank=True, default="",
        help_text="Formato HH:mm")
    n_bins_procesados = models.IntegerField(null=True, blank=True)
    velocidad_volcador = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="bins/h")
    obs_volcador = models.CharField(max_length=200, blank=True, default="")
    temp_agua_tina = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="°C")
    cloro_libre_ppm = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True)
    ph_agua = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True,
        help_text="Escala 0-14")
    tiempo_inmersion_seg = models.IntegerField(null=True, blank=True,
        help_text="Segundos enteros")
    recambio_agua = models.BooleanField(null=True, blank=True)
    temp_aire_secado = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="°C")
    velocidad_ventiladores = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True)
    fruta_sale_seca = models.BooleanField(null=True, blank=True)
    tipo_cera = models.CharField(max_length=50, blank=True, default="")
    dosis_cera_ml_min = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True)
    temp_cera = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="°C")
    cobertura_uniforme = models.BooleanField(null=True, blank=True)
    n_operarios_seleccion = models.IntegerField(null=True, blank=True)
    fruta_dano_condicion_kg = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True)
    fruta_dano_calidad_kg = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True)
    fruta_pudricion_kg = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True)
    merma_total_seleccion_kg = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True)
    equipo_calibrador = models.CharField(max_length=50, blank=True, default="")
    calibre_predominante = models.CharField(max_length=20, blank=True, default="")
    pct_calibre_export = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="% — rango 0-100")
    pct_calibres_menores = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="% — rango 0-100")
    tipo_caja = models.CharField(max_length=50, blank=True, default="")
    peso_promedio_caja_kg = models.DecimalField(
        max_digits=8, decimal_places=3, null=True, blank=True)
    n_cajas_producidas = models.IntegerField(null=True, blank=True)
    rendimiento_lote_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="% — rango 0-100")
    observaciones_generales = models.TextField(blank=True, default="")
    rol = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "operaciones_control_proceso_packing"
        ordering = ["-created_at"]

    def clean(self):
        errors = []
        for campo, valor in [
            ("rendimiento_lote_pct", self.rendimiento_lote_pct),
            ("pct_calibre_export", self.pct_calibre_export),
            ("pct_calibres_menores", self.pct_calibres_menores),
        ]:
            if valor is not None and not (0 <= valor <= 100):
                errors.append(f"{campo} debe estar en rango 0-100.")
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"ControlProceso - {self.lote} ({self.fecha})"


# ---------------------------------------------------------------------------
# CalidadPallet
# ---------------------------------------------------------------------------

class CalidadPallet(AuditSourceModel):
    """
    Control de calidad post-paletizaje. Segunda etapa de la secuencia lineal
    post-packing. Campos propuestos — pendientes de validacion con cliente.
    Un pallet puede tener multiples registros.
    """
    pallet = models.ForeignKey(
        Pallet,
        on_delete=models.PROTECT,
        related_name="calidad_pallet",
    )
    fecha = models.DateField(null=True, blank=True)
    hora = models.CharField(max_length=5, blank=True, default="",
        help_text="Formato HH:mm")
    temperatura_fruta = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="°C")
    peso_caja_muestra = models.DecimalField(
        max_digits=8, decimal_places=3, null=True, blank=True,
        help_text="kg")
    estado_embalaje = models.CharField(max_length=50, blank=True, default="")
    estado_visual_fruta = models.CharField(max_length=50, blank=True, default="")
    presencia_defectos = models.BooleanField(null=True, blank=True)
    descripcion_defectos = models.TextField(blank=True, default="")
    aprobado = models.BooleanField(null=True, blank=True,
        help_text="Aprobado para ingreso a camara de frio")
    observaciones = models.TextField(blank=True, default="")
    rol = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "operaciones_calidad_pallet"
        ordering = ["-created_at"]

    def __str__(self):
        return f"CalidadPallet - {self.pallet} ({self.fecha})"


# ---------------------------------------------------------------------------
# CalidadPalletMuestra
# ---------------------------------------------------------------------------

class CalidadPalletMuestra(AuditSourceModel):
    """
    Muestra individual de calidad para un pallet. Un pallet puede tener
    multiples muestras (tipicamente 2-3) registradas en la misma sesion.

    Tabla Dataverse: crf21_calidad_pallet_muestras (activa desde 2026-04-04).
    Persistida via guardar_muestra_calidad_pallet use case y
    repos.calidad_pallet_muestras (SQLite + Dataverse segun PERSISTENCE_BACKEND).
    """
    pallet = models.ForeignKey(
        Pallet,
        on_delete=models.PROTECT,
        related_name="muestras_calidad",
    )
    numero_muestra = models.PositiveSmallIntegerField(
        default=1,
        help_text="Numero correlativo de muestra en la sesion (1, 2, 3...)"
    )
    temperatura_fruta = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="°C")
    peso_caja_muestra = models.DecimalField(
        max_digits=8, decimal_places=3, null=True, blank=True,
        help_text="kg")
    n_frutos = models.IntegerField(null=True, blank=True,
        help_text="Numero de frutos en la caja muestra")
    aprobado = models.BooleanField(null=True, blank=True,
        help_text="Muestra aprobada")
    observaciones = models.TextField(blank=True, default="")
    rol = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "operaciones_calidad_pallet_muestra"
        ordering = ["pallet", "numero_muestra"]

    def __str__(self):
        return f"Muestra {self.numero_muestra} - {self.pallet}"


# ---------------------------------------------------------------------------
# CamaraFrio
# ---------------------------------------------------------------------------

class CamaraFrio(AuditSourceModel):
    """
    Registro de ingreso y salida del pallet en camara de frio.
    Tercera etapa de la secuencia lineal post-packing.
    Un pallet tiene un solo registro (1:1).
    Multiples pallets pueden ingresar a la misma camara.
    """
    pallet = models.OneToOneField(
        Pallet,
        on_delete=models.PROTECT,
        related_name="camara_frio",
    )
    camara_numero = models.CharField(max_length=20, blank=True, default="")
    temperatura_camara = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="°C")
    humedad_relativa = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="%")
    fecha_ingreso = models.DateField(null=True, blank=True)
    hora_ingreso = models.CharField(max_length=5, blank=True, default="",
        help_text="Formato HH:mm")
    fecha_salida = models.DateField(null=True, blank=True)
    hora_salida = models.CharField(max_length=5, blank=True, default="",
        help_text="Nullable. Restriccion: no puede ser anterior a hora_ingreso")
    destino_despacho = models.CharField(max_length=100, blank=True, default="")
    rol = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "operaciones_camara_frio"
        ordering = ["-created_at"]

    def clean(self):
        if (self.fecha_salida and self.fecha_ingreso
                and self.fecha_salida < self.fecha_ingreso):
            raise ValidationError(
                "fecha_salida no puede ser anterior a fecha_ingreso en CamaraFrio."
            )

    def __str__(self):
        return f"CamaraFrio - {self.pallet}"


# ---------------------------------------------------------------------------
# MedicionTemperaturaSalida
# ---------------------------------------------------------------------------

class MedicionTemperaturaSalida(AuditSourceModel):
    """
    Medicion de temperatura del pallet al salir de la camara de frio,
    previo al despacho. Ultima etapa de la secuencia lineal post-packing.
    Un pallet puede tener multiples mediciones.
    """
    pallet = models.ForeignKey(
        Pallet,
        on_delete=models.PROTECT,
        related_name="mediciones_temperatura",
    )
    fecha = models.DateField(null=True, blank=True)
    hora = models.CharField(max_length=5, blank=True, default="",
        help_text="Formato HH:mm")
    temperatura_pallet = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="°C — temperatura superficial del pallet")
    punto_medicion = models.CharField(max_length=100, blank=True, default="",
        help_text="Descripcion del punto donde se tomo la medicion")
    dentro_rango = models.BooleanField(null=True, blank=True,
        help_text="Si esta dentro del rango aceptable")
    observaciones = models.TextField(blank=True, default="")
    rol = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "operaciones_medicion_temperatura_salida"
        ordering = ["-created_at"]

    def __str__(self):
        return f"MedicionTemp - {self.pallet} ({self.fecha})"


# ---------------------------------------------------------------------------
# Planillas de Control de Calidad
# ---------------------------------------------------------------------------

class PlanillaDesverdizadoCalibre(AuditSourceModel):
    """
    Planilla CALIDAD DESVERDIZADO — medicion de calibres en terreno.
    Digitaliza la hoja Excel 'CALIDAD DESVERDIZADO'.
    Tabla Dataverse: crf21_planilla_desv_calibres.
    """
    lote = models.ForeignKey(
        Lote,
        on_delete=models.PROTECT,
        related_name="planillas_desv_calibre",
    )
    supervisor = models.CharField(max_length=100, blank=True, default="")
    productor = models.CharField(max_length=100, blank=True, default="")
    variedad = models.CharField(max_length=100, blank=True, default="")
    trazabilidad = models.CharField(max_length=100, blank=True, default="")
    cod_sdp = models.CharField(max_length=50, blank=True, default="")
    fecha_cosecha = models.DateField(null=True, blank=True)
    fecha_despacho = models.DateField(null=True, blank=True)
    cuartel = models.CharField(max_length=100, blank=True, default="")
    sector = models.CharField(max_length=100, blank=True, default="")
    # Defectos (columna derecha, 50 frutos)
    oleocelosis = models.IntegerField(null=True, blank=True)
    heridas_abiertas = models.IntegerField(null=True, blank=True)
    rugoso = models.IntegerField(null=True, blank=True)
    deforme = models.IntegerField(null=True, blank=True)
    golpe_sol = models.IntegerField(null=True, blank=True)
    verdes = models.IntegerField(null=True, blank=True)
    pre_calibre_defecto = models.IntegerField(null=True, blank=True,
        help_text="Pre calibre (defecto)")
    palo_largo = models.IntegerField(null=True, blank=True)
    # Grupos de calibres (3 grupos de color) — JSON
    # Estructura: [{"color": str, "calibres": {"1xx":N,"1x":N,"1":N,"2":N,"3":N,"4":N,"5":N,"Precalibre":N}, "observacion": str}]
    calibres_grupos = models.JSONField(default=list, blank=True)
    observaciones = models.TextField(blank=True, default="")
    rol = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "operaciones_planilla_desv_calibre"
        ordering = ["-created_at"]

    def __str__(self):
        return f"PlanCalibres - {self.lote} ({self.fecha_despacho})"


class PlanillaDesverdizadoSemillas(AuditSourceModel):
    """
    Planilla CALIDAD DESVERDIZADO_2 — medicion de semillas en cosecha citricos.
    Digitaliza la hoja Excel 'CALIDAD DESVERDIZADO_2'.
    Tabla Dataverse: crf21_planilla_desv_semillas.
    """
    lote = models.ForeignKey(
        Lote,
        on_delete=models.PROTECT,
        related_name="planillas_desv_semillas",
    )
    fecha = models.DateField(null=True, blank=True)
    supervisor = models.CharField(max_length=100, blank=True, default="")
    productor = models.CharField(max_length=100, blank=True, default="")
    variedad = models.CharField(max_length=100, blank=True, default="")
    cuartel = models.CharField(max_length=100, blank=True, default="")
    sector = models.CharField(max_length=100, blank=True, default="")
    trazabilidad = models.CharField(max_length=100, blank=True, default="")
    cod_sdp = models.CharField(max_length=50, blank=True, default="")
    color = models.CharField(max_length=30, blank=True, default="")
    # Datos de frutas — JSON
    # Estructura: [{"n_fruto": int, "n_semillas": int}] x50 (5 grupos x 10)
    frutas_data = models.JSONField(default=list, blank=True)
    # Resumen calculado
    total_frutos_muestra = models.IntegerField(null=True, blank=True)
    total_frutos_con_semillas = models.IntegerField(null=True, blank=True)
    total_semillas = models.IntegerField(null=True, blank=True)
    pct_frutos_con_semillas = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True)
    promedio_semillas = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True)
    rol = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "operaciones_planilla_desv_semillas"
        ordering = ["-created_at"]

    def __str__(self):
        return f"PlanSemillas - {self.lote} ({self.fecha})"


class PlanillaCalidadPacking(AuditSourceModel):
    """
    Planilla CALIDAD PACKING CITRICOS — control de calidad para exportacion.
    Digitaliza la hoja Excel 'CALIDAD PACKING CITRICOS'.
    Tabla Dataverse: crf21_planilla_calidad_packings.
    """
    pallet = models.ForeignKey(
        Pallet,
        on_delete=models.PROTECT,
        related_name="planillas_calidad_packing",
    )
    # Identificacion
    productor = models.CharField(max_length=100, blank=True, default="")
    trazabilidad = models.CharField(max_length=100, blank=True, default="")
    cod_sdp = models.CharField(max_length=50, blank=True, default="")
    cuartel = models.CharField(max_length=100, blank=True, default="")
    sector = models.CharField(max_length=100, blank=True, default="")
    nombre_control = models.CharField(max_length=100, blank=True, default="")
    n_cuadrilla = models.CharField(max_length=50, blank=True, default="")
    supervisor = models.CharField(max_length=100, blank=True, default="")
    fecha_despacho = models.DateField(null=True, blank=True)
    fecha_cosecha = models.DateField(null=True, blank=True)
    numero_hoja = models.IntegerField(default=1, help_text="Numero de hoja de la planilla (1 o 2)")
    tipo_fruta = models.CharField(max_length=50, blank=True, default="",
        help_text="clementina o mandarina")
    variedad = models.CharField(max_length=100, blank=True, default="",
        help_text="orogrande, oronules, clemenule, tango")
    # Condiciones ambientales
    temperatura = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    humedad = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    horas_cosecha = models.CharField(max_length=20, blank=True, default="")
    color = models.CharField(max_length=20, blank=True, default="")
    n_frutos_muestreados = models.IntegerField(null=True, blank=True)
    brix = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # Calibre
    pre_calibre = models.IntegerField(null=True, blank=True)
    sobre_calibre = models.IntegerField(null=True, blank=True)
    # CALIDAD
    color_contrario_evaluado = models.IntegerField(null=True, blank=True)
    cantidad_frutos = models.IntegerField(null=True, blank=True)
    ausencia_roseta = models.IntegerField(null=True, blank=True)
    deformes = models.IntegerField(null=True, blank=True)
    frutos_con_semilla = models.IntegerField(null=True, blank=True)
    n_semillas = models.IntegerField(null=True, blank=True)
    fumagina = models.IntegerField(null=True, blank=True)
    h_cicatrizadas = models.IntegerField(null=True, blank=True)
    manchas = models.IntegerField(null=True, blank=True)
    peduculo_largo = models.IntegerField(null=True, blank=True)
    residuos = models.IntegerField(null=True, blank=True)
    rugosos = models.IntegerField(null=True, blank=True)
    # Russet
    russet_leve_claros = models.IntegerField(null=True, blank=True)
    russet_moderados_claros = models.IntegerField(null=True, blank=True)
    russet_severos_oscuros = models.IntegerField(null=True, blank=True)
    # CONDICION
    creasing_leve = models.IntegerField(null=True, blank=True)
    creasing_mod_sev = models.IntegerField(null=True, blank=True)
    dano_frio_granulados = models.IntegerField(null=True, blank=True)
    bufado = models.IntegerField(null=True, blank=True)
    deshidratacion_roseta = models.IntegerField(null=True, blank=True)
    golpe_sol = models.IntegerField(null=True, blank=True)
    h_abiertas_superior = models.IntegerField(null=True, blank=True)
    h_abiertas_inferior = models.IntegerField(null=True, blank=True)
    acostillado = models.IntegerField(null=True, blank=True)
    machucon = models.IntegerField(null=True, blank=True)
    blandos = models.IntegerField(null=True, blank=True)
    oleocelosis = models.IntegerField(null=True, blank=True)
    ombligo_rasgado = models.IntegerField(null=True, blank=True)
    colapso_corteza = models.IntegerField(null=True, blank=True)
    pudricion = models.IntegerField(null=True, blank=True)
    # Dano Arana
    dano_arana_leve = models.IntegerField(null=True, blank=True)
    dano_arana_moderado = models.IntegerField(null=True, blank=True)
    dano_arana_severo = models.IntegerField(null=True, blank=True)
    # Otros
    dano_mecanico = models.IntegerField(null=True, blank=True)
    otros_condicion = models.CharField(max_length=200, blank=True, default="")
    total_defectos_pct = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Total defectos %")
    rol = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "operaciones_planilla_calidad_packing"
        ordering = ["-created_at"]

    def __str__(self):
        return f"PlanCalidadPacking - {self.pallet} (Hoja {self.numero_hoja})"


class PlanillaCalidadCamara(AuditSourceModel):
    """
    Planilla CALIDAD CAMARAS — control de proceso y temperatura en camara.
    Digitaliza la hoja Excel 'CALIDAD CAMARAS'.
    Tabla Dataverse: crf21_planilla_calidad_camaras.
    """
    pallet = models.ForeignKey(
        Pallet,
        on_delete=models.PROTECT,
        related_name="planillas_calidad_camara",
        null=True, blank=True,
    )
    # Encabezado
    fecha_control = models.DateField(null=True, blank=True)
    tipo_proceso = models.CharField(max_length=100, blank=True, default="")
    zona_planta = models.CharField(max_length=100, blank=True, default="")
    tunel_camara = models.CharField(max_length=50, blank=True, default="")
    capacidad_maxima = models.CharField(max_length=50, blank=True, default="")
    temperatura_equipos = models.CharField(max_length=50, blank=True, default="")
    codigo_envases = models.CharField(max_length=100, blank=True, default="")
    cantidad_pallets = models.IntegerField(null=True, blank=True)
    especie = models.CharField(max_length=100, blank=True, default="")
    variedad = models.CharField(max_length=100, blank=True, default="")
    fecha_embalaje = models.DateField(null=True, blank=True)
    estiba = models.CharField(max_length=100, blank=True, default="")
    tipo_inversion = models.CharField(max_length=100, blank=True, default="")
    # Mediciones por hora — JSON
    # Estructura: [{hora, ambiente, pulpa_ext_entrada, pulpa_ext_medio, pulpa_ext_salida,
    #               pulpa_int_entrada, pulpa_int_media, pulpa_int_salida}]
    mediciones = models.JSONField(default=list, blank=True)
    # Promedios
    temp_pulpa_ext_inicio = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True)
    temp_pulpa_ext_termino = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True)
    temp_pulpa_int_inicio = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True)
    temp_pulpa_int_termino = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True)
    temp_ambiente_inicio = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True)
    temp_ambiente_termino = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True)
    # Tiempos
    tiempo_carga_inicio = models.CharField(max_length=10, blank=True, default="")
    tiempo_carga_termino = models.CharField(max_length=10, blank=True, default="")
    tiempo_descarga_inicio = models.CharField(max_length=10, blank=True, default="")
    tiempo_descarga_termino = models.CharField(max_length=10, blank=True, default="")
    tiempo_enfriado_inicio = models.CharField(max_length=10, blank=True, default="")
    tiempo_enfriado_termino = models.CharField(max_length=10, blank=True, default="")
    observaciones = models.TextField(blank=True, default="")
    nombre_control = models.CharField(max_length=100, blank=True, default="")
    rol = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "operaciones_planilla_calidad_camara"
        ordering = ["-created_at"]

    def __str__(self):
        return f"PlanCalidadCamara - {self.tunel_camara} ({self.fecha_control})"


# ---------------------------------------------------------------------------
# RegistroEtapa  (evento de trazabilidad — no reemplaza las entidades anteriores)
# ---------------------------------------------------------------------------

class RegistroEtapa(AuditSourceModel):
    """
    Registro de eventos de trazabilidad del flujo. Complementa a las entidades
    especificas (CamaraMantencion, Desverdizado, etc.) como capa de auditoria.
    """
    temporada = models.CharField(max_length=20, db_index=True)
    event_key = models.CharField(
        max_length=120,
        unique=True,
        db_index=True,
        help_text="Clave idempotente unica del evento."
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


# ---------------------------------------------------------------------------
# SequenceCounter  —  correlativos por entidad y dimension
# ---------------------------------------------------------------------------

class SequenceCounter(models.Model):
    """
    Tabla de correlativos para generacion dinamica de codigos en backend.

    entity_name: nombre de la entidad ('lote', 'bin', 'pallet').
    dimension:   clave de agrupacion del correlativo.
                 Para lote: temporada_codigo (ej: '2025-2026').
                 Para bin y pallet: fecha en formato YYYYMMDD (ej: '20260329').
    last_value:  ultimo valor asignado. El siguiente es last_value + 1.
    """
    entity_name = models.CharField(max_length=50, db_index=True)
    dimension   = models.CharField(max_length=50, db_index=True)
    last_value  = models.PositiveIntegerField(default=0)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "operaciones_sequence_counter"
        constraints = [
            models.UniqueConstraint(
                fields=["entity_name", "dimension"],
                name="uq_seq_entity_dimension",
            ),
        ]
        indexes = [
            models.Index(fields=["entity_name", "dimension"], name="ix_seq_entity_dim"),
        ]

    def __str__(self):
        return f"{self.entity_name}:{self.dimension} → {self.last_value}"
