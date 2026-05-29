"""Корневой conftest: импорт `app` при любом способе запуска pytest."""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_root = str(_ROOT)
if _root not in sys.path:
    sys.path.insert(0, _root)
