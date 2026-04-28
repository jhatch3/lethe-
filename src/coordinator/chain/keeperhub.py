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


async def _lookup_existing_anchor_tx(sha_hex: str) -> Dict[str, Any]:
    """Find the tx hash of the original `Anchored` event for a given bill hash.

    Used when KeeperHub reports "already anchored" — KH itself doesn't surface
    the original tx for duplicates, so we query the Sepolia RPC directly with
    an `eth_getLogs` call filtered by the indexed `sha256Hash` topic.

    Returns {"tx_hash": "0x...", "block_number": int} on success, {} on miss.
    """
    if not settings.bill_registry_address_sepolia or not settings.sepolia_rpc_url:
        return {}

    def _sync_lookup() -> Dict[str, Any]:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(settings.sepolia_rpc_url, request_kwargs={"timeout": 8}))
        if not w3.is_connected():
            return {}
        sha = sha_hex if sha_hex.startswith("0x") else "0x" + sha_hex
        anchored_topic = "0x" + Web3.keccak(
            text="Anchored(bytes32,uint8,uint8,uint8,uint64,address)"
        ).hex().lstrip("0x")
        logs = w3.eth.get_logs({
            "address": Web3.to_checksum_address(settings.bill_registry_address_sepolia),
            "topics": [anchored_topic, sha],
            "fromBlock": "earliest",
            "toBlock": "latest",
        })
        if not logs:
            return {}
        first = logs[0]
        tx_hex = first["transactionHash"].hex()
        return {
            "tx_hash": tx_hex if tx_hex.startswith("0x") else "0x" + tx_hex,
            "block_number": int(first["blockNumber"]),
        }

    try:
        return await asyncio.to_thread(_sync_lookup)
    except Exception as e:
        log.debug("sepolia anchor lookup failed: %s", e)
        return {}


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

            # Treat the "already anchored" contract revert as a non-error
            # duplicate state — same semantics as zerog.py. The canonical
            # tx is whichever audit anchored this hash first; we just signal
            # the bill is already on-chain.
            err_msg = initial.get("error") or ""
            if not ok and "already anchored" in err_msg.lower():
                # Best-effort: look up the original Anchored event so the
                # receipt can link to the actual tx, not "pending".
                original = await _lookup_existing_anchor_tx(sha)
                orig_tx = original.get("tx_hash")
                return {
                    "executor": "keeperhub (already anchored)",
                    "live": True,
                    "network": "sepolia",
                    "chain_id": 11155111,
                    "execution_id": exec_id,
                    "status": "duplicate",
                    "tx_hash": orig_tx,
                    "tx_link": (
                        f"https://sepolia.etherscan.io/tx/{orig_tx}"
                        if orig_tx
                        else f"https://sepolia.etherscan.io/address/{settings.bill_registry_address_sepolia}#events"
                    ),
                    "block_number": original.get("block_number"),
                    "registry_address": settings.bill_registry_address_sepolia,
                    "duration_ms": duration_ms,
                    "note": "this sha-256 was already anchored to the Sepolia mirror by a prior audit",
                }

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
                "error": err_msg if not ok else None,
            }
    except Exception as e:
        log.warning("keeperhub call failed: %s", e)
        return {
            **_stub(f"error: {type(e).__name__}"),
            "error": str(e)[:240],
            "duration_ms": int((time.perf_counter() - started) * 1000),
        }


# Reasons mirror the verdict semantics — only `dispute` actually files; this
# enum exists so future verdict types can be slotted in without ABI churn.
_DISPUTE_REASONS = {"dispute": 1}

# Compact ABI for the dispute-filer endpoint. KH expects ABI as JSON STRING.
def _dispute_abi_json(function_name: str) -> str:
    return json.dumps([{
        "type": "function",
        "name": function_name,
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "billHash", "type": "bytes32"},
            {"name": "reason",   "type": "uint8"},
            {"name": "note",     "type": "string"},
        ],
        "outputs": [],
    }])


