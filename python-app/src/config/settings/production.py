import os

from .base import *

DEBUG = False
from .base import *

DEBUG = False
ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = ["https://mvp-packing-exportacion.onrender.com"]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True