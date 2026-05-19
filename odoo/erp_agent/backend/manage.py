#!/usr/bin/env python
import os
import sys
from pathlib import Path

_ADDON_DIR = Path(__file__).parent.parent
_REPO_ROOT = _ADDON_DIR.parent.parent

for _p in [str(_ADDON_DIR), str(_REPO_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

from django.core.management import execute_from_command_line

execute_from_command_line(sys.argv)
