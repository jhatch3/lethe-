"""Public NCCI rulebook endpoint.

Exposes the active CMS NCCI ruleset stored on-chain. Anyone can call this
and get the same rules the audit agents see — no Lethe-side database, no
hidden ruleset, no "trust us, we follow CMS."
"""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter

from chain import ncci_rulebook

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("")
async def get_rules() -> Dict[str, Any]:
    """Return the current on-chain NCCI ruleset."""
    return await ncci_rulebook.fetch_active_rules()
