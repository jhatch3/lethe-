"""Consensus tally.

A finding only enters the final result if at least 2 of 3 agents flagged it.
The verdict is the majority verdict, and confidence is the mean across agents
that voted that way. When no verdict has a majority (e.g. 1-1-1 split), the
verdict falls back to "clarify" rather than letting insertion order decide —
"we could not agree" is more honest than picking whichever agent ran first.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List

from agents.base import AgentVote

# Canonical billing code: type + identifier. Anything after that
# (e.g. "(lines 3-4)", "Office Visit") is annotation, not part of the key.
_CODE_RE = re.compile(
    r"^\s*(cpt|hcpcs|icd|rev|modifier|mod)\s+([a-z0-9.\-]+)",
    re.IGNORECASE,
)


def _canonical_code(s: str) -> str:
    """Extract a stable lookup key from an agent-reported code string.

    Examples:
        "CPT 74177"               -> "cpt 74177"
        "CPT 74177 (lines 3-4)"   -> "cpt 74177"
        "Modifier 25"             -> "modifier 25"
        "HCPCS J3490 (line 5)"    -> "hcpcs j3490"
        "REV 0450"                -> "rev 0450"
        "Mod 25"                  -> "mod 25"
    """
    if not s:
        return ""
    s = " ".join(str(s).strip().split())
    m = _CODE_RE.match(s)
    if m:
        kind = m.group(1).lower()
        # Normalize "mod" → "modifier" so the two forms collapse.
        if kind == "mod":
            kind = "modifier"
        return f"{kind} {m.group(2).lower()}"
    return s.lower()


def tally(votes: List[AgentVote], quorum: int = 2) -> Dict[str, Any]:
    verdict_counts = Counter(v.verdict for v in votes)
    top_verdict, top_count = verdict_counts.most_common(1)[0]

    # If no verdict reaches the quorum (e.g. 1-1-1 split), fall back to "clarify"
    # rather than letting insertion order silently decide. "We could not agree"
    # is more honest than picking whichever agent ran first.
    if top_count < quorum:
        top_verdict = "clarify"
        top_count = verdict_counts.get("clarify", 0)
        no_majority = True
    else:
        no_majority = False

    def _key(f: Dict[str, Any]) -> str:
        code = f.get("code") or f.get("id") or ""
        return _canonical_code(str(code))

    finding_seen: Dict[str, Dict[str, Any]] = {}
    finding_voters: Dict[str, List[str]] = {}
    for v in votes:
        for f in v.findings:
            k = _key(f)
            if not k:
                continue
            finding_seen.setdefault(k, f)
            finding_voters.setdefault(k, []).append(v.agent)

    consensus_findings: List[Dict[str, Any]] = []
    for fid, voters in finding_voters.items():
        if len(set(voters)) >= quorum:
            f = dict(finding_seen[fid])
            f["voted_by"] = sorted(set(voters))
            consensus_findings.append(f)

    consensus_findings.sort(
        key=lambda f: (
            {"high": 0, "medium": 1, "low": 2}.get(f.get("severity", "low"), 3),
            -float(f.get("amount_usd", 0)),
        )
    )

    aligned_voters = [v for v in votes if v.verdict == top_verdict]
    mean_conf = round(sum(v.confidence for v in aligned_voters) / max(1, len(aligned_voters)), 3)

    def _amt(f: Dict[str, Any]) -> float:
        try:
            return float(f.get("amount_usd", 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    # An "aligned" finding means agents agree the line is correctly billed — it
    # does NOT add to flagged money. Only dispute + clarify count.
    actionable = [f for f in consensus_findings if f.get("action") != "aligned"]
    aligned = [f for f in consensus_findings if f.get("action") == "aligned"]
    disputed_total = sum(_amt(f) for f in actionable if f.get("action") == "dispute")
    clarify_total = sum(_amt(f) for f in actionable if f.get("action") == "clarify")
    flagged_total = disputed_total + clarify_total
    aligned_total = sum(_amt(f) for f in aligned)

    return {
        "verdict": top_verdict,
        "agree_count": top_count,
        "total_agents": len(votes),
        "mean_confidence": mean_conf,
        "no_majority": no_majority,
        "findings": consensus_findings,
        "actionable_count": len(actionable),
        "aligned_count": len(aligned),
        "disputed_total_usd": round(disputed_total, 2),
        "clarify_total_usd": round(clarify_total, 2),
        "flagged_total_usd": round(flagged_total, 2),
        "aligned_total_usd": round(aligned_total, 2),
        "agents": [v.public_dict() for v in votes],
    }