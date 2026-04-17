"""
Formularios web para el flujo operativo de packing.
Cada formulario corresponde a una etapa del flujo.
"""
from decimal import Decimal

from django import forms
from operaciones.models import DisponibilidadCamara, AOR


# ---------------------------------------------------------------------------
# Recepcion — flujo de lote abierto
# ---------------------------------------------------------------------------

class IniciarLoteForm(forms.Form):
    """Inicia una sesion de recepcion (crea lote en estado abierto)."""
    pass


class CerrarLoteForm(forms.Form):
    """
    Confirma el cierre del lote. Los kilos de conformacion se calculan
    automaticamente desde los pesajes parciales registrados en sesion.
    Solo se define si el lote requiere desverdizado (si/no).
    La disponibilidad de camara desverdizado se gestiona en la etapa de desverdizado.
    """
    requiere_desverdizado = forms.BooleanField(
        required=False, label="Requiere desverdizado",
    )


class PesajeParcialCierreForm(forms.Form):
    """
    Registro de un pesaje parcial durante el cierre del lote.
    Permite pesar grupos de bins del mismo tipo (misma tara) de forma incremental.
    kilos_netos se calcula: kilos_brutos - (cantidad_bins x tara).
    """
    cantidad_bins = forms.IntegerField(
        min_value=1, required=True, label="Cantidad de bins",
        widget=forms.NumberInput(attrs={
            "id": "id-pesaje-cantidad-bins",
            "min": "1",
            "inputmode": "numeric",
            "autocomplete": "off",
        }),
    )
    kilos_brutos_grupo = forms.DecimalField(
        max_digits=10, decimal_places=2, required=True, label="Kilos brutos del grupo",
        widget=forms.NumberInput(attrs={
            "id": "id-pesaje-kilos-brutos",
            "step": "0.01",
            "min": "0.01",
        }),
    )
    tara = forms.DecimalField(
        max_digits=8, decimal_places=2, required=True,
        min_value=Decimal("0.01"), label="Tara del tipo de bin (kg)",
        widget=forms.NumberInput(attrs={
            "id": "id-pesaje-tara",
            "step": "0.01",
            "min": "0.01",
        }),
    )

    def clean(self):
        cleaned = super().clean()
        cantidad = cleaned.get("cantidad_bins")
        brutos = cleaned.get("kilos_brutos_grupo")
        tara = cleaned.get("tara")
        if cantidad and brutos is not None and tara is not None:
            from decimal import Decimal as D
            netos = brutos - D(str(cantidad)) * tara
            if netos < 0:
                raise forms.ValidationError(
                    "Los kilos netos resultan negativos con estos valores. "
                    "Verifique kilos brutos y tara."
                )
            cleaned["kilos_netos_grupo"] = netos
        return cleaned


class PesajeParcialIngresoPackingForm(forms.Form):
    """
    Registro de un pesaje parcial durante el ingreso a packing.
    Logica identica a PesajeParcialCierreForm; IDs de widget prefijados id-pp-
    para coexistir en la misma pagina sin colisiones.
    kilos_netos = kilos_brutos - (cantidad_bins x tara).
    """
    cantidad_bins = forms.IntegerField(
        min_value=1, required=True, label="Cantidad de bins",
        widget=forms.NumberInput(attrs={
            "id": "id-pp-cantidad-bins",
            "min": "1",
            "inputmode": "numeric",
            "autocomplete": "off",
        }),
    )
    kilos_brutos_grupo = forms.DecimalField(
        max_digits=10, decimal_places=2, required=True, label="Kilos brutos del grupo",
        widget=forms.NumberInput(attrs={
            "id": "id-pp-kilos-brutos",
            "step": "0.01",
            "min": "0.01",
        }),
    )
    tara = forms.DecimalField(
        max_digits=8, decimal_places=2, required=True,
        min_value=Decimal("0.01"), label="Tara del tipo de bin (kg)",
        widget=forms.NumberInput(attrs={
            "id": "id-pp-tara",
            "step": "0.01",
            "min": "0.01",
        }),
    )

    def clean(self):
        cleaned = super().clean()
        cantidad = cleaned.get("cantidad_bins")
        brutos = cleaned.get("kilos_brutos_grupo")
        tara = cleaned.get("tara")
        if cantidad and brutos is not None and tara is not None:
            from decimal import Decimal as D
            netos = brutos - D(str(cantidad)) * tara
            if netos < 0:
                raise forms.ValidationError(
                    "Los kilos netos resultan negativos con estos valores. "
                    "Verifique kilos brutos y tara."
                )
            cleaned["kilos_netos_grupo"] = netos
        return cleaned


