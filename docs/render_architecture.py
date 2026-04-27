"""Render an in-depth architecture wireframe PDF for Lethe.

Pure-Python (ReportLab — already installed for the sample-bill generator).
No system deps, no headless Chrome, no Mermaid.

Output: docs/lethe-architecture.pdf

Run from src/coordinator (so we have the venv on the path):
    .venv/Scripts/python ../../docs/render_architecture.py
"""

from __future__ import annotations

import math
from pathlib import Path

from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas


# =============================================================================
# Theme — matches the project's dark palette
# =============================================================================

BG       = Color(0.04, 0.04, 0.04)
PANEL    = Color(0.06, 0.06, 0.06)
INK      = Color(0.96, 0.96, 0.94)
DIM      = Color(0.66, 0.66, 0.63)
FAINT    = Color(0.42, 0.42, 0.40)
LINE     = Color(1.0,  1.0,  1.0,  alpha=0.16)
RULE     = Color(0.20, 0.20, 0.20)

GREEN    = Color(0.13, 0.77, 0.37)   # live
AMBER    = Color(0.98, 0.75, 0.14)   # stub / partial
ROSE     = Color(0.97, 0.44, 0.44)   # todo
VIOLET   = Color(0.65, 0.55, 0.98)   # accent / agent
CYAN     = Color(0.40, 0.91, 0.97)   # data flow
GREEN_BG = Color(0.13, 0.77, 0.37, alpha=0.10)
AMBER_BG = Color(0.98, 0.75, 0.14, alpha=0.10)
ROSE_BG  = Color(0.97, 0.44, 0.44, alpha=0.08)
VIOLET_BG= Color(0.65, 0.55, 0.98, alpha=0.10)


# =============================================================================
# Helpers
# =============================================================================

def page(c: canvas.Canvas) -> None:
    """Paint the page background + tiny grid."""
    w, h = c._pagesize
    c.setFillColor(BG); c.rect(0, 0, w, h, stroke=0, fill=1)
    # Faint dot grid
    c.setStrokeColor(Color(0.12, 0.12, 0.12))
    c.setLineWidth(0.2)
    for x in range(0, int(w), 40):
        for y in range(0, int(h), 40):
            c.circle(x, y, 0.4, stroke=1, fill=0)


def text(c, x, y, s, *, size=9, color=INK, font="Helvetica", center_x=False):
    c.setFillColor(color)
    c.setFont(font, size)
    if center_x:
        x = x - c.stringWidth(s, font, size) / 2
    c.drawString(x, y, s)
    return c.stringWidth(s, font, size)


def title(c, x, y, s, *, size=18):
    text(c, x, y, s, size=size, color=INK, font="Helvetica-Bold")


def kicker(c, x, y, s, *, size=8):
    text(c, x, y, s, size=size, color=DIM, font="Helvetica")


def box(c, x, y, w, h, *, border=LINE, fill=PANEL, radius=6, dashed=False, lw=0.8):
    c.setStrokeColor(border)
    c.setLineWidth(lw)
    if dashed:
        c.setDash(3, 2)
    c.setFillColor(fill)
    c.roundRect(x, y, w, h, radius, stroke=1, fill=1)
    c.setDash()  # reset


def labeled_box(c, x, y, w, h, label, sublabel=None, *, accent=INK, fill=PANEL,
                lines=None, status=None, dashed=False):
    """A labeled card. `accent` colors the top edge + the label dot.

    `status` is one of None | "live" | "stub" | "todo" — colors the dot.
    """
    bg = fill
    if status == "live":   bg = GREEN_BG;  accent = GREEN
    if status == "stub":   bg = AMBER_BG;  accent = AMBER
    if status == "todo":   bg = ROSE_BG;   accent = ROSE; dashed = True
    if status == "agent":  bg = VIOLET_BG; accent = VIOLET

    box(c, x, y, w, h, border=accent, fill=bg, dashed=dashed)

    # Top accent bar
    c.setFillColor(accent)
    c.rect(x, y + h - 3, w, 3, stroke=0, fill=1)

    # Label
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 10, y + h - 18, label)

    if sublabel:
        c.setFillColor(DIM)
        c.setFont("Helvetica-Oblique", 7.5)
        c.drawString(x + 10, y + h - 30, sublabel)

    if lines:
        cy = y + h - (44 if sublabel else 32)
        c.setFillColor(DIM)
        c.setFont("Helvetica", 7.5)
        for ln in lines:
            c.drawString(x + 10, cy, "·  " + ln)
            cy -= 11


