"""Dispute letter stage.

Delegates to whichever drafter is registered. The runner calls this from a
pipeline stage so the LLM call is timed alongside the other stages.

If no drafter is registered (e.g., the project was bootstrapped without
loading the agents package), falls back to a hard-coded template so the
pipeline still produces output.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List

from agents.registry import get_drafter


async def draft(consensus: Dict[str, Any], sha256: str) -> Dict[str, Any]:
    drafter = get_drafter()
    if drafter is not None:
        letter = await drafter.draft(consensus, sha256)
        return letter.public_dict() | {
            "disputed_total_usd": float(consensus.get("disputed_total_usd", 0.0)),
            "anchor_sha256": sha256,
        }

    # Fallback: minimal template, no LLM, no agent.
    started = time.perf_counter()
    await asyncio.sleep(0)
    findings: List[Dict[str, Any]] = consensus.get("findings", [])
    disputed_total = float(consensus.get("disputed_total_usd", 0.0))
    items = "; ".join(
        f"{f['code']} — {str(f['description']).rstrip('.')} (${float(f['amount_usd']):.2f})"
        for f in findings
    ) or "no specific items"
    body = (
        "RE: Account [ACCOUNT] · DOS [DATE-OF-SERVICE]\n\n"
        "To Whom It May Concern,\n\n"
        f"I am formally disputing line items totaling ${disputed_total:.2f} on the referenced "
        f"statement. Independent review identified the following: {items}.\n\n"
        "Pursuant to 45 CFR § 149.620 (No Surprises Act, patient-provider dispute resolution) "
        "and CMS NCCI policy chapter 7, please review and correct these charges within 30 days.\n\n"
        f"This dispute is anchored on 0G Chain at sha256 {sha256} for reference.\n"
    )
    return {
        "subject": "Formal dispute · medical bill review",
        "body": body,
        "citations": ["45 CFR § 149.620", "CMS NCCI policy ch. 7"],
        "drafted_by": "fallback-template",
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "disputed_total_usd": disputed_total,
        "anchor_sha256": sha256,
    }
