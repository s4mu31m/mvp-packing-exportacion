"""
Formularios de gestión de usuarios para la app usuarios.
"""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()

ROL_CHOICES = [
    ("operador", "Operador"),
    ("jefatura", "Jefatura"),
    ("administrador", "Administrador"),
]


class CaliProUserCreationForm(UserCreationForm):
    """
    Formulario de creación de usuario con rol operativo.
    Roles se mapean a is_staff / is_superuser de Django Auth.
    """
    first_name = forms.CharField(max_length=150, required=False, label="Nombre")
    last_name = forms.CharField(max_length=150, required=False, label="Apellido")
    email = forms.EmailField(required=False, label="Correo electrónico")
    rol = forms.ChoiceField(choices=ROL_CHOICES, label="Rol operativo")

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password1", "password2", "rol"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        user.email = self.cleaned_data.get("email", "")

        rol = self.cleaned_data.get("rol", "operador")
        user.is_staff = rol in ("jefatura", "administrador")
        user.is_superuser = rol == "administrador"
        user.is_active = True

        if commit:
            user.save()
        return user


class CaliProUserEditForm(forms.ModelForm):
    """Edición básica de usuario (sin contraseña)."""
    rol = forms.ChoiceField(choices=ROL_CHOICES, label="Rol operativo", required=False)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            if self.instance.is_superuser:
                self.fields["rol"].initial = "administrador"
            elif self.instance.is_staff:
                self.fields["rol"].initial = "jefatura"
            else:
                self.fields["rol"].initial = "operador"
