"""Gamma — 0G Compute Network audit agent (decentralized inference).

When `LETHE_0G_COMPUTE_ENDPOINT` + `LETHE_0G_COMPUTE_TOKEN` are configured,
agent γ runs on 0G Compute's decentralized inference network instead of
Google Gemini. This satisfies the 0G hackathon track's "use 0G Compute"
requirement — not just 0G Chain.

Implementation: 0G Compute providers expose OpenAI-compatible HTTP at
`<provider>/v1/proxy/chat/completions`, so we use the stock `openai` SDK
with a custom `base_url` + bearer token. The provider runs the model
(default `GLM-5-FP8`) and streams tokens back via SSE — identical wire
format to OpenAI's chat-completions API.

Provisioning (one-time):
  cd src/coordinator/scripts
  npm install
  npm run provision:0g       # picks a provider, deposits to ledger, prints env
  npm run headers:0g         # long-running sidecar that signs each request

NOTE: 0G Compute auth headers are signed against the request body hash and
are single-use — there is no static bearer token. This module talks to a
local Node sidecar (default http://localhost:8787/v1) which signs each
request transparently. `LETHE_0G_COMPUTE_TOKEN` can be any non-empty
string; the sidecar provides the real headers.

Falls back to Google Gemini → Stub if env vars are missing — no behavior
change for users who haven't provisioned a 0G Compute provider yet.
"""

from __future__ import annotations

import json
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional

from agents._streaming import StreamCollector, parse_json_block
from agents.base import AgentSpec, AgentVote
from agents.prompts import (
    GAMMA_CONTEXT_CLUES,
    GAMMA_SKILLS,
    GAMMA_SYSTEM_PROMPT,
    build_reflect_user_msg,
)


class ZGComputeAgent:
    """Drop-in replacement for the Gemini γ agent that runs on 0G Compute.

    Keeps the same `name="gamma"` so the consensus tally and AXL exchange
    don't need to change. The `spec.model` and `spec.provider` honestly reflect
    that inference is happening on 0G Compute — surfaced in /api/status.
    """

    def __init__(
        self,
        endpoint: str,
        token: str,
        model: str,
        provider_address: str = "",
        via_sidecar: bool = False,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._token = token
        self._model = model
        # Display string makes it obvious in logs + /api/status which provider.
        display_model = f"{model} · 0g compute"
        if via_sidecar:
            display_model += " · sidecar"
        if provider_address:
            display_model += f" · {provider_address[:8]}…"
        self.spec = AgentSpec(
            name="gamma",
            role="audit",
            model=display_model,
            provider="0g-compute",
            color="green",
            skills=GAMMA_SKILLS,
            system_prompt=GAMMA_SYSTEM_PROMPT,
            context_clues=GAMMA_CONTEXT_CLUES,
        )

    def _client(self):
        # Lazy import — only loaded if 0G Compute is actually configured.
        from openai import AsyncOpenAI
        return AsyncOpenAI(api_key=self._token, base_url=self._endpoint)

    async def analyze(
        self,
        redacted_payload: Dict[str, Any],
        on_message: Optional[Callable[[str], Awaitable[None]]] = None,
        prior_patterns: Optional[str] = None,
    ) -> AgentVote:
        client = self._client()
        started = time.perf_counter()

        clues = "\n".join(f"- {c}" for c in self.spec.context_clues)
        parts = [f"CONTEXT CLUES:\n{clues}\n"]
        if prior_patterns:
            parts.append(prior_patterns + "\n")
        parts.append(f"REDACTED BILL:\n{json.dumps(redacted_payload, indent=2)}")
        user_msg = "\n".join(parts)

        collector = StreamCollector(on_message=on_message)
        try:
            stream = await client.chat.completions.create(
                model=self._model,
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
            if not data:
                data = {
                    "verdict": "clarify",
                    "confidence": 0.0,
                    "findings": [],
                    "notes": "0g compute returned empty/unparsable response",
                }
        except Exception as e:
            data = {
                "verdict": "clarify",
                "confidence": 0.0,
                "findings": [],
                "notes": f"0g compute error: {type(e).__name__}: {str(e)[:200]}",
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
        peer_received: List[Dict[str, Any]],
        on_message: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> AgentVote:
        """Round-2 reflection on 0G Compute — sees own vote + peer findings."""
        client = self._client()
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
            stream = await client.chat.completions.create(
                model=self._model,
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
            if not data:
                return original_vote
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
