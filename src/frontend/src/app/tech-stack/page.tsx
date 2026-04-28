"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { NavBar } from "@/components/NavBar";

const reveal = (delay = 0) => ({
  initial: { opacity: 0, y: 16 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, amount: 0.2 } as const,
  transition: { duration: 0.6, delay, ease: "easeOut" as const },
});

type StageRow = {
  step: string;
  what: string;
  tool: string;
  out: string;
};

const STAGES: StageRow[] = [
  {
    step: "1 · parse",
    what: "Extract structured bill text (CPT/ICD codes, modifiers, charges, DOS) from PDF / TXT / image.",
    tool: "pdfplumber + image fallback",
    out: "in-memory parsed payload",
  },
  {
    step: "2 · redact",
    what: "Strip every PHI identifier — patient name, DOB, address, MRN, account numbers — by regex pass + LLM sweep.",
    tool: "regex + OpenAI gpt-4o redactor",
    out: "redacted payload (no PHI)",
  },
  {
    step: "3 · broadcast",
    what: "Open AXL handshake to each agent's sidecar and confirm the three peer nodes are live on the Gensyn mesh.",
    tool: "Gensyn AXL · ed25519 peers",
    out: "agent.handshake event",
  },
  {
    step: "4 · reason",
    what: "Three LLM agents reason in parallel over the redacted payload, each streaming prose tokens back to the dashboard. γ optionally runs on 0G Compute via decentralized inference instead of Gemini.",
    tool: "GPT-4o · Claude Sonnet 4.5 · Gemini Flash · (optional) 0G Compute",
    out: "round-1 votes + findings",
  },
  {
    step: "5 · exchange",
    what: "Each agent broadcasts its OWN findings to peers via real POST /send; sidecars drain inboxes via GET /recv so peers actually receive.",
    tool: "Gensyn AXL · POST /send + GET /recv",
    out: "peer_received attached to each vote",
  },
  {
    step: "6 · reflect",
    what: "Each agent gets ONE more LLM call with peer findings as context. May add findings it missed, downgrade ones peers disagreed with, or hold its ground.",
    tool: "round-2 LLM call per agent",
    out: "revised votes (round 2)",
  },
  {
    step: "7 · consensus",
    what: "Tally round-2 votes. A finding only counts if ≥2 of 3 agents flagged the same canonical billing code. 1-1-1 splits fall back to clarify.",
    tool: "majority vote · 2-of-3 quorum",
    out: "consensus verdict + findings",
  },
  {
    step: "8 · anchor",
    what: "Write SHA-256 + verdict to BillRegistry on 0G Galileo (canonical). Mirror the same record to a Sepolia BillRegistry via KeeperHub Direct Execution (REST or MCP transport, configurable).",
    tool: "web3.py · KeeperHub Direct Execution · MCP",
    out: "two on-chain tx hashes",
  },
  {
    step: "8.5 · file dispute",
    what: "On consensus = dispute, fire a SECOND KeeperHub workflow against a configurable Sepolia DisputeRegistry — recordDispute(billHash, reason, note). Different contract, different method, different verdict gate.",
    tool: "KeeperHub Direct Execution (workflow #2)",
    out: "third on-chain tx (dispute filing)",
  },
  {
    step: "9 · patterns + storage",
    what: "Index anonymized findings (code · action · severity · amount) to PatternRegistry on 0G Chain in parallel with uploading the full schema-versioned audit blob to 0G Storage. Two pillars, one stage. Future audits read patterns back as priors.",
    tool: "PatternRegistry events on 0G Chain · @0glabs/0g-ts-sdk via Node sidecar",
    out: "indexed event log + storage merkle root + commitment tx",
  },
  {
    step: "10 · draft",
    what: "A fourth agent writes a formal appeal letter from the consensus findings, with regulatory citations.",
    tool: "Claude Sonnet 4.5 (drafter)",
    out: "appeal letter + receipt PDF",
  },
];

type StackEntry = {
  layer: string;
  items: { name: string; role: string }[];
};

