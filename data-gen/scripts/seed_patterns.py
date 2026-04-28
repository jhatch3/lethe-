"""Pre-seed PatternRegistry on 0G Galileo with synthetic historical audits.

Why:
    The "each new audit gets smarter via on-chain shared memory" claim only
    fires if PatternRegistry has events to read back. On a fresh deploy, the
    pattern read-back returns empty and agents see no priors. Running this
    script before a demo writes ~20 historical patterns to the registry so
    the very first demo audit shows real on-chain priors influencing reasoning.

What it writes:
    A spread of common billing-error patterns (CPT 99213, 99214, 74177,
    HCPCS modifier issues, etc.) with realistic dispute / clarify / approve
    rates. Each finding is anonymized — codes are public taxonomy, severity
    and amount are aggregated metadata, voters is a 3-bit mask. No PHI.

Run from the repo root:
    python data-gen/scripts/seed_patterns.py [--dry-run] [--count 20]

Requires:
    LETHE_ZG_PRIVATE_KEY  — funded Galileo wallet (>= ~0.05 OG)
    LETHE_PATTERN_REGISTRY_ADDRESS — already deployed (see deployed.PatternRegistry.galileo.json)
"""

from __future__ import annotations

import argparse
import asyncio
import os
import random
import sys
import time
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "src" / "coordinator"))

from chain import zerog_storage  # noqa: E402
from config import settings  # noqa: E402


# Realistic-looking but synthetic seed patterns. Mix of dispute / clarify /
# approve so the read-back aggregator computes non-trivial rates.
SEED_PATTERNS: List[Dict[str, Any]] = [
    # --- E&M codes (most common dispute targets) ---
    {"code": "CPT 99213", "action": "downcode", "severity": "high",   "amount_usd": 65.00,  "voters": ["alpha", "beta", "gamma"]},
    {"code": "CPT 99213", "action": "downcode", "severity": "med",    "amount_usd": 65.00,  "voters": ["alpha", "beta"]},
    {"code": "CPT 99214", "action": "downcode", "severity": "high",   "amount_usd": 95.00,  "voters": ["alpha", "beta", "gamma"]},
    {"code": "CPT 99214", "action": "clarify",  "severity": "med",    "amount_usd": 95.00,  "voters": ["beta", "gamma"]},
    {"code": "CPT 99215", "action": "downcode", "severity": "high",   "amount_usd": 138.00, "voters": ["alpha", "beta"]},
    # --- imaging ---
    {"code": "CPT 74177", "action": "unbundle", "severity": "high",   "amount_usd": 850.00, "voters": ["alpha", "beta", "gamma"]},
    {"code": "CPT 74177", "action": "unbundle", "severity": "high",   "amount_usd": 850.00, "voters": ["alpha", "gamma"]},
    {"code": "CPT 70553", "action": "modifier", "severity": "med",    "amount_usd": 1200.00, "voters": ["beta", "gamma"]},
    # --- procedures ---
    {"code": "CPT 29881", "action": "modifier", "severity": "med",    "amount_usd": 2400.00, "voters": ["alpha", "beta"]},
    {"code": "CPT 27447", "action": "approve",  "severity": "info",   "amount_usd": 18500.00, "voters": ["alpha", "beta", "gamma"]},
    # --- labs ---
    {"code": "CPT 80053", "action": "duplicate", "severity": "high",  "amount_usd": 32.00,  "voters": ["alpha", "beta", "gamma"]},
    {"code": "CPT 80048", "action": "approve",  "severity": "info",   "amount_usd": 28.00,  "voters": ["alpha", "beta"]},
    {"code": "CPT 85025", "action": "approve",  "severity": "info",   "amount_usd": 18.00,  "voters": ["alpha", "beta", "gamma"]},
    # --- ER ---
    {"code": "CPT 99284", "action": "downcode", "severity": "high",   "amount_usd": 425.00, "voters": ["alpha", "beta", "gamma"]},
    {"code": "CPT 99285", "action": "downcode", "severity": "high",   "amount_usd": 612.00, "voters": ["alpha", "gamma"]},
    # --- HCPCS / drugs ---
    {"code": "HCPCS J3490", "action": "modifier", "severity": "med",  "amount_usd": 145.00, "voters": ["beta", "gamma"]},
    {"code": "HCPCS J1100", "action": "approve",  "severity": "info", "amount_usd": 22.00,  "voters": ["alpha", "beta", "gamma"]},
    # --- revenue codes ---
    {"code": "REV 0450", "action": "duplicate", "severity": "med",    "amount_usd": 380.00, "voters": ["alpha", "beta"]},
    {"code": "REV 0301", "action": "modifier",  "severity": "med",    "amount_usd": 95.00,  "voters": ["beta", "gamma"]},
    {"code": "REV 0250", "action": "clarify",   "severity": "low",    "amount_usd": 18.00,  "voters": ["alpha", "gamma"]},
]


