"""Alpha — OpenAI GPT-4o audit agent.

Streams reasoning prose to the runner via the `on_message` callback, then
parses the structured JSON vote from the post-`---` portion of the response.
"""

from __future__ import annotations

import json
import time
from typing import Any, Awaitable, Callable, Dict, Optional

from agents._streaming import StreamCollector, parse_json_block
from agents.base import AgentClient, AgentSpec, AgentVote
from agents.prompts import (
    ALPHA_CONTEXT_CLUES,
    ALPHA_SKILLS,
    ALPHA_SYSTEM_PROMPT,
)
from agents.registry import register_audit
from agents.stub import StubAuditAgent
from config import settings

MODEL = "gpt-4o"

SPEC = AgentSpec(
    name="alpha",
    role="audit",
    model=MODEL,
    provider="openai",
    color="violet",
    skills=ALPHA_SKILLS,
    system_prompt=ALPHA_SYSTEM_PROMPT,
    context_clues=ALPHA_CONTEXT_CLUES,
)


class OpenAIAuditAgent:
    spec = SPEC

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def analyze(
        self,
        redacted_payload: Dict[str, Any],
        on_message: Optional[Callable[[str], Awaitable[None]]] = None,
        prior_patterns: Optional[str] = None,
    ) -> AgentVote:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._api_key)
        started = time.perf_counter()

        clues = "\n".join(f"- {c}" for c in self.spec.context_clues)
        user_msg_parts = [f"CONTEXT CLUES:\n{clues}\n"]
        if prior_patterns:
            user_msg_parts.append(prior_patterns + "\n")
        user_msg_parts.append(
            f"REDACTED BILL:\n{json.dumps(redacted_payload, indent=2)}"
        )
        user_msg = "\n".join(user_msg_parts)

        collector = StreamCollector(on_message=on_message)
        try:
            stream = await client.chat.completions.create(
                model=self.spec.model,
                messages=[
                    {"role": "system", "content": self.spec.system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.2,
                max_tokens=1500,
                stream=True,
            )
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    await collector.feed(delta)
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


def _factory() -> AgentClient:
    if settings.openai_api_key:
        return OpenAIAuditAgent(settings.openai_api_key)
    return StubAuditAgent("alpha")


register_audit("alpha", _factory)
