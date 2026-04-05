"""
Formularios web para el flujo operativo de packing.
Cada formulario corresponde a una etapa del flujo.
"""
from django import forms
from operaciones.models import DisponibilidadCamara, AOR


# ---------------------------------------------------------------------------
# Recepcion — flujo de lote abierto
# ---------------------------------------------------------------------------

class IniciarLoteForm(forms.Form):
    """Inicia una sesion de recepcion (crea lote en estado abierto)."""
    pass


class CerrarLoteForm(forms.Form):
    """Cierra el lote abierto — ya no se pueden agregar mas bins."""
    requiere_desverdizado = forms.BooleanField(
        required=False, label="Requiere desverdizado",
    )
    disponibilidad_camara_desverdizado = forms.ChoiceField(
        choices=[("", "— no aplica —")] + list(DisponibilidadCamara.choices),
        required=False, label="Disponibilidad camara desverdizado",
        help_text="Solo si requiere desverdizado",
    )
    kilos_bruto_conformacion = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, label="Kilos bruto total lote",
    )
    kilos_neto_conformacion = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, label="Kilos neto total lote",
    )


class BinForm(forms.Form):
    """Registro de bin en recepcion. El bin_code se genera automaticamente en backend."""
    # --- Campos base del lote (se bloquean tras el primer bin) ---
    codigo_productor = forms.CharField(
        max_length=50, required=False, label="Codigo productor / agricultor",
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
        max_length=30, required=False, label="Color (numero)",
        help_text="Numero de color segun tabla interna. Ej: 1, 2, 5",
        widget=forms.TextInput(attrs={"placeholder": "1", "inputmode": "numeric", "autocomplete": "off"}),
    )
    fecha_cosecha = forms.DateField(
        required=False, label="Fecha de cosecha",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    # --- Campos variables por bin ---
    numero_cuartel = forms.CharField(
        max_length=20, required=False, label="Cuartel",
        widget=forms.TextInput(attrs={"placeholder": "C01", "autocomplete": "off"}),
    )
    # --- Campos operativos adicionales ---
    hora_recepcion = forms.TimeField(
        required=False, label="Hora recepcion",
        widget=forms.TimeInput(attrs={"type": "time", "class": "campo-hora"}),
    )
    kilos_bruto_ingreso = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False,
        label="Kilos bruto ingreso",
    )
    kilos_neto_ingreso = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False,
        label="Kilos neto ingreso",
    )
    a_o_r = forms.ChoiceField(
        choices=[("", "---------")] + list(AOR.choices),
        required=False, label="A/O/R",
    )
    observaciones = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False, label="Observaciones",
    )


class CamaraMantencionForm(forms.Form):
    """Ingreso a camara de mantencion."""
    camara_numero = forms.CharField(
        max_length=20, required=False, label="Numero de camara",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    fecha_ingreso = forms.DateField(
        required=False, label="Fecha ingreso",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    hora_ingreso = forms.TimeField(
        required=False, label="Hora ingreso",
        widget=forms.TimeInput(attrs={"type": "time", "class": "campo-hora"}),
    )
    temperatura_camara = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Temperatura camara (°C)",
    )
    humedad_relativa = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Humedad relativa (%)",
    )
    observaciones = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False, label="Observaciones",
    )


class DesverdizadoForm(forms.Form):
    """Ingreso a desverdizado."""
    fecha_ingreso = forms.DateField(
        required=False, label="Fecha ingreso",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    hora_ingreso = forms.TimeField(
        required=False, label="Hora ingreso",
        widget=forms.TimeInput(attrs={"type": "time", "class": "campo-hora"}),
    )
    color = forms.CharField(
        max_length=30, required=False, label="Color objetivo (numero)",
        help_text="Numero de color esperado al salir. Ej: 3, 4. El operador puede ajustar.",
        widget=forms.TextInput(attrs={"placeholder": "3", "inputmode": "numeric", "autocomplete": "off"}),
    )
    horas_desverdizado = forms.IntegerField(
        required=False, label="Horas de desverdizado",
        help_text="Horas planificadas (1-240). Reemplaza el campo legacy 'proceso' para este dato.",
        widget=forms.NumberInput(attrs={"placeholder": "72", "min": "1", "max": "240"}),
    )
    kilos_enviados_terreno = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False,
        label="Kilos enviados terreno",
    )
    kilos_recepcionados = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False,
        label="Kilos recepcionados",
    )

    def clean_horas_desverdizado(self):
        val = self.cleaned_data.get("horas_desverdizado")
        if val is None:
            return val
        if val < 1 or val > 240:
            raise forms.ValidationError("Debe estar entre 1 y 240 horas.")
        return val


class IngresoPackingForm(forms.Form):
    """Ingreso al area de packing."""
    fecha_ingreso = forms.DateField(
        required=False, label="Fecha ingreso",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    hora_ingreso = forms.TimeField(
        required=False, label="Hora ingreso",
        widget=forms.TimeInput(attrs={"type": "time", "class": "campo-hora"}),
    )
    kilos_bruto_ingreso_packing = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False,
        label="Kilos bruto",
    )
    kilos_neto_ingreso_packing = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False,
        label="Kilos neto",
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
        label="Merma seleccion (%)",
        help_text="Rango 0-100",
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
    n_bins_procesados = forms.IntegerField(required=False, label="N bins procesados")
    temp_agua_tina = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, label="Temp agua tina (°C)",
    )
    ph_agua = forms.DecimalField(
        max_digits=4, decimal_places=2, required=False, label="pH agua",
    )
    recambio_agua = forms.NullBooleanField(
        required=False, label="Recambio agua",
    )
    rendimiento_lote_pct = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False,
        label="Rendimiento lote (%)", help_text="Rango 0-100",
    )
    observaciones_generales = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False, label="Observaciones generales",
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
