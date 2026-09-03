"""Load individual integration modules without importing Home Assistant.

``custom_components.eastron_sdm72d.__init__`` imports Home Assistant, which is
not a test dependency here. The helper below binds selected modules into a
synthetic package so their relative imports resolve, letting the Home
Assistant-free parts of the integration be tested on their own.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types

INTEGRATION_DIR = (
    Path(__file__).resolve().parent.parent / "custom_components" / "eastron_sdm72d"
)
_PACKAGE = "sdm72d_under_test"


def load_module(name: str) -> types.ModuleType:
    """Import one integration module by name, with its siblings available."""
    if _PACKAGE not in sys.modules:
        package = types.ModuleType(_PACKAGE)
        package.__path__ = [str(INTEGRATION_DIR)]
        sys.modules[_PACKAGE] = package

    qualified = f"{_PACKAGE}.{name}"
    if qualified in sys.modules:
        return sys.modules[qualified]

    spec = importlib.util.spec_from_file_location(
        qualified, INTEGRATION_DIR / f"{name}.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified] = module
    spec.loader.exec_module(module)
    return module
