"""KeeperHub mirror anchor (Sepolia).

Submits a parallel anchor write to the Sepolia BillRegistry mirror via
KeeperHub's Direct Execution API. KH handles signing (with its auto-provisioned
wallet at 0xC33E920102d53Bf2B4286361c23E63D93FeB02ee), gas, retries, and the
audit trail visible in the KH dashboard.

The 0G anchor is the canonical record. This is the redundant execution-layer
demo for the KeeperHub sponsor track.

Falls back to a stub when:
    - KEEPERHUB_API_KEY is missing, or
    - BILL_REGISTRY_ADDRESS_SEPOLIA is missing, or
    - the API call errors

so the rest of the pipeline keeps running.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict

import httpx

from config import settings

log = logging.getLogger("lethe.chain.keeperhub")


# Same verdict enum as BillRegistry.sol
_VERDICT_ENUM = {"none": 0, "dispute": 1, "approve": 2, "clarify": 3}

# Compact ABI for the one method we hit. KH wants this as a JSON STRING.
_ANCHOR_ABI_JSON = json.dumps([{
    "type": "function",
    "name": "anchor",
    "stateMutability": "nonpayable",
    "inputs": [
        {"name": "sha256Hash",  "type": "bytes32"},
        {"name": "verdict",     "type": "uint8"},
        {"name": "agreeCount",  "type": "uint8"},
        {"name": "totalAgents", "type": "uint8"},
    ],
    "outputs": [],
}])


def _stub(reason: str) -> Dict[str, Any]:
    return {
        "executor": f"stub ({reason})",
        "live": False,
        "network": "sepolia",
    }


async def _kh_post(client: httpx.AsyncClient, path: str, json_body: Dict[str, Any]) -> httpx.Response:
    """POST with both auth header styles — KH's docs reference two; we try both."""
    base = settings.keeperhub_base_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {settings.keeperhub_api_key}",
        "X-API-Key": settings.keeperhub_api_key,
        "Content-Type": "application/json",
    }
    return await client.post(f"{base}{path}", json=json_body, headers=headers, timeout=30.0)


async def _kh_get(client: httpx.AsyncClient, path: str) -> httpx.Response:
    base = settings.keeperhub_base_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {settings.keeperhub_api_key}",
        "X-API-Key": settings.keeperhub_api_key,
    }
    return await client.get(f"{base}{path}", headers=headers, timeout=30.0)


async def anchor_via_keeperhub(
    sha256_hex: str,
    verdict: str = "dispute",
    agree_count: int = 3,
    total_agents: int = 3,
) -> Dict[str, Any]:
    """Submit a Sepolia BillRegistry anchor via KeeperHub Direct Execution.

    Returns:
        {
          executor: "keeperhub" | "stub (reason)",
          live: bool,
          network: "sepolia",
          execution_id: str,
          status: "completed" | "failed" | "pending",
          tx_hash: str,
          tx_link: str,
          registry_address: str,
          duration_ms: int,
        }
    """
    if not settings.keeperhub_api_key:
        return _stub("no api key")
    if not settings.bill_registry_address_sepolia:
        return _stub("no sepolia registry")
    if verdict.lower() not in _VERDICT_ENUM or _VERDICT_ENUM[verdict.lower()] == 0:
        return _stub(f"verdict={verdict} not anchored")

    sha = sha256_hex if sha256_hex.startswith("0x") else "0x" + sha256_hex
    verdict_int = _VERDICT_ENUM[verdict.lower()]
    agree = max(1, min(int(agree_count), int(total_agents)))
    total = max(agree, int(total_agents))

    body = {
        "contractAddress": settings.bill_registry_address_sepolia,
        "network": "sepolia",
        "functionName": "anchor",
        "functionArgs": json.dumps([sha, verdict_int, agree, total]),
        "abi": _ANCHOR_ABI_JSON,
        "gasLimitMultiplier": "1.2",
    }

    started = time.perf_counter()
    try:
        async with httpx.AsyncClient() as client:
            r = await _kh_post(client, "/api/execute/contract-call", body)
            if r.status_code not in (200, 201, 202):
                err = r.text[:240]
                return {
                    **_stub(f"http {r.status_code}"),
                    "error": err,
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                }
            initial = r.json()
            exec_id = initial.get("executionId") or initial.get("id")
            status = initial.get("status", "pending")

            # The POST response is minimal — even when KH reports "completed"
            # immediately, the tx_hash only lives on the /status endpoint.
            # Always do at least one GET, then poll until terminal.
            terminal = {"completed", "failed", "succeeded", "success"}
            for poll_idx in range(31):  # 0..30 = up to 60s
                rr = await _kh_get(client, f"/api/execute/{exec_id}/status")
                if rr.status_code == 200:
                    initial = rr.json()
                    status = initial.get("status", status)
                if status in terminal:
                    break
                await asyncio.sleep(2.0)

            # Tx hash can also live under result.transactionHash for completed calls.
            result_obj = initial.get("result") or {}
            tx_hash = (
                initial.get("transactionHash")
                or initial.get("transaction_hash")
                or (result_obj.get("transactionHash") if isinstance(result_obj, dict) else None)
            )
            tx_link = (
                initial.get("transactionLink")
                or initial.get("transaction_link")
                or (result_obj.get("transactionLink") if isinstance(result_obj, dict) else None)
            )
            duration_ms = int((time.perf_counter() - started) * 1000)

            log.info(
                "keeperhub anchor exec=%s status=%s tx=%s ms=%d",
                exec_id, status, (tx_hash or "")[:18], duration_ms,
            )

            ok = status in ("completed", "succeeded", "success")
            return {
                "executor": "keeperhub",
                "live": ok,
                "network": "sepolia",
                "chain_id": 11155111,
                "execution_id": exec_id,
                "status": status,
                "tx_hash": tx_hash,
                "tx_link": tx_link
                    or (f"https://sepolia.etherscan.io/tx/{tx_hash}" if tx_hash else None),
                "registry_address": settings.bill_registry_address_sepolia,
                "duration_ms": duration_ms,
                "error": initial.get("error") if not ok else None,
            }
    except Exception as e:
        log.warning("keeperhub call failed: %s", e)
        return {
            **_stub(f"error: {type(e).__name__}"),
            "error": str(e)[:240],
            "duration_ms": int((time.perf_counter() - started) * 1000),
        }
