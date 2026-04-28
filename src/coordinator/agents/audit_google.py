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
    build_reflect_user_msg,
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


    async def reflect(
        self,
        redacted_payload: Dict[str, Any],
        original_vote: AgentVote,
        peer_received: list,
        on_message: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> AgentVote:
        """Round-2 LLM call — sees own vote + peers' findings, returns revised vote."""
        import google.generativeai as genai

        started = time.perf_counter()
        user_msg = build_reflect_user_msg(
            redacted_payload=redacted_payload,
            original_verdict=original_vote.verdict,
            original_confidence=original_vote.confidence,
            original_findings=original_vote.findings,
            peer_received=peer_received,
        )

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


def _zg_compute_reachable() -> bool:
    """Quick TCP probe of the 0G Compute endpoint. Used by the factory to
    silently fall back to Gemini when the sidecar isn't running, so the user
    never sees `APIConnectionError` mid-audit and `/api/status` honestly
    reports γ as `google` instead of stale `0g-compute`.
    """
    import socket
    from urllib.parse import urlparse

    try:
        parsed = urlparse(settings.zg_compute_endpoint)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if not host:
            return False
        with socket.create_connection((host, port), timeout=1.5):
            return True
    except Exception:
        return False


def _factory() -> AgentClient:
    # Preference order for γ:
    #   1. 0G Compute (decentralized inference) — only if endpoint is reachable
    #   2. Google Gemini (default real LLM)
    #   3. Stub (when no provider is configured)
    import logging
    log = logging.getLogger("lethe.agent.gamma")

    if settings.zg_compute_endpoint and settings.zg_compute_token:
        if _zg_compute_reachable():
            from agents.audit_0g import ZGComputeAgent
            log.info("gamma → 0G Compute via %s", settings.zg_compute_endpoint)
            return ZGComputeAgent(
                endpoint=settings.zg_compute_endpoint,
                token=settings.zg_compute_token,
                model=settings.zg_compute_model,
                provider_address=settings.zg_compute_provider_address,
                via_sidecar=settings.zg_compute_sidecar,
            )
        log.warning(
            "gamma · 0G Compute endpoint %s unreachable — falling back to Gemini. "
            "Start the headers sidecar (`npm run headers:0g`) to enable decentralized inference.",
            settings.zg_compute_endpoint,
        )
    if settings.google_api_key:
        return GoogleAuditAgent(settings.google_api_key)
    return StubAuditAgent("gamma")


register_audit("gamma", _factory)