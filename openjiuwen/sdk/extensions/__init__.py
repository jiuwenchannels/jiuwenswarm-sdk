"""SDK extension points — register custom session stores and checkpointers.

Quick start::

    from openjiuwen.sdk.extensions import register_store, register_checkpointer

    register_store("postgres", my_postgres_store)
    register_checkpointer("s3", my_s3_checkpointer)

    agent = await Agent.create("my-agent", ..., checkpoint_store="s3")
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Registries
# ---------------------------------------------------------------------------

_store_registry: dict[str, Any] = {}
_checkpointer_registry: dict[str, Any] = {}


def register_store(name: str, store: Any) -> None:
    """Register a custom session store under *name*.

    Args:
        name:  Registry key (used in ``Agent.create`` and ``Session`` APIs).
        store: A :class:`~openjiuwen.sdk.extensions.store.BaseSessionStore` instance.

    Example::

        register_store("postgres", PostgresSessionStore(dsn="postgresql://..."))
    """
    _store_registry[name] = store


def get_store(name: str) -> Any | None:
    """Return the registered store for *name*, or ``None``."""
    return _store_registry.get(name)


def register_checkpointer(name: str, checkpointer: Any) -> None:
    """Register a custom checkpoint backend under *name*.

    Args:
        name:         Registry key (used in ``Agent.create(checkpoint_store=name)``).
        checkpointer: A :class:`~openjiuwen.sdk.extensions.checkpointer.BaseCheckpointer` instance.

    Example::

        register_checkpointer("s3", S3Checkpointer(bucket="my-checkpoints"))
    """
    _checkpointer_registry[name] = checkpointer


def get_checkpointer(name: str) -> Any | None:
    """Return the registered checkpointer for *name*, or ``None``."""
    return _checkpointer_registry.get(name)


__all__ = [
    "register_store",
    "get_store",
    "register_checkpointer",
    "get_checkpointer",
]
