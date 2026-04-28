"""NCCIRulebook reads — agents query the active CMS coding ruleset on-chain.

Why on-chain: CMS publishes NCCI quarterly. Codifying the rules in a contract
means any auditor — Lethe or otherwise — can query a single canonical source
without trusting Lethe's database. Versioning + governance are properly
solved problems on a chain. Updates can be voted by a multisig instead of
hot-pushed by a vendor.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from config import settings

log = logging.getLogger("lethe.chain.ncci_rulebook")


_KIND_NAMES = ["unknown", "mutually_exclusive", "bundled_into_column1",
               "modifier_required", "units_cap", "modifier_abuse_flag"]


_NCCI_RULEBOOK_ABI = [
    {"type": "function", "name": "currentVersion", "stateMutability": "view",
     "inputs": [], "outputs": [{"type": "uint16"}]},
    {"type": "function", "name": "ruleCount", "stateMutability": "view",
     "inputs": [{"name": "version", "type": "uint16"}], "outputs": [{"type": "uint256"}]},
    {"type": "function", "name": "ruleIdsByVersion", "stateMutability": "view",
     "inputs": [{"name": "version", "type": "uint16"}, {"name": "i", "type": "uint256"}],
     "outputs": [{"type": "uint16"}]},
    {"type": "function", "name": "getRule", "stateMutability": "view",
     "inputs": [{"name": "id", "type": "uint16"}], "outputs": [{
         "type": "tuple",
         "components": [
             {"name": "id", "type": "uint16"},
             {"name": "version", "type": "uint16"},
             {"name": "kind", "type": "uint8"},
             {"name": "cptA", "type": "bytes32"},
             {"name": "cptB", "type": "bytes32"},
             {"name": "mod", "type": "bytes16"},
             {"name": "unitsCapPerDay", "type": "uint32"},
             {"name": "citation", "type": "string"},
         ],
     }]},
]


def _b32_to_str(b: bytes) -> str:
    try:
        return b.rstrip(b"\x00").decode("ascii", errors="replace")
    except Exception:
        return b.hex()


def _read_active_rules_sync() -> Dict[str, Any]:
    from web3 import Web3
    if not settings.ncci_rulebook_address:
        return {"configured": False, "rules": []}
    w3 = Web3(Web3.HTTPProvider(settings.zg_rpc_url, request_kwargs={"timeout": 8}))
    if not w3.is_connected():
        return {"configured": True, "error": "rpc unreachable", "rules": []}
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(settings.ncci_rulebook_address),
        abi=_NCCI_RULEBOOK_ABI,
    )
    try:
        version = contract.functions.currentVersion().call()
        # Try the latest published version first; if it's empty we may be
        # reading the in-progress draft, so fall back one.
        n = contract.functions.ruleCount(version).call()
        if n == 0 and version > 1:
            version -= 1
            n = contract.functions.ruleCount(version).call()
    except Exception as e:
        return {"configured": True, "error": str(e)[:200], "rules": []}

    rules: List[Dict[str, Any]] = []
    for i in range(min(n, 200)):  # cap at 200 just to bound the read
        try:
            rule_id = contract.functions.ruleIdsByVersion(version, i).call()
            r = contract.functions.getRule(rule_id).call()
            rules.append({
                "id": int(r[0]),
                "version": int(r[1]),
                "kind": _KIND_NAMES[int(r[2])] if int(r[2]) < len(_KIND_NAMES) else "unknown",
                "cpt_a": _b32_to_str(r[3]),
                "cpt_b": _b32_to_str(r[4]),
                "modifier": _b32_to_str(r[5]),
                "units_cap_per_day": int(r[6]),
                "citation": str(r[7]),
            })
        except Exception:
            continue
    return {
        "configured": True,
        "version": int(version),
        "count": len(rules),
        "rules": rules,
        "registry_address": settings.ncci_rulebook_address,
    }


async def fetch_active_rules() -> Dict[str, Any]:
    """Read the active NCCI ruleset from chain. Returns {} on stub mode."""
    return await asyncio.to_thread(_read_active_rules_sync)


def format_rules_for_prompt(rules_data: Dict[str, Any]) -> str:
    """Compact text block listing the active rules — appended to agent prompts
    so reasoning is grounded in the current on-chain ruleset."""
    rules = rules_data.get("rules") or []
    if not rules:
        return ""
    lines = [
        f"NCCI RULEBOOK (active version v{rules_data.get('version', '?')}, "
        f"on-chain at {(rules_data.get('registry_address') or '')[:10]}…):",
    ]
    for r in rules[:30]:
        line = f"  · {r['kind']:24s} {r['cpt_a']:14s}"
        if r.get("cpt_b"):
            line += f" ↔ {r['cpt_b']:14s}"
        if r.get("modifier"):
            line += f" mod={r['modifier']}"
        if r.get("units_cap_per_day"):
            line += f" units<={r['units_cap_per_day']}"
        if r.get("citation"):
            line += f"  [{r['citation']}]"
        lines.append(line)
    return "\n".join(lines)
