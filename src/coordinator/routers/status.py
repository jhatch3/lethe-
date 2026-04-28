"""Coordinator status: liveness, registered agents, rolling timing averages."""

from __future__ import annotations

from fastapi import APIRouter

import agents  # noqa: F401  — ensures registry is populated
from agents import transport_axl
from agents.registry import get_audit_agents, get_drafter
from chain import patterns as chain_patterns
from config import settings
from store.stats import stats

router = APIRouter(prefix="/api", tags=["status"])


def _agent_card(agent) -> dict:
    s = agent.spec
    return {
        "name": s.name,
        "role": s.role,
        "model": s.model,
        "provider": s.provider,
        "color": s.color,
        "skills": s.skills,
        "context_clue_count": len(s.context_clues),
        "live": s.provider != "stub",
    }


@router.get("/status")
async def status():
    timing = await stats.snapshot()
    suggested_ttl = await stats.suggested_ttl_seconds(
        default_seconds=settings.job_ttl_seconds,
        buffer_seconds=settings.job_ttl_buffer_seconds,
    )
    audit_agents = get_audit_agents(disabled=settings.disabled_agents)
    drafter = get_drafter()
    return {
        "coordinator": {
            "service": "lethe-coordinator",
            "version": "0.1.0",
            "status": "online",
        },
        "agents": {
            "audit": [_agent_card(a) for a in audit_agents],
            "drafter": _agent_card(drafter) if drafter else None,
        },
        "axl": {
            "peers_connected": len(audit_agents),
            "transport": "axl-live" if transport_axl.is_enabled() else "stub (asyncio.gather)",
            "expected_peer_ids": transport_axl.PEER_IDS,
            "enabled": transport_axl.is_enabled(),
            "see_also": "/api/axl",
        },
        "chain": {
            "network": "0g-galileo-testnet",
            "primary_anchor": (
                "0g-direct"
                if settings.zg_private_key and settings.bill_registry_address
                else "stub"
            ),
            "mirror_anchor": (
                "keeperhub-sepolia"
                if settings.keeperhub_api_key and settings.bill_registry_address_sepolia
                else "stub"
            ),
            "pattern_index": (
                "0g-direct"
                if settings.zg_private_key and settings.pattern_registry_address
                else "stub"
            ),
            "pattern_storage": (
                "0g-storage-sidecar"
                if settings.zg_storage_sidecar_url
                else "stub"
            ),
            "zg_storage_sidecar_url": settings.zg_storage_sidecar_url or None,
            "storage_index": (
                "0g-direct"
                if settings.zg_private_key and settings.storage_index_address
                else "stub"
            ),
            "storage_index_address": settings.storage_index_address or None,
        },
        "timing": timing,
        "ttl": {
            "default_seconds": settings.job_ttl_seconds,
            "buffer_seconds": settings.job_ttl_buffer_seconds,
            "suggested_seconds": suggested_ttl,
        },
        "config": {
            "disabled_agents": settings.disabled_agents,
            "openai_configured": bool(settings.openai_api_key),
            "anthropic_configured": bool(settings.anthropic_api_key),
            "google_configured": bool(settings.google_api_key),
            "zg_compute_configured": bool(
                settings.zg_compute_endpoint and settings.zg_compute_token
            ),
            "zg_compute_model": settings.zg_compute_model if (
                settings.zg_compute_endpoint and settings.zg_compute_token
            ) else None,
            "zg_compute_transport": (
                "sidecar"
                if settings.zg_compute_endpoint and settings.zg_compute_sidecar
                else "direct"
                if settings.zg_compute_endpoint and settings.zg_compute_token
                else None
            ),
            "zg_compute_provider": settings.zg_compute_provider_address or None,
            "zg_private_key_len": len(settings.zg_private_key),
            "zg_chain_id": settings.zg_chain_id,
            "zg_rpc_url": settings.zg_rpc_url,
            "bill_registry_address": settings.bill_registry_address,
            "pattern_registry_address": settings.pattern_registry_address,
            "bill_registry_address_sepolia": settings.bill_registry_address_sepolia,
            "keeperhub_configured": bool(settings.keeperhub_api_key),
            "keeperhub_transport": "mcp" if settings.keeperhub_use_mcp else "rest",
            "keeperhub_mcp_url": settings.keeperhub_mcp_url if settings.keeperhub_use_mcp else None,
            "keeperhub_dispute_filer": (
                "live"
                if settings.keeperhub_api_key and settings.dispute_registry_address_sepolia
                else "stub"
            ),
            "dispute_registry_address_sepolia": settings.dispute_registry_address_sepolia or None,
            "dispute_function_name": settings.dispute_function_name,
            "keeperhub_appeal_attestor": (
                "live"
                if settings.keeperhub_api_key and settings.appeal_registry_address_sepolia
                else "stub"
            ),
            "appeal_registry_address_sepolia": settings.appeal_registry_address_sepolia or None,
            "email_provider": settings.email_provider,
            "email_configured": bool(
                (settings.email_provider == "resend" and settings.email_resend_api_key)
                or (settings.email_provider == "smtp" and settings.email_smtp_host and settings.email_smtp_user)
            ),
        },
    }


@router.get("/axl")
async def axl_topology():
    """Live AXL mesh topology — read each sidecar's /topology endpoint and
    return the three real ed25519 peer IDs. Used by judges/demo to confirm
    P2P transport is real, not asyncio.gather."""
    return await transport_axl.gather_topology()


@router.get("/patterns")
async def list_patterns(refresh: bool = False):
    """Aggregated pattern stats from on-chain PatternRegistry events.

    Public, read-only — no auth needed. Surfaces what the agents see as priors.
    """
    stats_dict = await chain_patterns.get_pattern_stats(force=refresh)
    rows = sorted(
        stats_dict.values(),
        key=lambda s: s["n_observations"],
        reverse=True,
    )
    total_obs = sum(s["n_observations"] for s in stats_dict.values())
    return {
        "registry_address": settings.pattern_registry_address,
        "network": "0g-galileo-testnet",
        "chain_id": settings.zg_chain_id,
        "code_count": len(stats_dict),
        "total_observations": total_obs,
        "patterns": rows,
    }