const STACK: StackEntry[] = [
  {
    layer: "Frontend",
    items: [
      { name: "Next.js 16", role: "App Router, React Server Components" },
      { name: "React 19", role: "UI runtime" },
      { name: "TypeScript", role: "type safety throughout" },
      { name: "Tailwind v4", role: "styling, including @theme inline" },
      { name: "Framer Motion 12", role: "page transitions, micro-animations" },
      { name: "jsPDF", role: "ASCII receipt PDF generation in-browser" },
      { name: "EventSource (SSE)", role: "live pipeline events from coordinator" },
    ],
  },
  {
    layer: "Coordinator",
    items: [
      { name: "Python 3.11", role: "runtime" },
      { name: "FastAPI", role: "HTTP API + lifespan + middleware" },
      { name: "uvicorn", role: "ASGI server" },
      { name: "sse-starlette", role: "Server-Sent Events for live pipeline" },
      { name: "pdfplumber", role: "deterministic PDF text extraction" },
      { name: "pydantic-settings", role: "12-factor env config" },
      { name: "httpx", role: "async HTTP — talks to AXL sidecars, KH, 0G Storage sidecar" },
      { name: "mcp (Python SDK)", role: "KeeperHub MCP client (alternate transport)" },
    ],
  },
  {
    layer: "AI Providers",
    items: [
      { name: "OpenAI GPT-4o", role: "agent α + the redactor sweep" },
      { name: "Anthropic Claude Sonnet 4.5", role: "agent β + the appeal-letter drafter" },
      { name: "Google Gemini Flash", role: "agent γ (default)" },
      { name: "0G Compute Network", role: "agent γ (optional) — decentralized inference, OpenAI-compatible" },
    ],
  },
  {
    layer: "P2P transport",
    items: [
      { name: "Gensyn AXL", role: "Go node binary, one Docker sidecar per agent" },
      { name: "Yggdrasil mesh", role: "encrypted overlay network" },
      { name: "ed25519", role: "agent peer identity (one keypair each)" },
      { name: "socat", role: "container-internal port forwarder for the AXL HTTP API" },
      { name: "Live message ring buffer", role: "200-entry server-side log of every send/recv with pubkeys + latency, surfaced on /axl" },
    ],
  },
  {
    layer: "0G — Chain",
    items: [
      { name: "Solidity", role: "BillRegistry + PatternRegistry contracts" },
      { name: "web3.py + eth-account", role: "EVM RPC + wallet signing for writes" },
      { name: "py-solc-x", role: "compile + deploy contracts (no Foundry)" },
      { name: "0G Galileo testnet (chain id 16602)", role: "canonical anchor + pattern index + storage commitments" },
    ],
  },
  {
    layer: "0G — Storage",
    items: [
      { name: "@0glabs/0g-ts-sdk", role: "Node SDK for 0G Storage uploads (Python SDK is broken upstream)" },
      { name: "Node storage sidecar", role: "POST /upload → merkle root + on-chain commitment tx (port 8788)" },
      { name: "Indexer turbo endpoint", role: "indexer-storage-testnet-turbo.0g.ai — selects replication nodes" },
      { name: "Schema lethe.audit.pattern.v1", role: "anonymized full-resolution audit blob format" },
    ],
  },
  {
    layer: "0G — Compute",
    items: [
      { name: "@0glabs/0g-serving-broker", role: "Node SDK for 0G Compute provisioning + per-request signing" },
      { name: "Node headers sidecar", role: "OpenAI-compatible proxy that signs each request body hash (port 8787)" },
      { name: "ethers v6", role: "wallet signer for ledger deposits + provider acknowledgement" },
      { name: "Provisioning scripts", role: "provision:0g · headers:0g · check:0g · storage:0g (in src/coordinator/scripts/)" },
    ],
  },
  {
    layer: "KeeperHub — execution",
    items: [
      { name: "Direct Execution REST", role: "workflow #1: Sepolia BillRegistry mirror anchor" },
      { name: "Direct Execution REST (workflow #2)", role: "DisputeRegistry recordDispute on consensus = dispute" },
      { name: "MCP server transport", role: "alternate path for the mirror anchor" },
      { name: "Sepolia event lookup", role: "publicnode RPC fallback to find original tx for 'already anchored' duplicates" },
      { name: "Ethereum Sepolia", role: "secondary verifiability via etherscan" },
    ],
  },
  {
    layer: "Infra",
    items: [
      { name: "Docker Compose", role: "orchestrates 5+ services" },
      { name: "Multi-stage Dockerfile", role: "builds AXL Go binary on Linux for Windows hosts" },
      { name: "tsx + TypeScript", role: "runs Node sidecars without a build step" },
      { name: "GitHub", role: "source + collaboration" },
    ],
  },
];

