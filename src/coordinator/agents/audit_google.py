"""Gamma — Google Gemini audit agent (streaming)."""

from __future__ import annotations

import asyncio
import json
import queue
import threading
import time
from typing import Any, Awaitable, Callable, Dict, Optional

from agents._streaming import StreamCollector, parse_json_block
from agents.base import AgentClient, AgentSpec, AgentVote
from agents.prompts import (
    GAMMA_CONTEXT_CLUES,
    GAMMA_SKILLS,
    GAMMA_SYSTEM_PROMPT,
)
from agents.registry import register_audit
from agents.stub import StubAuditAgent
from config import settings

MODEL = "gemini-flash-latest"

SPEC = AgentSpec(
    name="gamma",
    role="audit",
    model=MODEL,
    provider="google",
    color="green",
    skills=GAMMA_SKILLS,
    system_prompt=GAMMA_SYSTEM_PROMPT,
    context_clues=GAMMA_CONTEXT_CLUES,
)


_SENTINEL_DONE = object()


class GoogleAuditAgent:
    spec = SPEC

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def analyze(
        self,
        redacted_payload: Dict[str, Any],
        on_message: Optional[Callable[[str], Awaitable[None]]] = None,
        prior_patterns: Optional[str] = None,
    ) -> AgentVote:
        # google-generativeai is sync. Run the streaming iterator in a thread,
        # forward each chunk through a thread-safe queue to the asyncio loop.
        import google.generativeai as genai

        started = time.perf_counter()
        clues = "\n".join(f"- {c}" for c in self.spec.context_clues)
        parts = [f"CONTEXT CLUES:\n{clues}\n"]
        if prior_patterns:
            parts.append(prior_patterns + "\n")
        parts.append(f"REDACTED BILL:\n{json.dumps(redacted_payload, indent=2)}")
        user_msg = "\n".join(parts)

        chunk_queue: "queue.Queue[Any]" = queue.Queue()
        error: list[Exception] = []

        def producer() -> None:
            try:
                genai.configure(api_key=self._api_key)
                model = genai.GenerativeModel(
                    model_name=self.spec.model,
                    system_instruction=self.spec.system_prompt,
                    generation_config={
                        "temperature": 0.2,
                        "max_output_tokens": 6000,
                        # Note: NOT response_mime_type=application/json — we want prose first.
                    },
                )
                resp = model.generate_content(user_msg, stream=True)
                for chunk in resp:
                    try:
                        text = chunk.text or ""
                    except Exception:
                        text = ""
                    if text:
                        chunk_queue.put(text)
            except Exception as e:
                error.append(e)
            finally:
                chunk_queue.put(_SENTINEL_DONE)

        thread = threading.Thread(target=producer, daemon=True)
        thread.start()

        collector = StreamCollector(on_message=on_message)
        try:
            while True:
                item = await asyncio.to_thread(chunk_queue.get)
                if item is _SENTINEL_DONE:
                    break
                await collector.feed(item)
            if error:
                raise error[0]
            _, json_text = await collector.finalize()
            data = parse_json_block(json_text)
            if not data:
                data = {
                    "verdict": "clarify",
                    "confidence": 0.0,
                    "findings": [],
                    "notes": "empty/unparsable response",
                }
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
    if settings.google_api_key:
        return GoogleAuditAgent(settings.google_api_key)
    return StubAuditAgent("gamma")


register_audit("gamma", _factory)