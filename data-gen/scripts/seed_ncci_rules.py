"""Pre-seed NCCIRulebook on 0G Galileo with representative CMS NCCI edits.

Run after deploying NCCIRulebook to populate v1 with a handful of real
NCCI policy rules so agents have something to reference during reasoning.
Quarterly updates can be applied later via the same script with a fresh
batch + publishVersion().

Usage from repo root:
    python data-gen/scripts/seed_ncci_rules.py [--dry-run] [--publish]

Requires:
    LETHE_ZG_PRIVATE_KEY            — owner of the NCCIRulebook contract
    LETHE_NCCI_RULEBOOK_ADDRESS     — deployed contract address
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "src" / "coordinator"))


# (kind_int, cptA, cptB, mod, unitsCapPerDay, citation)
SEED_RULES = [
    (1, "CPT 29881", "CPT 29877", "59", 0, "NCCI Policy Manual Ch. 4 (Surgery: orthopedic)"),
    (2, "CPT 99214", "CPT 99213", "",  0, "NCCI E/M coding — higher level bundles lower"),
    (3, "CPT 93970", "CPT 93971", "59", 0, "NCCI Ch. 9 (Vascular ultrasound)"),
    (4, "CPT 80053", "",          "",  1, "NCCI MUE — comprehensive metabolic panel"),
    (5, "CPT 99213", "CPT 99214", "25", 0, "Modifier 25 abuse on E/M with same-day procedure"),
    (1, "CPT 29881", "CPT 29874", "59", 0, "NCCI Ch. 4 — meniscectomy + loose-body removal"),
    (3, "CPT 70553", "CPT 70551", "59", 0, "MRI brain w/ + w/o contrast bundle"),
    (4, "CPT 96372", "",          "",  4, "NCCI MUE — therapeutic injection daily cap"),
]

PROVISION_GAS = 220_000


def _to_b32(s: str, n: int = 32) -> bytes:
    raw = s.encode("ascii")[:n]
    return raw + b"\x00" * (n - len(raw))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--publish", action="store_true",
                    help="call publishVersion() after seeding (bumps to v2)")
    args = ap.parse_args()

    from config import settings  # noqa: E402

    if not settings.zg_private_key:
        sys.exit("ERROR: LETHE_ZG_PRIVATE_KEY not set")
    if not settings.ncci_rulebook_address:
        sys.exit("ERROR: LETHE_NCCI_RULEBOOK_ADDRESS not set — deploy first")

    from web3 import Web3                                        # noqa: E402
    from eth_account import Account                              # noqa: E402

    NCCI_ABI = [
        {"type": "function", "name": "addRule", "stateMutability": "nonpayable",
         "inputs": [
             {"name": "kind", "type": "uint8"},
             {"name": "cptA", "type": "bytes32"},
             {"name": "cptB", "type": "bytes32"},
             {"name": "mod_", "type": "bytes16"},
             {"name": "unitsCapPerDay", "type": "uint32"},
             {"name": "citation", "type": "string"},
         ], "outputs": [{"type": "uint16"}]},
        {"type": "function", "name": "publishVersion", "stateMutability": "nonpayable",
         "inputs": [], "outputs": []},
    ]

    w3 = Web3(Web3.HTTPProvider(settings.zg_rpc_url))
    if not w3.is_connected():
        sys.exit("ERROR: 0G RPC unreachable")
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(settings.ncci_rulebook_address),
        abi=NCCI_ABI,
    )
    acct = Account.from_key(settings.zg_private_key)

    print(f"seeding {len(SEED_RULES)} NCCI rules to {settings.ncci_rulebook_address}")
    print(f"  signer  : {acct.address}")
    print(f"  network : 0g-galileo-testnet (chain {settings.zg_chain_id})")
    print(f"  dry-run : {args.dry_run}")
    print()

    nonce = w3.eth.get_transaction_count(acct.address, "pending")
    success = 0
    for i, (kind, a, b, mod_, units, citation) in enumerate(SEED_RULES):
        cpt_a = _to_b32(a, 32)
        cpt_b = _to_b32(b, 32)
        mod_b = _to_b32(mod_, 16)
        print(f"[{i+1:2d}/{len(SEED_RULES)}] kind={kind} {a:12s} ↔ {b:12s} mod={mod_!r:5s} cap={units}")
        if args.dry_run:
            success += 1
            continue
        try:
            tx = contract.functions.addRule(kind, cpt_a, cpt_b, mod_b, units, citation).build_transaction({
                "from": acct.address,
                "nonce": nonce,
                "chainId": w3.eth.chain_id,
                "type": 2,
                "maxFeePerGas": w3.to_wei(6, "gwei"),
                "maxPriorityFeePerGas": w3.to_wei(4, "gwei"),
                "gas": PROVISION_GAS,
            })
            signed = acct.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=90, poll_latency=2)
            if receipt.status == 1:
                success += 1
                tx_hex = tx_hash.hex()
                print(f"           ✓ tx={tx_hex[:18]} block=#{receipt.blockNumber}")
            else:
                print(f"           ✗ reverted")
            nonce += 1
        except Exception as e:
            print(f"           ✗ {type(e).__name__}: {e}")

    if args.publish and success > 0 and not args.dry_run:
        print()
        print("publishing version (bumps currentVersion → v2)…")
        try:
            tx = contract.functions.publishVersion().build_transaction({
                "from": acct.address, "nonce": nonce, "chainId": w3.eth.chain_id,
                "type": 2, "maxFeePerGas": w3.to_wei(6, "gwei"),
                "maxPriorityFeePerGas": w3.to_wei(4, "gwei"), "gas": 60_000,
            })
            signed = acct.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            w3.eth.wait_for_transaction_receipt(tx_hash, timeout=90, poll_latency=2)
            print(f"           ✓ tx={tx_hash.hex()[:18]}")
        except Exception as e:
            print(f"           ✗ {e}")

    print()
    print(f"done — {success}/{len(SEED_RULES)} rules seeded")


if __name__ == "__main__":
    main()