def arrow(c, x1, y1, x2, y2, *, color=CYAN, lw=1.0, dashed=False, label=None):
    c.setStrokeColor(color)
    c.setLineWidth(lw)
    if dashed:
        c.setDash(3, 2)
    c.line(x1, y1, x2, y2)
    c.setDash()
    # Arrowhead
    angle = math.atan2(y2 - y1, x2 - x1)
    head = 5
    c.line(x2, y2, x2 - head * math.cos(angle - 0.45), y2 - head * math.sin(angle - 0.45))
    c.line(x2, y2, x2 - head * math.cos(angle + 0.45), y2 - head * math.sin(angle + 0.45))
    if label:
        midx = (x1 + x2) / 2
        midy = (y1 + y2) / 2
        c.setFillColor(DIM)
        c.setFont("Helvetica-Oblique", 6.5)
        c.drawString(midx + 4, midy + 4, label)


def section_header(c, x, y, num, label, kicker_text=None):
    c.setFillColor(VIOLET)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x, y + 16, num)
    title(c, x + 26, y + 12, label, size=14)
    if kicker_text:
        kicker(c, x, y, kicker_text)


def footer(c, page_num, total):
    w, h = c._pagesize
    c.setFillColor(FAINT)
    c.setFont("Helvetica", 7)
    c.drawString(36, 18, "lethe — medical bills, audited by AI consensus")
    c.drawCentredString(w / 2, 18, "github.com/your-org/lethe  ·  forgotten by design")
    c.drawRightString(w - 36, 18, f"page {page_num} / {total}")
    c.setStrokeColor(RULE)
    c.setLineWidth(0.4)
    c.line(36, 28, w - 36, 28)


def legend(c, x, y):
    """Top-right status legend used on every diagram page."""
    items = [("live",   GREEN),
             ("stub",   AMBER),
             ("todo",   ROSE),
             ("agent",  VIOLET)]
    cx = x
    for label, color in items:
        c.setFillColor(color)
        c.circle(cx + 4, y + 3, 3, stroke=0, fill=1)
        text(c, cx + 12, y, label, size=7, color=DIM)
        cx += 50


# =============================================================================
# PAGE 1 — System overview
# =============================================================================

