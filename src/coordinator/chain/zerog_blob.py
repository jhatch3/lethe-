"""0G Storage blob writer — uploads anonymized audit records via the local sidecar.

Why a sidecar:
    The official 0G Storage Python SDK on PyPI ships broken (relative-import
    issues we documented in zerog_storage.py). The TS SDK (`@0glabs/0g-ts-sdk`)
    works and is what the rest of the 0G ecosystem uses, so we run a small
    Node sidecar (`src/coordinator/scripts/storage_sidecar.ts`) on a local
    port and POST the blob to it. The sidecar handles wallet signing, node
    selection, merkle-tree construction, and the on-chain commitment.

Privacy:
    Same redaction guarantees as PatternRegistry — codes are public taxonomy,
    severity/action/amount are aggregated metadata, voters is a 3-bit mask,
    and there are no descriptions, dates, or identifiers in the blob.

Behavior:
    - When LETHE_0G_STORAGE_SIDECAR_URL is empty OR the sidecar is unreachable,
      returns a stub result so the rest of the pipeline keeps working.
    - When live, returns the storage merkle root + on-chain commitment tx so
      the receipt can link to both.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List

import httpx

from config import settings

log = logging.getLogger("lethe.chain.zerog_blob")


# Circuit breaker — once the sidecar fails N times in a row (e.g. 0G Galileo
# flow contract is rejecting submissions for our wallet), short-circuit all
# subsequent uploads to a stub instead of repeatedly hammering the sidecar.
# Resets on the next successful upload, so transient failures don't lock the
# breaker permanently. State is per-coordinator-process (memory only).
_CIRCUIT_BREAKER_THRESHOLD = 2
_consecutive_failures = 0
_circuit_open = False


def _record_failure(reason: str) -> None:
    global _consecutive_failures, _circuit_open
    _consecutive_failures += 1
    if _consecutive_failures >= _CIRCUIT_BREAKER_THRESHOLD and not _circuit_open:
        _circuit_open = True
        log.warning(
            "0g storage circuit breaker OPEN after %d consecutive failures (last: %s) — "
            "subsequent uploads will short-circuit to stub. Will retry on next coordinator restart.",
            _consecutive_failures, reason,
        )


def _record_success() -> None:
    global _consecutive_failures, _circuit_open
    if _circuit_open:
        log.info("0g storage circuit breaker CLOSED — uploads succeeding again.")
    _consecutive_failures = 0
    _circuit_open = False


def _stub(reason: str) -> Dict[str, Any]:
    return {
        "executor": f"stub ({reason})",
        "live": False,
        "root_hash": None,
        "tx_hash": None,
    }


def _build_blob(consensus: Dict[str, Any], sha256_hex: str) -> Dict[str, Any]:
    """Compose the JSON blob written to 0G Storage.

    Carries everything PatternRegistry's truncated bytes32/16/8 fields can't —
    full code strings, action labels, severity strings, voter agent names,
    and the bill SHA-256 as the join key.
    """
    findings: List[Dict[str, Any]] = consensus.get("findings", []) or []
    return {
        "schema": "lethe.audit.pattern.v1",
        "bill_sha256": sha256_hex,
        "verdict": consensus.get("verdict"),
        "agree_count": consensus.get("agree_count"),
        "total_agents": consensus.get("total_agents"),
        "findings": [
            {
                "code": f.get("code"),
                "action": f.get("action"),
                "severity": f.get("severity"),
                "amount_usd": f.get("amount_usd"),
                "voted_by": f.get("voted_by", []),
            }
            for f in findings
        ],
        "ts": int(time.time()),
    }


def _padded_blob_bytes(blob: Dict[str, Any], target_bytes: int = 4096) -> bytes:
    """Serialize the blob, padding with whitespace so the byte length is at
    least `target_bytes`. Bypasses 0G Storage Galileo's small-blob revert —
    the flow contract's `submit()` rejects ~533-byte / 3-chunk uploads
    intermittently. Padding to ~4 KB pushes us past that edge case.

    The `_padding` field is ignored by `format_storage_priors_for_prompt`,
    so this is read-side transparent.
    """
    initial = json.dumps(blob, separators=(",", ":")).encode("utf-8")
    needed = target_bytes - len(initial)
    if needed <= 0:
        return initial
    # Account for ',"_padding":""' overhead (≈14 bytes) when sizing the field.
    overhead = 14
    pad_len = max(0, needed - overhead)
    padded = dict(blob)
    padded["_padding"] = " " * pad_len
    return json.dumps(padded, separators=(",", ":")).encode("utf-8")


async def upload_pattern_blob(
    consensus: Dict[str, Any], sha256_hex: str,
) -> Dict[str, Any]:
    """POST the audit blob to the 0G Storage sidecar.

    Returns the sidecar's response on success; a stub dict on any failure
    (no sidecar URL configured, sidecar unreachable, upload error).
    """
    sidecar_url = settings.zg_storage_sidecar_url.strip().rstrip("/")
    if not sidecar_url:
        return _stub("no sidecar url")

    # Circuit breaker — short-circuit if the sidecar has failed N consecutive
    # times (testnet flow contract rejecting submissions, etc.). Avoids log
    # spam + wasted round-trips. Auto-resets on next successful upload.
    if _circuit_open:
        return {
            **_stub("circuit open · testnet flow contract unavailable"),
            "circuit_breaker": "open",
            "consecutive_failures": _consecutive_failures,
        }

    blob = _build_blob(consensus, sha256_hex)
    blob_json = _padded_blob_bytes(blob, target_bytes=4096)
    started = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                f"{sidecar_url}/upload",
                content=blob_json,
                headers={"Content-Type": "application/json"},
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            if r.status_code != 200:
                _record_failure(f"http {r.status_code}")
                return {
                    **_stub(f"http {r.status_code}"),
                    "error": r.text[:240],
                    "duration_ms": duration_ms,
                }
            data = r.json()
            if not data.get("ok"):
                _record_failure("sidecar error")
                return {
                    **_stub("sidecar error"),
                    "error": data.get("error", "")[:240],
                    "duration_ms": duration_ms,
                }
            tx = data.get("tx_hash")
            _record_success()
            return {
                "executor": "0g-storage",
                "live": True,
                "network": "0g-galileo-testnet",
                "root_hash": data.get("root_hash"),
                "tx_hash": tx,
                "tx_link": f"https://chainscan-galileo.0g.ai/tx/{tx}" if tx else None,
                "bytes": data.get("bytes", len(blob_json)),
                "schema": blob["schema"],
                "duration_ms": duration_ms,
            }
    except Exception as e:
        _record_failure(f"{type(e).__name__}")
        log.warning("0g storage upload failed: %s", e)
        return {
            **_stub(f"error: {type(e).__name__}"),
            "error": str(e)[:240],
            "duration_ms": int((time.perf_counter() - started) * 1000),
        }
