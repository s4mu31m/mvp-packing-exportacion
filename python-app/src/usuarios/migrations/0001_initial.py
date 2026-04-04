import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="UsuarioProfile",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "dataverse_id",
                    models.CharField(
                        default=uuid.uuid4,
                        editable=False,
                        max_length=36,
                        unique=True,
                        verbose_name="ID Dataverse (UUID)",
                    ),
                ),
                (
                    "usernamelogin",
                    models.CharField(
                        max_length=150,
                        unique=True,
                        verbose_name="Usuario login (crf21_usernamelogin)",
                    ),
                ),
                (
                    "nombrecompleto",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        verbose_name="Nombre completo (crf21_nombrecompleto)",
                    ),
                ),
                (
                    "correo",
                    models.EmailField(
                        blank=True,
                        max_length=254,
                        verbose_name="Correo electrónico (crf21_correo)",
                    ),
                ),
                (
                    "passwordhash",
                    models.CharField(
                        max_length=255,
                        verbose_name="Hash de contraseña (crf21_passwordhash)",
                    ),
                ),
                (
                    "rol",
                    models.CharField(
                        blank=True,
                        help_text='"Recepcion, Pesaje" o "Administrador"',
                        max_length=500,
                        verbose_name="Roles separados por coma (crf21_rol)",
                    ),
                ),
                (
                    "activo",
                    models.BooleanField(
                        default=True,
                        verbose_name="Activo (crf21_activo)",
                    ),
                ),
                (
                    "bloqueado",
                    models.BooleanField(
                        default=False,
                        verbose_name="Bloqueado (crf21_bloqueado)",
                    ),
                ),
                (
                    "codigooperador",
                    models.CharField(
                        editable=False,
                        max_length=20,
                        unique=True,
                        verbose_name="Código de operador (crf21_codigooperador)",
                        help_text="Generado en backend: ADM-NNN, JEF-NNN, OPE-NNN. Inmutable.",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
            ],
            options={
                "verbose_name": "Perfil de usuario operativo",
                "verbose_name_plural": "Perfiles de usuarios operativos",
                "ordering": ["usernamelogin"],
            },
        ),
    ]