async def file_dispute_via_keeperhub(
    sha256_hex: str,
    findings_summary: str,
    reason: str = "dispute",
) -> Dict[str, Any]:
    """Second KH workflow execution: when consensus = dispute, KH fires a
    Direct Execution against the configurable dispute-registry contract.

    This is distinct from the mirror anchor — different contract, different
    method, different verdict gate. Demonstrates KH as an execution platform
    for multiple workflows, not a single mirror call.

    `findings_summary` is a short human-readable string (≤512 chars) capturing
    the disputed CPT codes and severity — already PHI-redacted upstream.

    Returns the same shape as `anchor_via_keeperhub` for receipt-symmetry.
    """
    if not settings.keeperhub_api_key:
        return _stub("no api key")
    if not settings.dispute_registry_address_sepolia:
        return _stub("no dispute registry configured")
    if reason.lower() not in _DISPUTE_REASONS:
        return _stub(f"reason={reason} not filed")

    sha = sha256_hex if sha256_hex.startswith("0x") else "0x" + sha256_hex
    reason_int = _DISPUTE_REASONS[reason.lower()]
    note = (findings_summary or "")[:512]

    body = {
        "contractAddress": settings.dispute_registry_address_sepolia,
        "network": "sepolia",
        "functionName": settings.dispute_function_name,
        "functionArgs": json.dumps([sha, reason_int, note]),
        "abi": _dispute_abi_json(settings.dispute_function_name),
        "gasLimitMultiplier": "1.2",
    }

    started = time.perf_counter()
    try:
        async with httpx.AsyncClient() as client:
            r = await _kh_post(client, "/api/execute/contract-call", body)
            if r.status_code not in (200, 201, 202):
                return {
                    **_stub(f"http {r.status_code}"),
                    "error": r.text[:240],
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                }
            initial = r.json()
            exec_id = initial.get("executionId") or initial.get("id")
            status = initial.get("status", "pending")
            terminal = {"completed", "failed", "succeeded", "success"}
            for _ in range(31):
                rr = await _kh_get(client, f"/api/execute/{exec_id}/status")
                if rr.status_code == 200:
                    initial = rr.json()
                    status = initial.get("status", status)
                if status in terminal:
                    break
                await asyncio.sleep(2.0)

            result_obj = initial.get("result") or {}
            tx_hash = (
                initial.get("transactionHash")
                or (result_obj.get("transactionHash") if isinstance(result_obj, dict) else None)
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            ok = status in ("completed", "succeeded", "success")

            log.info(
                "keeperhub dispute exec=%s status=%s tx=%s ms=%d",
                exec_id, status, (tx_hash or "")[:18], duration_ms,
            )
            return {
                "executor": "keeperhub",
                "live": ok,
                "network": "sepolia",
                "chain_id": 11155111,
                "execution_id": exec_id,
                "status": status,
                "tx_hash": tx_hash,
                "tx_link": f"https://sepolia.etherscan.io/tx/{tx_hash}" if tx_hash else None,
                "registry_address": settings.dispute_registry_address_sepolia,
                "function_name": settings.dispute_function_name,
                "duration_ms": duration_ms,
                "error": initial.get("error") if not ok else None,
            }
    except Exception as e:
        log.warning("keeperhub dispute call failed: %s", e)
        return {
            **_stub(f"error: {type(e).__name__}"),
            "error": str(e)[:240],
            "duration_ms": int((time.perf_counter() - started) * 1000),
        }


# Compact ABI for the AppealRegistry endpoint.
_APPEAL_ABI_JSON = json.dumps([{
    "type": "function",
    "name": "recordAppealSent",
    "stateMutability": "nonpayable",
    "inputs": [
        {"name": "billHash",      "type": "bytes32"},
        {"name": "recipientHash", "type": "bytes32"},
    ],
    "outputs": [],
}])


async def attest_appeal_sent_via_keeperhub(
    sha256_hex: str,
    recipient_hash_hex: str,
) -> Dict[str, Any]:
    """Third KH workflow: record on-chain that an appeal letter was emailed.

    `recipient_hash_hex` is keccak256 of `email | salt` so the actual recipient
    address never touches Sepolia. Same Direct Execution path as the mirror
    anchor + dispute filer; stub-fallback when AppealRegistry isn't configured.
    """
    if not settings.keeperhub_api_key:
        return _stub("no api key")
    if not settings.appeal_registry_address_sepolia:
        return _stub("no appeal registry configured")

    sha = sha256_hex if sha256_hex.startswith("0x") else "0x" + sha256_hex
    rh  = recipient_hash_hex if recipient_hash_hex.startswith("0x") else "0x" + recipient_hash_hex

    body = {
        "contractAddress": settings.appeal_registry_address_sepolia,
        "network": "sepolia",
        "functionName": "recordAppealSent",
        "functionArgs": json.dumps([sha, rh]),
        "abi": _APPEAL_ABI_JSON,
        "gasLimitMultiplier": "1.2",
    }

    started = time.perf_counter()
    try:
        async with httpx.AsyncClient() as client:
            r = await _kh_post(client, "/api/execute/contract-call", body)
            if r.status_code not in (200, 201, 202):
                return {
                    **_stub(f"http {r.status_code}"),
                    "error": r.text[:240],
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                }
            initial = r.json()
            exec_id = initial.get("executionId") or initial.get("id")
            status = initial.get("status", "pending")
            terminal = {"completed", "failed", "succeeded", "success"}
            for _ in range(31):
                rr = await _kh_get(client, f"/api/execute/{exec_id}/status")
                if rr.status_code == 200:
                    initial = rr.json()
                    status = initial.get("status", status)
                if status in terminal:
                    break
                await asyncio.sleep(2.0)

            result_obj = initial.get("result") or {}
            tx_hash = (
                initial.get("transactionHash")
                or (result_obj.get("transactionHash") if isinstance(result_obj, dict) else None)
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            ok = status in ("completed", "succeeded", "success")
            log.info(
                "keeperhub appeal-attest exec=%s status=%s tx=%s ms=%d",
                exec_id, status, (tx_hash or "")[:18], duration_ms,
            )
            return {
                "executor": "keeperhub",
                "live": ok,
                "network": "sepolia",
                "chain_id": 11155111,
                "execution_id": exec_id,
                "status": status,
                "tx_hash": tx_hash,
                "tx_link": f"https://sepolia.etherscan.io/tx/{tx_hash}" if tx_hash else None,
                "registry_address": settings.appeal_registry_address_sepolia,
                "duration_ms": duration_ms,
                "error": initial.get("error") if not ok else None,
            }
    except Exception as e:
        log.warning("keeperhub appeal-attest call failed: %s", e)
        return {
            **_stub(f"error: {type(e).__name__}"),
            "error": str(e)[:240],
            "duration_ms": int((time.perf_counter() - started) * 1000),
        }
