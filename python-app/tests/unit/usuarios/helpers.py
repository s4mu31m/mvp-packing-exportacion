"""
Helpers compartidos para tests de usuarios.

Importar desde aquí tanto en tests unitarios (usuarios/test/test_usuarios.py)
como en tests E2E (tests/e2e/conftest.py) para tener una sola fuente de verdad.
"""
from django.contrib.auth.hashers import make_password

from usuarios.models import UsuarioProfile


def make_profile(
    usernamelogin: str = "operador1",
    rol: str = "Recepcion",
    activo: bool = True,
    bloqueado: bool = False,
    password: str = "testpass123",
    nombrecompleto: str = "Operador Uno",
) -> UsuarioProfile:
    """Crea un UsuarioProfile en SQLite para tests.

    Genera automáticamente un codigooperador único con el prefijo correcto
    según el rol: ADM- para Administrador, JEF- para Jefatura, OPE- para el resto.
    """
    prefix = (
        "ADM" if "Administrador" in rol
        else ("JEF" if "Jefatura" in rol else "OPE")
    )
    count = UsuarioProfile.objects.filter(
        codigooperador__startswith=prefix + "-"
    ).count()
    return UsuarioProfile.objects.create(
        usernamelogin=usernamelogin,
        nombrecompleto=nombrecompleto,
        correo=f"{usernamelogin}@test.com",
        passwordhash=make_password(password),
        rol=rol,
        activo=activo,
        bloqueado=bloqueado,
        codigooperador=f"{prefix}-{count + 1:03d}",
    )
