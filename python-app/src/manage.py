#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
    # Tests always run against SQLite, regardless of PERSISTENCE_BACKEND in .env.
    # load_dotenv() in base.py does NOT override env vars already set (default behavior),
    # so setting this here before Django loads ensures tests stay isolated from
    # production .env config.
    if 'test' in sys.argv:
        os.environ['PERSISTENCE_BACKEND'] = 'sqlite'
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
