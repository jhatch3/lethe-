"""Payer (insurance) claim submission router.

POST /api/payer/submit
    body: {
      job_id: str,                     # which audit
      payer_id: str,                   # which payer/clearinghouse
      patient: { member_id?, dob?, plan_id? },  # optional
    }

Pulls the audit's findings from the job store, builds a claim payload,
hands off to the adapter via `payer.submit.submit_claim()`. Returns the
adapter's response shape.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from payer import submit as payer_submit
from store.memory import store

log = logging.getLogger("lethe.payer")
router = APIRouter(prefix="/api/payer", tags=["payer"])


class PayerSubmitBody(BaseModel):
    job_id: str
    payer_id: str = "stedi-test"
    member_id: Optional[str] = None
    plan_id: Optional[str] = None
    patient_dob: Optional[str] = None  # ISO yyyy-mm-dd (never persisted)


def _build_claim_payload(result: Dict[str, Any], body: PayerSubmitBody, sha: str) -> Dict[str, Any]:
    consensus = (result or {}).get("consensus") or {}
    findings: List[Dict[str, Any]] = list(consensus.get("findings") or [])
    disputed_codes = []
    for f in findings:
        disputed_codes.append({
            "cpt": str(f.get("code") or ""),
            "action": str(f.get("action") or ""),
            "severity": str(f.get("severity") or ""),
            "charge_cents": int(round(float(f.get("amount_usd") or 0) * 100)),
            "voted_by": list(f.get("voted_by") or []),
        })
    return {
        "payer_id": body.payer_id,
        "patient": {
            "member_id": body.member_id,
            "plan_id": body.plan_id,
            "dob": body.patient_dob,  # passed through; not persisted
        },
        "provider_npi": (result.get("provider_reputation") or {}).get("npi_extracted"),
        "bill_sha256": sha,
        "verdict": consensus.get("verdict"),
        "agree_count": consensus.get("agree_count"),
        "total_agents": consensus.get("total_agents"),
        "disputed_codes": disputed_codes,
        "attachments": {
            # Don't include the actual letter — adapters that need it pull
            # from the existing receipt. This keeps the payer payload PHI-free.
            "verify_url_path": f"/verify?sha={sha}",
        },
    }


@router.post("/submit")
async def submit_to_payer(body: PayerSubmitBody) -> Dict[str, Any]:
    job = await store.get(body.job_id)
    if job is None:
        raise HTTPException(status_code=410, detail="job not found or expired")
    if not job.result:
        raise HTTPException(status_code=409, detail="job has no result yet")

    sha = ("0x" + job.sha256) if not job.sha256.startswith("0x") else job.sha256
    payload = _build_claim_payload(job.result, body, sha)
    return await payer_submit.submit_claim(payload)


@router.get("/adapters")
async def list_adapters() -> Dict[str, Any]:
    """List which adapters are wired vs scaffolded — for the dashboard button."""
    return {
        "active": payer_submit._ADAPTERS,
        "registered_keys": list(payer_submit._ADAPTERS.keys()),
    }
