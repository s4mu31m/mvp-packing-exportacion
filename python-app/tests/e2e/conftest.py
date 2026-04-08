"""
Fixtures compartidos para la suite E2E de CaliPro.

Por defecto la suite sigue corriendo sobre SQLite. Para ejecutar subsets
contra Dataverse real:

    CALIPRO_TEST_BACKEND=dataverse pytest tests/e2e/test_dataverse_*.py -v
"""
from __future__ import annotations

import os

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

import pytest
from django.conf import settings as django_settings
from django.contrib.auth.hashers import make_password


E2E_BACKEND = os.getenv("CALIPRO_TEST_BACKEND", "sqlite").lower().strip() or "sqlite"
django_settings.PERSISTENCE_BACKEND = E2E_BACKEND

if E2E_BACKEND == "sqlite":
    model_backend = "django.contrib.auth.backends.ModelBackend"
    if model_backend not in django_settings.AUTHENTICATION_BACKENDS:
        django_settings.AUTHENTICATION_BACKENDS = list(
            django_settings.AUTHENTICATION_BACKENDS
        ) + [model_backend]


TEST_PASSWORD = "CaliPro2026!"


@pytest.fixture(autouse=True)
def patch_allowed_hosts(settings):
    settings.ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]


@pytest.fixture()
def test_backend():
    return E2E_BACKEND


@pytest.fixture()
def repositories():
    from infrastructure.repository_factory import get_repositories

    return get_repositories()


@pytest.fixture()
def make_user(transactional_db, test_backend):
    """
    Crea o actualiza un usuario operativo para la suite.

    - sqlite: usa helpers.make_profile como antes.
    - dataverse: crea/actualiza crf21_usuariooperativos para permitir login real.
    """

    if test_backend == "sqlite":
        from usuarios.test.helpers import make_profile

        def _make(
            username: str,
            rol: str,
            password: str = TEST_PASSWORD,
            activo: bool = True,
            bloqueado: bool = False,
            nombrecompleto: str = "",
        ) -> object:
            nombre = nombrecompleto or f"Test {rol}"
            return make_profile(
                usernamelogin=username,
                rol=rol,
                password=password,
                activo=activo,
                bloqueado=bloqueado,
                nombrecompleto=nombre,
            )

        return _make

    from usuarios.repositories import get_usuario_repository
    from usuarios.auth_backend import CaliProAuthBackend

    repo = get_usuario_repository()

    def _make(
        username: str,
        rol: str,
        password: str = TEST_PASSWORD,
        activo: bool = True,
        bloqueado: bool = False,
        nombrecompleto: str = "",
    ) -> object:
        nombre = nombrecompleto or f"Test {rol}"
        correo = f"{username}@e2e.local"
        passwordhash = make_password(password)

        existing = repo.get_by_username(username)
        if existing:
            repo.update(
                existing.id,
                {
                    "nombrecompleto": nombre,
                    "correo": correo,
                    "passwordhash": passwordhash,
                    "rol": rol,
                    "activo": activo,
                    "bloqueado": bloqueado,
                },
            )
            perfil = repo.get_by_username(username)
        else:
            perfil = repo.create(
                usernamelogin=username,
                nombrecompleto=nombre,
                correo=correo,
                passwordhash=passwordhash,
                rol=rol,
                activo=activo,
                bloqueado=bloqueado,
            )

        # Mantiene sincronizado el User de Django para sesiones/flags de portal.
        CaliProAuthBackend()._get_or_create_django_user(perfil)
        return perfil

    return _make


@pytest.fixture()
def login(page, live_server):
    def _login(username: str, password: str = TEST_PASSWORD) -> None:
        page.goto(f"{live_server.url}/usuarios/login/")
        page.get_by_label("Usuario").fill(username)
        page.get_by_label("Contraseña").fill(password)
        page.get_by_role("button", name="Acceder").click()
        page.wait_for_url(f"{live_server.url}/usuarios/portal/")

    return _login


@pytest.fixture()
def as_admin(page, make_user, login):
    make_user("admin_e2e", "Administrador")
    login("admin_e2e")
    return page


@pytest.fixture()
def as_recepcion(page, make_user, login):
    make_user("recepcion_e2e", "Recepcion")
    login("recepcion_e2e")
    return page


@pytest.fixture()
def as_jefatura(page, make_user, login):
    make_user("jefatura_e2e", "Jefatura")
    login("jefatura_e2e")
    return page


@pytest.fixture()
def as_control(page, make_user, login):
    make_user("control_e2e", "Control")
    login("control_e2e")
    return page