def page_overview(c, page_num, total):
    page(c)
    w, h = c._pagesize

    # Title strip
    title(c, 36, h - 50, "Lethe — system architecture")
    kicker(c, 36, h - 64,
           "medical bills, audited by AI consensus  ·  three independent LLMs  ·  on-chain anchor on 0G Galileo")
    legend(c, w - 270, h - 60)

    # === FRONTEND row ===
    fy = h - 120
    fh = 70
    text(c, 36, fy + fh + 6, "FRONTEND", size=8, color=DIM, font="Helvetica-Bold")
    bw = (w - 36 * 2 - 16 * 2) / 3
    fx = 36
    labeled_box(c, fx, fy, bw, fh, "Landing  /",
                "hero · sections · scroll reveals · CTA",
                status="live",
                lines=["Next.js 16 + Tailwind 4", "Fraunces serif + Inter + JetBrains Mono"])
    fx += bw + 16
    labeled_box(c, fx, fy, bw, fh, "Dashboard  /dashboard",
                "idle → processing → complete · live SSE",
                status="live",
                lines=["real-time agent terminals", "PDF receipt + edit/submit"])
    fx += bw + 16
    labeled_box(c, fx, fy, bw, fh, "Verify  /verify",
                "drop file · SHA-256 in browser · query chain",
                status="live",
                lines=["file never uploads", "?sha=… deep-link supported"])

    # === COORDINATOR row ===
    cy = fy - 130
    ch = 110
    text(c, 36, cy + ch + 6, "COORDINATOR  ·  FastAPI :8000  ·  Python 3.12",
         size=8, color=DIM, font="Helvetica-Bold")
    box(c, 32, cy - 4, w - 32 * 2, ch + 8, border=LINE, fill=PANEL, lw=0.6)

    cw = (w - 36 * 2 - 16 * 3) / 4
    cx = 36
    labeled_box(c, cx, cy, cw, ch, "Routers",
                "/api/jobs · /api/samples · /api/status · /api/verify",
                status="live",
                lines=["multipart upload",
                       "SSE event stream",
                       "verify endpoint reads chain",
                       "rolling p50/p95 timing"])
    cx += cw + 16
    labeled_box(c, cx, cy, cw, ch, "Pipeline (8 stages)",
                "parse → redact → broadcast → reason →",
                status="live",
                lines=["consensus → anchor → patterns → draft",
                       "real-time agent.message events",
                       "stage timing emitted live",
                       "see page 2 for stage detail"])
    cx += cw + 16
    labeled_box(c, cx, cy, cw, ch, "Agents (registry)",
                "α GPT-4o · β Claude · γ Gemini · drafter",
                status="agent",
                lines=["pluggable registry",
                       "streamed reasoning",
                       "per-agent stub fallback",
                       "see page 4 for prompts"])
    cx += cw + 16
    labeled_box(c, cx, cy, cw, ch, "Stores",
                "in-memory · TTL eviction · stats",
                status="live",
                lines=["JobStore (per-job)",
                       "TimingStats (rolling p95)",
                       "SSE EventBus (per-job queue)",
                       "running jobs immune from sweep"])

    # Privacy boundary divider
    by = cy - 40
    c.setStrokeColor(VIOLET)
    c.setDash(4, 3)
    c.setLineWidth(1.2)
    c.line(36, by, w - 36, by)
    c.setDash()
    text(c, 44, by + 4, "PRIVACY BOUNDARY", size=7, color=VIOLET, font="Helvetica-Bold")
    text(c, 200, by + 4,
         "bill bytes are zeroed after parse · only redacted_payload crosses · only sha256 + verdict + counts on chain",
         size=7, color=DIM)

    # === CHAIN row ===
    chy = by - 130
    chh = 100
    text(c, 36, chy + chh + 6, "ON-CHAIN · 0G Galileo testnet (chain 16602)",
         size=8, color=DIM, font="Helvetica-Bold")

    chw = (w - 36 * 2 - 16) / 2
    chx = 36
    labeled_box(c, chx, chy, chw, chh, "BillRegistry",
                "0xf6B4C9CA2e8C8a3CE2DE77baa119004d6B51B457",
                status="live",
                lines=["anchor(sha256, verdict, agree, total)",
                       "isAnchored(sha256) view",
                       "anchors(sha256) → struct (read-back)",
                       "emits  Anchored(sha256, verdict, ...)",
                       "≈ 0.0006 OG / anchor (~4 gwei × 200k)"])
    chx += chw + 16
    labeled_box(c, chx, chy, chw, chh, "PatternRegistry",
                "0x7665c9692b1c4e6ef90495a584288604b735e23f",
                status="live",
                lines=["indexBatch(billHash, codes, actions, ...)",
                       "totalPatterns()  view",
                       "emits  PatternIndexed(billHash, code, ...)",
                       "indexed by code → public learning",
                       "no PHI: codes + severity + voters bitmask"])

    # === EXTERNAL TODO row ===
    ey = chy - 100
    eh = 70
    text(c, 36, ey + eh + 6, "EXTERNAL  ·  not yet integrated",
         size=8, color=DIM, font="Helvetica-Bold")
    ew = (w - 36 * 2 - 16 * 2) / 3
    ex = 36
    labeled_box(c, ex, ey, ew, eh, "Gensyn AXL",
                "P2P transport · ed25519 peer IDs",
                status="todo",
                lines=["currently asyncio.gather (in-process)",
                       "phase D: 3 sidecar containers"])
    ex += ew + 16
    labeled_box(c, ex, ey, ew, eh, "KeeperHub",
                "reliable on-chain execution",
                status="todo",
                lines=["mirror anchor on Sepolia",
                       "$5K sponsor prize, real API exists"])
    ex += ew + 16
    labeled_box(c, ex, ey, ew, eh, "Smart contracts (Sepolia)",
                "BillRegistry mirror via KeeperHub",
                status="todo",
                lines=["dual-anchor: 0G + Sepolia",
                       "redundancy + execution-layer demo"])

    # Connecting arrows: frontend → coordinator
    bx = w / 2
    arrow(c, bx,        fy,            bx,        cy + ch,    label="HTTP + SSE")
    # coordinator → chain
    arrow(c, 36 + cw / 2, cy,          36 + chw / 2, chy + chh, color=GREEN, label="anchor")
    arrow(c, 36 + cw * 2.5 + 32, cy,   36 + chw * 1.5 + 16, chy + chh, color=GREEN, label="patterns")
    # external dashed
    arrow(c, w - 100, cy,              w - 100, ey + eh, color=ROSE, dashed=True, label="phase B/D")

    footer(c, page_num, total)


