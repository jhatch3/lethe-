"""Appeal submission router.

POST /api/appeal/submit
    body: {job_id: str, recipient_email: str}

Flow:
    1. Look up the completed job result from the store.
    2. Build the formatted HTML email (appeal letter + chain verification).
    3. Send via the configured email provider (resend / smtp / stub).
    4. Fire KH workflow #3 — record on-chain that the appeal was sent
       (recipient address is keccak-hashed, never stored plaintext).
    5. Return the email + on-chain attestation status to the client.

Stub-fallback at every layer so the UI flow works end-to-end without email
or chain credentials configured.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from chain import keeperhub
from email_delivery.sender import send_email
from email_delivery.template import build_appeal_email_html
from store.memory import store

log = logging.getLogger("lethe.appeal")

router = APIRouter(prefix="/api/appeal", tags=["appeal"])

# Pragmatic email regex — enough to catch typos / empty fields without pulling
# in the email-validator package as a hard dependency.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AppealSubmitBody(BaseModel):
    job_id: str
    recipient_email: str
    # Frontend sends the user's fully-composed letter (structured form fields
    # filled in + any body edits) so the email reflects exactly what they see
    # on screen, not the drafter's untouched output. Optional — falls back to
    # _extract_appeal_letter(result) if missing or blank.
    letter_override: Optional[str] = None

    @field_validator("recipient_email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        v = v.strip()
        if not _EMAIL_RE.match(v):
            raise ValueError("recipient_email must be a valid email address")
        return v


def _recipient_hash_hex(email: str, bill_sha: str) -> str:
    """keccak256(email | ":" | bill_sha) — bill hash acts as the salt so the
    same email to two different bills produces two different on-chain hashes
    (so explorers can't trivially correlate one provider across audits).
    """
    try:
        from web3 import Web3
        digest = Web3.keccak(text=f"{email.strip().lower()}:{bill_sha}")
        h = digest.hex()
        return h if h.startswith("0x") else "0x" + h
    except Exception:
        # Fallback: SHA-256 of the same input. Different hash function but
        # still 32 bytes; the contract just stores opaque bytes32.
        h = hashlib.sha256(f"{email.strip().lower()}:{bill_sha}".encode()).hexdigest()
        return "0x" + h


def _extract_appeal_letter(result: Dict[str, Any]) -> str:
    """The runner stores the drafter's output under `result["dispute"]` (an
    alias for the drafted letter, set in pipeline/runner.py:511). Older code
    paths used `drafted` — try both for resilience.
    """
    src = (
        (result or {}).get("dispute")
        or (result or {}).get("drafted")
        or {}
    )
    body = src.get("body") or src.get("letter") or src.get("text") or src.get("draft")
    if not body:
        return (
            "(No drafted appeal letter is available for this audit. The "
            "consensus findings + chain verification below are still valid.)"
        )
    return str(body)


def _extract_consensus(result: Dict[str, Any]) -> Dict[str, Any]:
    consensus = (result or {}).get("consensus") or (result or {}).get("verdict") or {}
    return {
        "verdict": str(consensus.get("verdict", result.get("verdict", "unknown"))),
        "agree_count": int(consensus.get("agree_count", 0) or 0),
        "total_agents": int(consensus.get("total_agents", 3) or 3),
    }


@router.post("/submit")
async def submit_appeal(body: AppealSubmitBody) -> Dict[str, Any]:
    job = await store.get(body.job_id)
    if job is None:
        raise HTTPException(status_code=410, detail="job not found or expired")
    result: Optional[Dict[str, Any]] = job.result
    if not result:
        raise HTTPException(status_code=409, detail="job has no result yet")

    bill_sha = "0x" + job.sha256 if not job.sha256.startswith("0x") else job.sha256
    proof = result.get("proof") or {}
    consensus = _extract_consensus(result)
    # Prefer the frontend-composed letter (with the user's filled-in structured
    # fields + any body edits). Fall back to the drafter's untouched output
    # only if the override is missing or blank.
    override = (body.letter_override or "").strip()
    letter_md = override if override else _extract_appeal_letter(result)

    from config import settings as _s
    html = build_appeal_email_html(
        appeal_letter_markdown=letter_md,
        bill_sha256=bill_sha,
        verdict=consensus["verdict"],
        agree_count=consensus["agree_count"],
        total_agents=consensus["total_agents"],
        proof=proof,
        public_url=_s.public_url,
    )
    subject = (
        f"Lethe audit — {consensus['verdict']} consensus — "
        f"bill {bill_sha[:10]}…"
    )

    email_result = await send_email(to=body.recipient_email, subject=subject, html=html)

    # Fire the third KH workflow regardless of email outcome — the on-chain
    # attestation just records "we attempted to send"; provenance is the
    # point. If you'd prefer it gates on email success, swap the order and
    # bail early on email failure.
    recipient_hash = _recipient_hash_hex(body.recipient_email, bill_sha[2:])
    attestation = await keeperhub.attest_appeal_sent_via_keeperhub(
        sha256_hex=bill_sha,
        recipient_hash_hex=recipient_hash,
    )

    log.info(
        "appeal submit job=%s sent=%s provider=%s attest=%s tx=%s",
        body.job_id,
        email_result.get("sent"),
        email_result.get("provider"),
        attestation.get("status"),
        (attestation.get("tx_hash") or "")[:18],
    )

    return {
        "job_id": body.job_id,
        "recipient": body.recipient_email,
        "recipient_hash": recipient_hash,
        "bill_sha256": bill_sha,
        "email": email_result,
        "attestation": attestation,
    }