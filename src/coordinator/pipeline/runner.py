"""Pipeline orchestrator.

Six stages: parse → redact → broadcast → reason → consensus → anchor.

Privacy invariants:
- bill_bytes are read once for parsing, then immediately released
- only the redacted_payload is passed to agents
- events emitted on the bus carry NO bill content — only structured progress
- on success or error, bill_bytes are zeroed before the function returns
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import List

import agents  # noqa: F401  — import side-effects: registers all agents
from agents import transport_axl
from agents.base import AgentClient, AgentVote
from agents.registry import get_audit_agents, get_drafter
from agents.stub import STUB_BEHAVIOR
from config import settings
from store.memory import Job, store
from store.stats import stats
from pipeline import consensus as consensus_mod
from pipeline import dispute as dispute_mod
from pipeline import parser as parser_mod
from pipeline import redactor as redactor_mod
from pipeline.events import Event, bus
from chain import zerog
from chain import zerog_storage
from chain import keeperhub
from chain import patterns as chain_patterns

log = logging.getLogger("lethe.pipeline")

STAGE_ORDER = ["parse", "redact", "broadcast", "reason", "exchange", "reflect", "consensus", "anchor"]


def _short(job_id: str) -> str:
    return job_id[:8]


async def _emit(job_id: str, type_: str, **data) -> None:
    """Publish to the SSE bus AND log to the uvicorn terminal.

    Privacy: data fields here are structured metadata only (stage names,
    durations, verdicts, agent names, finding counts). Bill content is
    never passed through here.
    """
    log.info("[%s] %-22s %s", _short(job_id), type_, data)
    await bus.publish(Event(type=type_, job_id=job_id, data=data))


async def _stage(job: Job, name: str, coro):
    delay_ms = int(settings.stage_delays_ms.get(name, 0))
    await _emit(job.job_id, "step.started", step=name, simulated_delay_ms=delay_ms)
    started = time.perf_counter()
    try:
        result = await coro
    except Exception as e:
        duration_ms = int((time.perf_counter() - started) * 1000)
        job.stage_timings[name] = duration_ms
        log.warning("[%s] step.failed %-12s %dms err=%s", _short(job.job_id), name, duration_ms, type(e).__name__)
        await _emit(job.job_id, "step.failed", step=name, duration_ms=duration_ms, error=str(e))
        raise
    duration_ms = int((time.perf_counter() - started) * 1000)
    job.stage_timings[name] = duration_ms
    await stats.record_stage(name, duration_ms)
    await _emit(job.job_id, "step.completed", step=name, duration_ms=duration_ms)
    return result


async def run(job_id: str) -> None:
    job = await store.get(job_id)
    if job is None:
        return
    if job.bill_bytes is None:
        return

    started_total = time.perf_counter()
    job.status = "running"
    await _emit(job_id, "job.started", filename=job.filename, sha256=job.sha256)

    try:
        # 1. Parse
        parsed = await _stage(
            job,
            "parse",
            parser_mod.parse(job.filename, job.bill_bytes, settings.stage_delays_ms["parse"]),
        )
        # bill_bytes will not be touched again — release them.
        await store.clear_bill_bytes(job_id)

        # 2. Redact
        redacted = await _stage(
            job,
            "redact",
            redactor_mod.redact(parsed, settings.stage_delays_ms["redact"]),
        )
        # discard the parsed (still un-redacted) snapshot
        parsed = None  # noqa: F841

        job.redacted_payload = redacted

        # 3. Broadcast (handshake step — measurable but logically just a delay)
        audit_agents: List[AgentClient] = get_audit_agents(disabled=settings.disabled_agents)
        peer_names = [a.spec.name for a in audit_agents]

        async def _broadcast():
            await asyncio.sleep(settings.stage_delays_ms["broadcast"] / 1000)
            await _emit(job_id, "agent.handshake", peers=peer_names)
            return {"peers": len(peer_names)}

        await _stage(job, "broadcast", _broadcast())

        # 4. Reason — agents in parallel, each only sees redacted payload.
        # Fetch prior pattern stats once for all three agents — cached.
        # Surface the read on the SSE bus so the dashboard can show the
        # agents literally pulling from the on-chain PatternRegistry.
        try:
            prior_stats = await chain_patterns.get_pattern_stats()
            prior_block = chain_patterns.format_for_prompt(prior_stats, top_n=30)
        except Exception as e:
            log.warning("prior pattern fetch failed: %s — proceeding without", e)
            prior_stats = {}
            prior_block = ""
        if prior_block:
            top = sorted(prior_stats.values(), key=lambda s: s["n_observations"], reverse=True)[:3]
            top_codes = [
                {
                    "code": s["code"],
                    "n_observations": s["n_observations"],
                    "dispute_rate": s["dispute_rate"],
                    "clarify_rate": s["clarify_rate"],
                    "mean_amount_usd": s["mean_amount_usd"],
                }
                for s in top
            ]
            registry_short = (
                settings.pattern_registry_address[:10] + "…"
                if settings.pattern_registry_address
                else ""
            )
            await _emit(
                job_id, "patterns.prior_loaded",
                code_count=len(prior_stats),
                total_observations=sum(s["n_observations"] for s in prior_stats.values()),
                top_codes=top_codes,
                registry_address=settings.pattern_registry_address,
                registry_short=registry_short,
                network="0g-galileo-testnet",
            )

        async def _run_agent(agent: AgentClient) -> AgentVote:
            await _emit(
                job_id, "agent.started",
                agent=agent.spec.name, model=agent.spec.model, provider=agent.spec.provider,
            )

            async def on_message(line: str) -> None:
                # Real reasoning tokens, streamed live from the LLM provider.
                await _emit(
                    job_id, "agent.message",
                    agent=agent.spec.name, line=line,
                )

            # If the agent doesn't accept on_message (e.g. stub fallback), call without it.
            try:
                vote = await agent.analyze(redacted, on_message=on_message, prior_patterns=prior_block or None)
            except TypeError:
                # Stub agent or older signature — fall back to canned stream + non-streaming call.
                template = STUB_BEHAVIOR.get(agent.spec.name, {}).get("stream", [])
                async def _emit_canned():
                    try:
                        for line in template:
                            await _emit(job_id, "agent.message",
                                        agent=agent.spec.name, line=line)
                            await asyncio.sleep(2.4)
                    except asyncio.CancelledError:
                        return
                streamer = asyncio.create_task(_emit_canned())
                try:
                    vote = await agent.analyze(redacted)
                finally:
                    streamer.cancel()
                    try:
                        await streamer
                    except asyncio.CancelledError:
                        pass

            await _emit(
                job_id,
                "agent.completed",
                agent=agent.spec.name,
                model=agent.spec.model,
                provider=agent.spec.provider,
                verdict=vote.verdict,
                confidence=vote.confidence,
                finding_count=len(vote.findings),
                duration_ms=vote.duration_ms,
            )
            return vote

        async def _reason() -> List[AgentVote]:
            return await asyncio.gather(*(_run_agent(a) for a in audit_agents))

        votes: List[AgentVote] = await _stage(job, "reason", _reason())

        # 4.5. P2P findings exchange — each agent broadcasts its OWN findings
        # via its sidecar. Then every sidecar's inbox is drained so peers
        # actually receive what was sent. Without this step the AXL traffic
        # would be symbolic; with it, the mesh literally carries each agent's
        # analysis between peers.
        async def _exchange() -> None:
            if not transport_axl.is_enabled():
                return

            vote_by_name = {v.agent: v for v in votes}

            async def _broadcast_findings(v: AgentVote) -> None:
                summary = {
                    "phase": "findings",
                    "job_id": job_id,
                    "agent": v.agent,
                    "verdict": v.verdict,
                    "confidence": v.confidence,
                    # Trim findings to code/action/severity so the broadcast
                    # is small and contains zero PHI by construction.
                    "findings": [
                        {
                            "code": f.get("code"),
                            "action": f.get("action"),
                            "severity": f.get("severity"),
                            "amount_usd": f.get("amount_usd"),
                        }
                        for f in v.findings
                    ],
                }
                manifest = await transport_axl.broadcast_payload(v.agent, summary)
                await _emit(
                    job_id, "axl.findings_sent",
                    agent=v.agent,
                    delivered_to=manifest.get("delivered_to", []),
                    from_peer_id=manifest.get("from_peer_id"),
                    payload_bytes=manifest.get("payload_bytes", 0),
                    finding_count=len(summary["findings"]),
                    errors=manifest.get("errors", []),
                )

            await asyncio.gather(*(_broadcast_findings(v) for v in votes))

            # Give the mesh a brief moment to deliver before draining inboxes.
            await asyncio.sleep(0.5)

            async def _drain(name: str) -> None:
                inbox = await transport_axl.poll_inbox(name)
                # Filter to messages that are findings broadcasts for this job.
                received = []
                for m in inbox:
                    j = m.get("json") or {}
                    if j.get("phase") == "findings" and j.get("job_id") == job_id:
                        received.append({
                            "from_agent": m.get("from_agent"),
                            "from_peer_id": m.get("from_peer_id"),
                            "verdict": j.get("verdict"),
                            "confidence": j.get("confidence"),
                            "finding_count": len(j.get("findings", [])),
                            "findings": j.get("findings", []),
                        })
                # Attach to this agent's vote so consensus + UI can see it.
                v = vote_by_name.get(name)
                if v is not None:
                    v.peer_received = received
                for r in received:
                    await _emit(
                        job_id, "axl.findings_received",
                        agent=name,
                        from_agent=r["from_agent"],
                        from_peer_id=r["from_peer_id"],
                        finding_count=r["finding_count"],
                        verdict=r["verdict"],
                    )

            await asyncio.gather(*(_drain(a.spec.name) for a in audit_agents))

        await _stage(job, "exchange", _exchange())

        # 4.7. Reflection round — each agent sees its peers' findings (delivered
        # via AXL during exchange) and gets ONE additional LLM call to revise.
        # The original round-1 vote is preserved on the SSE bus via
        # `agent.revised`; the consensus tally below runs on the round-2 votes.
        async def _reflect_all() -> None:
            if not transport_axl.is_enabled():
                return  # No peer findings to reflect on without AXL.

            vote_by_name = {v.agent: v for v in votes}

            async def _reflect_one(agent: AgentClient) -> AgentVote:
                original = vote_by_name.get(agent.spec.name)
                if original is None:
                    return None  # type: ignore[return-value]

                # If reflect isn't supported (stub or older client), keep original.
                if not hasattr(agent, "reflect"):
                    return original

                # Nothing to reflect on if AXL didn't deliver any peer findings —
                # don't burn an LLM call for no-op revision.
                if not original.peer_received:
                    return original

                async def on_message(line: str) -> None:
                    await _emit(
                        job_id, "agent.message",
                        agent=agent.spec.name, line=line, phase="reflect",
                    )

                await _emit(
                    job_id, "agent.reflect_started",
                    agent=agent.spec.name,
                    peer_finding_total=sum(p.get("finding_count", 0) for p in original.peer_received),
                )

                try:
                    revised = await agent.reflect(
                        redacted_payload=redacted,
                        original_vote=original,
                        peer_received=original.peer_received,
                        on_message=on_message,
                    )
                except Exception as e:
                    log.warning("[%s] reflect failed for %s: %s — keeping round-1 vote",
                                _short(job_id), agent.spec.name, e)
                    return original

                await _emit(
                    job_id, "agent.revised",
                    agent=agent.spec.name,
                    round1_verdict=original.verdict,
                    round1_confidence=original.confidence,
                    round1_finding_count=len(original.findings),
                    round2_verdict=revised.verdict,
                    round2_confidence=revised.confidence,
                    round2_finding_count=len(revised.findings),
                    verdict_changed=(revised.verdict != original.verdict),
                    duration_ms=revised.duration_ms,
                )
                return revised

            revised_list = await asyncio.gather(*(_reflect_one(a) for a in audit_agents))
            # Replace the votes list in-place so consensus uses round-2 outcomes.
            votes.clear()
            for v in revised_list:
                if v is not None:
                    votes.append(v)

        await _stage(job, "reflect", _reflect_all())

        # 5. Consensus
        async def _consensus():
            await asyncio.sleep(settings.stage_delays_ms["consensus"] / 1000)
            return consensus_mod.tally(votes)

        verdict = await _stage(job, "consensus", _consensus())
        await _emit(
            job_id,
            "consensus.reached",
            verdict=verdict["verdict"],
            agree_count=verdict["agree_count"],
            total_agents=verdict["total_agents"],
            mean_confidence=verdict["mean_confidence"],
            disputed_total_usd=verdict["disputed_total_usd"],
            finding_count=len(verdict["findings"]),
        )

        # 6. Anchor
        # Dual-anchor: 0G Galileo (canonical) + KeeperHub→Sepolia (mirror).
        # Fire both in parallel — KH typically takes 15-30s, 0G ~5-8s.
        async def _dual_anchor():
            zg_task = asyncio.create_task(zerog.anchor(
                job.sha256,
                settings.stage_delays_ms["anchor"],
                verdict=str(verdict.get("verdict", "dispute")),
                agree_count=int(verdict.get("agree_count", 3)),
                total_agents=int(verdict.get("total_agents", 3)),
            ))
            kh_task = asyncio.create_task(keeperhub.anchor_via_keeperhub(
                job.sha256,
                verdict=str(verdict.get("verdict", "dispute")),
                agree_count=int(verdict.get("agree_count", 3)),
                total_agents=int(verdict.get("total_agents", 3)),
            ))
            zg_proof, kh_proof = await asyncio.gather(zg_task, kh_task)
            zg_proof["mirror"] = kh_proof
            return zg_proof

        proof = await _stage(job, "anchor", _dual_anchor())
        await _emit(
            job_id,
            "anchor.confirmed",
            anchor_tx=proof["anchor_tx"],
            network=proof["network"],
            executor=proof["executor"],
        )
        if proof.get("mirror", {}).get("live"):
            await _emit(
                job_id,
                "mirror.confirmed",
                tx_hash=proof["mirror"].get("tx_hash"),
                network=proof["mirror"].get("network"),
                executor=proof["mirror"].get("executor"),
            )

        # 6.5 Index anonymized patterns on PatternRegistry (cheap event log on 0G).
        async def _patterns():
            return await zerog_storage.index_patterns(verdict, job.sha256)

        patterns = await _stage(job, "patterns", _patterns())
        await _emit(
            job_id,
            "patterns.indexed",
            indexed=int(patterns.get("patterns_indexed", 0)),
            tx=patterns.get("tx"),
            executor=patterns.get("executor", "stub"),
        )
        proof["patterns"] = patterns

        # 7. Draft dispute letter (own stage so timing is captured)
        async def _draft():
            return await dispute_mod.draft(verdict, job.sha256)

        drafted = await _stage(job, "draft", _draft())
        await _emit(
            job_id,
            "draft.completed",
            drafted_by=drafted.get("drafted_by", "stub"),
            citation_count=len(drafted.get("citations", [])),
            duration_ms=drafted.get("duration_ms", 0),
        )
        dispute = drafted

        total_ms = int((time.perf_counter() - started_total) * 1000)
        await stats.record_job(total_ms)

        result = {
            "filename": job.filename,
            "sha256": job.sha256,
            "consensus": verdict,
            "dispute": dispute,
            "proof": proof,
            "stage_timings_ms": job.stage_timings,
            "total_runtime_ms": total_ms,
        }
        job.result = result
        job.status = "done"
        # extend lifetime so the (no-PHI) result is retrievable post-pipeline.
        # bill bytes were zeroed at the parse stage, so this only keeps the
        # public_dict-shaped result in memory.
        job.expires_at = time.time() + settings.result_ttl_seconds

        await _emit(job_id, "done", total_runtime_ms=total_ms)

    except Exception as e:
        job.status = "error"
        job.error = type(e).__name__
        # keep error visible briefly so callers can fetch it
        job.expires_at = time.time() + settings.result_ttl_seconds
        await _emit(job_id, "error", error=type(e).__name__)
    finally:
        # belt-and-suspenders: ensure bill bytes are gone no matter what
        await store.clear_bill_bytes(job_id)
        await bus.close(job_id)