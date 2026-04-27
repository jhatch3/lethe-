"""Agent contracts.

Every agent in the system — audit or drafter, stub or real — implements one
of these protocols and exposes an AgentSpec. The pipeline runner only ever
talks to these protocols; it never imports a concrete agent directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol


@dataclass
class AgentSpec:
    """Identity + capabilities of an agent. Surfaced in /api/status."""
    name: str            # alpha | beta | gamma | drafter | ...
    role: str            # "audit" | "drafter"
    model: str           # gpt-4o | claude-sonnet-4-6 | gemini-1.5-pro | ...
    provider: str        # openai | anthropic | google | stub
    color: str           # violet | amber | green | rose | cyan
    skills: List[str]
    system_prompt: str
    context_clues: List[str] = field(default_factory=list)

    def public_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "model": self.model,
            "provider": self.provider,
            "color": self.color,
            "skills": self.skills,
            "context_clue_count": len(self.context_clues),
            "system_prompt_chars": len(self.system_prompt),
        }


@dataclass
class AgentVote:
    agent: str
    model: str
    verdict: str         # dispute | approve | clarify
    confidence: float    # 0..1
    findings: List[Dict[str, Any]]
    notes: str
    duration_ms: int
    # Findings this agent received from peers via AXL after their own reasoning.
    # Each entry: {from_agent, from_peer_id, verdict, finding_count, summary}.
    # Empty when AXL is disabled.
    peer_received: List[Dict[str, Any]] = field(default_factory=list)

    def public_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent,
            "model": self.model,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "findings": self.findings,
            "notes": self.notes,
            "duration_ms": self.duration_ms,
            "peer_received": self.peer_received,
        }


@dataclass
class DraftedLetter:
    subject: str
    body: str
    citations: List[str]
    drafted_by: str
    duration_ms: int

    def public_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject,
            "body": self.body,
            "citations": self.citations,
            "drafted_by": self.drafted_by,
            "duration_ms": self.duration_ms,
        }


class AgentClient(Protocol):
    spec: AgentSpec

    async def analyze(self, redacted_payload: Dict[str, Any]) -> AgentVote: ...

    async def reflect(
        self,
        redacted_payload: Dict[str, Any],
        original_vote: AgentVote,
        peer_received: List[Dict[str, Any]],
    ) -> AgentVote:
        """Round-2 LLM call after the AXL findings exchange.

        Sees the agent's own round-1 vote plus all findings received from peers.
        Returns a revised AgentVote (may be identical to original if no revision).
        Optional — falls back to the original vote if not implemented.
        """
        ...


class DrafterClient(Protocol):
    spec: AgentSpec

    async def draft(
        self,
        consensus: Dict[str, Any],
        sha256: str,
    ) -> DraftedLetter: ...
