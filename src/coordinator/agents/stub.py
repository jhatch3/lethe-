"""Stub agents — predictable canned behavior.

Used for development and as a fallback when real LLM API keys are not set.
Stubs share the same AgentSpec (skills/system prompt/context clues) as the
real agents — only the analyze/draft implementations differ.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List

from agents.base import AgentClient, AgentSpec, AgentVote, DrafterClient, DraftedLetter
from agents.prompts import (
    ALPHA_CONTEXT_CLUES,
    ALPHA_SKILLS,
    ALPHA_SYSTEM_PROMPT,
    BETA_CONTEXT_CLUES,
    BETA_SKILLS,
    BETA_SYSTEM_PROMPT,
    DRAFTER_CONTEXT_CLUES,
    DRAFTER_SKILLS,
    DRAFTER_SYSTEM_PROMPT,
    GAMMA_CONTEXT_CLUES,
    GAMMA_SKILLS,
    GAMMA_SYSTEM_PROMPT,
)


# ============================================================
# Specs shared between stub and real implementations
# ============================================================

STUB_SPECS: Dict[str, AgentSpec] = {
    "alpha": AgentSpec(
        name="alpha",
        role="audit",
        model="gpt-4o-stub",
        provider="stub",
        color="violet",
        skills=ALPHA_SKILLS,
        system_prompt=ALPHA_SYSTEM_PROMPT,
        context_clues=ALPHA_CONTEXT_CLUES,
    ),
    "beta": AgentSpec(
        name="beta",
        role="audit",
        model="claude-stub",
        provider="stub",
        color="amber",
        skills=BETA_SKILLS,
        system_prompt=BETA_SYSTEM_PROMPT,
        context_clues=BETA_CONTEXT_CLUES,
    ),
    "gamma": AgentSpec(
        name="gamma",
        role="audit",
        model="gemini-stub",
        provider="stub",
        color="green",
        skills=GAMMA_SKILLS,
        system_prompt=GAMMA_SYSTEM_PROMPT,
        context_clues=GAMMA_CONTEXT_CLUES,
    ),
}

DRAFTER_STUB_SPEC = AgentSpec(
    name="drafter",
    role="drafter",
    model="claude-stub",
    provider="stub",
    color="rose",
    skills=DRAFTER_SKILLS,
    system_prompt=DRAFTER_SYSTEM_PROMPT,
    context_clues=DRAFTER_CONTEXT_CLUES,
)


# ============================================================
# Audit stubs — canned findings keyed off agent personality
# ============================================================

CANONICAL_FINDINGS: Dict[str, Dict[str, Any]] = {
    "dup_99214": {
        "id": "dup_99214",
        "severity": "high",
        "code": "CPT 99214",
        "description": "Duplicate office visit billed twice on the same DOS. NCCI flags this combination.",
        "amount_usd": 185.00,
        "action": "dispute",
        "citation": "CMS NCCI policy ch. 7",
    },
    "modifier_25": {
        "id": "modifier_25",
        "severity": "high",
        "code": "Modifier 25",
        "description": "Significant E/M with procedure 96372 — modifier 25 missing from the E/M line.",
        "amount_usd": 118.40,
        "action": "dispute",
        "citation": "AMA CPT modifier 25 guidance",
    },
    "j3490": {
        "id": "j3490",
        "severity": "medium",
        "code": "HCPCS J3490",
        "description": "Unclassified drug code without NDC invoice attached. Insurer typically requires NDC.",
        "amount_usd": 62.20,
        "action": "clarify",
        "citation": "Payer policy · NDC documentation",
    },
    "rev_0450": {
        "id": "rev_0450",
        "severity": "medium",
        "code": "Rev 0450",
        "description": "ER level 5 charge, but documented services align closer to level 3.",
        "amount_usd": 121.60,
        "action": "clarify",
        "citation": "CMS ER acuity guidelines",
    },
}

STUB_BEHAVIOR: Dict[str, Dict[str, Any]] = {
    "alpha": {
        "confidence": 0.91,
        "latency_s": 1.1,
        "emphasized": ["dup_99214", "modifier_25", "j3490"],
        "stream": [
            "▸ payload received · 14 line items",
            "▸ cross-ref CMS NCCI policy 7.1",
            "▸ flag CPT 99214 duplicate · DOS 2026-04-14",
            "▸ flag modifier 25 missing on E/M",
            "▸ vote: dispute · conf 0.91",
        ],
    },
    "beta": {
        "confidence": 0.94,
        "latency_s": 1.3,
        "emphasized": ["dup_99214", "modifier_25", "rev_0450", "j3490"],
        "stream": [
            "▸ ed25519:7f3a peer linked · α γ ok",
            "▸ scoring 14 entries · payer alignment",
            "▸ flag Rev 0450 ER acuity over-coded",
            "▸ flag 99214 + missing modifier 25",
            "▸ vote: dispute · conf 0.94",
        ],
    },
    "gamma": {
        "confidence": 0.88,
        "latency_s": 0.9,
        "emphasized": ["dup_99214", "j3490", "rev_0450"],
        "stream": [
            "▸ AXL handshake · 2 peers handshaken",
            "▸ indexing CPT / HCPCS · 14 entries",
            "▸ flag HCPCS J3490 missing NDC",
            "▸ flag 99214 duplicate billing",
            "▸ vote: dispute · conf 0.88",
        ],
    },
}


class StubAuditAgent:
    def __init__(self, name: str) -> None:
        if name not in STUB_SPECS:
            raise ValueError(f"unknown stub audit agent: {name}")
        self.spec: AgentSpec = STUB_SPECS[name]
        self._behavior = STUB_BEHAVIOR[name]

    async def analyze(
        self,
        redacted_payload: Dict[str, Any],
        on_message=None,
        prior_patterns=None,
    ) -> AgentVote:
        started = time.perf_counter()
        # Replay the canned stream lines via the real-time callback if provided.
        if on_message is not None:
            for line in self._behavior.get("stream", []):
                try:
                    await on_message(line)
                except Exception:
                    pass
                await asyncio.sleep(self._behavior["latency_s"] / max(1, len(self._behavior.get("stream", [1]))))
        else:
            await asyncio.sleep(self._behavior["latency_s"])
        findings: List[Dict[str, Any]] = [
            CANONICAL_FINDINGS[fid]
            for fid in self._behavior["emphasized"]
            if fid in CANONICAL_FINDINGS
        ]
        duration_ms = int((time.perf_counter() - started) * 1000)
        return AgentVote(
            agent=self.spec.name,
            model=self.spec.model,
            verdict="dispute" if findings else "approve",
            confidence=float(self._behavior["confidence"]),
            findings=findings,
            notes=f"{len(findings)} issues identified (stub).",
            duration_ms=duration_ms,
        )

    def stream_template(self) -> List[str]:
        return list(self._behavior["stream"])


# ============================================================
# Drafter stub — template-based appeal letter
# ============================================================

class StubDrafter:
    spec = DRAFTER_STUB_SPEC

    async def draft(self, consensus: Dict[str, Any], sha256: str) -> DraftedLetter:
        started = time.perf_counter()
        await asyncio.sleep(0.4)
        findings: List[Dict[str, Any]] = consensus.get("findings", [])
        disputed_total = float(consensus.get("disputed_total_usd", 0.0))
        flagged_total = float(consensus.get("flagged_total_usd", 0.0))

        item_lines = "; ".join(
            f"{f['code']} — {str(f['description']).rstrip('.')} (${float(f['amount_usd']):.2f})"
            for f in findings
        ) or "no specific items"

        body = (
            "RE: Account [ACCOUNT] · DOS [DATE-OF-SERVICE]\n\n"
            "To Whom It May Concern,\n\n"
            f"I am formally disputing line items totaling ${flagged_total:.2f} on the referenced "
            f"statement (${disputed_total:.2f} as outright dispute, the remainder requested for "
            f"clarification). Independent review identified the following: {item_lines}.\n\n"
            "Pursuant to 45 CFR § 149.620 (No Surprises Act, patient-provider dispute resolution) "
            "and CMS NCCI policy chapter 7, I request that these charges be reviewed and corrected, "
            "and an itemized statement reflecting the corrected balance be issued within 30 days.\n\n"
            f"This dispute is anchored on 0G Chain at sha256 {sha256} for reference. "
            "Please direct correspondence to the address on file.\n"
        )
        return DraftedLetter(
            subject="Formal dispute · medical bill review",
            body=body,
            citations=[
                "45 CFR § 149.620",
                "CMS NCCI policy ch. 7",
                "AMA CPT modifier 25 guidance",
            ],
            drafted_by=self.spec.name,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )