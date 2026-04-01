"""
Modelo de perfil de usuario operativo para modo SQLite.

Simula el esquema de crf21_usuariooperativos en base de datos local.
En modo Dataverse, este modelo NO se usa; la fuente de verdad es la tabla Dataverse.
"""
import uuid

from django.db import models


class UsuarioProfile(models.Model):
    """
    Perfil operativo de un usuario del sistema (backend SQLite).

    Campos mapeados 1:1 con crf21_usuariooperativos:
        dataverse_id   → crf21_usuariooperativoid  (UUID, generado local en SQLite)
        usernamelogin  → crf21_usernamelogin
        nombrecompleto → crf21_nombrecompleto
        correo         → crf21_correo
        passwordhash   → crf21_passwordhash (hash Django compatible)
        rol            → crf21_rol (texto separado por coma)
        activo         → crf21_activo
        bloqueado      → crf21_bloqueado
        codigooperador → crf21_codigooperador (generado en backend, inmutable)
    """
    dataverse_id = models.CharField(
        max_length=36,
        unique=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID Dataverse (UUID)",
    )
    usernamelogin = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Usuario login (crf21_usernamelogin)",
    )
    nombrecompleto = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Nombre completo (crf21_nombrecompleto)",
    )
    correo = models.EmailField(
        blank=True,
        verbose_name="Correo electrónico (crf21_correo)",
    )
    passwordhash = models.CharField(
        max_length=255,
        verbose_name="Hash de contraseña (crf21_passwordhash)",
    )
    rol = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Roles separados por coma (crf21_rol)",
        help_text='Ej: "Recepcion, Pesaje" o "Administrador"',
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Activo (crf21_activo)",
    )
    bloqueado = models.BooleanField(
        default=False,
        verbose_name="Bloqueado (crf21_bloqueado)",
    )
    codigooperador = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name="Código de operador (crf21_codigooperador)",
        help_text="Generado en backend: ADM-NNN, JEF-NNN, OPE-NNN. Inmutable.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "usuarios"
        verbose_name = "Perfil de usuario operativo"
        verbose_name_plural = "Perfiles de usuarios operativos"
        ordering = ["usernamelogin"]

    def __str__(self) -> str:
        return f"{self.usernamelogin} [{self.codigooperador}]"
