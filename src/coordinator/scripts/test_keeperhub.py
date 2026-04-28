"""Standalone KeeperHub round-trip test.

Verifies the full Direct Execution flow without running the full pipeline:
  1. POST /api/execute/contract-call with a synthetic SHA-256
  2. Poll /api/execute/{id}/status until terminal
  3. Print the Sepolia tx hash + etherscan link

Run from src/coordinator/ with venv active:
    python scripts/test_keeperhub.py

Useful when:
  - You want to confirm KeeperHub credentials work before debugging the LLM pipeline.
  - You hit the "Sepolia mirror — pending" placeholder on the dashboard and want
    to know whether the issue is KH or something upstream (it'll be upstream — KH
    just calls a contract; it has no dependency on agents/LLMs/parsers).
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import sys
import time
from pathlib import Path

# Allow running as a script from repo root or src/coordinator/
HERE = Path(__file__).resolve().parent
COORD = HERE.parent
if str(COORD) not in sys.path:
    sys.path.insert(0, str(COORD))

# Make the keeperhub module's INFO logs visible — without this the script
# looks frozen during the 5-15s round-trip.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)-22s %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("httpx").setLevel(logging.INFO)
logging.getLogger("lethe.chain.keeperhub").setLevel(logging.INFO)


async def main() -> None:
    from chain import keeperhub
    from config import settings

    # Build a UNIQUE test hash each run — the BillRegistry contract rejects
    # duplicate anchors, so a deterministic hash would only succeed once.
    nonce = f"lethe-keeperhub-test-{time.time_ns()}"
    sha = hashlib.sha256(nonce.encode()).hexdigest()
    print("== KeeperHub round-trip test ==")
    print(f"test sha256       : 0x{sha[:16]}…")
    print(f"keeperhub key set : {bool(settings.keeperhub_api_key)}")
    print(f"sepolia registry  : {settings.bill_registry_address_sepolia or '(not set)'}")
    print()

    if not settings.keeperhub_api_key:
        print("FAIL: KEEPERHUB_API_KEY is not set in .env. Cannot test.")
        sys.exit(1)
    if not settings.bill_registry_address_sepolia:
        print("FAIL: BILL_REGISTRY_ADDRESS_SEPOLIA is not set in .env. Cannot test.")
        sys.exit(1)

    print(f"keeperhub base    : {settings.keeperhub_base_url}")
    print()
    print("calling KeeperHub anchor (POST /api/execute/contract-call)…")
    print("expect 5-30s for first 200/202 + status polling")
    print("─" * 60)

    started = time.time()
    result = await keeperhub.anchor_via_keeperhub(
        sha256_hex=sha,
        verdict="dispute",
        agree_count=3,
        total_agents=3,
    )
    elapsed = time.time() - started

    print("─" * 60)
    print(f"completed in      : {elapsed:.1f}s")
    print()
    print("=== result ===")
    for k, v in result.items():
        print(f"  {k:18s}: {v}")
    print()

    if result.get("live") and result.get("tx_hash"):
        print("✓ SUCCESS — KeeperHub is wired correctly.")
        print(f"  Verify at: {result.get('tx_link')}")
        sys.exit(0)
    else:
        print("✗ KeeperHub returned a stub/error. See `executor` and `error` fields above.")
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())