# =============================================================================
# PAGE 2 — Pipeline stages
# =============================================================================

PIPELINE = [
    ("01", "parse",       "0.1-2s",   "PDF/TXT/IMG → text",       "live",
     ["pdfplumber for PDF", "GPT-4o vision for image OCR", "raw bytes only here"]),
    ("02", "redact",      "0.8-5s",   "strip PHI from text",       "live",
     ["regex pass (SSN/DOB/MRN/...)", "LLM pass via gpt-4o-mini", "labeled patient/DOB/address line strip"]),
    ("03", "broadcast",   "0.6s",     "AXL handshake",             "stub",
     ["currently asyncio.gather", "phase D: real ed25519 peers", "emits agent.handshake event"]),
    ("04", "reason",      "12-20s",   "3 agents in parallel",      "live",
     ["streamed token-by-token", "α GPT-4o · β Claude · γ Gemini", "real LLM cost per run"]),
    ("05", "consensus",   "0.7s",     "tally votes (≥2/3 quorum)", "live",
     ["canonical-code dedup", "majority verdict", "split totals: dispute/clarify/aligned"]),
    ("06", "anchor",      "5-10s",    "BillRegistry.anchor()",     "live",
     ["EIP-1559 type-2 tx", "real contract on 0G Galileo", "read-back to confirm"]),
    ("07", "patterns",    "5-8s",     "PatternRegistry.indexBatch()","live",
     ["one tx for all findings", "events queryable on-chain", "no PHI written"]),
    ("08", "draft",       "12-16s",   "appeal letter via Claude",   "live",
     ["drafter agent (claude-sonnet-4.5)", "regulatory citations included", "user can edit before submit"]),
]


