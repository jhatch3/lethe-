"""Pre-flight check for the Lethe coordinator.

Run after `pip install -r requirements.txt` and before `uvicorn main:app`.
Verifies addresses, balances, sidecar reachability, and AXL mesh topology so
you don't discover broken config from a 30-second-old SSE error.

Exits 0 always — checks are advisory. Pass --strict to exit 1 on any red.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
COORDINATOR = REPO_ROOT / "src" / "coordinator"
sys.path.insert(0, str(COORDINATOR))

import httpx
from config import settings  # noqa: E402  — sys.path manipulated above


# ─────────────────────────────────────────────────────────────────────────────
# Output
# ─────────────────────────────────────────────────────────────────────────────


GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
DIM = "\033[2m"
RESET = "\033[0m"
BOLD = "\033[1m"


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def ok(self, label: str, value: str = "") -> None:
        print(f"  {GREEN}✓{RESET} {label:<32} {DIM}{value}{RESET}")

    def warn(self, label: str, value: str = "") -> None:
        self.warnings.append(label)
        print(f"  {YELLOW}!{RESET} {label:<32} {DIM}{value}{RESET}")

    def err(self, label: str, value: str = "") -> None:
        self.errors.append(label)
        print(f"  {RED}✗{RESET} {label:<32} {DIM}{value}{RESET}")

    def section(self, name: str) -> None:
        print(f"\n{BOLD}{name}{RESET}")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def derive_address(pk: str) -> Optional[str]:
    if not pk:
        return None
    try:
        from eth_account import Account
        return Account.from_key(pk).address
    except Exception:
        return None


def short(s: Optional[str], head: int = 10, tail: int = 6) -> str:
    if not s:
        return "—"
    if len(s) <= head + tail + 1:
        return s
    return f"{s[:head]}…{s[-tail:]}"


async def rpc(client: httpx.AsyncClient, url: str, method: str, params: list) -> Optional[str]:
    try:
        r = await client.post(url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, timeout=5.0)
        r.raise_for_status()
        return r.json().get("result")
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Checks
# ─────────────────────────────────────────────────────────────────────────────


async def check_wallet(report: Report, client: httpx.AsyncClient) -> None:
    report.section("Coordinator wallet")
    addr = derive_address(settings.zg_private_key)
    if not addr:
        report.err("ZG_PRIVATE_KEY", "missing or invalid — anchor + indexFindings + storage will stub")
        return
    report.ok("derived address", addr)

    bal_hex = await rpc(client, settings.zg_rpc_url, "eth_getBalance", [addr, "latest"])
    if bal_hex is None:
        report.warn("Galileo balance", f"RPC unreachable at {settings.zg_rpc_url}")
        return
    bal_wei = int(bal_hex, 16)
    bal_og = bal_wei / 1e18
    if bal_og < 0.005:
        report.warn("Galileo balance", f"{bal_og:.6f} OG — too low for a full audit (need ≥ 0.005)")
    else:
        report.ok("Galileo balance", f"{bal_og:.6f} OG")


async def check_galileo_contracts(report: Report, client: httpx.AsyncClient) -> None:
    report.section("0G Galileo contracts")
    rpc_url = settings.zg_rpc_url

    chain_hex = await rpc(client, rpc_url, "eth_chainId", [])
    if chain_hex is None:
        report.err("RPC", f"unreachable at {rpc_url}")
        return
    chain_id = int(chain_hex, 16)
    if chain_id != settings.zg_chain_id:
        report.warn("chain id", f"RPC reports {chain_id}, configured {settings.zg_chain_id}")
    else:
        report.ok("chain id", f"{chain_id}")

    contracts = [
        ("LetheRegistry", settings.lethe_registry_address or settings.bill_registry_address),
        ("PatternRegistry", settings.pattern_registry_address),
        ("StorageIndex", settings.storage_index_address),
    ]
    for name, addr in contracts:
        if not addr:
            report.warn(name, "not configured — feature stubs")
            continue
        code = await rpc(client, rpc_url, "eth_getCode", [addr, "latest"])
        if code in (None, "0x", "0x0"):
            report.err(name, f"{short(addr)} — no contract at this address")
        else:
            report.ok(name, f"{short(addr)} · {len(code)//2} bytes deployed")


async def check_sepolia(report: Report, client: httpx.AsyncClient) -> None:
    report.section("Sepolia mirror (KeeperHub)")
    rpc_url = settings.sepolia_rpc_url
    addr = settings.lethe_registry_address_sepolia or settings.bill_registry_address_sepolia
    if not addr:
        report.warn("LetheRegistry", "not configured")
        return
    code = await rpc(client, rpc_url, "eth_getCode", [addr, "latest"])
    if code in (None, "0x", "0x0"):
        report.err("LetheRegistry", f"{short(addr)} — no contract at this address")
    else:
        report.ok("LetheRegistry", f"{short(addr)} · {len(code)//2} bytes deployed")

    if settings.keeperhub_api_key:
        report.ok("KeeperHub key", "configured")
    else:
        report.warn("KeeperHub key", "missing — all 3 KH workflows will stub")


async def check_storage_sidecar(report: Report, client: httpx.AsyncClient) -> None:
    report.section("0G Storage sidecar")
    url = (settings.zg_storage_sidecar_url or "").strip().rstrip("/")
    if not url:
        report.warn("sidecar URL", "not configured — uploads will stub")
        return
    try:
        r = await client.get(f"{url}/health", timeout=2.0)
        r.raise_for_status()
        d = r.json()
        report.ok("sidecar /health", f"{url} · wallet {short(d.get('wallet'))}")
    except Exception as e:
        report.err("sidecar /health", f"{url} unreachable — start `npm run storage:0g` ({type(e).__name__})")


async def check_axl(report: Report, client: httpx.AsyncClient) -> None:
    report.section("Gensyn AXL sidecars")
    if not settings.axl_enabled:
        report.warn("AXL", "LETHE_AXL_ENABLED=false — pipeline uses asyncio.gather")
        return
    sidecars = [
        ("alpha", settings.axl_alpha_url),
        ("beta", settings.axl_beta_url),
        ("gamma", settings.axl_gamma_url),
    ]
    for name, url in sidecars:
        try:
            r = await client.get(f"{url.rstrip('/')}/topology", timeout=2.0)
            r.raise_for_status()
            d = r.json()
            peer = d.get("peer_id") or d.get("self") or "?"
            report.ok(f"{name} sidecar", f"{url} · {short(peer)}")
        except Exception as e:
            report.err(f"{name} sidecar", f"{url} unreachable ({type(e).__name__})")


def check_api_keys(report: Report) -> None:
    report.section("LLM keys")
    keys = [
        ("OPENAI_API_KEY  (α)", settings.openai_api_key),
        ("ANTHROPIC_API_KEY (β)", settings.anthropic_api_key),
        ("GOOGLE_API_KEY  (γ)", settings.google_api_key),
    ]
    for name, val in keys:
        if val:
            report.ok(name, "set")
        else:
            report.warn(name, "missing — agent will use deterministic stub")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


async def main_async(strict: bool) -> int:
    print(f"{BOLD}Lethe coordinator preflight{RESET}  {DIM}{REPO_ROOT}{RESET}")
    report = Report()

    async with httpx.AsyncClient() as client:
        await asyncio.gather(
            check_wallet(report, client),
            check_galileo_contracts(report, client),
            check_sepolia(report, client),
            check_storage_sidecar(report, client),
            check_axl(report, client),
        )
    check_api_keys(report)

    print()
    if report.errors:
        print(f"{RED}{len(report.errors)} error(s){RESET}, "
              f"{YELLOW}{len(report.warnings)} warning(s){RESET}")
        return 1 if strict else 0
    if report.warnings:
        print(f"{YELLOW}{len(report.warnings)} warning(s){RESET} — non-blocking")
    else:
        print(f"{GREEN}all green{RESET}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="exit 1 on any error")
    args = parser.parse_args()
    rc = asyncio.run(main_async(args.strict))
    sys.exit(rc)


if __name__ == "__main__":
    main()