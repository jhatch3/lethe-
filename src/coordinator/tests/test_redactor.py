"""Redactor regex coverage tests.

These don't exercise the LLM pass — that requires an API key and is not
deterministic. We test the regex layer here, which IS deterministic and
is the privacy backstop.
"""

from __future__ import annotations

import asyncio

import pytest

from pipeline.redactor import _regex_scrub, redact


@pytest.mark.parametrize(
    "raw,expected_redactions",
    [
        ("SSN: 123-45-6789", ["[REDACTED-SSN]"]),
        # bare date in a non-DOB-labeled context
        ("Service performed 1990-04-22 with referral", ["[REDACTED-DATE]"]),
        ("Phone: (555) 123-4567", ["[REDACTED-PHONE]"]),
        ("Email me at john.doe@example.com", ["[REDACTED-EMAIL]"]),
        ("MRN: 0099281", ["[REDACTED-MRN]"]),
        ("Account #: 552014", ["[REDACTED-ACCT]"]),
        ("Patient: John Doe", ["[REDACTED-PATIENT]"]),
        # "DOB" or "Date of Birth" labeled lines get the whole line stripped
        ("Date of Birth: 04/22/1990", ["[REDACTED-DOB]"]),
        ("DOB 1990-04-22", ["[REDACTED-DOB]"]),
        ("Address: 123 Main St", ["[REDACTED-ADDRESS]"]),
        ("ZIP: 97401", ["[REDACTED-ZIP]"]),
    ],
)
def test_regex_catches_phi(raw: str, expected_redactions: list[str]) -> None:
    out = _regex_scrub(raw)
    for token in expected_redactions:
        assert token in out, f"expected {token!r} in {out!r}"


def test_cpt_codes_are_not_treated_as_zip() -> None:
    """5-digit CPT codes (74177, 99214, etc.) must NOT be redacted as ZIPs."""
    raw = "CPT 99214 Office visit\nCPT 74177 CT scan\nCPT 96372 Injection"
    out = _regex_scrub(raw)
    assert "99214" in out, "CPT 99214 was redacted but should not be"
    assert "74177" in out, "CPT 74177 was redacted but should not be"
    assert "96372" in out, "CPT 96372 was redacted but should not be"
    assert "[REDACTED-ZIP]" not in out, f"ZIP redaction false positive: {out!r}"


def test_hcpcs_codes_unaffected() -> None:
    raw = "HCPCS J3490 Unclassified drug\nHCPCS Q9967 LOCM contrast"
    out = _regex_scrub(raw)
    assert "J3490" in out
    assert "Q9967" in out


def test_full_redact_pipeline_no_api_key(monkeypatch) -> None:
    """When OPENAI_API_KEY is empty, the LLM pass is skipped cleanly."""
    from config import settings

    monkeypatch.setattr(settings, "openai_api_key", "")
    parsed = {"text": "Patient: J. Doe\nMRN: 0099281\nCPT 99214 Office visit", "size_bytes": 100}
    result = asyncio.run(redact(parsed, simulated_delay_ms=0))
    assert "[REDACTED-PATIENT]" in result["text"]
    assert "[REDACTED-MRN]" in result["text"]
    assert "99214" in result["text"]
    passes = result["redaction"]["passes"]
    names = [p.get("name") for p in passes]
    assert "regex" in names
    llm_pass = next((p for p in passes if p["name"] == "llm"), None)
    assert llm_pass is not None
    assert "skipped" in llm_pass