def page_pipeline(c, page_num, total):
    page(c)
    w, h = c._pagesize

    section_header(c, 36, h - 60, "[ 02 ]", "Pipeline · 8 stages",
                   "real durations from production runs · privacy invariants per stage")
    legend(c, w - 270, h - 60)

    # Each stage gets a card. 4 per row, 2 rows.
    cols = 4
    rows = 2
    pad = 16
    total_w = w - 36 * 2
    cw = (total_w - pad * (cols - 1)) / cols
    ch = 110
    top = h - 110
    for i, (num, name, dur, oneliner, status, bullets) in enumerate(PIPELINE):
        col = i % cols
        row = i // cols
        x = 36 + col * (cw + pad)
        y = top - row * (ch + pad) - ch

        labeled_box(c, x, y, cw, ch,
                    f"{num}  ·  {name}",
                    f"{oneliner}   ({dur})",
                    status=status,
                    lines=bullets)
        # Connector arrow to the next box (right-pointing inside row, wrap arrow at row break)
        if i < len(PIPELINE) - 1 and col < cols - 1:
            arrow(c, x + cw, y + ch / 2, x + cw + pad, y + ch / 2, color=CYAN, lw=0.8)
        if i == cols - 1:
            # wrap arrow: from end of row 1 down/around to start of row 2
            arrow(c, x + cw + pad/2, y, x + cw + pad/2, y - pad / 2, color=CYAN, lw=0.6)
            arrow(c, x + cw + pad/2, y - pad / 2, 36 - pad/2, y - pad / 2, color=CYAN, lw=0.6)
            arrow(c, 36 - pad/2, y - pad / 2, 36 - pad/2, y - ch - pad/2, color=CYAN, lw=0.6)
            arrow(c, 36 - pad/2, y - ch - pad/2, 36, y - ch - pad/2, color=CYAN, lw=0.6)

    # Footer note for pipeline
    fy = top - 2 * (ch + pad) - 30
    text(c, 36, fy, "PRIVACY INVARIANTS",
         size=8, color=VIOLET, font="Helvetica-Bold")
    notes = [
        "·  Bill bytes live ONLY in JobStore memory and are zeroed immediately after parse.",
        "·  Only the redacted_payload (no patient identifiers) is passed to any LLM provider.",
        "·  SSE events carry no bill content — only stage names, durations, verdicts, counts.",
        "·  On-chain: only sha256 + verdict + agree/total + canonical billing codes.",
        "·  Background sweeper purges any job past TTL — except those still actively running.",
    ]
    cy = fy - 14
    for n in notes:
        text(c, 36, cy, n, size=8, color=DIM)
        cy -= 12

    footer(c, page_num, total)


# =============================================================================
# PAGE 3 — Privacy boundary diagram
# =============================================================================

