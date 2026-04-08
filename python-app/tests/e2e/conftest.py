"""
Fixtures compartidos para la suite E2E de CaliPro.

Requiere:
  pip install -r requirements-dev.txt
  playwright install

Correr:
  pytest tests/e2e/ -v
  pytest tests/e2e/ --headed --slowmo=300   # con navegador visible
"""
# ── Django 6.0 + Playwright async-safety ────────────────────────────────────
# Django 6.0 lanza SynchronousOnlyOperation cuando detecta que se llaman
# operaciones síncronas de DB desde dentro de un event loop asyncio. Playwright
# usa asyncio internamente, lo que activa esa detección incluso en el setup de
# fixtures (create_test_db → connection.close()). Esta variable de entorno
# desactiva esa comprobación para que los tests E2E puedan crear la DB de test.
# Es seguro para tests unitarios: si no hay event loop activo (tests síncronos)
# la comprobación de Django no se dispara de todos modos.
import os
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

# ── Forzar SQLite ANTES de cualquier fixture/test ───────────────────────────
# os.environ.setdefault NO funciona aquí porque load_dotenv() ya estableció
# PERSISTENCE_BACKEND=dataverse desde .env antes de que pytest importe este
# conftest. Modificamos el objeto vivo de settings de Django en su lugar.
from django.conf import settings as _django_settings

_django_settings.PERSISTENCE_BACKEND = "sqlite"

# ModelBackend puede estar ausente si .env cargó el backend Dataverse
# (que solo registra CaliProAuthBackend). Lo añadimos para que c.login()
# y authenticate() con usuarios Django nativos funcionen en los tests E2E.
_model_backend = "django.contrib.auth.backends.ModelBackend"
if _model_backend not in _django_settings.AUTHENTICATION_BACKENDS:
    _django_settings.AUTHENTICATION_BACKENDS = list(
        _django_settings.AUTHENTICATION_BACKENDS
    ) + [_model_backend]

import pytest

# ─── Credencial de test única para toda la suite ───────────────────────────
TEST_PASSWORD = "CaliPro2026!"


# ─── ALLOWED_HOSTS ──────────────────────────────────────────────────────────
# local.py trae ALLOWED_HOSTS=[] — lo parcheamos en cada test.
# scope="function" evita colisiones de scope con otros fixtures de pytest-django.
@pytest.fixture(autouse=True)
def patch_allowed_hosts(settings):
    settings.ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]


# ─── Fábrica de usuarios ────────────────────────────────────────────────────
@pytest.fixture()
def make_user(transactional_db):
    """
    Fábrica de UsuarioProfile con contraseña hasheada y codigooperador correcto.
    Delega en helpers.make_profile (fuente única de verdad compartida con tests unitarios).
    """
    from usuarios.test.helpers import make_profile

    def _make(username: str, rol: str, password: str = TEST_PASSWORD,
              activo: bool = True, bloqueado: bool = False,
              nombrecompleto: str = "") -> object:
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


# ─── Login helper ───────────────────────────────────────────────────────────
@pytest.fixture()
def login(page, live_server):
    """
    Realiza el login a través del formulario del navegador.
    Esto activa el pipeline completo de Django: CaliProAuthBackend +
    store_user_session() → sesión con crf21_rol, crf21_codigooperador, etc.

    Uso:
        login("username")          # usa TEST_PASSWORD
        login("username", "pwd")   # contraseña explícita
    """
    def _login(username: str, password: str = TEST_PASSWORD) -> None:
        page.goto(f"{live_server.url}/usuarios/login/")
        page.get_by_label("Usuario").fill(username)
        page.get_by_label("Contraseña").fill(password)
        page.get_by_role("button", name="Acceder").click()
        page.wait_for_url(f"{live_server.url}/usuarios/portal/")

    return _login


# ─── Páginas pre-autenticadas ───────────────────────────────────────────────
@pytest.fixture()
def as_admin(page, make_user, login):
    """Página ya autenticada como Administrador."""
    make_user("admin_e2e", "Administrador")
    login("admin_e2e")
    return page


@pytest.fixture()
def as_recepcion(page, make_user, login):
    """Página ya autenticada como operador de Recepcion."""
    make_user("recepcion_e2e", "Recepcion")
    login("recepcion_e2e")
    return page


@pytest.fixture()
def as_jefatura(page, make_user, login):
    """Página ya autenticada como Jefatura."""
    make_user("jefatura_e2e", "Jefatura")
    login("jefatura_e2e")
    return page


@pytest.fixture()
def as_control(page, make_user, login):
    """Página ya autenticada como operador de Control."""
    make_user("control_e2e", "Control")
    login("control_e2e")
    return page