const PRIVACY_RULES = [
  {
    label: "Bill bytes",
    state: "in-memory only",
    detail: "Held in coordinator memory keyed by job_id, zeroed immediately after the parse stage. Never written to disk, never logged, never persisted.",
  },
  {
    label: "Patient identifiers",
    state: "stripped pre-AI",
    detail: "Name, DOB, address, MRN, and account numbers are removed by regex + LLM redactor before any audit agent sees the payload.",
  },
  {
    label: "AXL P2P traffic",
    state: "redacted only",
    detail: "What crosses the Gensyn mesh is either the redacted payload or each agent's findings — both PHI-free by construction.",
  },
  {
    label: "0G BillRegistry",
    state: "hash + verdict only",
    detail: "Stores SHA-256 of the bill plus consensus verdict. Pre-image is impossible to recover from the hash alone.",
  },
  {
    label: "0G PatternRegistry",
    state: "anonymized findings",
    detail: "Code · action · severity · amount only — no patient identifiers, no descriptions, no bill content. Read back as priors for future audits.",
  },
  {
    label: "Sepolia mirror",
    state: "same hash + verdict",
    detail: "Identical record to 0G, written via KeeperHub Direct Execution. Provides cross-chain verifiability without expanding what's stored.",
  },
  {
    label: "Model providers",
    state: "redacted only",
    detail: "OpenAI / Anthropic / Google see the redacted payload during reasoning and peer findings during reflection — never the original bill.",
  },
];

