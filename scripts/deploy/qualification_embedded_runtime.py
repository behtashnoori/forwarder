"""Run a qualification snippet against an embedded Python runtime.

The packaged runtime uses ``python._pth`` safe-path mode, which omits the
working directory.  The release probe must explicitly insert the extracted
application root before importing it.
"""
from __future__ import annotations

import json
from pathlib import Path


def bootstrap_code(application_root: Path, code: str) -> str:
    """Return code that imports only from the supplied extracted release."""
    root = json.dumps(str(application_root.resolve()))
    return f"import sys\nsys.path.insert(0, {root})\n" + code
