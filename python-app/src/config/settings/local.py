from .base import *

DEBUG = True
ALLOWED_HOSTS = []

LOGGING = {
    "version": 1,
    "disable_existing_handlers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "infrastructure": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "operaciones": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}