"""Dashboard endpoints: global event stream + system snapshot.

Powers tools/dashboard.py — a separate CLI TUI that subscribes to the
coordinator and renders a live ASCII view of every track's state.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from agents import transport_axl
from agents.registry import get_audit_agents, get_drafter
from config import settings
from pipeline.events import Event, bus

router = APIRouter(prefix="/api", tags=["dashboard"])

log = logging.getLogger("lethe.dashboard")


def _wallet_address_from_private_key(pk: str) -> Optional[str]:
    """Derive 0x address from configured private key without an RPC call."""
    if not pk:
        return None
    try:
        from eth_account import Account
        return Account.from_key(pk).address
    except Exception as e:
        log.debug("wallet derive failed: %s", e)
        return None


async def _fetch_galileo_balance(address: str) -> Optional[int]:
    if not address:
        return None
    try:
        async with httpx.AsyncClient(timeout=4.0) as c:
            r = await c.post(settings.zg_rpc_url, json={
                "jsonrpc": "2.0", "id": 1,
                "method": "eth_getBalance",
                "params": [address, "latest"],
            })
            r.raise_for_status()
            return int(r.json()["result"], 16)
    except Exception as e:
        log.debug("balance fetch failed: %s", e)
        return None


async def _probe_storage_sidecar() -> Dict[str, Any]:
    url = settings.zg_storage_sidecar_url.strip().rstrip("/")
    if not url:
        return {"configured": False, "reachable": False}
    try:
        async with httpx.AsyncClient(timeout=2.0) as c:
            r = await c.get(f"{url}/health")
            r.raise_for_status()
            d = r.json()
            return {"configured": True, "reachable": True, "wallet": d.get("wallet")}
    except Exception as e:
        return {"configured": True, "reachable": False, "error": type(e).__name__}


@router.get("/dashboard/snapshot")
async def dashboard_snapshot():
    """One-shot system snapshot — addresses, balances, and per-track config.

    Used by the CLI dashboard to fill its panels on startup. Every section is
    independent, so no single failure (e.g. RPC unreachable) blocks the rest.
    """
    audit_agents = get_audit_agents(disabled=settings.disabled_agents)
    drafter = get_drafter()

    coord_addr = _wallet_address_from_private_key(settings.zg_private_key)
    storage_info = await _probe_storage_sidecar()
    galileo_balance_wei = await _fetch_galileo_balance(coord_addr) if coord_addr else None

    return {
        "coordinator": {
            "service": "lethe-coordinator",
            "version": "0.1.0",
        },
        "wallets": {
            "coordinator_galileo": {
                "address": coord_addr,
                "balance_wei": galileo_balance_wei,
                "balance_og": (galileo_balance_wei / 1e18) if galileo_balance_wei is not None else None,
                "rpc_url": settings.zg_rpc_url,
                "chain_id": settings.zg_chain_id,
            },
            "storage_sidecar": storage_info,
        },
        "tracks": {
            "axl": {
                "enabled": transport_axl.is_enabled(),
                "transport": "axl-live" if transport_axl.is_enabled() else "stub (asyncio.gather)",
                "peers": [
                    {"agent": agent.spec.name, "url": url, "peer_id": pid}
                    for (agent, url, pid) in zip(
                        audit_agents,
                        [settings.axl_alpha_url, settings.axl_beta_url, settings.axl_gamma_url],
                        transport_axl.PEER_IDS,
                    )
                    if pid
                ],
                "expected_peer_count": len(transport_axl.PEER_IDS),
            },
            "zerog": {
                "rpc_url": settings.zg_rpc_url,
                "chain_id": settings.zg_chain_id,
                "lethe_registry_address": settings.lethe_registry_address or settings.bill_registry_address or None,
                "pattern_registry_address": settings.pattern_registry_address or None,
                "storage_index_address": settings.storage_index_address or None,
                "storage_sidecar_url": settings.zg_storage_sidecar_url or None,
                "storage_reachable": storage_info.get("reachable"),
                "compute_endpoint": settings.zg_compute_endpoint or None,
                "compute_model": settings.zg_compute_model if settings.zg_compute_endpoint else None,
                "anchor_executor": (
                    "0g-direct"
                    if settings.zg_private_key and (
                        settings.lethe_registry_address or settings.bill_registry_address
                    ) else "stub"
                ),
            },
            "keeperhub": {
                "configured": bool(settings.keeperhub_api_key),
                "transport": "mcp" if settings.keeperhub_use_mcp else "rest",
                "base_url": settings.keeperhub_base_url,
                "mcp_url": settings.keeperhub_mcp_url if settings.keeperhub_use_mcp else None,
                "lethe_registry_sepolia": (
                    settings.lethe_registry_address_sepolia
                    or settings.bill_registry_address_sepolia
                    or None
                ),
                "dispute_filer": (
                    "live"
                    if settings.keeperhub_api_key and settings.dispute_registry_address_sepolia
                    else "stub"
                ),
                "appeal_attestor": (
                    "live"
                    if settings.keeperhub_api_key and settings.appeal_registry_address_sepolia
                    else "stub"
                ),
            },
        },
        "agents": [
            {
                "name": a.spec.name,
                "role": a.spec.role,
                "model": a.spec.model,
                "provider": a.spec.provider,
                "live": a.spec.provider != "stub",
            }
            for a in audit_agents
        ] + ([
            {
                "name": drafter.spec.name,
                "role": drafter.spec.role,
                "model": drafter.spec.model,
                "provider": drafter.spec.provider,
                "live": drafter.spec.provider != "stub",
            }
        ] if drafter else []),
    }


@router.get("/events/global")
async def global_event_stream():
    """SSE stream of every pipeline event across every job.

    Used by tools/dashboard.py. Same `Event` shape the per-job `/api/jobs/<id>/stream`
    endpoint serves, just fan-out across all jobs.
    """
    queue = await bus.subscribe_global(maxsize=256)

    async def event_gen():
        yield {"event": "open", "data": json.dumps({"endpoint": "global"})}
        try:
            while True:
                try:
                    evt: Event = await asyncio.wait_for(queue.get(), timeout=20.0)
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "{}"}
                    continue
                if evt.type == "__end__":
                    continue
                payload = evt.to_sse()
                yield {"event": payload["event"], "data": json.dumps(payload["data"])}
        finally:
            await bus.unsubscribe_global(queue)

    return EventSourceResponse(event_gen())