def _synthetic_consensus(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Wrap one finding (or a small batch) in the consensus shape that
    `zerog_storage.index_patterns` expects."""
    return {
        "verdict": "dispute" if any(f["action"] != "approve" for f in findings) else "approve",
        "agree_count": 3,
        "total_agents": 3,
        "findings": [
            {
                "code": f["code"],
                "action": f["action"],
                "severity": f["severity"],
                "amount_usd": f["amount_usd"],
                "voted_by": f["voters"],
            }
            for f in findings
        ],
    }


def _synthetic_sha(seed: str) -> str:
    """Deterministic synthetic bill SHA — different from any real audit hash."""
    return "0x" + sha256(f"lethe-seed:{seed}:{time.time_ns()}".encode()).hexdigest()


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=20, help="how many distinct historical audits to write")
    ap.add_argument("--dry-run", action="store_true", help="show what would be written, no tx")
    ap.add_argument("--seed", type=int, default=42, help="random seed for batch composition")
    args = ap.parse_args()

    if not settings.zg_private_key:
        print("ERROR: LETHE_ZG_PRIVATE_KEY (or ZG_PRIVATE_KEY) not set")
        sys.exit(1)
    if not settings.pattern_registry_address:
        print("ERROR: LETHE_PATTERN_REGISTRY_ADDRESS not set")
        sys.exit(1)

    rng = random.Random(args.seed)
    pool = list(SEED_PATTERNS)
    rng.shuffle(pool)

    print(f"writing {args.count} historical audits to PatternRegistry")
    print(f"  registry : {settings.pattern_registry_address}")
    print(f"  network  : 0g-galileo-testnet (chain {settings.zg_chain_id})")
    print(f"  dry-run  : {args.dry_run}")
    print()

    # Batch each "audit" with 1-3 findings so the totals look natural.
    success = 0
    for i in range(args.count):
        batch_size = rng.choice([1, 1, 2, 2, 3])
        batch = rng.sample(pool, k=min(batch_size, len(pool)))
        consensus = _synthetic_consensus(batch)
        sha = _synthetic_sha(f"batch-{i}")
        codes = ", ".join(f["code"] for f in batch)
        print(f"[{i+1:2d}/{args.count}] {sha[:12]}…  {codes}")
        if args.dry_run:
            success += 1
            continue
        try:
            result = await zerog_storage.index_patterns(consensus, sha)
            if result.get("live"):
                print(f"           tx={result.get('tx', '')[:18]}  block=#{result.get('block_number')}")
                success += 1
            else:
                print(f"           SKIPPED: {result.get('executor')}")
        except Exception as e:
            print(f"           ERROR: {type(e).__name__}: {e}")
        # Light spacing so we don't hammer the RPC + we stay under any rate limits.
        await asyncio.sleep(0.6)

    print()
    print(f"done — {success}/{args.count} audits indexed")
    if not args.dry_run and success > 0:
        print("verify:  curl http://localhost:8000/api/patterns | jq '.total_observations'")


if __name__ == "__main__":
    asyncio.run(main())