"""Payer claim submission — stubbed for the hackathon.

Pretends to file a claim with whichever payer adapter is configured. Real
adapters (Stedi, Change Healthcare, Availity, direct FHIR) get wired into
the dispatch table below as they become available.

The stub:
- Validates the request shape.
- Generates a deterministic mock claim ID derived from the bill SHA + payer.
- Returns a result that matches the live response schema, so swapping in a
  real adapter doesn't change the caller.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional

from config import settings

log = logging.getLogger("lethe.payer.submit")


# Adapter registry. Each adapter is an async callable that takes the payload
# dict and returns a result dict. Today only stub is implemented.
_ADAPTERS: Dict[str, str] = {
    "stub":     "stub-only — generates a mock claim id, returns success",
    "stedi":    "Stedi REST API (X12 837) — TODO: wire SDK + sandbox creds",
    "availity": "Availity FHIR R4 + Web Services — TODO: wire OAuth + claim resource",
    "ch":       "Change Healthcare clearinghouse — TODO: wire SOAP/REST",
    "fhir":     "Direct payer FHIR — TODO: per-plan endpoint registry",
}


def _mock_claim_id(payload: Dict[str, Any]) -> str:
    """Deterministic-ish mock claim id so re-submissions of the same bill
    against the same payer produce the same id."""
    seed = (
        f"{payload.get('payer_id','?')}::"
        f"{payload.get('bill_sha256','?')}::"
        f"{payload.get('provider_npi','?')}"
    )
    digest = hashlib.sha256(seed.encode()).hexdigest()
    return f"CLM-{digest[:12].upper()}"


def _validate(payload: Dict[str, Any]) -> Optional[str]:
    if not isinstance(payload, dict):
        return "payload must be an object"
    if not payload.get("bill_sha256"):
        return "bill_sha256 required"
    if not payload.get("payer_id"):
        return "payer_id required"
    if not payload.get("disputed_codes") or not isinstance(payload["disputed_codes"], list):
        return "disputed_codes (list) required"
    return None


async def submit_claim(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch the claim filing to the adapter named by `settings.payer_adapter`.

    Returns the adapter's response, or a stub-shaped response when no real
    adapter is configured. Always returns; never raises.
    """
    err = _validate(payload)
    if err:
        return {"submitted": False, "adapter": "stub", "error": err}

    adapter = (settings.payer_adapter or "stub").strip().lower()
    started = time.perf_counter()

    if adapter not in _ADAPTERS:
        return {
            "submitted": False,
            "adapter": adapter,
            "error": f"unknown adapter '{adapter}' — known: {list(_ADAPTERS)}",
        }

    if adapter != "stub":
        log.warning(
            "payer adapter %s requested but not yet implemented — stubbing",
            adapter,
        )

    # Stub path (also used as the response shape for real adapters):
    claim_id = _mock_claim_id(payload)
    duration_ms = int((time.perf_counter() - started) * 1000)
    log.info(
        "payer submit (%s/stub) bill=%s codes=%d → %s",
        adapter,
        (payload["bill_sha256"] or "")[:14],
        len(payload.get("disputed_codes", [])),
        claim_id,
    )
    return {
        "submitted": True,
        "adapter": f"{adapter} (stub)",
        "live": False,
        "claim_id": claim_id,
        "payer_id": payload["payer_id"],
        "bill_sha256": payload["bill_sha256"],
        "disputed_count": len(payload.get("disputed_codes", [])),
        "submitted_at": int(time.time()),
        "duration_ms": duration_ms,
        "stub_note": (
            "Real adapter not yet wired. When configured (Stedi / Availity / "
            "Change Healthcare / direct FHIR), swap LETHE_PAYER_ADAPTER from "
            "'stub' to the adapter name and provide the corresponding API "
            "credentials. Response schema stays identical."
        ),
    }
