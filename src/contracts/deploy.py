"""Compile and deploy BillRegistry.sol to 0G Galileo (or any EVM RPC).

Pure-Python alternative to Foundry — no WSL needed on Windows.

Usage (from src/contracts/):
    python deploy.py [--network galileo|sepolia]

Reads from the repo-root .env:
    ZG_RPC_URL, ZG_PRIVATE_KEY, ZG_CHAIN_ID  (for galileo)
    SEPOLIA_RPC_URL, ZG_PRIVATE_KEY          (for sepolia, reusing the same key)

After a successful deploy, prints the contract address. Paste it into .env as
BILL_REGISTRY_ADDRESS (galileo) or BILL_REGISTRY_ADDRESS_SEPOLIA.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from eth_account import Account
import solcx
from web3 import Web3


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE = REPO_ROOT / ".env"
CONTRACTS_DIR = Path(__file__).parent / "src"
SOLC_VERSION = "0.8.24"

CONTRACTS = {
    "BillRegistry":    CONTRACTS_DIR / "BillRegistry.sol",
    "PatternRegistry": CONTRACTS_DIR / "PatternRegistry.sol",
    "DisputeRegistry": CONTRACTS_DIR / "DisputeRegistry.sol",
    "AppealRegistry":  CONTRACTS_DIR / "AppealRegistry.sol",
    "StorageIndex":    CONTRACTS_DIR / "StorageIndex.sol",
    "ProviderReputation": CONTRACTS_DIR / "ProviderReputation.sol",
    "NCCIRulebook":    CONTRACTS_DIR / "NCCIRulebook.sol",
}

# Contract name -> .env variable to paste the address into. The Sepolia
# suffix is appended automatically when --network sepolia is selected.
ENV_KEYS = {
    "BillRegistry":    "BILL_REGISTRY_ADDRESS",
    "PatternRegistry": "PATTERN_REGISTRY_ADDRESS",
    "DisputeRegistry": "LETHE_DISPUTE_REGISTRY_ADDRESS",
    "AppealRegistry":  "LETHE_APPEAL_REGISTRY_ADDRESS",
    "StorageIndex":    "LETHE_STORAGE_INDEX_ADDRESS",
    "ProviderReputation": "LETHE_PROVIDER_REPUTATION_ADDRESS",
    "NCCIRulebook":    "LETHE_NCCI_RULEBOOK_ADDRESS",
}


def load_env() -> dict[str, str]:
    if not ENV_FILE.exists():
        sys.exit(f"ERROR: {ENV_FILE} not found")
    out = {}
    for line in ENV_FILE.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def compile_contract(contract_name: str) -> tuple[list, str]:
    src = CONTRACTS[contract_name]
    solcx.set_solc_version(SOLC_VERSION)
    print(f"Compiling {src.name}…")
    compiled = solcx.compile_files(
        [str(src)],
        output_values=["abi", "bin"],
        solc_version=SOLC_VERSION,
        evm_version="cancun",
        optimize=True,
        optimize_runs=200,
    )
    key = next(k for k in compiled if k.endswith(":" + contract_name))
    return compiled[key]["abi"], compiled[key]["bin"]


def deploy(rpc_url: str, chain_id: int, private_key: str, abi: list, bytecode: str) -> tuple[str, str]:
    print(f"Connecting to {rpc_url} …")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        sys.exit("ERROR: RPC unreachable")
    if w3.eth.chain_id != chain_id:
        sys.exit(f"ERROR: chain id mismatch — RPC reports {w3.eth.chain_id}, expected {chain_id}")

    acct = Account.from_key(private_key)
    print(f"Deploying from {acct.address}")
    bal = w3.eth.get_balance(acct.address)
    print(f"  balance: {w3.from_wei(bal, 'ether')} (native token)")
    if bal == 0:
        sys.exit("ERROR: deployer wallet has zero balance — fund it from the faucet first")

    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = w3.eth.get_transaction_count(acct.address)

    # 0G Galileo enforces a ~4 gwei legacy floor; matches Sepolia just fine too.
    tx = Contract.constructor().build_transaction({
        "from": acct.address,
        "nonce": nonce,
        "chainId": chain_id,
        "type": 2,
        "maxFeePerGas": w3.to_wei(6, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(4, "gwei"),
        "gas": 1_500_000,
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"  deploy tx: 0x{tx_hash.hex()}")
    print(f"  waiting for receipt…")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120, poll_latency=2)
    if receipt.status != 1:
        sys.exit(f"ERROR: deploy reverted — receipt {receipt}")
    return receipt.contractAddress, tx_hash.hex()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--network", default="galileo", choices=["galileo", "sepolia"])
    p.add_argument("--contract", default="BillRegistry", choices=list(CONTRACTS))
    args = p.parse_args()

    env = load_env()

    if args.network == "galileo":
        rpc = env.get("ZG_RPC_URL", "https://evmrpc-testnet.0g.ai")
        chain_id = int(env.get("ZG_CHAIN_ID", "16602"))
        explorer = "https://chainscan-galileo.0g.ai"
    else:
        rpc = env.get("SEPOLIA_RPC_URL") or "https://ethereum-sepolia.publicnode.com"
        chain_id = 11155111
        explorer = "https://sepolia.etherscan.io"

    pk = env.get("ZG_PRIVATE_KEY")
    if not pk:
        sys.exit("ERROR: ZG_PRIVATE_KEY not set in .env")

    abi, bytecode = compile_contract(args.contract)
    addr, tx_hex = deploy(rpc, chain_id, pk, abi, bytecode)

    out = {"network": args.network, "chain_id": chain_id, "contract": args.contract,
           "address": addr, "deploy_tx": "0x" + tx_hex, "abi": abi}
    out_path = Path(__file__).parent / f"deployed.{args.contract}.{args.network}.json"
    out_path.write_text(json.dumps(out, indent=2))
    print()
    print("=" * 60)
    print(f" Deployed {args.contract} on {args.network} (chain {chain_id})")
    print("=" * 60)
    print(f" Address:  {addr}")
    print(f" Tx:       {explorer}/tx/0x{tx_hex}")
    print(f" Saved:    {out_path.relative_to(REPO_ROOT)}")
    print()
    env_key = ENV_KEYS.get(args.contract, args.contract.upper() + "_ADDRESS")
    if args.network == "sepolia":
        env_key += "_SEPOLIA"
    print(f" Now paste into .env:")
    print(f"    {env_key}={addr}")


if __name__ == "__main__":
    main()
