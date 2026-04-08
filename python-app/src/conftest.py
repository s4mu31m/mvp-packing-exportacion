"""
Configuracion global de pytest para la suite del proyecto.

Por defecto fuerza `PERSISTENCE_BACKEND=sqlite` para mantener aislados los
tests unitarios e integraciones locales. Para suites especiales que deban
golpear Dataverse real puede sobrescribirse mediante:

    CALIPRO_TEST_BACKEND=dataverse pytest ...

El override ocurre al importar este archivo despues de `django.setup()`, por
lo que afecta tambien a `setUpTestData` y a cualquier fixture que construya
repositorios.
"""
from __future__ import annotations

import os

from django.conf import settings


TEST_BACKEND = os.getenv("CALIPRO_TEST_BACKEND", "sqlite").lower().strip() or "sqlite"
settings.PERSISTENCE_BACKEND = TEST_BACKEND

# En settings/base.py, ModelBackend se agrega solo cuando el backend cargado
# inicialmente es sqlite. Lo reinyectamos unicamente en ese modo porque varios
# tests usan usuarios Django nativos via c.login()/authenticate().
if TEST_BACKEND == "sqlite":
    model_backend = "django.contrib.auth.backends.ModelBackend"
    if model_backend not in settings.AUTHENTICATION_BACKENDS:
        settings.AUTHENTICATION_BACKENDS = list(settings.AUTHENTICATION_BACKENDS) + [
            model_backend
        ]
