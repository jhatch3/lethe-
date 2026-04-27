"""Drafter — Anthropic Claude appeal-letter generator.

Self-registers at import time. Real LLM if LETHE_ANTHROPIC_API_KEY is set,
otherwise falls back to the template-based stub.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List

from agents.base import AgentSpec, DrafterClient, DraftedLetter
from agents.prompts import (
    DRAFTER_CONTEXT_CLUES,
    DRAFTER_SKILLS,
    DRAFTER_SYSTEM_PROMPT,
)
from agents.registry import register_drafter
from agents.stub import StubDrafter
from config import settings

MODEL = "claude-sonnet-4-5-20250929"

SPEC = AgentSpec(
    name="drafter",
    role="drafter",
    model=MODEL,
    provider="anthropic",
    color="rose",
    skills=DRAFTER_SKILLS,
    system_prompt=DRAFTER_SYSTEM_PROMPT,
    context_clues=DRAFTER_CONTEXT_CLUES,
)


def _extract_json(text: str) -> Dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


class AnthropicDrafter:
    spec = SPEC

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def draft(self, consensus: Dict[str, Any], sha256: str) -> DraftedLetter:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self._api_key)
        started = time.perf_counter()

        # Build the user message: consensus summary + per-finding detail + sha256.
        findings: List[Dict[str, Any]] = consensus.get("findings", [])
        lines = "\n".join(
            f"- {f.get('code')} ({f.get('severity', '?')}): {f.get('description')} "
            f"[${float(f.get('amount_usd', 0)):.2f}] · cite: {f.get('citation', 'n/a')}"
            for f in findings
        ) or "- (no findings reached consensus)"

        clues = "\n".join(f"- {c}" for c in self.spec.context_clues)

        user_msg = (
            f"CONTEXT CLUES:\n{clues}\n\n"
            f"CONSENSUS VERDICT: {consensus.get('verdict')} "
            f"({consensus.get('agree_count', 0)}/{consensus.get('total_agents', 0)})\n"
            f"DISPUTED TOTAL: ${float(consensus.get('disputed_total_usd', 0)):.2f}\n"
            f"FLAGGED TOTAL:  ${float(consensus.get('flagged_total_usd', 0)):.2f}\n"
            f"BILL SHA-256: {sha256}\n\n"
            f"FINDINGS:\n{lines}\n\n"
            "Draft the appeal letter now. Respond with valid JSON only."
        )

        try:
            resp = await client.messages.create(
                model=self.spec.model,
                system=self.spec.system_prompt,
                messages=[{"role": "user", "content": user_msg}],
                max_tokens=2000,
                temperature=0.3,
            )
            text = "".join(
                block.text for block in resp.content if getattr(block, "type", None) == "text"
            )
            data = _extract_json(text)
        except Exception as e:
            # Fall back to the stub on failure so the pipeline always returns something.
            stub = StubDrafter()
            return await stub.draft(consensus, sha256)

        duration_ms = int((time.perf_counter() - started) * 1000)
        return DraftedLetter(
            subject=str(data.get("subject", "Formal dispute · medical bill review")),
            body=str(data.get("body", "")),
            citations=list(data.get("citations", []) or []),
            drafted_by=self.spec.name,
            duration_ms=duration_ms,
        )


def _factory() -> DrafterClient:
    if settings.anthropic_api_key:
        return AnthropicDrafter(settings.anthropic_api_key)
    return StubDrafter()


register_drafter(_factory)