export default function TechStackPage() {
  return (
    <>
      <NavBar subBrand="tech-stack" />

      <div className="dash-page">
        <section className="dash-hero" style={{ paddingBottom: 24 }}>
          <motion.div className="dash-eyebrow" {...reveal(0)}>
            <span className="pulse-dot" />
            <span className="pill">stack · data flow · invariants</span>
            <span>everything under the hood</span>
          </motion.div>

          <motion.h1 className="dash-headline" {...reveal(0.05)}>
            Tech stack &amp; <em>data flow.</em>
          </motion.h1>

          <motion.p className="dash-sub" {...reveal(0.12)}>
            Lethe is one Next.js dashboard, one FastAPI coordinator, three AXL
            sidecars, two Solidity contracts, and a careful refusal to keep
            anyone&apos;s bill on disk. This page lays out every stage, every tool,
            and every privacy invariant — in the order they fire on a real audit.
          </motion.p>
        </section>

        {/* ============================================================ */}
        {/* DATA FLOW */}
        {/* ============================================================ */}
        <section className="band">
          <div className="container">
            <motion.div className="section-head" {...reveal(0)}>
              <span className="section-num">[ 01 ]</span>
              <h2 className="section-title">
                Ten stages, <span className="em">one pipeline.</span>
              </h2>
              <p className="section-kicker">
                A real audit fires every one of these stages over Server-Sent
                Events. Each row is a single SSE event type the dashboard listens
                to, in the order it arrives.
              </p>
            </motion.div>

            <motion.div className="stages-table" {...reveal(0.08)}>
              {STAGES.map((s, i) => (
                <div key={s.step} className="stage-row">
                  <div className="stage-step">{s.step}</div>
                  <div className="stage-body">
                    <div className="stage-what">{s.what}</div>
                    <div className="stage-meta">
                      <span className="stage-tool">tool · {s.tool}</span>
                      <span className="stage-out">→ {s.out}</span>
                    </div>
                  </div>
                  <div className="stage-idx">{String(i + 1).padStart(2, "0")}</div>
                </div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* ============================================================ */}
        {/* HOW IT FITS TOGETHER */}
        {/* ============================================================ */}
        <section className="band">
          <div className="container">
            <motion.div className="section-head" {...reveal(0)}>
              <span className="section-num">[ 02 ]</span>
              <h2 className="section-title">
                How the parts <span className="em">fit together.</span>
              </h2>
              <p className="section-kicker">
                Five top-level boxes. The orchestrator owns the pipeline; the
                agent mesh actually talks to itself; the chain anchors don&apos;t
                see anything but a hash.
              </p>
            </motion.div>

            <motion.div className="dataflow" {...reveal(0.1)}>
              <div className="df-row">
                <div className="df-box client">
                  <div className="df-label">Client</div>
                  <div className="df-name">Next.js Dashboard</div>
                  <div className="df-detail">Upload · live SSE stream · receipt PDF</div>
                </div>
              </div>

              <div className="df-arrow">↓ HTTP request · SSE event stream</div>

              <div className="df-row">
                <div className="df-box orch">
                  <div className="df-label">Orchestration node</div>
                  <div className="df-name">FastAPI Coordinator</div>
                  <div className="df-detail">
                    Parser · PHI Redactor · Consensus tally · Drafter
                    <br />
                    Holds the bill bytes in memory only. Owns the SSE event bus.
                  </div>
                </div>
              </div>

              <div className="df-arrow">↓ redacted payload</div>

              <div className="df-row">
                <div className="df-box agent">
                  <div className="df-label">α</div>
                  <div className="df-name">Agent Alpha</div>
                  <div className="df-detail">GPT-4o<br />ed25519 c4737e16…</div>
                </div>
                <div className="df-box agent">
                  <div className="df-label">β</div>
                  <div className="df-name">Agent Beta</div>
                  <div className="df-detail">Claude Sonnet 4.5<br />ed25519 fc40f9dd…</div>
                </div>
                <div className="df-box agent">
                  <div className="df-label">γ</div>
                  <div className="df-name">Agent Gamma</div>
                  <div className="df-detail">Gemini Flash<br />ed25519 739dd219…</div>
                </div>
              </div>

              <div className="df-arrow">⇄ AXL P2P · findings exchange · round-2 reflection</div>

              <div className="df-row">
                <div className="df-box orch">
                  <div className="df-label">Back to orchestrator</div>
                  <div className="df-name">Consensus + Drafter</div>
                  <div className="df-detail">
                    Round-2 votes tallied · 2-of-3 quorum · clarify on tie
                    <br />
                    Drafter produces the appeal letter
                  </div>
                </div>
              </div>

              <div className="df-arrow">↓ sha-256 + verdict + anonymized findings</div>

              <div className="df-row">
                <div className="df-box chain">
                  <div className="df-label">Canonical</div>
                  <div className="df-name">0G Galileo</div>
                  <div className="df-detail">
                    BillRegistry (anchor)
                    <br />
                    PatternRegistry (priors for next audit)
                  </div>
                </div>
                <div className="df-box chain">
                  <div className="df-label">Mirror</div>
                  <div className="df-name">KeeperHub → Sepolia</div>
                  <div className="df-detail">
                    Same SHA-256 + verdict
                    <br />
                    Cross-chain verifiability
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </section>

        {/* ============================================================ */}
        {/* TECH STACK */}
        {/* ============================================================ */}
        <section className="band">
          <div className="container">
            <motion.div className="section-head" {...reveal(0)}>
              <span className="section-num">[ 03 ]</span>
              <h2 className="section-title">
                The <span className="em">tools</span>, by layer.
              </h2>
              <p className="section-kicker">
                Every dependency that does real work in production. No
                speculative libraries, no &ldquo;coming soon&rdquo; entries.
              </p>
            </motion.div>

            <motion.div className="stack-grid" {...reveal(0.08)}>
              {STACK.map((g) => (
                <div key={g.layer} className="stack-card">
                  <div className="stack-head">{g.layer}</div>
                  <div className="stack-list">
                    {g.items.map((it) => (
                      <div key={it.name} className="stack-item">
                        <span className="stack-name">{it.name}</span>
                        <span className="stack-role">{it.role}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* ============================================================ */}
        {/* PRIVACY INVARIANTS */}
        {/* ============================================================ */}
        <section className="band">
          <div className="container">
            <motion.div className="section-head" {...reveal(0)}>
              <span className="section-num">[ 04 ]</span>
              <h2 className="section-title">
                What we <span className="em">never</span> keep.
              </h2>
              <p className="section-kicker">
                Each row is an invariant the codebase enforces, not a goal it
                aspires to. If any of these break, it&apos;s a bug.
              </p>
            </motion.div>

            <motion.div className="invariants" {...reveal(0.08)}>
              {PRIVACY_RULES.map((r) => (
                <div key={r.label} className="inv-row">
                  <div className="inv-label">{r.label}</div>
                  <div className="inv-state">{r.state}</div>
                  <div className="inv-detail">{r.detail}</div>
                </div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* ============================================================ */}
        {/* CTAs */}
        {/* ============================================================ */}
        <section className="cta-band">
          <motion.h2 {...reveal(0)}>
            See it run.<br />
            <em>The receipts are real.</em>
          </motion.h2>
          <motion.p {...reveal(0.08)}>
            Open the dashboard and run a sample bill end-to-end. Every tx hash
            on the receipt resolves on the matching block explorer.
          </motion.p>
          <motion.div className="hero-ctas" {...reveal(0.16)}>
            <Link className="btn btn-primary" href="/dashboard">
              Open dashboard <span className="arr">→</span>
            </Link>
            <Link className="btn btn-ghost" href="/axl">
              View live mesh
            </Link>
          </motion.div>
        </section>
      </div>
    </>
  );
}
