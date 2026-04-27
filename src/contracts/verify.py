"""Submit BillRegistry source to chainscan-galileo for verification.

After this runs successfully, the explorer decodes:
  - the `anchor(bytes32, uint8, uint8, uint8)` function call on the tx page
  - the `Anchored(...)` event log into named fields (verdict, agreeCount, etc.)
  - the contract's `anchors(bytes32)` mapping into a "Read Contract" tab

Usage (from src/contracts/):
    python verify.py [--address 0x...] [--network galileo|sepolia]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE_FILE = Path(__file__).parent / "src" / "BillRegistry.sol"
DEPLOY_ARTIFACT = Path(__file__).parent / "deployed.galileo.json"

NETWORKS = {
    "galileo": {
        "explorer_base": "https://chainscan-galileo.0g.ai",
    },
    "sepolia": {
        "explorer_base": "https://eth-sepolia.blockscout.com",
    },
}


def submit_verification(address: str, base_url: str, source: str) -> requests.Response:
    """Try the Blockscout v2 API first (multipart), fall back to v1 (form)."""

    address = address.lower()
    contract_name = "BillRegistry"
    compiler_version = "v0.8.24+commit.e11b9ed9"

    standard_input = {
        "language": "Solidity",
        "sources": {"BillRegistry.sol": {"content": source}},
        "settings": {
            "optimizer": {"enabled": True, "runs": 200},
            "evmVersion": "cancun",
            "outputSelection": {"*": {"*": ["abi", "evm.bytecode"]}},
        },
    }

    # === Attempt 1: Blockscout v2 standard-input ===
    v2_url = f"{base_url}/api/v2/smart-contracts/{address}/verification/via/standard-input"
    files = {"files": ("input.json", json.dumps(standard_input), "application/json")}
    data = {
        "compiler_version": compiler_version,
        "license_type": "mit",
        "is_optimization_enabled": "true",
        "optimization_runs": "200",
        "evm_version": "cancun",
        "contract_name": contract_name,
        "is_yul_contract": "false",
        "autodetect_constructor_args": "true",
    }
    print(f"→ POST {v2_url}")
    resp = requests.post(v2_url, files=files, data=data, timeout=60)
    print(f"  status: {resp.status_code}")
    if resp.status_code in (200, 201, 202):
        try:
            print(f"  body:   {json.dumps(resp.json(), indent=2)[:400]}")
        except Exception:
            print(f"  body:   {resp.text[:400]}")
        return resp
    print(f"  body:   {resp.text[:400]}")

    # === Attempt 2: Legacy v1 form ===
    print()
    v1_url = f"{base_url}/api"
    print(f"→ POST {v1_url} (action=verifysourcecode)")
    payload = {
        "module": "contract",
        "action": "verifysourcecode",
        "addressHash": address,
        "name": contract_name,
        "compilerVersion": compiler_version,
        "optimization": "true",
        "optimizationRuns": "200",
        "evmVersion": "cancun",
        "contractSourceCode": source,
        "autodetectConstructorArguments": "true",
    }
    resp = requests.post(v1_url, data=payload, timeout=60)
    print(f"  status: {resp.status_code}")
    print(f"  body:   {resp.text[:400]}")
    return resp


def poll_status(address: str, base_url: str, max_seconds: int = 60) -> None:
    address = address.lower()
    url = f"{base_url}/api/v2/smart-contracts/{address}"
    print(f"\nPolling verification status…")
    deadline = time.time() + max_seconds
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                body = r.json()
                verified = body.get("is_verified") or body.get("isVerified")
                if verified:
                    print(f"  ✓ verified at {url}")
                    return
                print(f"  …not yet (is_verified={verified})")
        except Exception as e:
            print(f"  poll error: {type(e).__name__}: {e}")
        time.sleep(4)
    print(f"  ⚠ still not showing as verified after {max_seconds}s — check the explorer UI")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--address", default=None, help="contract address (default: read from deployed.galileo.json)")
    p.add_argument("--network", default="galileo", choices=list(NETWORKS))
    args = p.parse_args()

    if args.address:
        address = args.address
    else:
        if not DEPLOY_ARTIFACT.exists():
            sys.exit(f"ERROR: {DEPLOY_ARTIFACT} not found — pass --address explicitly")
        artifact = json.loads(DEPLOY_ARTIFACT.read_text())
        address = artifact["address"]

    base_url = NETWORKS[args.network]["explorer_base"]
    source = SOURCE_FILE.read_text()
    print(f"Verifying {address} on {args.network} ({base_url})")
    print()
    submit_verification(address, base_url, source)
    poll_status(address, base_url)
    print()
    print(f"  contract page: {base_url}/address/{address}")
    print(f"  (verified contracts get a 'Code', 'Read Contract', and 'Events' tab)")


if __name__ == "__main__":
    main()