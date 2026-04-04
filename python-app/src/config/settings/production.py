import os

from .base import *

DEBUG = False

# Falla en startup si SECRET_KEY no fue configurada como variable de entorno real.
# Nunca debe desplegarse con el valor por defecto "dev-only-change-me".
if SECRET_KEY == "dev-only-change-me":
    raise RuntimeError(
        "DJANGO_SECRET_KEY no está configurada. "
        "Define la variable de entorno en el panel de Render antes de desplegar."
    )

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True