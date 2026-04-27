"""Beta — Anthropic Claude audit agent (streaming)."""

from __future__ import annotations

import json
import time
from typing import Any, Awaitable, Callable, Dict, Optional

from agents._streaming import StreamCollector, parse_json_block
from agents.base import AgentClient, AgentSpec, AgentVote
from agents.prompts import (
    BETA_CONTEXT_CLUES,
    BETA_SKILLS,
    BETA_SYSTEM_PROMPT,
    build_reflect_user_msg,
)
from agents.registry import register_audit
from agents.stub import StubAuditAgent
from config import settings

MODEL = "claude-sonnet-4-5-20250929"

SPEC = AgentSpec(
    name="beta",
    role="audit",
    model=MODEL,
    provider="anthropic",
    color="amber",
    skills=BETA_SKILLS,
    system_prompt=BETA_SYSTEM_PROMPT,
    context_clues=BETA_CONTEXT_CLUES,
)


class AnthropicAuditAgent:
    spec = SPEC

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def analyze(
        self,
        redacted_payload: Dict[str, Any],
        on_message: Optional[Callable[[str], Awaitable[None]]] = None,
        prior_patterns: Optional[str] = None,
    ) -> AgentVote:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self._api_key)
        started = time.perf_counter()

        clues = "\n".join(f"- {c}" for c in self.spec.context_clues)
        parts = [f"CONTEXT CLUES:\n{clues}\n"]
        if prior_patterns:
            parts.append(prior_patterns + "\n")
        parts.append(f"REDACTED BILL:\n{json.dumps(redacted_payload, indent=2)}")
        user_msg = "\n".join(parts)

        collector = StreamCollector(on_message=on_message)
        try:
            async with client.messages.stream(
                model=self.spec.model,
                system=self.spec.system_prompt,
                messages=[{"role": "user", "content": user_msg}],
                max_tokens=1500,
                temperature=0.2,
            ) as stream:
                async for text in stream.text_stream:
                    if text:
                        await collector.feed(text)
            _, json_text = await collector.finalize()
            data = parse_json_block(json_text)
        except Exception as e:
            data = {
                "verdict": "clarify",
                "confidence": 0.0,
                "findings": [],
                "notes": f"agent error: {type(e).__name__}: {str(e)[:200]}",
            }
        duration_ms = int((time.perf_counter() - started) * 1000)
        return AgentVote(
            agent=self.spec.name,
            model=self.spec.model,
            verdict=str(data.get("verdict", "clarify")),
            confidence=float(data.get("confidence", 0.0) or 0.0),
            findings=list(data.get("findings", []) or []),
            notes=str(data.get("notes", "") or ""),
            duration_ms=duration_ms,
        )


    async def reflect(
        self,
        redacted_payload: Dict[str, Any],
        original_vote: AgentVote,
        peer_received: list,
        on_message: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> AgentVote:
        """Round-2 LLM call — sees own vote + peers' findings, returns revised vote."""
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self._api_key)
        started = time.perf_counter()

        user_msg = build_reflect_user_msg(
            redacted_payload=redacted_payload,
            original_verdict=original_vote.verdict,
            original_confidence=original_vote.confidence,
            original_findings=original_vote.findings,
            peer_received=peer_received,
        )

        collector = StreamCollector(on_message=on_message)
        try:
            async with client.messages.stream(
                model=self.spec.model,
                system=self.spec.system_prompt,
                messages=[{"role": "user", "content": user_msg}],
                max_tokens=1500,
                temperature=0.2,
            ) as stream:
                async for text in stream.text_stream:
                    if text:
                        await collector.feed(text)
            _, json_text = await collector.finalize()
            data = parse_json_block(json_text)
        except Exception:
            return original_vote

        duration_ms = int((time.perf_counter() - started) * 1000)
        return AgentVote(
            agent=self.spec.name,
            model=self.spec.model,
            verdict=str(data.get("verdict", original_vote.verdict)),
            confidence=float(data.get("confidence", original_vote.confidence) or 0.0),
            findings=list(data.get("findings", []) or []),
            notes=str(data.get("notes", "") or ""),
            duration_ms=duration_ms,
            peer_received=peer_received,
        )


def _factory() -> AgentClient:
    if settings.anthropic_api_key:
        return AnthropicAuditAgent(settings.anthropic_api_key)
    return StubAuditAgent("beta")


register_audit("beta", _factory)