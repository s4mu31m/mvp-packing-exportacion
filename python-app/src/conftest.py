"""
Configuración global de pytest para la suite de tests unitarios/integración.

Fuerza PERSISTENCE_BACKEND=sqlite independientemente del valor configurado
en .env, garantizando que TODOS los tests usen la base de datos local SQLite
con aislamiento transaccional completo.

Por qué es necesario
--------------------
Cuando .env tiene PERSISTENCE_BACKEND=dataverse los tests fallan porque:

  1. setUpTestData se ejecuta ANTES de que @override_settings aplique (el
     decorator solo protege los métodos de test, no el classmethod de setup).

  2. Las aserciones con Django ORM (Lote.objects.get(pk=...), Bin.objects.count())
     no encuentran datos escritos vía repositorios Dataverse — ambos backends
     usan almacenamientos distintos.

  3. Los repositorios Dataverse requieren credenciales de red reales
     (DATAVERSE_URL, DATAVERSE_CLIENT_ID, etc.) que no están disponibles
     en entornos de CI ni de desarrollo local sin VPN.

Cómo funciona
-------------
Este archivo es importado por pytest DESPUÉS de que pytest-django llama a
django.setup() (en su pytest_configure). Al importarlo, el código de nivel
de módulo se ejecuta antes de cualquier recolección de tests, setUpTestData
o fixture de test, lo que garantiza que settings.PERSISTENCE_BACKEND="sqlite"
está activo para toda la sesión.

Tests de integración contra Dataverse real
-------------------------------------------
Para ejecutar tests contra la API real de Dataverse, usar un directorio
separado (p.ej. tests/integration/) con su propio conftest.py que no tenga
este override y que provea las credenciales reales:

    PERSISTENCE_BACKEND=dataverse pytest tests/integration/ -v
"""
from django.conf import settings

# ── Forzar SQLite para toda la suite ────────────────────────────────────────
# Corre al importar el conftest (después de django.setup()), antes de cualquier
# setUpTestData, fixture o método de test.
settings.PERSISTENCE_BACKEND = "sqlite"

# ── ModelBackend ─────────────────────────────────────────────────────────────
# En settings/base.py, ModelBackend se agrega solo cuando PERSISTENCE_BACKEND
# == "sqlite" en el momento de carga del módulo. Como .env puede cargar
# "dataverse" primero, el backend puede quedar ausente. Lo agregamos aquí para
# que tests que usan c.login() / authenticate() con usuarios Django nativos
# funcionen correctamente.
_model_backend = "django.contrib.auth.backends.ModelBackend"
if _model_backend not in settings.AUTHENTICATION_BACKENDS:
    settings.AUTHENTICATION_BACKENDS = list(settings.AUTHENTICATION_BACKENDS) + [
        _model_backend
    ]
