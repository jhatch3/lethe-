"""Lethe CLI dashboard.

Live ASCII TUI that subscribes to the coordinator's /api/events/global SSE
stream and renders per-track status (Gensyn AXL · 0G · KeeperHub) with all
addresses and the current job.

Usage:
    python tools/dashboard.py [coordinator_url]
        # default: http://localhost:8000

Refreshes the snapshot (balance, sidecar reachability) every 15s; pipeline
events are streamed in real time. Press Ctrl+C to exit.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

import httpx
from rich.align import Align
from rich.console import Console, Group
from rich.json import JSON
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text


DEFAULT_URL = "http://localhost:8000"
EVENT_BUFFER = 24
PAYLOAD_BUFFER = 6      # how many recent events to render with full payload
SNAPSHOT_REFRESH_S = 15.0


# ─────────────────────────────────────────────────────────────────────────────
# State
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class TrackHealth:
    last_event: Optional[str] = None
    last_ts: float = 0.0
    last_tx: Optional[str] = None
    last_executor: Optional[str] = None
    hits: int = 0


@dataclass
class State:
    coordinator_url: str
    snapshot: Dict[str, Any] = field(default_factory=dict)
    snapshot_ts: float = 0.0
    snapshot_error: Optional[str] = None
    sse_connected: bool = False
    sse_error: Optional[str] = None
    events: Deque[Dict[str, Any]] = field(default_factory=lambda: deque(maxlen=EVENT_BUFFER))
    current_job_id: Optional[str] = None
    current_step: Optional[str] = None
    last_verdict: Optional[str] = None
    last_finding_count: int = 0
    last_disputed_usd: float = 0.0
    audits_seen: int = 0
    axl: TrackHealth = field(default_factory=TrackHealth)
    zerog: TrackHealth = field(default_factory=TrackHealth)
    keeperhub: TrackHealth = field(default_factory=TrackHealth)
    # Optional file handle — when set, every event is appended as one JSON line
    # (JSONL). Lets you tail a long-running session in another terminal:
    #     tail -f dashboard-events.jsonl | jq .
    log_fp: Optional[Any] = None


# ─────────────────────────────────────────────────────────────────────────────
# Network
# ─────────────────────────────────────────────────────────────────────────────


async def fetch_snapshot(state: State, client: httpx.AsyncClient) -> None:
    try:
        r = await client.get(f"{state.coordinator_url}/api/dashboard/snapshot", timeout=5.0)
        r.raise_for_status()
        state.snapshot = r.json()
        state.snapshot_ts = time.time()
        state.snapshot_error = None
    except Exception as e:
        state.snapshot_error = f"{type(e).__name__}: {e}"


def classify_track(event_type: str) -> Optional[str]:
    """Map a pipeline event to which sponsor track it belongs to."""
    if event_type.startswith("axl."):
        return "axl"
    if event_type in ("anchor.confirmed", "patterns.indexed", "patterns.prior_loaded"):
        return "zerog"
    if event_type in ("mirror.confirmed", "dispute.filed", "appeal.attested"):
        return "keeperhub"
    return None


def consume_event(state: State, evt_type: str, data: Dict[str, Any]) -> None:
    now = time.time()
    state.events.appendleft({"type": evt_type, "data": data, "ts": now})

    if state.log_fp is not None:
        try:
            state.log_fp.write(json.dumps(
                {"ts": now, "iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now)),
                 "type": evt_type, "data": data},
                default=str,
            ) + "\n")
            state.log_fp.flush()
        except Exception:
            pass  # never let log I/O break the TUI

    job_id = data.get("job_id")
    if job_id:
        state.current_job_id = job_id

    if evt_type == "step.started":
        state.current_step = data.get("step")
    elif evt_type == "step.completed":
        if state.current_step == data.get("step"):
            state.current_step = None
    elif evt_type == "consensus.reached":
        state.last_verdict = data.get("verdict")
        state.last_finding_count = int(data.get("finding_count") or 0)
        state.last_disputed_usd = float(data.get("disputed_total_usd") or 0)
    elif evt_type == "done":
        state.audits_seen += 1
        state.current_step = None
    elif evt_type == "job.started":
        state.current_step = "starting"

    track = classify_track(evt_type)
    if track:
        h: TrackHealth = getattr(state, track)
        h.last_event = evt_type
        h.last_ts = time.time()
        h.hits += 1
        tx = data.get("tx_hash") or data.get("anchor_tx")
        if tx:
            h.last_tx = tx
        if data.get("executor"):
            h.last_executor = data["executor"]


async def stream_events(state: State, client: httpx.AsyncClient) -> None:
    """Subscribe to /api/events/global; reconnect on drop."""
    url = f"{state.coordinator_url}/api/events/global"
    while True:
        try:
            async with client.stream("GET", url, timeout=None,
                                     headers={"Accept": "text/event-stream"}) as r:
                r.raise_for_status()
                state.sse_connected = True
                state.sse_error = None
                event_name: Optional[str] = None
                async for raw in r.aiter_lines():
                    if raw == "":
                        event_name = None
                        continue
                    if raw.startswith(":"):
                        continue
                    if raw.startswith("event:"):
                        event_name = raw[6:].strip()
                        continue
                    if raw.startswith("data:"):
                        try:
                            data = json.loads(raw[5:].strip() or "{}")
                        except json.JSONDecodeError:
                            data = {}
                        if event_name and event_name not in ("ping", "open"):
                            consume_event(state, event_name, data)
        except Exception as e:
            state.sse_connected = False
            state.sse_error = f"{type(e).__name__}: {e}"
            await asyncio.sleep(2.0)


async def refresh_loop(state: State, client: httpx.AsyncClient) -> None:
    while True:
        await fetch_snapshot(state, client)
        await asyncio.sleep(SNAPSHOT_REFRESH_S)


# ─────────────────────────────────────────────────────────────────────────────
# Rendering
# ─────────────────────────────────────────────────────────────────────────────


def short(addr: Optional[str], head: int = 10, tail: int = 6) -> str:
    if not addr:
        return "—"
    if len(addr) <= head + tail + 2:
        return addr
    return f"{addr[:head]}…{addr[-tail:]}"


def fmt_balance(balance_og: Optional[float]) -> str:
    if balance_og is None:
        return "—"
    if balance_og < 0.0001:
        return f"{balance_og*1e6:.2f} μOG"
    if balance_og < 1:
        return f"{balance_og*1000:.3f} mOG"
    return f"{balance_og:.4f} OG"


def fmt_age(ts: float) -> str:
    if not ts:
        return "—"
    secs = int(time.time() - ts)
    if secs < 60:
        return f"{secs}s ago"
    return f"{secs // 60}m{secs % 60}s ago"


def render_header(state: State) -> Panel:
    snap = state.snapshot
    coord = (snap.get("coordinator") or {}).get("service", "—")
    wallet = ((snap.get("wallets") or {}).get("coordinator_galileo") or {})
    addr = wallet.get("address")
    bal_og = wallet.get("balance_og")

    sse_dot = "[green]●[/green]" if state.sse_connected else "[red]●[/red]"
    sse_label = "connected" if state.sse_connected else "disconnected"
    sse_err = ""
    if state.sse_error and not state.sse_connected:
        sse_err = f" [dim]· {state.sse_error[:60]}[/dim]"

    snap_age = fmt_age(state.snapshot_ts) if state.snapshot_ts else "—"
    snap_err = ""
    if state.snapshot_error:
        snap_err = f" [red]· {state.snapshot_error[:50]}[/red]"

    bal_color = "yellow" if (bal_og is not None and bal_og < 0.005) else "green"
    markup = (
        f"[bold cyan]Lethe coordinator[/bold cyan]  ·  {coord}\n"
        f"[dim]wallet[/dim]  {short(addr, 10, 8)}   "
        f"[dim]bal[/dim]  [{bal_color}]{fmt_balance(bal_og)}[/{bal_color}]\n"
        f"SSE: {sse_dot} {sse_label}{sse_err}   "
        f"[dim]snapshot:[/dim] {snap_age}{snap_err}"
    )
    return Panel(Text.from_markup(markup), title="lethe", border_style="cyan", padding=(0, 1))


def render_axl(state: State) -> Panel:
    snap = state.snapshot
    track = (snap.get("tracks") or {}).get("axl") or {}
    h = state.axl
    enabled = track.get("enabled", False)

    table = Table.grid(padding=(0, 1))
    table.add_column(style="dim", justify="right", no_wrap=True)
    table.add_column()
    status = "[green]LIVE[/green]" if enabled else "[red]STUB[/red] (asyncio.gather)"
    table.add_row("transport", status)
    for peer in track.get("peers") or []:
        table.add_row(
            peer.get("agent", "?"),
            f"{peer.get('url','—')}  [dim]{short(peer.get('peer_id'), 10, 6)}[/dim]",
        )
    if not track.get("peers"):
        table.add_row("peers", "[dim]—[/dim]")

    table.add_row("hits", f"{h.hits}  [dim]· {h.last_event or '—'}  {fmt_age(h.last_ts)}[/dim]")
    return Panel(table, title="🕸  Gensyn AXL", border_style="magenta", padding=(0, 1))


def render_zerog(state: State) -> Panel:
    snap = state.snapshot
    track = (snap.get("tracks") or {}).get("zerog") or {}
    h = state.zerog
    storage_ok = track.get("storage_reachable")

    table = Table.grid(padding=(0, 1))
    table.add_column(style="dim", justify="right", no_wrap=True)
    table.add_column()
    table.add_row("rpc", track.get("rpc_url", "—"))
    table.add_row("chain", str(track.get("chain_id", "—")))
    table.add_row("registry", short(track.get("lethe_registry_address"), 10, 6))
    table.add_row("storage",
                  ("[green]reachable[/green]" if storage_ok
                   else "[red]unreachable[/red]" if storage_ok is False
                   else "[dim]not configured[/dim]"))
    if track.get("compute_endpoint"):
        table.add_row("compute", f"{track.get('compute_model','?')}  [dim]{track['compute_endpoint']}[/dim]")
    table.add_row("anchor", str(track.get("anchor_executor", "—")))
    last_tx = h.last_tx or "—"
    table.add_row("last tx", f"{short(last_tx, 10, 6)}  [dim]{h.last_executor or ''}[/dim]")
    table.add_row("hits", f"{h.hits}  [dim]· {h.last_event or '—'}  {fmt_age(h.last_ts)}[/dim]")
    return Panel(table, title="⛓  0G", border_style="blue", padding=(0, 1))


def render_keeperhub(state: State) -> Panel:
    snap = state.snapshot
    track = (snap.get("tracks") or {}).get("keeperhub") or {}
    h = state.keeperhub
    configured = track.get("configured", False)

    table = Table.grid(padding=(0, 1))
    table.add_column(style="dim", justify="right", no_wrap=True)
    table.add_column()
    table.add_row(
        "transport",
        ("[green]" + str(track.get("transport", "—")) + "[/green]")
        if configured else "[red]not configured[/red]",
    )
    table.add_row("base", track.get("base_url", "—"))
    if track.get("mcp_url"):
        table.add_row("mcp", track["mcp_url"])
    table.add_row("registry", short(track.get("lethe_registry_sepolia"), 10, 6))
    table.add_row("WF #1", "anchor mirror")
    table.add_row("WF #2", f"dispute · {track.get('dispute_filer','—')}")
    table.add_row("WF #3", f"appeal-sent · {track.get('appeal_attestor','—')}")
    last_tx = h.last_tx or "—"
    table.add_row("last tx", short(last_tx, 10, 6))
    table.add_row("hits", f"{h.hits}  [dim]· {h.last_event or '—'}  {fmt_age(h.last_ts)}[/dim]")
    return Panel(table, title="💚 KeeperHub", border_style="green", padding=(0, 1))


def render_current(state: State) -> Panel:
    if state.current_job_id:
        body = Text.assemble(
            ("job  ", "dim"), state.current_job_id[:8],
            ("   step  ", "dim"), state.current_step or "—",
            ("\n", ""),
            ("verdict  ", "dim"), state.last_verdict or "—",
            ("   findings  ", "dim"), str(state.last_finding_count),
            ("   disputed  ", "dim"), f"${state.last_disputed_usd:,.2f}",
            ("\n", ""),
            ("audits seen  ", "dim"), str(state.audits_seen),
        )
    else:
        body = Text.assemble(("idle  ", "dim"), "no active job\n",
                             ("audits seen  ", "dim"), str(state.audits_seen))
    return Panel(body, title="current", border_style="white", padding=(0, 1))


VERDICT_STYLE = {"dispute": "red", "approve": "green", "clarify": "yellow"}


def render_events(state: State) -> Panel:
    table = Table.grid(padding=(0, 1))
    table.add_column(style="dim", no_wrap=True)
    table.add_column(no_wrap=True)
    table.add_column()
    if not state.events:
        table.add_row("", "[dim]waiting for events…[/dim]", "")
    for evt in state.events:
        ts = time.strftime("%H:%M:%S", time.localtime(evt["ts"]))
        et = evt["type"]
        d = evt["data"]
        track = classify_track(et)
        track_tag = {
            "axl": "[magenta]AXL[/magenta]",
            "zerog": "[blue]0G[/blue]",
            "keeperhub": "[green]KH[/green]",
        }.get(track or "", "[dim]••[/dim]")

        # Compose a single-line summary per event type.
        summary = et
        if et == "step.started":
            summary = f"step.started  {d.get('step','?')}"
        elif et == "step.completed":
            summary = f"step.completed  {d.get('step','?')}  {d.get('duration_ms','?')}ms"
        elif et == "agent.completed":
            summary = (f"agent.completed  {d.get('agent','?')}  "
                       f"verdict={d.get('verdict','?')}  conf={d.get('confidence','?')}  "
                       f"findings={d.get('finding_count','?')}")
        elif et == "agent.revised":
            summary = (f"agent.revised  {d.get('agent','?')}  "
                       f"{d.get('round1_verdict','?')}→{d.get('round2_verdict','?')}  "
                       f"changed={d.get('verdict_changed','?')}")
        elif et == "axl.findings_sent":
            summary = (f"axl.send       {d.get('agent','?')} → {','.join(d.get('delivered_to') or [])}  "
                       f"{d.get('payload_bytes','?')}b")
        elif et == "axl.findings_received":
            summary = (f"axl.recv       {d.get('agent','?')} ← peer  "
                       f"verdict={d.get('verdict','?')}  findings={d.get('finding_count','?')}")
        elif et == "anchor.confirmed":
            summary = (f"anchor          tx={short(d.get('anchor_tx'), 10, 6)}  "
                       f"executor={d.get('executor','?')}")
        elif et == "mirror.confirmed":
            summary = f"mirror          tx={short(d.get('tx_hash'), 10, 6)}"
        elif et == "dispute.filed":
            summary = f"dispute.filed   tx={short(d.get('tx_hash'), 10, 6)}"
        elif et == "patterns.indexed":
            summary = f"patterns        tx={short(d.get('tx'), 10, 6)}  executor={d.get('executor','?')}"
        elif et == "consensus.reached":
            v = d.get("verdict", "?")
            summary = (f"consensus       {v} · {d.get('agree_count','?')}/{d.get('total_agents','?')}  "
                       f"$${d.get('disputed_total_usd', 0):,.2f}")
            style = VERDICT_STYLE.get(v, "white")
            summary = f"[{style}]{summary}[/{style}]"
        elif et == "done":
            summary = f"done            runtime={d.get('total_runtime_ms','?')}ms"
        elif et == "job.started":
            summary = f"job.started     {d.get('filename','?')}  sha={d.get('sha256','')[:10]}…"

        table.add_row(ts, track_tag, summary)
    return Panel(table, title="event log", border_style="white", padding=(0, 1))


def render_payloads(state: State) -> Panel:
    """Last PAYLOAD_BUFFER events, each rendered with its full JSON payload.

    Complements the one-line event log above — when a judge wants to see the
    actual fields (peer IDs, tx hashes, byte counts, voter masks) without
    cracking open `eth_getLogs` or coordinator stdout, this is where to look.
    """
    if not state.events:
        return Panel(Text("waiting for events…", style="dim"),
                     title="payloads (last events · full)",
                     border_style="white", padding=(0, 1))

    blocks: List[Any] = []
    for evt in list(state.events)[:PAYLOAD_BUFFER]:
        ts = time.strftime("%H:%M:%S", time.localtime(evt["ts"]))
        et = evt["type"]
        track = classify_track(et)
        track_tag = {
            "axl": "[magenta]AXL[/magenta]",
            "zerog": "[blue]0G[/blue]",
            "keeperhub": "[green]KH[/green]",
        }.get(track or "", "[dim]••[/dim]")
        header = Text.from_markup(
            f"[dim]{ts}[/dim]  {track_tag}  [bold]{et}[/bold]"
        )
        try:
            payload = JSON(json.dumps(evt["data"], default=str), indent=2)
        except Exception:
            payload = Text(str(evt["data"]), style="dim red")
        blocks.append(header)
        blocks.append(payload)
        blocks.append(Rule(style="grey15"))

    # Drop the trailing rule so the last block doesn't have a divider under it.
    if blocks and isinstance(blocks[-1], Rule):
        blocks.pop()

    return Panel(Group(*blocks),
                 title=f"payloads (last {min(PAYLOAD_BUFFER, len(state.events))} · full JSON)",
                 border_style="white", padding=(0, 1))


def build_layout(state: State) -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=5),
        Layout(name="tracks", size=14),
        Layout(name="middle", size=14),
        Layout(name="payloads", ratio=1),
    )
    layout["header"].update(render_header(state))
    layout["tracks"].split_row(
        Layout(render_axl(state), name="axl"),
        Layout(render_zerog(state), name="zerog"),
        Layout(render_keeperhub(state), name="kh"),
    )
    layout["middle"].split_row(
        Layout(render_current(state), name="current", size=40),
        Layout(render_events(state), name="events", ratio=1),
    )
    layout["payloads"].update(render_payloads(state))
    return layout


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


async def main_async(coord_url: str, log_path: Optional[str]) -> None:
    state = State(coordinator_url=coord_url)
    console = Console()

    if log_path:
        # Append-mode so re-runs accumulate; flush on every event so a tail/jq
        # on a separate terminal sees lines immediately.
        state.log_fp = open(log_path, "a", encoding="utf-8")
        console.print(f"[dim]logging events to[/dim] [cyan]{log_path}[/cyan] "
                      f"[dim](JSONL · one event per line)[/dim]")

    async with httpx.AsyncClient() as client:
        await fetch_snapshot(state, client)

        sse_task = asyncio.create_task(stream_events(state, client))
        refresh_task = asyncio.create_task(refresh_loop(state, client))

        try:
            with Live(build_layout(state), console=console, refresh_per_second=4,
                      screen=False) as live:
                while True:
                    live.update(build_layout(state))
                    await asyncio.sleep(0.25)
        finally:
            sse_task.cancel()
            refresh_task.cancel()
            if state.log_fp is not None:
                state.log_fp.close()


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Lethe CLI dashboard.")
    p.add_argument("url", nargs="?", default=DEFAULT_URL,
                   help="coordinator URL (default: %(default)s)")
    p.add_argument("--log", action="store_true",
                   help="write every event as JSONL to ./dashboard-events.jsonl")
    p.add_argument("--log-file", metavar="PATH",
                   help="write every event as JSONL to PATH (implies --log)")
    args = p.parse_args()

    url = args.url.rstrip("/")
    log_path = args.log_file or ("dashboard-events.jsonl" if args.log else None)

    try:
        asyncio.run(main_async(url, log_path))
    except KeyboardInterrupt:
        print("\nbye.")


if __name__ == "__main__":
    main()