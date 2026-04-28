"""Public provider-reputation endpoint.

Anyone can look up a healthcare provider's audit history by NPI. The
contract on 0G Galileo is the source of truth — Lethe can't fudge the
numbers, can't hide bad providers, can't manipulate the rate.

Routes:
    GET /api/providers/{npi}   — Returns aggregate stats (total audits,
                                 dispute count, total flagged dollars,
                                 dispute rate).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from chain import provider_reputation

router = APIRouter(prefix="/api/providers", tags=["providers"])
log = logging.getLogger("lethe.providers")

_NPI_RE = re.compile(r"^\d{10}$")


@router.get("/{npi}")
async def get_provider(npi: str) -> Dict[str, Any]:
    """Look up aggregate stats for a provider by NPI."""
    npi = npi.strip()
    if not _NPI_RE.match(npi):
        raise HTTPException(status_code=400, detail="NPI must be 10 digits")
    return await provider_reputation.fetch_stats(npi)
