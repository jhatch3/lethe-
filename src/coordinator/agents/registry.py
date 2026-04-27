"""Agent registry.

Each agent module registers a factory at import time. The factory decides at
call time whether to return a real LLM-backed agent (if its API key is set)
or a stub fallback. The pipeline runner only ever talks to this registry.

To add an agent:
  1. Drop a new file in agents/<name>.py that calls register_audit() or
     register_drafter().
  2. Add the import to agents/__init__.py so the registration runs.

To remove an agent:
  - Delete the file (or remove the import) — that's it.

To temporarily disable an agent without code changes:
  - Add its name to settings.disabled_agents (LETHE_DISABLED_AGENTS env var).
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from agents.base import AgentClient, AgentSpec, DrafterClient


_AUDIT_FACTORIES: Dict[str, Callable[[], AgentClient]] = {}
_DRAFTER_FACTORY: Optional[Callable[[], DrafterClient]] = None


def register_audit(name: str, factory: Callable[[], AgentClient]) -> None:
    _AUDIT_FACTORIES[name] = factory


def register_drafter(factory: Callable[[], DrafterClient]) -> None:
    global _DRAFTER_FACTORY
    _DRAFTER_FACTORY = factory


def get_audit_agents(disabled: Optional[List[str]] = None) -> List[AgentClient]:
    skip = set(disabled or [])
    return [
        factory()
        for name, factory in _AUDIT_FACTORIES.items()
        if name not in skip
    ]


def get_drafter() -> Optional[DrafterClient]:
    if _DRAFTER_FACTORY is None:
        return None
    return _DRAFTER_FACTORY()


def list_audit_specs(disabled: Optional[List[str]] = None) -> List[AgentSpec]:
    skip = set(disabled or [])
    return [
        factory().spec
        for name, factory in _AUDIT_FACTORIES.items()
        if name not in skip
    ]


def list_audit_names() -> List[str]:
    return list(_AUDIT_FACTORIES.keys())


def has_drafter() -> bool:
    return _DRAFTER_FACTORY is not None