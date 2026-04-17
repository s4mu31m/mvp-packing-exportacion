"""
Shim de compatibilidad para `python manage.py test operaciones`.

La suite real vive en `python-app/tests/unit/operaciones/`.
"""
import importlib
import pkgutil
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _expose_test_classes():
    package = importlib.import_module("tests.unit.operaciones")
    for module_info in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        module_name = module_info.name
        if ".test_" not in module_name:
            continue
        module = importlib.import_module(module_name)
        for attr_name, attr_value in vars(module).items():
            if not isinstance(attr_value, type):
                continue
            globals().setdefault(attr_name, attr_value)


_expose_test_classes()


def load_tests(loader, tests, pattern):
    start_dir = PROJECT_ROOT / "tests" / "unit" / "operaciones"
    return loader.discover(
        start_dir=str(start_dir),
        pattern=pattern or "test*.py",
        top_level_dir=str(PROJECT_ROOT),
    )