class BinForm(forms.Form):
    """Registro de bin en recepcion. El bin_code se genera automaticamente en backend."""
    # --- Campos base del lote (se bloquean tras el primer bin) ---
    codigo_productor = forms.CharField(
        max_length=50, required=True, label="Codigo productor / agricultor",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    tipo_cultivo = forms.CharField(
        max_length=50, required=False, label="Tipo cultivo (especie)",
        widget=forms.TextInput(attrs={"placeholder": "Uva de mesa"}),
    )
    variedad_fruta = forms.CharField(
        max_length=100, required=True, label="Variedad",
        widget=forms.TextInput(attrs={"placeholder": "Ej: Thompson Seedless"}),
    )
    color = forms.CharField(
        max_length=30, required=True, label="Color (numero)",
        help_text="Numero de color segun tabla interna. Ej: 1, 2, 5",
        widget=forms.TextInput(attrs={"placeholder": "1", "inputmode": "numeric", "autocomplete": "off"}),
    )
    fecha_cosecha = forms.DateField(
        required=False, label="Fecha de cosecha",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    # --- Campos variables por bin ---
    numero_cuartel = forms.CharField(
        max_length=20, required=True, label="Cuartel",
        widget=forms.TextInput(attrs={"placeholder": "C01", "autocomplete": "off"}),
    )
    nombre_cuartel = forms.CharField(
        max_length=100, required=True, label="Nombre Cuartel",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    codigo_sag_csg = forms.CharField(
        max_length=50, required=True, label="CSG",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    codigo_sag_csp = forms.CharField(
        max_length=50, required=True, label="CSP",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    codigo_sdp = forms.CharField(
        max_length=50, required=True, label="SDP",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    lote_productor = forms.CharField(
        max_length=100, required=True, label="Lote campo",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    # --- Campos operativos adicionales ---
    hora_recepcion = forms.TimeField(
        required=True, label="Hora recepcion",
        widget=forms.TimeInput(attrs={"type": "time", "class": "campo-hora"}),
    )
    kilos_bruto_ingreso = forms.DecimalField(
        max_digits=10, decimal_places=2, required=True,
        label="Kilos brutos ingreso",
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
    )
    kilos_neto_ingreso = forms.DecimalField(
        max_digits=10, decimal_places=2, required=True,
        label="Kilos netos ingreso",
        widget=forms.NumberInput(attrs={"id": "id-kilos-neto-ingreso", "step": "0.01", "min": "0"}),
    )
    a_o_r = forms.ChoiceField(
        choices=[("", "---------")] + list(AOR.choices),
        required=True, label="A/O/R",
    )
    observaciones = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False, label="Observaciones",
    )


class EditBinVariableForm(forms.Form):
    """Edicion de campos variables de un bin ya registrado en un lote abierto."""
    numero_cuartel = forms.CharField(
        max_length=20, required=True, label="Cuartel",
        widget=forms.TextInput(attrs={"placeholder": "C01", "autocomplete": "off"}),
    )
    hora_recepcion = forms.TimeField(
        required=True, label="Hora recepcion",
        widget=forms.TimeInput(attrs={"type": "time", "class": "campo-hora"}),
    )
    kilos_bruto_ingreso = forms.DecimalField(
        max_digits=10, decimal_places=2, required=True, label="Kilos brutos ingreso",
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
    )
    kilos_neto_ingreso = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, label="Kilos netos ingreso",
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
    )
    a_o_r = forms.ChoiceField(
        choices=[("", "---------")] + list(AOR.choices),
        required=True, label="A/O/R",
    )
    observaciones = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False, label="Observaciones",
    )


class CamaraMantencionForm(forms.Form):
    """Ingreso a camara de mantencion."""
    camara_numero = forms.CharField(
        max_length=20, required=True, label="Numero de camara",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    fecha_ingreso = forms.DateField(
        required=True, label="Fecha ingreso",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    hora_ingreso = forms.TimeField(
        required=True, label="Hora ingreso",
        widget=forms.TimeInput(attrs={"type": "time", "class": "campo-hora"}),
    )
    temperatura_camara = forms.DecimalField(
        max_digits=5, decimal_places=2, required=True, label="Temperatura camara (°C)",
    )
    humedad_relativa = forms.DecimalField(
        max_digits=5, decimal_places=2, required=True, label="Humedad relativa (%)",
    )
    observaciones = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False, label="Observaciones",
    )


class DesverdizadoForm(forms.Form):
    """Ingreso a desverdizado."""
    numero_camara = forms.CharField(
        max_length=50, required=True, label="Numero de camara",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    fecha_ingreso = forms.DateField(
        required=True, label="Fecha ingreso",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    hora_ingreso = forms.TimeField(
        required=True, label="Hora ingreso",
        widget=forms.TimeInput(attrs={"type": "time", "class": "campo-hora"}),
    )
    color = forms.CharField(
        max_length=30, required=True, label="Color objetivo (numero)",
        help_text="Numero de color esperado al salir. Ej: 3, 4. El operador puede ajustar.",
        widget=forms.TextInput(attrs={"placeholder": "3", "inputmode": "numeric", "autocomplete": "off"}),
    )
    horas_desverdizado = forms.IntegerField(
        required=False, label="Horas de desverdizado",
        help_text="Horas planificadas (1-240). Reemplaza el campo legacy 'proceso' para este dato.",
        widget=forms.NumberInput(attrs={"placeholder": "72", "min": "1", "max": "240"}),
    )
    disponibilidad_camara_desverdizado = forms.ChoiceField(
        choices=[("", "— seleccione —")] + list(DisponibilidadCamara.choices),
        required=False, label="Disponibilidad camara",
        help_text="Confirmar si la camara esta disponible para iniciar el proceso",
    )

    def clean_horas_desverdizado(self):
        val = self.cleaned_data.get("horas_desverdizado")
        if val is None:
            return val
        if val < 1 or val > 240:
            raise forms.ValidationError("Debe estar entre 1 y 240 horas.")
        return val


class IngresoPackingForm(forms.Form):
    """Datos de fecha/hora/observaciones para el ingreso a packing.
    Los kilos se calculan desde los pesajes parciales registrados en sesion."""
    fecha_ingreso = forms.DateField(
        required=False, label="Fecha ingreso",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    hora_ingreso = forms.TimeField(
        required=False, label="Hora ingreso",
        widget=forms.TimeInput(attrs={"type": "time", "class": "campo-hora"}),
    )
    via_desverdizado = forms.BooleanField(
        required=False, label="Via desverdizado",
        help_text="Marcar si el lote llego desde desverdizado",
    )
    observaciones = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False, label="Observaciones",
    )


class RegistroPackingForm(forms.Form):
    """Registro de produccion en packing."""
    fecha = forms.DateField(
        required=False, label="Fecha",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    hora_inicio = forms.TimeField(
        required=False, label="Hora inicio",
        widget=forms.TimeInput(attrs={"type": "time", "class": "campo-hora"}),
    )
    linea_proceso = forms.CharField(
        max_length=50, required=False, label="Linea de proceso",
    )
    categoria_calidad = forms.CharField(
        max_length=50, required=False, label="Categoria calidad",
        help_text="Texto libre — pendiente definicion",
    )
    calibre = forms.CharField(max_length=20, required=False, label="Calibre")
    tipo_envase = forms.CharField(max_length=50, required=False, label="Tipo envase")
    cantidad_cajas_producidas = forms.IntegerField(
        required=False, label="Cantidad cajas producidas",
    )
    merma_seleccion_pct = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False,
        label="Merma seleccion (%) — deprecated",
        help_text="Usar merma_seleccion_kg",
    )
    merma_seleccion_kg = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False,
        label="Merma seleccion (kg)",
        help_text="Kilos descartados por seleccion",
    )
    kilos_fruta_comercial = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False,
        label="Kilos fruta comercial",
        help_text="Kilos disponibles para venta comercial",
    )
    kilos_descarte_local = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False,
        label="Kilos descarte / local",
        help_text="Kilos destinados a consumo local o descarte definitivo",
    )


class ControlProcesoPackingForm(forms.Form):
    """Control de parametros del proceso packing."""
    fecha = forms.DateField(
        required=False, label="Fecha",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    hora = forms.TimeField(
        required=False, label="Hora",
        widget=forms.TimeInput(attrs={"type": "time", "class": "campo-hora"}),
    )
    # --- Volcador ---
    n_bins_procesados = forms.IntegerField(required=False, label="N° bins procesados")
    velocidad_volcador = forms.DecimalField(
        max_digits=6, decimal_places=2, required=False, label="Velocidad volcador (bins/h)",
    )
    obs_volcador = forms.CharField(
        max_length=200, required=False, label="Observacion volcador",
    )
    # --- Tina de agua ---
    temp_agua_tina = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Temp agua tina (°C)",
    )
    cloro_libre_ppm = forms.DecimalField(
        max_digits=6, decimal_places=2, required=False, label="Cloro libre (ppm)",
    )
    ph_agua = forms.DecimalField(
        max_digits=4, decimal_places=2, required=False, label="pH agua",
    )
    tiempo_inmersion_seg = forms.IntegerField(required=False, label="Tiempo inmersion (seg)")
    recambio_agua = forms.NullBooleanField(required=False, label="Recambio agua")
    # --- Secado ---
    temp_aire_secado = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Temp aire secado (°C)",
    )
    velocidad_ventiladores = forms.DecimalField(
        max_digits=6, decimal_places=2, required=False, label="Velocidad ventiladores",
    )
    fruta_sale_seca = forms.NullBooleanField(required=False, label="Fruta sale seca")
    # --- Cera ---
    tipo_cera = forms.CharField(max_length=50, required=False, label="Tipo cera")
    dosis_cera_ml_min = forms.DecimalField(
        max_digits=7, decimal_places=2, required=False, label="Dosis cera (ml/min)",
    )
    temp_cera = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Temp cera (°C)",
    )
    cobertura_uniforme = forms.NullBooleanField(required=False, label="Cobertura uniforme")
    # --- Seleccion ---
    n_operarios_seleccion = forms.IntegerField(required=False, label="N° operarios seleccion")
    fruta_dano_condicion_kg = forms.DecimalField(
        max_digits=8, decimal_places=2, required=False, label="Fruta daño condicion (kg)",
    )
    fruta_dano_calidad_kg = forms.DecimalField(
        max_digits=8, decimal_places=2, required=False, label="Fruta daño calidad (kg)",
    )
    fruta_pudricion_kg = forms.DecimalField(
        max_digits=8, decimal_places=2, required=False, label="Fruta pudricion (kg)",
    )
    merma_total_seleccion_kg = forms.DecimalField(
        max_digits=8, decimal_places=2, required=False, label="Merma total seleccion (kg)",
    )
    # --- Calibrador ---
    equipo_calibrador = forms.CharField(max_length=50, required=False, label="Equipo calibrador")
    calibre_predominante = forms.CharField(max_length=20, required=False, label="Calibre predominante")
    pct_calibre_export = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False,
        label="% calibre export", help_text="Rango 0-100",
    )
    pct_calibres_menores = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False,
        label="% calibres menores", help_text="Rango 0-100",
    )
    # --- Cajas ---
    tipo_caja = forms.CharField(max_length=50, required=False, label="Tipo caja")
    peso_promedio_caja_kg = forms.DecimalField(
        max_digits=7, decimal_places=3, required=False, label="Peso promedio caja (kg)",
    )
    n_cajas_producidas = forms.IntegerField(required=False, label="N° cajas producidas")
    rendimiento_lote_pct = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False,
        label="Rendimiento lote (%)", help_text="Rango 0-100",
    )
    # --- General ---
    observaciones_generales = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False, label="Observaciones generales",
    )
    rol = forms.CharField(
        max_length=50, required=False, label="Responsable turno",
        widget=forms.TextInput(attrs={"readonly": True})
    )


