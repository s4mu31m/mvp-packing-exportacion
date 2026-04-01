"""
Formularios de gestión de usuarios alineados al esquema Dataverse.

Los campos siguen el contrato de crf21_usuariooperativos.
Reemplaza el formulario anterior basado en Django UserCreationForm.
"""
from django import forms
from django.contrib.auth.hashers import make_password

# Roles operativos del sistema — orden de presentación en el formulario
ROLES_CHOICES = [
    ("Recepcion",       "Recepcion"),
    ("Pesaje",          "Pesaje"),
    ("Desverdizado",    "Desverdizado"),
    ("Ingreso Packing", "Ingreso Packing"),
    ("Proceso",         "Proceso"),
    ("Control",         "Control"),
    ("Paletizado",      "Paletizado"),
    ("Camaras",         "Camaras"),
    ("Jefatura",        "Jefatura"),
    ("Administrador",   "Administrador"),
]


class UsuarioCreacionForm(forms.Form):
    """
    Formulario de creación de usuario operativo.

    Campos mapeados a crf21_usuariooperativos:
        usernamelogin  → crf21_usernamelogin
        nombrecompleto → crf21_nombrecompleto
        correo         → crf21_correo
        password       → crf21_passwordhash (hasheado antes de persistir)
        roles          → crf21_rol (normalizado a string separado por coma)
        activo         → crf21_activo
        bloqueado      → crf21_bloqueado

    codigooperador: generado en el repositorio, no es campo del formulario.
    """
    usernamelogin = forms.CharField(
        max_length=150,
        label="Usuario (login) *",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    nombrecompleto = forms.CharField(max_length=255, required=False, label="Nombre completo")
    correo         = forms.EmailField(required=False, label="Correo electrónico")
    password       = forms.CharField(
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        label="Contraseña *",
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        label="Confirmar contraseña *",
    )
    roles = forms.MultipleChoiceField(
        choices=ROLES_CHOICES,
        label="Roles *",
        required=True,
        widget=forms.CheckboxSelectMultiple,
    )
    activo    = forms.BooleanField(required=False, initial=True,  label="Activo")
    bloqueado = forms.BooleanField(required=False, initial=False, label="Bloqueado")

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password")
        p2 = cleaned.get("password_confirm")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned

    def get_passwordhash(self) -> str:
        """Retorna el hash listo para persistir en crf21_passwordhash."""
        return make_password(self.cleaned_data["password"])

    def get_rol_string(self) -> str:
        """Retorna los roles seleccionados como string canónico separado por coma."""
        return ", ".join(self.cleaned_data["roles"])


class UsuarioEdicionForm(forms.Form):
    """
    Edición de datos de un usuario existente (sin contraseña).
    No permite editar codigooperador ni usernamelogin (inmutables).
    """
    nombrecompleto = forms.CharField(max_length=255, required=False, label="Nombre completo")
    correo         = forms.EmailField(required=False, label="Correo electrónico")
    roles = forms.MultipleChoiceField(
        choices=ROLES_CHOICES,
        label="Roles *",
        required=True,
        widget=forms.CheckboxSelectMultiple,
    )
    activo    = forms.BooleanField(required=False, label="Activo")
    bloqueado = forms.BooleanField(required=False, label="Bloqueado")

    def get_rol_string(self) -> str:
        return ", ".join(self.cleaned_data["roles"])
