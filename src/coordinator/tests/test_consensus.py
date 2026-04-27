"""Consensus tally tests."""

from __future__ import annotations

from agents.base import AgentVote
from pipeline.consensus import _canonical_code, tally


def test_canonical_code_strips_parentheticals() -> None:
    assert _canonical_code("CPT 74177") == "cpt 74177"
    assert _canonical_code("CPT 74177 (lines 3-4)") == "cpt 74177"
    assert _canonical_code("Modifier 25") == "modifier 25"
    assert _canonical_code("Mod 25") == "modifier 25"  # collapses to canonical
    assert _canonical_code("HCPCS J3490 (line 5)") == "hcpcs j3490"
    assert _canonical_code("REV 0450") == "rev 0450"


def _vote(agent: str, verdict: str, findings: list[dict], conf: float = 0.9) -> AgentVote:
    return AgentVote(
        agent=agent,
        model=f"{agent}-model",
        verdict=verdict,
        confidence=conf,
        findings=findings,
        notes="",
        duration_ms=1000,
    )


def test_quorum_dedups_by_canonical_code() -> None:
    """Three agents flag the same CPT in slightly different formats — should
    still match into one consensus finding with all three voters."""
    votes = [
        _vote("alpha", "dispute", [
            {"code": "CPT 99214", "amount_usd": 185.00, "action": "dispute"},
        ]),
        _vote("beta", "dispute", [
            {"code": "CPT 99214 (lines 3-4)", "amount_usd": 185.00, "action": "dispute"},
        ]),
        _vote("gamma", "dispute", [
            {"code": "cpt 99214", "amount_usd": 185.00, "action": "dispute"},
        ]),
    ]
    result = tally(votes)
    assert result["verdict"] == "dispute"
    assert result["agree_count"] == 3
    assert len(result["findings"]) == 1
    f = result["findings"][0]
    assert sorted(f["voted_by"]) == ["alpha", "beta", "gamma"]
    assert result["disputed_total_usd"] == 185.00


def test_aligned_findings_dont_count_as_flagged() -> None:
    """An 'aligned' finding agreed on by 2+ agents is included in the
    consensus list but does NOT inflate disputed/flagged totals."""
    votes = [
        _vote("alpha", "approve", [
            {"code": "CPT 72148-TC", "amount_usd": 880.00, "action": "aligned"},
        ]),
        _vote("beta", "approve", [
            {"code": "CPT 72148-TC", "amount_usd": 880.00, "action": "aligned"},
        ]),
        _vote("gamma", "clarify", [
            {"code": "CPT 72148-TC", "amount_usd": 880.00, "action": "clarify"},
        ]),
    ]
    result = tally(votes)
    assert result["verdict"] == "approve"
    assert result["agree_count"] == 2
    # The finding makes quorum (3 voters) but its action is "aligned" or "clarify".
    # Aligned wins via setdefault since it's the first alpha+beta saw.
    assert len(result["findings"]) == 1
    assert result["disputed_total_usd"] == 0.0
    assert result["aligned_total_usd"] >= 0.0


def test_singleton_findings_filtered() -> None:
    """A finding only one agent flags should NOT make consensus."""
    votes = [
        _vote("alpha", "dispute", [
            {"code": "CPT 99214", "amount_usd": 185.00, "action": "dispute"},
            {"code": "Modifier 25", "amount_usd": 100.00, "action": "dispute"},
        ]),
        _vote("beta", "approve", []),
        _vote("gamma", "approve", []),
    ]
    result = tally(votes)
    assert result["verdict"] == "approve"  # 2/3 approve
    assert result["agree_count"] == 2
    # No findings reach quorum (alpha alone)
    assert len(result["findings"]) == 0


def test_three_way_split_falls_back_to_clarify() -> None:
    """1-1-1 split (approve, dispute, clarify) has no majority — fall back to
    clarify rather than letting registration order decide."""
    votes = [
        _vote("alpha", "approve",  [], conf=0.9),
        _vote("beta",  "dispute",  [], conf=0.8),
        _vote("gamma", "clarify",  [], conf=0.7),
    ]
    result = tally(votes)
    assert result["verdict"] == "clarify"
    assert result["no_majority"] is True
    # agree_count reflects how many actually voted clarify (1 in this case)
    assert result["agree_count"] == 1


def test_majority_does_not_set_no_majority_flag() -> None:
    """When a real majority exists, no_majority should be False."""
    votes = [
        _vote("alpha", "dispute", []),
        _vote("beta",  "dispute", []),
        _vote("gamma", "approve", []),
    ]
    result = tally(votes)
    assert result["verdict"] == "dispute"
    assert result["no_majority"] is False
    assert result["agree_count"] == 2