def page_privacy(c, page_num, total):
    page(c)
    w, h = c._pagesize

    section_header(c, 36, h - 60, "[ 03 ]", "Privacy boundary · what crosses what wires",
                   "the redactor is the load-bearing seam · everything past it is anonymized")
    legend(c, w - 270, h - 60)

    # Big "coordinator memory" container — everything inside is private.
    inner_x, inner_y = 60, 80
    inner_w = (w / 2) - 40
    inner_h = h - 200

    box(c, inner_x, inner_y, inner_w, inner_h, border=VIOLET, fill=Color(0.04, 0.03, 0.06), lw=1.4)
    text(c, inner_x + 14, inner_y + inner_h - 22,
         "COORDINATOR MEMORY  ·  ephemeral",
         size=10, color=VIOLET, font="Helvetica-Bold")
    text(c, inner_x + 14, inner_y + inner_h - 34,
         "everything in this box is gone after the pipeline finishes (TTL + zeroing)",
         size=7.5, color=DIM)

    # Inside boxes
    bx = inner_x + 24
    bw = inner_w - 48
    bh = 64

    by = inner_y + inner_h - 110
    labeled_box(c, bx, by, bw, bh, "1.  bill_bytes",
                "the raw upload  ·  PDF/TXT/PNG/JPG",
                status="todo",
                lines=["zeroed at the end of `parse`",
                       "never written to disk, never logged",
                       "lives ~5-10s in JobStore"])

    by -= 80
    labeled_box(c, bx, by, bw, bh, "2.  parsed text  (transient)",
                "pdfplumber output OR vision-OCR text",
                status="todo",
                lines=["dropped immediately after redact",
                       "may still contain PHI",
                       "passes ONLY to redactor"])

    by -= 80
    labeled_box(c, bx, by, bw, bh, "3.  redacted_payload",
                "regex-stripped + LLM-stripped",
                status="agent",
                lines=["this is the ONLY thing the agents see",
                       "patient/DOB/address/SSN/MRN replaced",
                       "no free-text PHI by design"])

    # OUTSIDE: things data flows out to
    out_x = inner_x + inner_w + 50
    out_w = w - out_x - 36

    # Three external destinations
    oh = 70
    oy = inner_y + inner_h - 50
    text(c, out_x, oy + 4, "EXTERNAL DESTINATIONS",
         size=10, color=INK, font="Helvetica-Bold")
    text(c, out_x, oy - 8, "what each downstream actually receives", size=7.5, color=DIM)

    oy -= 30
    labeled_box(c, out_x, oy - oh, out_w, oh, "OpenAI  ·  Anthropic  ·  Google",
                "audit + drafter LLM providers",
                status="agent",
                lines=["receive: redacted_payload only",
                       "DO NOT receive: bill bytes, names, MRN",
                       "streaming JSON over HTTPS"])

    oy -= oh + 18
    labeled_box(c, out_x, oy - oh, out_w, oh, "0G Chain  ·  BillRegistry",
                "Galileo testnet · public",
                status="live",
                lines=["receives: sha256 + verdict + counts",
                       "stores: 1 entry per bill, immutable",
                       "no patient data goes on-chain ever"])

    oy -= oh + 18
    labeled_box(c, out_x, oy - oh, out_w, oh, "0G Chain  ·  PatternRegistry",
                "Galileo testnet · public",
                status="live",
                lines=["receives: code + action + severity + voters",
                       "stores: events only (cheap)",
                       "queryable index of error patterns"])

    # Arrows from inside → outside
    # redacted_payload → LLM agents
    arrow(c,
          bx + bw, by + bh / 2 + 80,
          out_x, oy + oh + oh + 18 + oh + oh / 2 + 18,
          color=VIOLET, lw=1.0,
          label="redacted only")
    # sha256 + verdict → BillRegistry
    arrow(c,
          bx + bw, by + bh / 2 + 80,
          out_x, oy + oh + 18 + oh / 2,
          color=GREEN, lw=1.0,
          label="hash + verdict")
    # findings → PatternRegistry
    arrow(c,
          bx + bw, by + bh / 2 + 80,
          out_x, oy + oh / 2,
          color=GREEN, lw=1.0,
          label="codes only")

    # Bottom rule + privacy claim
    py = 60
    c.setStrokeColor(VIOLET)
    c.setDash(4, 3)
    c.setLineWidth(1)
    c.line(36, py, w - 36, py)
    c.setDash()
    text(c, 36, py - 14,
         "the bill never crosses the boundary on the right.  "
         "the chain remembers the audit, not the bill.",
         size=9, color=INK, font="Helvetica-Oblique")

    footer(c, page_num, total)


# =============================================================================
# PAGE 4 — Sponsor track integrations
# =============================================================================

