"""Shared pytest fixtures and startup hooks for the SDK test suite.

Namespace-package fix
---------------------
The SDK's editable install registers an ``openjiuwen`` namespace that only
contains the SDK's own directory.  When the openjiuwen runtime package is
also installed (editable) in the same virtual environment, its directory
needs to be merged into ``openjiuwen.__path__`` so that sub-packages like
``openjiuwen.core`` and ``openjiuwen.harness`` remain importable.

This conftest ensures the merge happens once, before any test module is
collected.
"""

from __future__ import annotations

import sys


def _fix_openjiuwen_namespace() -> None:
    """Merge the runtime package's path into openjiuwen.__path__ if needed."""
    try:
        import importlib
        import importlib.util

        # Import openjiuwen to materialise the namespace package object.
        import openjiuwen  # noqa: F401

        # Collect paths the runtime editable finder knows about.
        runtime_finder_name = "__editable___openjiuwen_0_1_14_finder"
        runtime_finder_mod = sys.modules.get(runtime_finder_name)
        if runtime_finder_mod is None:
            # Try importing it directly from site-packages.
            try:
                runtime_finder_mod = importlib.import_module(runtime_finder_name)
            except ImportError:
                return

        runtime_pkg_dir: str | None = getattr(runtime_finder_mod, "MAPPING", {}).get(
            "openjiuwen"
        )
        if runtime_pkg_dir is None:
            return

        # If the runtime path is not yet in openjiuwen.__path__, add it.
        current_paths = list(openjiuwen.__path__)
        if runtime_pkg_dir not in current_paths:
            openjiuwen.__path__ = list(current_paths) + [runtime_pkg_dir]  # type: ignore[assignment]

    except Exception:  # noqa: BLE001
        # Non-fatal — tests that need the runtime will skip/fail gracefully.
        pass


_fix_openjiuwen_namespace()
