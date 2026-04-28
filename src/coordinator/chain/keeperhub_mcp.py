"""KeeperHub mirror anchor — via MCP server (Model Context Protocol).

Same Sepolia anchor flow as `chain/keeperhub.py`, but reaches KeeperHub through
its MCP server instead of the Direct Execution REST API. The KeeperHub track's
prize description specifies "MCP server or CLI" as the integration vector; this
module is the strict-qualification path.

Drop-in replacement for `keeperhub.anchor_via_keeperhub` — returns the same
dict shape so the pipeline runner doesn't need to change.

Transport options:
  - HOSTED HTTP (default): https://app.keeperhub.com/mcp
    - Auth via `Authorization: Bearer <KEEPERHUB_API_KEY>` header.
    - If the hosted endpoint requires browser OAuth and rejects header auth,
      caller falls back to REST automatically (we surface the error).

Tools called (per KeeperHub's MCP schema):
  - `execute_contract_call(contract_address, network, function_name,
     function_args, abi)` -> {execution_id, status, ...}
  - `get_direct_execution_status(execution_id)` -> {status, transactionHash, ...}
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional

from config import settings

log = logging.getLogger("lethe.chain.keeperhub_mcp")


# Same verdict enum as BillRegistry.sol (mirrors keeperhub.py)
_VERDICT_ENUM = {"none": 0, "dispute": 1, "approve": 2, "clarify": 3}

_ANCHOR_ABI = [{
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
}]


def _stub(reason: str) -> Dict[str, Any]:
    return {
        "executor": f"stub-mcp ({reason})",
        "live": False,
        "network": "sepolia",
    }


def _parse_tool_result(result: Any) -> Dict[str, Any]:
    """MCP tools return content as a list — usually one TextContent with JSON.

    Handles both:
      - structuredContent (newer MCP servers return parsed dicts directly)
      - content[0].text (older servers return JSON-as-string)
    """
    # Prefer structuredContent if present (less parsing risk)
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        return structured

    content = getattr(result, "content", None) or []
    for block in content:
        text = getattr(block, "text", None)
        if not text:
            continue
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            continue
    return {}


async def anchor_via_keeperhub_mcp(
    sha256_hex: str,
    verdict: str = "dispute",
    agree_count: int = 3,
    total_agents: int = 3,
) -> Dict[str, Any]:
    """Same contract as `keeperhub.anchor_via_keeperhub` but via MCP."""
    if not settings.keeperhub_api_key:
        return _stub("no api key")
    if not settings.bill_registry_address_sepolia:
        return _stub("no sepolia registry")
    if verdict.lower() not in _VERDICT_ENUM or _VERDICT_ENUM[verdict.lower()] == 0:
        return _stub(f"verdict={verdict} not anchored")

    # Lazy import — MCP client is only needed when this path is enabled.
    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
    except ImportError:
        log.warning("mcp package not installed; falling back to stub")
        return _stub("mcp package missing — pip install mcp")

    sha = sha256_hex if sha256_hex.startswith("0x") else "0x" + sha256_hex
    verdict_int = _VERDICT_ENUM[verdict.lower()]
    agree = max(1, min(int(agree_count), int(total_agents)))
    total = max(agree, int(total_agents))

    args = {
        "contract_address": settings.bill_registry_address_sepolia,
        "network": "sepolia",
        "function_name": "anchor",
        "function_args": [sha, verdict_int, agree, total],
        "abi": json.dumps(_ANCHOR_ABI),
    }

    headers = {
        "Authorization": f"Bearer {settings.keeperhub_api_key}",
        "X-API-Key": settings.keeperhub_api_key,
    }

    started = time.perf_counter()
    try:
        async with streamablehttp_client(
            settings.keeperhub_mcp_url,
            headers=headers,
        ) as (read_stream, write_stream, _close):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                exec_call = await session.call_tool(
                    "execute_contract_call",
                    arguments=args,
                )
                initial = _parse_tool_result(exec_call)
                exec_id = (
                    initial.get("execution_id")
                    or initial.get("executionId")
                    or initial.get("id")
                )
                status = initial.get("status", "pending")

                if not exec_id:
                    return {
                        **_stub("mcp returned no execution_id"),
                        "raw_response": str(initial)[:240],
                        "duration_ms": int((time.perf_counter() - started) * 1000),
                    }

                # Poll status until terminal (≤ 60s).
                terminal = {"completed", "failed", "succeeded", "success"}
                final: Dict[str, Any] = initial
                for _ in range(31):
                    if status in terminal:
                        break
                    poll = await session.call_tool(
                        "get_direct_execution_status",
                        arguments={"execution_id": exec_id},
                    )
                    final = _parse_tool_result(poll) or final
                    status = final.get("status", status)
                    if status in terminal:
                        break
                    await asyncio.sleep(2.0)

                tx_hash = (
                    final.get("transactionHash")
                    or final.get("transaction_hash")
                    or final.get("tx_hash")
                )
                tx_link = (
                    final.get("transactionLink")
                    or final.get("transaction_link")
                    or final.get("tx_link")
                )
                duration_ms = int((time.perf_counter() - started) * 1000)
                err_msg = final.get("error") or ""

                log.info(
                    "keeperhub-mcp anchor exec=%s status=%s tx=%s ms=%d",
                    exec_id, status, (tx_hash or "")[:18], duration_ms,
                )

                ok = status in ("completed", "succeeded", "success")

                # Treat "already anchored" revert as success-with-duplicate
                # (matches keeperhub.py and zerog.py duplicate handling).
                if not ok and "already anchored" in err_msg.lower():
                    return {
                        "executor": "keeperhub-mcp (already anchored)",
                        "live": True,
                        "network": "sepolia",
                        "chain_id": 11155111,
                        "execution_id": exec_id,
                        "status": "duplicate",
                        "tx_hash": None,
                        "tx_link": None,
                        "registry_address": settings.bill_registry_address_sepolia,
                        "duration_ms": duration_ms,
                        "note": "this sha-256 was already anchored to the Sepolia mirror by a prior audit",
                    }

                return {
                    "executor": "keeperhub-mcp",
                    "live": ok,
                    "network": "sepolia",
                    "chain_id": 11155111,
                    "execution_id": exec_id,
                    "status": status,
                    "tx_hash": tx_hash,
                    "tx_link": tx_link or (
                        f"https://sepolia.etherscan.io/tx/{tx_hash}" if tx_hash else None
                    ),
                    "registry_address": settings.bill_registry_address_sepolia,
                    "duration_ms": duration_ms,
                    "error": err_msg if not ok else None,
                }
    except Exception as e:
        log.warning("keeperhub-mcp call failed: %s — caller can fall back to REST", e)
        return {
            **_stub(f"mcp error: {type(e).__name__}"),
            "error": str(e)[:240],
            "duration_ms": int((time.perf_counter() - started) * 1000),
        }