class CalidadPalletForm(forms.Form):
    """Control de calidad post-paletizaje."""
    fecha = forms.DateField(
        required=False, label="Fecha",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    hora = forms.TimeField(
        required=False, label="Hora",
        widget=forms.TimeInput(attrs={"type": "time", "class": "campo-hora"}),
    )
    temperatura_fruta = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Temperatura fruta (°C)",
    )
    peso_caja_muestra = forms.DecimalField(
        max_digits=8, decimal_places=3, required=False, label="Peso caja muestra (kg)",
    )
    estado_visual_fruta = forms.CharField(
        max_length=50, required=False, label="Estado visual fruta",
    )
    presencia_defectos = forms.NullBooleanField(required=False, label="Presencia defectos")
    aprobado = forms.NullBooleanField(
        required=False, label="Aprobado para camara de frio",
    )
    observaciones = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False, label="Observaciones",
    )


class CamaraFrioForm(forms.Form):
    """Ingreso a camara de frio."""
    camara_numero = forms.CharField(max_length=20, required=False, label="Numero camara")
    temperatura_camara = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Temperatura camara (°C)",
    )
    humedad_relativa = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Humedad relativa (%)",
    )
    fecha_ingreso = forms.DateField(
        required=False, label="Fecha ingreso",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    hora_ingreso = forms.TimeField(
        required=False, label="Hora ingreso",
        widget=forms.TimeInput(attrs={"type": "time", "class": "campo-hora"}),
    )
    destino_despacho = forms.CharField(
        max_length=100, required=False, label="Destino despacho",
    )


class CalidadPalletMuestraForm(forms.Form):
    """Una muestra individual de calidad para un pallet."""
    numero_muestra = forms.IntegerField(
        required=False, label="N° muestra",
        widget=forms.NumberInput(attrs={"min": "1", "max": "10"}),
    )
    temperatura_fruta = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Temp. fruta (°C)",
    )
    peso_caja_muestra = forms.DecimalField(
        max_digits=8, decimal_places=3, required=False, label="Peso caja (kg)",
    )
    n_frutos = forms.IntegerField(required=False, label="N° frutos")
    aprobado = forms.NullBooleanField(required=False, label="Aprobada")
    observaciones = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False, label="Observaciones",
    )