def page_sponsors(c, page_num, total):
    page(c)
    w, h = c._pagesize

    section_header(c, 36, h - 60, "[ 04 ]", "Sponsor tracks · integration status",
                   "ETHGlobal OpenAgents · honest assessment")
    legend(c, w - 270, h - 60)

    cols = 3
    pad = 18
    total_w = w - 36 * 2
    cw = (total_w - pad * (cols - 1)) / cols
    ch = h - 220
    y = 100

    # 0G column
    x = 36
    labeled_box(c, x, y, cw, ch, "0G Labs  (chain + storage)",
                "0g.ai  ·  Galileo testnet  ·  chain 16602",
                status="live",
                lines=[
                    "BillRegistry  · live",
                    "  0xf6B4C9CA…1B457",
                    "  real anchor + read-back",
                    "",
                    "PatternRegistry  · live",
                    "  0x7665c969…e23f",
                    "  indexBatch event log",
                    "",
                    "0G Storage SDK  · pivoted",
                    "  community Python SDK broken",
                    "  using chain events instead",
                    "",
                    "WHAT JUDGES SEE",
                    "  /verify page reads contract",
                    "  receipt PDF lists tx hash",
                    "  /api/verify/{sha} read-only",
                    "  ~0.0006 OG per audit",
                ])

    x += cw + pad
    labeled_box(c, x, y, cw, ch, "Gensyn AXL  (P2P transport)",
                "blog.gensyn.ai/introducing-axl  ·  ed25519 mesh",
                status="todo",
                lines=[
                    "current state",
                    "  asyncio.gather, in-process",
                    "  agents are coroutines, not peers",
                    "",
                    "what's required",
                    "  3 axl-node binaries (Go)",
                    "  one ed25519 keypair each",
                    "  yggdrasil mesh handshake",
                    "  HTTP API per sidecar (9002/12/22)",
                    "",
                    "judging signal",
                    "  curl localhost:9002/topology",
                    "  three distinct pubkeys visible",
                    "",
                    "PHASE D — ~4-6 hr scope",
                    "  docker compose with 4 services",
                    "  WSL/Linux (Go 1.25.5 + gVisor)",
                    "  smallest credible: one host",
                ])

    x += cw + pad
    labeled_box(c, x, y, cw, ch, "KeeperHub  (reliable execution)",
                "keeperhub.com  ·  $5K prize",
                status="todo",
                lines=[
                    "what it provides",
                    "  hosted exec layer for on-chain ops",
                    "  smart-gas, retry, audit trail",
                    "  Direct Execution + Workflow APIs",
                    "",
                    "supported chains",
                    "  Eth, Sepolia, Base, Arbitrum...",
                    "  0G NOT supported",
                    "  → use Sepolia mirror",
                    "",
                    "prerequisites",
                    "  account at app.keeperhub.com  (have)",
                    "  API key  kh_…  (have)",
                    "  Turnkey/Para wallet  (todo)",
                    "  Sepolia ETH on that wallet  (todo)",
                    "",
                    "PHASE B — ~2-3 hr scope",
                    "  deploy BillRegistry to Sepolia",
                    "  POST /api/execute/contract-call",
                    "  show KH dashboard run history",
                ])

    # Bottom strategic note
    text(c, 36, 70, "DEMO STORYLINE",
         size=8, color=VIOLET, font="Helvetica-Bold")
    text(c, 36, 56,
         "\"Three independent LLM agents reach consensus over a peer-to-peer mesh. "
         "The bill SHA-256 hits 0G Chain (canonical) and KeeperHub (Sepolia mirror, redundant execution).",
         size=8, color=DIM)
    text(c, 36, 44,
         "Anonymized patterns persist on-chain so future audits get smarter without retaining anyone's bill.\"",
         size=8, color=DIM)

    footer(c, page_num, total)


# =============================================================================
# PAGE 5 — Sequence (anchor lifecycle)
# =============================================================================

