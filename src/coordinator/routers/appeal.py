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
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from chain import keeperhub
from email_delivery.sender import send_email
from email_delivery.template import build_appeal_email_html
from store.memory import store

log = logging.getLogger("lethe.appeal")

router = APIRouter(prefix="/api/appeal", tags=["appeal"])


class AppealSubmitBody(BaseModel):
    job_id: str
    recipient_email: EmailStr


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
    drafted = (result or {}).get("drafted") or {}
    body = drafted.get("body") or drafted.get("letter") or drafted.get("text")
    if not body:
        # Fallback: a one-liner so the email isn't empty if drafting hasn't
        # happened or got skipped.
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
    letter_md = _extract_appeal_letter(result)

    html = build_appeal_email_html(
        appeal_letter_markdown=letter_md,
        bill_sha256=bill_sha,
        verdict=consensus["verdict"],
        agree_count=consensus["agree_count"],
        total_agents=consensus["total_agents"],
        proof=proof,
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