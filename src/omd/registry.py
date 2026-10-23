"""Module registry: every module in a package, found by walking it.

A library module is a file `<package>/<name>.py` that exposes `MODULE`, a `omd.module.Module`.
Adding a module adds that file and its test, and touches nothing else. Files whose name starts
with an underscore are not modules (helpers). A file without `MODULE` is an error, not a skip:
a module that cannot be found must not pass by being invisible.
"""

from __future__ import annotations

import importlib
import pkgutil

from .module import Module


class DiscoveryError(Exception):
    pass


def discover(package: str = "omd.modules") -> dict[str, Module]:
    """Import every non-private module under `package`; return {file name: MODULE}."""
    pkg = importlib.import_module(package)
    if not hasattr(pkg, "__path__"):
        raise DiscoveryError(f"{package} is not a package")
    found: dict[str, Module] = {}
    for info in sorted(pkgutil.iter_modules(pkg.__path__), key=lambda i: i.name):
        if info.name.startswith("_"):
            continue
        qual = f"{package}.{info.name}"
        try:
            mod = importlib.import_module(qual)
        except Exception as e:  # noqa: BLE001 — an import error is a finding, reported per module
            raise DiscoveryError(f"{qual}: import failed: {e!r}") from e
        m = getattr(mod, "MODULE", None)
        if not isinstance(m, Module):
            raise DiscoveryError(f"{qual}: no MODULE (an omd.module.Module) exposed")
        found[info.name] = m
    return found