def page_sequence(c, page_num, total):
    page(c)
    w, h = c._pagesize

    section_header(c, 36, h - 60, "[ 05 ]", "Anchor lifecycle  ·  sequence",
                   "what happens when a user drops a bill, end-to-end")

    # Vertical lifelines: User · Frontend · Coordinator · LLM Providers · 0G Chain
    actors = ["User",
              "Frontend\n(Next.js)",
              "Coordinator\n(FastAPI)",
              "LLM providers\n(OpenAI/Anthropic/Google)",
              "0G Chain\n(BillRegistry,\n PatternRegistry)"]
    n = len(actors)
    margin = 60
    avail = w - margin * 2
    spacing = avail / (n - 1)

    # Header / actor boxes
    bw = 130
    bh = 40
    by = h - 130
    actor_x = []
    for i, a in enumerate(actors):
        cx = margin + i * spacing
        actor_x.append(cx)
        # box
        c.setStrokeColor(VIOLET); c.setLineWidth(0.8)
        c.setFillColor(PANEL)
        c.roundRect(cx - bw / 2, by, bw, bh, 4, stroke=1, fill=1)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 8)
        for li, line in enumerate(a.split("\n")):
            c.drawCentredString(cx, by + bh - 14 - li * 9, line)

    # Lifelines
    line_top = by
    line_bot = 60
    c.setStrokeColor(RULE)
    c.setDash(2, 3)
    c.setLineWidth(0.6)
    for cx in actor_x:
        c.line(cx, line_top, cx, line_bot)
    c.setDash()

    # Sequence steps
    steps = [
        # (from_idx, to_idx, label, color)
        (0, 1, "drop file (drag/drop or click)", CYAN),
        (1, 2, "POST /api/jobs   multipart", CYAN),
        (2, 1, "{job_id, sha256}   200 OK", CYAN),
        (1, 2, "EventSource /api/jobs/{id}/stream", CYAN),
        (2, 2, "parse → redact (in-memory)", VIOLET),
        (2, 3, "POST chat/completions  stream=True   ×3 in parallel", VIOLET),
        (3, 2, "streamed reasoning tokens", VIOLET),
        (2, 1, "agent.message  (live)", VIOLET),
        (3, 2, "{verdict, findings, confidence}  json", VIOLET),
        (2, 2, "consensus.tally()  (≥2/3 quorum)", GREEN),
        (2, 4, "BillRegistry.anchor(sha, v, a, t)", GREEN),
        (4, 2, "tx receipt + Anchored event", GREEN),
        (2, 4, "PatternRegistry.indexBatch(...)", GREEN),
        (4, 2, "tx receipt + N PatternIndexed events", GREEN),
        (2, 3, "draft appeal letter   (Claude)", VIOLET),
        (3, 2, "letter body + citations", VIOLET),
        (2, 1, "done event + GET /api/jobs/{id} → result", CYAN),
        (1, 0, "render proof card + receipt PDF", CYAN),
    ]
    y = by - 22
    step_h = 18
    for from_idx, to_idx, label, color in steps:
        x1 = actor_x[from_idx]
        x2 = actor_x[to_idx]
        if from_idx == to_idx:
            # self-loop (small arc) — represented as a short right hop
            c.setStrokeColor(color)
            c.setLineWidth(1)
            c.line(x1, y, x1 + 30, y)
            c.line(x1 + 30, y, x1 + 30, y - 6)
            c.line(x1 + 30, y - 6, x1 + 4, y - 6)
            # arrowhead
            c.line(x1 + 4, y - 6, x1 + 9, y - 4)
            c.line(x1 + 4, y - 6, x1 + 9, y - 9)
            text(c, x1 + 36, y - 4, label, size=7, color=DIM, font="Helvetica-Oblique")
        else:
            arrow(c, x1, y, x2, y, color=color, lw=1.0)
            mid = (x1 + x2) / 2
            text(c, mid, y + 3, label, size=7, color=DIM, font="Helvetica-Oblique", center_x=True)
        y -= step_h
        if y < line_bot + 20:
            break  # don't overflow

    footer(c, page_num, total)


# =============================================================================
# Driver
# =============================================================================

def main() -> None:
    out = Path(__file__).resolve().parent / "lethe-architecture.pdf"
    c = canvas.Canvas(str(out), pagesize=landscape(letter))
    pages = [page_overview, page_pipeline, page_privacy, page_sponsors, page_sequence]
    total = len(pages)
    for i, fn in enumerate(pages, start=1):
        fn(c, i, total)
        c.showPage()
    c.save()
    print(f"wrote {out}  ({out.stat().st_size:,} bytes, {total} pages)")


if __name__ == "__main__":
    main()