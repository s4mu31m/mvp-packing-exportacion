"""
Formularios web para el flujo operativo de packing.
Cada formulario corresponde a una etapa del flujo.
"""
from django import forms
from operaciones.models import DisponibilidadCamara, AOR


class BinForm(forms.Form):
    """Registro de bin en recepcion. El bin_code se genera automaticamente en backend."""
    fecha_cosecha = forms.DateField(
        required=False, label="Fecha de cosecha",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    variedad_fruta = forms.CharField(
        max_length=100, required=False, label="Variedad",
    )
    codigo_productor = forms.CharField(
        max_length=50, required=False, label="Codigo productor",
    )
    hora_recepcion = forms.CharField(
        max_length=5, required=False, label="Hora recepcion (HH:mm)",
        widget=forms.TextInput(attrs={"placeholder": "08:30"}),
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
    operator_code = forms.CharField(
        max_length=50, required=False, label="Codigo operador",
    )


class LoteForm(forms.Form):
    """Conformacion de lote planta (pesaje). El lote_code se genera automaticamente en backend."""
    fecha_conformacion = forms.DateField(
        required=False, label="Fecha conformacion",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    bin_codes = forms.CharField(
        label="Codigos de bins (uno por linea)",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "BIN-001\nBIN-002"}),
        help_text="Ingrese un codigo de bin por linea",
    )
    kilos_bruto_conformacion = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False,
        label="Kilos bruto conformacion",
    )
    kilos_neto_conformacion = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False,
        label="Kilos neto conformacion",
    )
    requiere_desverdizado = forms.BooleanField(
        required=False, label="Requiere desverdizado",
    )
    disponibilidad_camara_desverdizado = forms.ChoiceField(
        choices=[("", "---------")] + list(DisponibilidadCamara.choices),
        required=False, label="Disponibilidad camara desverdizado",
        help_text="Solo aplica si requiere desverdizado",
    )
    operator_code = forms.CharField(
        max_length=50, required=False, label="Codigo operador",
    )

    def clean_bin_codes(self):
        raw = self.cleaned_data.get("bin_codes", "")
        codes = [c.strip() for c in raw.splitlines() if c.strip()]
        if not codes:
            raise forms.ValidationError("Debe ingresar al menos un codigo de bin")
        return codes


class CamaraMantencionForm(forms.Form):
    """Ingreso a camara de mantencion."""
    camara_numero = forms.CharField(max_length=20, required=False, label="Numero de camara")
    fecha_ingreso = forms.DateField(
        required=False, label="Fecha ingreso",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    hora_ingreso = forms.CharField(
        max_length=5, required=False, label="Hora ingreso (HH:mm)",
        widget=forms.TextInput(attrs={"placeholder": "08:30"}),
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
    operator_code = forms.CharField(max_length=50, required=False, label="Codigo operador")


class DesverdizadoForm(forms.Form):
    """Ingreso a desverdizado."""
    fecha_ingreso = forms.DateField(
        required=False, label="Fecha ingreso",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    hora_ingreso = forms.CharField(
        max_length=5, required=False, label="Hora ingreso (HH:mm)",
        widget=forms.TextInput(attrs={"placeholder": "08:30"}),
    )
    kilos_enviados_terreno = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False,
        label="Kilos enviados terreno",
    )
    kilos_recepcionados = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False,
        label="Kilos recepcionados",
    )
    proceso = forms.CharField(
        max_length=100, required=False, label="Proceso/metodo",
        help_text="Texto libre por ahora",
    )
    operator_code = forms.CharField(max_length=50, required=False, label="Codigo operador")


class IngresoPackingForm(forms.Form):
    """Ingreso al area de packing."""
    fecha_ingreso = forms.DateField(
        required=False, label="Fecha ingreso",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    hora_ingreso = forms.CharField(
        max_length=5, required=False, label="Hora ingreso (HH:mm)",
        widget=forms.TextInput(attrs={"placeholder": "08:30"}),
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
    operator_code = forms.CharField(max_length=50, required=False, label="Codigo operador")


class RegistroPackingForm(forms.Form):
    """Registro de produccion en packing."""
    fecha = forms.DateField(
        required=False, label="Fecha",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    hora_inicio = forms.CharField(
        max_length=5, required=False, label="Hora inicio (HH:mm)",
        widget=forms.TextInput(attrs={"placeholder": "08:30"}),
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
    operator_code = forms.CharField(max_length=50, required=False, label="Codigo operador")


class ControlProcesoPackingForm(forms.Form):
    """Control de parametros del proceso packing."""
    fecha = forms.DateField(
        required=False, label="Fecha",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    hora = forms.CharField(
        max_length=5, required=False, label="Hora (HH:mm)",
        widget=forms.TextInput(attrs={"placeholder": "08:30"}),
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
    operator_code = forms.CharField(max_length=50, required=False, label="Codigo operador")


class CalidadPalletForm(forms.Form):
    """Control de calidad post-paletizaje."""
    fecha = forms.DateField(
        required=False, label="Fecha",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    hora = forms.CharField(
        max_length=5, required=False, label="Hora (HH:mm)",
        widget=forms.TextInput(attrs={"placeholder": "08:30"}),
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
    operator_code = forms.CharField(max_length=50, required=False, label="Codigo operador")


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
    hora_ingreso = forms.CharField(
        max_length=5, required=False, label="Hora ingreso (HH:mm)",
        widget=forms.TextInput(attrs={"placeholder": "08:30"}),
    )
    destino_despacho = forms.CharField(
        max_length=100, required=False, label="Destino despacho",
    )
    operator_code = forms.CharField(max_length=50, required=False, label="Codigo operador")


class MedicionTemperaturaForm(forms.Form):
    """Medicion de temperatura al salir de camara de frio."""
    fecha = forms.DateField(
        required=False, label="Fecha",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    hora = forms.CharField(
        max_length=5, required=False, label="Hora (HH:mm)",
        widget=forms.TextInput(attrs={"placeholder": "08:30"}),
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
    operator_code = forms.CharField(max_length=50, required=False, label="Codigo operador")
