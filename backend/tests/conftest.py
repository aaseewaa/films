"""Общая настройка pytest: путь к `app`, маркеры по умолчанию."""
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_ROOT = str(_BACKEND_ROOT)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def pytest_configure(config) -> None:
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)


def pytest_collection_modifyitems(config, items) -> None:
    """Автометки: unit/ → unit, integration/ → integration."""
    for item in items:
        path = Path(str(item.fspath))
        rel = path.relative_to(Path(__file__).parent)
        parts = rel.parts
        if not parts:
            continue
        level = parts[0]
        if level == "unit" and "unit" not in item.keywords:
            item.add_marker("unit")
        elif level == "integration" and "integration" not in item.keywords:
            item.add_marker("integration")
