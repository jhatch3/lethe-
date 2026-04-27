"""Read-back from PatternRegistry — feed prior pattern stats into agent prompts.

Closes the learning loop: each audit writes events; future audits read the
aggregated stats so agents have prior probabilities for each billing code.

Privacy: only canonical codes + actions + counts + amounts are fetched. No PHI
ever existed in PatternRegistry, so this read path is safe to surface anywhere.

Caching:
    The fetch hits eth_getLogs across the registry's lifetime. On 0G Galileo
    testnet that's cheap, but we cache the aggregate for `_CACHE_TTL` seconds
    to keep the reasoning stage snappy. Stats refresh on a sweep loop and
    after each new write event we'd see during a run.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from typing import Any, Dict, List

from config import settings

log = logging.getLogger("lethe.chain.patterns")


_CACHE_TTL = 120  # seconds
_cache: Dict[str, Any] = {"stats": None, "fetched_at": 0.0, "block": 0}


_PATTERN_INDEXED_ABI = [
    {
        "type": "event",
        "name": "PatternIndexed",
        "anonymous": False,
        "inputs": [
            {"name": "billHash",  "type": "bytes32", "indexed": True},
            {"name": "code",      "type": "bytes32", "indexed": True},
            {"name": "action",    "type": "bytes16", "indexed": False},
            {"name": "severity",  "type": "bytes8",  "indexed": False},
            {"name": "amountUsd", "type": "uint64",  "indexed": False},
            {"name": "voters",    "type": "uint8",   "indexed": False},
            {"name": "indexedBy", "type": "address", "indexed": True},
            {"name": "indexedAt", "type": "uint64",  "indexed": False},
        ],
    }
]


def _decode_bytes(b: bytes) -> str:
    """bytes32/16/8 → ascii string, stripped of trailing nulls."""
    if isinstance(b, (bytes, bytearray)):
        return b.rstrip(b"\x00").decode("ascii", errors="replace")
    if isinstance(b, str):
        return b
    return str(b)


def _fetch_sync() -> Dict[str, Dict[str, Any]]:
    from web3 import Web3

    if not settings.pattern_registry_address:
        return {}

    w3 = Web3(Web3.HTTPProvider(settings.zg_rpc_url))
    if not w3.is_connected():
        log.warning("0G RPC unreachable — returning empty pattern stats")
        return {}

    addr = Web3.to_checksum_address(settings.pattern_registry_address)
    contract = w3.eth.contract(address=addr, abi=_PATTERN_INDEXED_ABI)

    # eth_getLogs across the contract's full life. Galileo testnet is small;
    # fine for a hackathon. For production we'd batch by block range.
    try:
        latest = w3.eth.block_number
        # Cap at 100k blocks back — testnet should always be well under this
        from_block = max(0, latest - 100_000)
        events = contract.events.PatternIndexed.get_logs(from_block=from_block)
    except Exception as e:
        log.warning("getLogs failed: %s — returning empty", e)
        return {}

    by_code: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"n": 0, "actions": defaultdict(int), "severities": defaultdict(int),
                 "amounts": [], "first_block": None, "last_block": None}
    )
    for ev in events:
        try:
            args = ev["args"]
            code = _decode_bytes(args["code"])
            action = _decode_bytes(args["action"])
            severity = _decode_bytes(args["severity"])
            amount = float(int(args["amountUsd"])) / 100.0
            blk = ev["blockNumber"]
            entry = by_code[code]
            entry["n"] += 1
            entry["actions"][action] += 1
            entry["severities"][severity] += 1
            entry["amounts"].append(amount)
            if entry["first_block"] is None or blk < entry["first_block"]:
                entry["first_block"] = blk
            if entry["last_block"] is None or blk > entry["last_block"]:
                entry["last_block"] = blk
        except Exception as e:
            log.warning("event parse failed: %s", e)
            continue

    out: Dict[str, Dict[str, Any]] = {}
    for code, data in by_code.items():
        n = data["n"]
        if n == 0:
            continue
        actions = dict(data["actions"])
        amounts = data["amounts"]
        out[code] = {
            "code": code,
            "n_observations": n,
            "actions": actions,
            "severities": dict(data["severities"]),
            "dispute_count": actions.get("dispute", 0),
            "clarify_count": actions.get("clarify", 0),
            "aligned_count": actions.get("aligned", 0),
            "dispute_rate": round(actions.get("dispute", 0) / n, 3),
            "clarify_rate": round(actions.get("clarify", 0) / n, 3),
            "mean_amount_usd": round(sum(amounts) / n, 2) if amounts else 0.0,
            "first_block": data["first_block"],
            "last_block": data["last_block"],
        }

    log.info("fetched %d unique codes from PatternRegistry (%d events)",
             len(out), sum(s["n_observations"] for s in out.values()))
    return out


async def get_pattern_stats(force: bool = False) -> Dict[str, Dict[str, Any]]:
    """Returns {code: stats}. Cached for ~120s."""
    now = time.time()
    if not force and _cache["stats"] is not None and now - _cache["fetched_at"] < _CACHE_TTL:
        return _cache["stats"]
    stats = await asyncio.to_thread(_fetch_sync)
    _cache["stats"] = stats
    _cache["fetched_at"] = now
    return stats


def format_for_prompt(stats: Dict[str, Dict[str, Any]], top_n: int = 30) -> str:
    """Format stats as a compact prior-probabilities block for an LLM prompt."""
    if not stats:
        return ""
    rows = sorted(stats.values(), key=lambda s: s["n_observations"], reverse=True)[:top_n]
    if not rows:
        return ""
    lines = [
        "PRIOR PATTERN STATS — public on-chain rollup from past Lethe audits.",
        "Use as priors to calibrate confidence; do NOT treat as ground truth.",
        "",
        f"{'code':<22} {'n':>4} {'dispute%':>9} {'clarify%':>9} {'mean $':>10}",
    ]
    for r in rows:
        code = r["code"][:22]
        n = r["n_observations"]
        dr = int(r["dispute_rate"] * 100)
        cr = int(r["clarify_rate"] * 100)
        amt = r["mean_amount_usd"]
        lines.append(f"{code:<22} {n:>4} {dr:>8}% {cr:>8}% ${amt:>9.2f}")
    return "\n".join(lines)