class MedicionTemperaturaForm(forms.Form):
    """Medicion de temperatura al salir de camara de frio."""
    fecha = forms.DateField(
        required=False, label="Fecha",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    hora = forms.TimeField(
        required=False, label="Hora",
        widget=forms.TimeInput(attrs={"type": "time", "class": "campo-hora"}),
    )
    temperatura_pallet = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False,
        label="Temperatura pallet (°C)",
    )
    punto_medicion = forms.CharField(
        max_length=100, required=False, label="Punto de medicion",
    )
    dentro_rango = forms.NullBooleanField(
        required=False, label="Dentro del rango aceptable",
    )
    observaciones = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False, label="Observaciones",
    )


# ---------------------------------------------------------------------------
# Planillas de Control de Calidad
# ---------------------------------------------------------------------------

class PlanillaDesverdizadoCalibreForm(forms.Form):
    """Encabezado de la planilla CALIDAD DESVERDIZADO (calibres).
    Los 3 grupos de calibres se envian como campos dinamicos en el POST."""
    supervisor = forms.CharField(max_length=100, required=False, label="Supervisor")
    productor = forms.CharField(max_length=100, required=False, label="Productor")
    variedad = forms.CharField(max_length=100, required=False, label="Variedad")
    trazabilidad = forms.CharField(max_length=100, required=False, label="Trazabilidad")
    cod_sdp = forms.CharField(max_length=50, required=False, label="Cod. SDP")
    fecha_cosecha = forms.DateField(
        required=False, label="Fecha cosecha",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    fecha_despacho = forms.DateField(
        required=False, label="Fecha despacho",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    cuartel = forms.CharField(max_length=100, required=False, label="Cuartel")
    sector = forms.CharField(max_length=100, required=False, label="Sector")
    # Defectos (columna derecha — 50 frutos)
    oleocelosis = forms.IntegerField(required=False, label="Oleocelosis", min_value=0)
    heridas_abiertas = forms.IntegerField(required=False, label="Heridas abiertas", min_value=0)
    rugoso = forms.IntegerField(required=False, label="Rugoso", min_value=0)
    deforme = forms.IntegerField(required=False, label="Deforme", min_value=0)
    golpe_sol = forms.IntegerField(required=False, label="Golpe de sol", min_value=0)
    verdes = forms.IntegerField(required=False, label="Verdes", min_value=0)
    pre_calibre_defecto = forms.IntegerField(required=False, label="Pre calibre", min_value=0)
    palo_largo = forms.IntegerField(required=False, label="Palo largo", min_value=0)
    observaciones = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False, label="Observaciones",
    )


class PlanillaDesverdizadoSemillasForm(forms.Form):
    """Encabezado de la planilla CALIDAD DESVERDIZADO_2 (semillas).
    Los 50 datos de frutas se envian como campos g{G}_f{N}_semillas en el POST."""
    fecha = forms.DateField(
        required=False, label="Fecha",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    supervisor = forms.CharField(max_length=100, required=False, label="Supervisor")
    productor = forms.CharField(max_length=100, required=False, label="Productor")
    variedad = forms.CharField(max_length=100, required=False, label="Variedad")
    cuartel = forms.CharField(max_length=100, required=False, label="Cuartel")
    sector = forms.CharField(max_length=100, required=False, label="Sector")
    trazabilidad = forms.CharField(max_length=100, required=False, label="Trazabilidad")
    cod_sdp = forms.CharField(max_length=50, required=False, label="Cod. SDP")
    color = forms.CharField(max_length=30, required=False, label="Color(es)")


class PlanillaCalidadPackingForm(forms.Form):
    """Planilla CALIDAD PACKING CITRICOS — todos los campos escalares."""
    # Identificacion
    productor = forms.CharField(max_length=100, required=False, label="Productor")
    trazabilidad = forms.CharField(max_length=100, required=False, label="Trazabilidad")
    cod_sdp = forms.CharField(max_length=50, required=False, label="Cod. SDP")
    cuartel = forms.CharField(max_length=100, required=False, label="Cuartel")
    sector = forms.CharField(max_length=100, required=False, label="Sector")
    nombre_control = forms.CharField(max_length=100, required=False, label="Nombre control")
    n_cuadrilla = forms.CharField(max_length=50, required=False, label="N° cuadrilla")
    supervisor = forms.CharField(max_length=100, required=False, label="Supervisor")
    fecha_despacho = forms.DateField(
        required=False, label="Fecha despacho",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    fecha_cosecha = forms.DateField(
        required=False, label="Fecha cosecha",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    numero_hoja = forms.IntegerField(
        required=False, label="N° hoja", min_value=1, max_value=2,
        widget=forms.NumberInput(attrs={"min": "1", "max": "2"}),
    )
    tipo_fruta = forms.ChoiceField(
        choices=[("", "— seleccione —"), ("clementina", "Clementina"), ("mandarina", "Mandarina")],
        required=False, label="Tipo fruta",
    )
    variedad = forms.CharField(max_length=100, required=False, label="Variedad")
    # Condiciones
    temperatura = forms.DecimalField(max_digits=5, decimal_places=1, required=False, label="Temp. (°C)")
    humedad = forms.DecimalField(max_digits=5, decimal_places=1, required=False, label="Hum. (%)")
    horas_cosecha = forms.CharField(max_length=20, required=False, label="H/Cos")
    color = forms.CharField(max_length=20, required=False, label="Color")
    n_frutos_muestreados = forms.IntegerField(required=False, label="N° frutos muestreados")
    brix = forms.DecimalField(max_digits=5, decimal_places=2, required=False, label="BRIX")
    # Calibre
    pre_calibre = forms.IntegerField(required=False, label="Pre calibre", min_value=0)
    sobre_calibre = forms.IntegerField(required=False, label="Sobre calibre", min_value=0)
    # CALIDAD
    color_contrario_evaluado = forms.IntegerField(required=False, label="Color contrario evaluado", min_value=0)
    cantidad_frutos = forms.IntegerField(required=False, label="Cantidad de frutos", min_value=0)
    ausencia_roseta = forms.IntegerField(required=False, label="Ausencia roseta", min_value=0)
    deformes = forms.IntegerField(required=False, label="Deformes", min_value=0)
    frutos_con_semilla = forms.IntegerField(required=False, label="Frutos con semilla", min_value=0)
    n_semillas = forms.IntegerField(required=False, label="N° semillas", min_value=0)
    fumagina = forms.IntegerField(required=False, label="Fumagina", min_value=0)
    h_cicatrizadas = forms.IntegerField(required=False, label="H. cicatrizadas", min_value=0)
    manchas = forms.IntegerField(required=False, label="Manchas", min_value=0)
    peduculo_largo = forms.IntegerField(required=False, label="Pedúnculo largo", min_value=0)
    residuos = forms.IntegerField(required=False, label="Residuos", min_value=0)
    rugosos = forms.IntegerField(required=False, label="Rugosos", min_value=0)
    # Russet
    russet_leve_claros = forms.IntegerField(required=False, label="Russet leve claros", min_value=0)
    russet_moderados_claros = forms.IntegerField(required=False, label="Russet moderados claros", min_value=0)
    russet_severos_oscuros = forms.IntegerField(required=False, label="Russet severos oscuros", min_value=0)
    # CONDICION
    creasing_leve = forms.IntegerField(required=False, label="Creasing leve", min_value=0)
    creasing_mod_sev = forms.IntegerField(required=False, label="Creasing mod./severo", min_value=0)
    dano_frio_granulados = forms.IntegerField(required=False, label="Daño frío/granulados", min_value=0)
    bufado = forms.IntegerField(required=False, label="Bufado", min_value=0)
    deshidratacion_roseta = forms.IntegerField(required=False, label="Deshidratación roseta", min_value=0)
    golpe_sol = forms.IntegerField(required=False, label="Golpe de sol", min_value=0)
    h_abiertas_superior = forms.IntegerField(required=False, label="H. abiertas superior", min_value=0)
    h_abiertas_inferior = forms.IntegerField(required=False, label="H. abiertas inferior", min_value=0)
    acostillado = forms.IntegerField(required=False, label="Acostillado", min_value=0)
    machucon = forms.IntegerField(required=False, label="Machucón", min_value=0)
    blandos = forms.IntegerField(required=False, label="Blandos", min_value=0)
    oleocelosis = forms.IntegerField(required=False, label="Oleocelosis", min_value=0)
    ombligo_rasgado = forms.IntegerField(required=False, label="Ombligo rasgado", min_value=0)
    colapso_corteza = forms.IntegerField(required=False, label="Colapso corteza", min_value=0)
    pudricion = forms.IntegerField(required=False, label="Pudrición", min_value=0)
    # Daño Araña
    dano_arana_leve = forms.IntegerField(required=False, label="Daño araña leve", min_value=0)
    dano_arana_moderado = forms.IntegerField(required=False, label="Daño araña moderado", min_value=0)
    dano_arana_severo = forms.IntegerField(required=False, label="Daño araña severo", min_value=0)
    # Otros
    dano_mecanico = forms.IntegerField(required=False, label="Daño mecánico", min_value=0)
    otros_condicion = forms.CharField(max_length=200, required=False, label="Otros condición")
    total_defectos_pct = forms.DecimalField(
        max_digits=6, decimal_places=2, required=False, label="Total defectos (%)",
    )


class PlanillaCalidadCamaraForm(forms.Form):
    """Encabezado y resumen de la planilla CALIDAD CAMARAS.
    Las filas de medicion horaria se envian como med_{i}_{campo} desde JS dinamico."""
    fecha_control = forms.DateField(
        required=False, label="Fecha del control",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    tipo_proceso = forms.CharField(max_length=100, required=False, label="Tipo de proceso")
    zona_planta = forms.CharField(max_length=100, required=False, label="Zona/planta")
    tunel_camara = forms.CharField(max_length=50, required=False, label="Túnel/cámara")
    capacidad_maxima = forms.CharField(max_length=50, required=False, label="Capacidad máxima")
    temperatura_equipos = forms.CharField(max_length=50, required=False, label="Temp. equipos")
    codigo_envases = forms.CharField(max_length=100, required=False, label="Cód. envases")
    cantidad_pallets = forms.IntegerField(required=False, label="Cantidad pallets", min_value=0)
    especie = forms.CharField(max_length=100, required=False, label="Especie")
    variedad = forms.CharField(max_length=100, required=False, label="Variedad")
    fecha_embalaje = forms.DateField(
        required=False, label="Fecha embalaje",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    estiba = forms.CharField(max_length=100, required=False, label="Estiba")
    tipo_inversion = forms.CharField(max_length=100, required=False, label="Tipo inversión")
    # Promedios
    temp_pulpa_ext_inicio = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Pulpa ext. inicio (°C)")
    temp_pulpa_ext_termino = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Pulpa ext. término (°C)")
    temp_pulpa_int_inicio = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Pulpa int. inicio (°C)")
    temp_pulpa_int_termino = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Pulpa int. término (°C)")
    temp_ambiente_inicio = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Ambiente inicio (°C)")
    temp_ambiente_termino = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Ambiente término (°C)")
    # Tiempos
    tiempo_carga_inicio = forms.TimeField(
        required=False, label="Carga inicio",
        widget=forms.TimeInput(attrs={"type": "time", "class": "campo-hora"}),
    )
    tiempo_carga_termino = forms.TimeField(
        required=False, label="Carga término",
        widget=forms.TimeInput(attrs={"type": "time", "class": "campo-hora"}),
    )
    tiempo_descarga_inicio = forms.TimeField(
        required=False, label="Descarga inicio",
        widget=forms.TimeInput(attrs={"type": "time", "class": "campo-hora"}),
    )
    tiempo_descarga_termino = forms.TimeField(
        required=False, label="Descarga término",
        widget=forms.TimeInput(attrs={"type": "time", "class": "campo-hora"}),
    )
    tiempo_enfriado_inicio = forms.TimeField(
        required=False, label="Enfriado inicio",
        widget=forms.TimeInput(attrs={"type": "time", "class": "campo-hora"}),
    )
    tiempo_enfriado_termino = forms.TimeField(
        required=False, label="Enfriado término",
        widget=forms.TimeInput(attrs={"type": "time", "class": "campo-hora"}),
    )
    observaciones = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False, label="Observaciones",
    )
    nombre_control = forms.CharField(max_length=100, required=False, label="Nombre control proceso")
