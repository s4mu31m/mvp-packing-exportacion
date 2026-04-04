"""
Setup de entorno para scripts standalone de Dataverse.

Importar este módulo ANTES de cualquier import de infrastructure.*

Hace tres cosas:
  1. Agrega python-app/src al sys.path para que los imports de infra funcionen.
  2. Carga las variables de entorno desde python-app/src/.env (si existe).
  3. Configura django.conf.settings con los valores Dataverse sin levantar la
     app Django completa — suficiente para que DataverseTokenProvider y
     DataverseClient funcionen sin manage.py ni INSTALLED_APPS.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# ── 1. sys.path ──────────────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC = _REPO_ROOT / "python-app" / "src"

if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# ── 2. .env ───────────────────────────────────────────────────────────────────
# Buscar .env en orden: raíz repo → python-app/ → python-app/src/
try:
    from dotenv import load_dotenv
    for _candidate in [
        _REPO_ROOT / ".env",
        _REPO_ROOT / "python-app" / ".env",
        _SRC / ".env",
    ]:
        if _candidate.exists():
            load_dotenv(_candidate)
            break
except ImportError:
    pass  # python-dotenv no instalado; usar variables del sistema

# ── 3. Django settings minimal ────────────────────────────────────────────────
from django.conf import settings as _dj

if not _dj.configured:
    _dj.configure(
        DATAVERSE_URL=os.getenv("DATAVERSE_URL", "").rstrip("/"),
        DATAVERSE_TENANT_ID=os.getenv("DATAVERSE_TENANT_ID", ""),
        DATAVERSE_CLIENT_ID=os.getenv("DATAVERSE_CLIENT_ID", ""),
        DATAVERSE_CLIENT_SECRET=os.getenv("DATAVERSE_CLIENT_SECRET", ""),
        DATAVERSE_API_VERSION=os.getenv("DATAVERSE_API_VERSION", "v9.2"),
        DATAVERSE_TIMEOUT=int(os.getenv("DATAVERSE_TIMEOUT", "30")),
    )
