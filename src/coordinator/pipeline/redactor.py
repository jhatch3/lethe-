"""PHI redactor.

Two-pass design:

  1. **Regex pass** — fast, deterministic, never leaves the coordinator.
     Catches SSN, DOB, phone, email, MRN, account, ZIP, labeled patient/DOB/address lines.

  2. **LLM pass** (optional, gated on OPENAI_API_KEY) — runs *after* the regex pass
     to catch stragglers the regex misses, especially names without labels
     ("John Smith was admitted on..."), provider names, and free-text notes.
     The LLM only ever sees the already-regex-redacted text.

The redacted_payload returned here is the only thing the audit agents see.
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any, Dict, Tuple

from config import settings

_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_DOB = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})\b")
_PHONE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_EMAIL = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}\b")
_MRN = re.compile(r"\bMRN[\s:#-]*[A-Z0-9-]+\b", re.IGNORECASE)
_ACCT = re.compile(r"\b(?:Account|Acct|Acc)\s*[#:-]+\s*[A-Z0-9-]+\b", re.IGNORECASE)
# Labeled ZIP only — bare 5-digit numbers are usually CPT codes, not ZIPs.
# True ZIP scrubbing happens in the LLM pass which has the context to tell them apart.
_ZIP_LABELED = re.compile(r"\bZIP\s*[:#-]?\s*\d{5}(?:-\d{4})?\b", re.IGNORECASE)
_PATIENT_LINE = re.compile(r"(?im)^(?:patient|name|insured|subscriber)\s*[:#-]?\s*[^\n]+$")
_DOB_LINE = re.compile(r"(?im)^(?:dob|date of birth)\s*[:#-]?\s*[^\n]+$")
_ADDRESS_LINE = re.compile(r"(?im)^(?:address|addr|home address|mailing address)\s*[:#-]?\s*[^\n]+$")


def _regex_scrub(text: str) -> str:
    text = _PATIENT_LINE.sub("[REDACTED-PATIENT]", text)
    text = _DOB_LINE.sub("[REDACTED-DOB]", text)
    text = _ADDRESS_LINE.sub("[REDACTED-ADDRESS]", text)
    text = _SSN.sub("[REDACTED-SSN]", text)
    text = _DOB.sub("[REDACTED-DATE]", text)
    text = _PHONE.sub("[REDACTED-PHONE]", text)
    text = _EMAIL.sub("[REDACTED-EMAIL]", text)
    text = _MRN.sub("[REDACTED-MRN]", text)
    text = _ACCT.sub("[REDACTED-ACCT]", text)
    text = _ZIP_LABELED.sub("[REDACTED-ZIP]", text)
    return text


_LLM_REDACTOR_PROMPT = """You are a PHI redactor for medical bills. Your ONLY job is to replace remaining patient identifiers in the input text with bracketed placeholders. Do not modify, summarize, or comment on anything else.

REPLACE with [REDACTED-XXX] tokens:
- Person names (patient, family members)
- Specific provider / doctor / nurse names ("Dr. Jane Smith" -> "[REDACTED-PROVIDER]")
- Address fragments (street numbers, street names, city, state, ZIP code in address context)
- Phone, fax, email
- Medical record numbers, account numbers, claim IDs, member IDs
- Dates of birth, dates of service when tied to a person
- Any remaining unique identifier that could re-identify a patient

KEEP (these are NOT PHI — DO NOT TOUCH):
- CPT codes (5-digit numeric, e.g. 99214, 74177, 96372)
- ICD codes (alphanumeric, e.g. M54.5, I10)
- HCPCS codes (letter + digits, e.g. J3490, Q9967)
- Revenue codes (REV 0450, etc.) and modifiers (25, 50, 59, 76, 77)
- Procedure descriptions and medical terminology
- Charge amounts (dollar values)
- Hospital / facility / clinic names (e.g. "General Hospital")
- NPI numbers (provider identifier, not patient)
- Existing [REDACTED-...] tokens — leave those untouched

CRITICAL: A bare 5-digit number on a billing line is almost always a CPT code, not a ZIP. Only redact 5-digit numbers when clearly in an address context (e.g. "Eugene, OR 97401" or "ZIP: 97401").

OUTPUT: return the redacted text only. No prose before or after. No JSON wrapper. Preserve line breaks and structure."""


async def _llm_scrub(text: str, api_key: str) -> Tuple[str, Dict[str, Any]]:
    """Run a small LLM pass to catch what the regex missed.

    Uses gpt-4o-mini for speed/cost. The model only ever sees the
    already-regex-redacted text — never raw bill bytes.
    """
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    started = time.perf_counter()
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _LLM_REDACTOR_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0,
        max_tokens=4000,
    )
    out = (resp.choices[0].message.content or "").strip() or text
    return out, {
        "model": "gpt-4o-mini",
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "input_chars": len(text),
        "output_chars": len(out),
    }


async def redact(parsed: Dict[str, Any], simulated_delay_ms: int) -> Dict[str, Any]:
    text = parsed.get("text", "") or ""
    passes = []

    # Pass 1 — regex
    text = _regex_scrub(text)
    passes.append({
        "name": "regex",
        "patterns": [
            "patient_line", "dob_line", "address_line", "ssn",
            "date", "phone", "email", "mrn", "account", "zip",
        ],
    })

    # Pass 2 — LLM (optional; gated on OPENAI_API_KEY)
    llm_meta: Dict[str, Any] = {}
    if settings.openai_api_key and text.strip():
        try:
            text, llm_meta = await _llm_scrub(text, settings.openai_api_key)
            passes.append({"name": "llm", **llm_meta})
        except Exception as e:
            passes.append({"name": "llm", "error": f"{type(e).__name__}: {str(e)[:160]}"})
    else:
        passes.append({"name": "llm", "skipped": "no api key" if not settings.openai_api_key else "empty input"})

    if simulated_delay_ms:
        await asyncio.sleep(simulated_delay_ms / 1000)

    return {
        "filename_hint": "[REDACTED]",
        "size_bytes": parsed.get("size_bytes", 0),
        "page_count": parsed.get("page_count", 0),
        "parser": parsed.get("parser", "?"),
        "text": text,
        "redaction": {"passes": passes},
    }