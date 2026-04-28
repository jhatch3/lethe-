"use client";

import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
} from "react";
import { NavBar } from "@/components/NavBar";

type Phase = "idle" | "processing" | "complete";

const PIPELINE = [
  { id: "parse", name: "Parse", detail: "extracting line items" },
  { id: "redact", name: "Redact PHI", detail: "stripping identifiers" },
  { id: "broadcast", name: "Broadcast", detail: "AXL · 3 peers" },
  { id: "reason", name: "Reason", detail: "α · β · γ analyzing" },
  { id: "exchange", name: "P2P exchange", detail: "agents share findings" },
  { id: "reflect", name: "Reflect", detail: "round-2 with peer input" },
  { id: "consensus", name: "Consensus", detail: "tallying votes" },
  { id: "anchor", name: "Anchor", detail: "0G chain · sha-256" },
  { id: "patterns", name: "Patterns", detail: "indexing on PatternRegistry" },
  { id: "draft", name: "Draft", detail: "writing appeal letter" },
] as const;

const HEX = "0123456789abcdef";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type BackendFinding = {
  id?: string;
  severity?: string;
  code?: string;
  description?: string;
  amount_usd?: number;
  action?: string;
  citation?: string;
  voted_by?: string[];
};

type BackendAgentVote = {
  agent: string;
  model: string;
  verdict: string;
  confidence: number;
  findings: BackendFinding[];
  notes: string;
  duration_ms: number;
};

type BackendResult = {
  filename: string;
  sha256: string;
  consensus: {
    verdict: string;
    agree_count: number;
    total_agents: number;
    mean_confidence: number;
    findings: BackendFinding[];
    actionable_count?: number;
    aligned_count?: number;
    disputed_total_usd: number;
    clarify_total_usd?: number;
    flagged_total_usd: number;
    aligned_total_usd?: number;
    agents: BackendAgentVote[];
  };
  dispute: {
    subject: string;
    body: string;
    citations: string[];
    drafted_by: string;
    duration_ms: number;
  } | null;
  proof: {
    network: string;
    bill_sha256: string;
    anchor_tx: string | null;
    executor: string;
    status: string;
    block_number?: number | null;
    chain_id?: number;
    registry_address?: string;
    gas_used?: number;
    live?: boolean;
    onchain?: {
      verdict: string;
      verdict_int: number;
      agree_count: number;
      total_agents: number;
      anchored_at: number;
      anchored_by: string;
    };
    patterns?: {
      executor: string;
      live: boolean;
      patterns_indexed: number;
      tx?: string;
      block_number?: number;
      registry_address?: string;
      gas_used?: number;
      storage?: {
        executor: string;
        live: boolean;
        network?: string;
        root_hash?: string | null;
        tx_hash?: string | null;
        tx_link?: string | null;
        bytes?: number;
        schema?: string;
      };
    };
    mirror?: {
      executor: string;
      live: boolean;
      network: string;
      chain_id?: number;
      execution_id?: string;
      status?: string;
      tx_hash?: string | null;
      tx_link?: string | null;
      registry_address?: string;
      block_number?: number | null;
      note?: string;
    };
    dispute_filing?: {
      executor: string;
      live: boolean;
      network?: string;
      chain_id?: number;
      execution_id?: string;
      status?: string;
      tx_hash?: string | null;
      tx_link?: string | null;
      registry_address?: string;
      function_name?: string;
    };
  } | null;
  stage_timings_ms: Record<string, number>;
  total_runtime_ms: number;
};

const SAMPLE_BILLS = [
  { name: "general-hospital-er", ext: "pdf" },
  { name: "imaging-center-ct", ext: "pdf" },
  { name: "ortho-clinic-mri", ext: "pdf" },
  { name: "discharge-summary", ext: "txt" },
  { name: "labs-itemized", ext: "png" },
] as const;

const AGENT_STREAMS: Record<"alpha" | "beta" | "gamma", string[]> = {
  alpha: [
    "▸ payload received · 14 line items",
    "▸ cross-ref CMS NCCI policy 7.1",
    "▸ flag CPT 99214 duplicate · DOS 2026-04-14",
    "▸ flag modifier 25 missing on E/M",
    "▸ vote: dispute · conf 0.91",
  ],
  beta: [
    "▸ ed25519:7f3a peer linked · α γ ok",
    "▸ scoring 14 entries · payer alignment",
    "▸ flag Rev 0450 ER acuity over-coded",
    "▸ flag 99214 + missing modifier 25",
    "▸ vote: dispute · conf 0.94",
  ],
  gamma: [
    "▸ AXL handshake · 2 peers handshaken",
    "▸ indexing CPT / HCPCS · 14 entries",
    "▸ flag HCPCS J3490 missing NDC",
    "▸ flag 99214 duplicate billing",
    "▸ vote: dispute · conf 0.88",
  ],
};

const FINDINGS = [
  {
    sev: "high" as const,
    code: "CPT 99214",
    desc: "Duplicate office visit billed twice on the same DOS. NCCI flags this combination.",
    amt: "$185.00",
    action: "Dispute",
  },
  {
    sev: "high" as const,
    code: "Modifier 25",
    desc: "Significant E/M with procedure 96372 — modifier 25 missing from the E/M line.",
    amt: "$118.40",
    action: "Dispute",
  },
  {
    sev: "med" as const,
    code: "HCPCS J3490",
    desc: "Unclassified drug code without NDC invoice attached. Insurer typically requires NDC.",
    amt: "$62.20",
    action: "Clarify",
  },
  {
    sev: "med" as const,
    code: "Rev 0450",
    desc: "ER level 5 charge, but documented services align closer to level 3.",
    amt: "$121.60",
    action: "Clarify",
  },
];

const AGENT_META = {
  alpha: { glyph: "α", model: "GPT-4o",  findings: 3, confidence: 0.91, runtime: "1.8s" },
  beta:  { glyph: "β", model: "Claude",  findings: 4, confidence: 0.94, runtime: "2.1s" },
  gamma: { glyph: "γ", model: "Gemini",  findings: 3, confidence: 0.88, runtime: "1.5s" },
} as const;

const DEFAULT_LETTER = `RE: Account LETHE-7F3A2B · DOS 2026-04-14

To Whom It May Concern,

I am formally disputing four line items totaling $487.20 on the referenced statement. Independent review identified a duplicate billing of CPT 99214, a missing modifier 25 on the corresponding E/M line, an unclassified HCPCS J3490 entry without an NDC invoice, and an ER acuity level (Rev 0450) that is not supported by the documented services.

Pursuant to 45 CFR § 149.620 (No Surprises Act, patient-provider dispute resolution) and CMS NCCI policy chapter 7, I request that these charges be reviewed and corrected, and an itemized statement reflecting the corrected balance be issued within 30 days.

This dispute is anchored on 0G Chain at the hash below for reference. Please direct correspondence to the address on file.
`;

const EXPLORER_URL = "https://chainscan-galileo.0g.ai/tx";
const ANCHOR_TX = "0x9f021a8b4c3e5d6f7a8b2c1d0e9f8a7b6c5d4e7c41";

function randomHex(len: number) {
  let s = "";
  for (let i = 0; i < len; i++) s += HEX[Math.floor(Math.random() * 16)];
  return s;
}

function ConvCard({
  variant,
  vote,
  fallbackStream,
}: {
  variant: "alpha" | "beta" | "gamma";
  vote: BackendAgentVote | null;
  fallbackStream: string[];
}) {
  const m = AGENT_META[variant];
  const model = vote?.model ?? m.model;
  const findings = vote?.findings.length ?? m.findings;
  const confidence = vote?.confidence ?? m.confidence;
  const runtime = vote ? `${(vote.duration_ms / 1000).toFixed(1)}s` : m.runtime;
  const verdict = vote?.verdict ?? "dispute";
  const verdictColor =
    verdict === "approve"
      ? "var(--accent-green)"
      : verdict === "clarify"
      ? "var(--accent-amber)"
      : "var(--accent-rose)";

  // When we have a real vote, render the agent's actual notes + per-finding bullets.
  // When we don't (e.g., backend offline or older job), fall back to the canned stream.
  const lines: { text: string; muted?: boolean }[] = vote
    ? [
        ...(vote.notes ? [{ text: `▸ ${vote.notes}` }] : []),
        ...vote.findings.slice(0, 5).map((f) => ({
          text: `▸ ${f.code ?? "?"} — ${f.action ?? "?"} · $${(f.amount_usd ?? 0).toFixed(2)}`,
          muted: false,
        })),
      ]
    : fallbackStream.map((s) => ({ text: s, muted: true }));

  return (
    <div className={`conv-card ${variant}`}>
      <div className="conv-head">
        <span className="conv-glyph">{m.glyph}</span>
        <div className="conv-meta">
          <div className="conv-model">{model}</div>
          <div className="conv-runtime">agent {variant} · {runtime}</div>
        </div>
        <span className="conv-vote" style={{ color: verdictColor }}>
          {verdict}
        </span>
      </div>
      <div className="conv-stats">
        <span>{findings} findings</span>
        <span className="div">·</span>
        <span>conf {confidence.toFixed(2)}</span>
      </div>
      <div className="conv-body">
        {lines.map((l, i) => (
          <div
            key={i}
            className="conv-line"
            style={l.muted ? { opacity: 0.55 } : undefined}
          >
            {l.text}
          </div>
        ))}
      </div>
    </div>
  );
}

function MeshSvg({ active }: { active: number }) {
  // Three nodes positioned in a triangle around a center hash core.
  // active = current pipeline step index (-1 idle, 0..5 progressing)
  const links = [
    { from: "core", to: "alpha", live: active >= 2 },
    { from: "core", to: "beta", live: active >= 2 },
    { from: "core", to: "gamma", live: active >= 2 },
    { from: "alpha", to: "beta", live: active >= 3 },
    { from: "beta", to: "gamma", live: active >= 3 },
    { from: "gamma", to: "alpha", live: active >= 3 },
  ];
  const nodes: Record<
    string,
    { x: number; y: number; label: string; color: string }
  > = {
    core:  { x: 50, y: 50, label: "0",   color: "#ffffff" },
    alpha: { x: 18, y: 22, label: "α",   color: "#a78bfa" },
    beta:  { x: 82, y: 22, label: "β",   color: "#fbbf24" },
    gamma: { x: 50, y: 86, label: "γ",   color: "#22c55e" },
  };
  return (
    <svg className="mesh-svg" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
      {links.map((l, i) => {
        const a = nodes[l.from];
        const b = nodes[l.to];
        return (
          <line
            key={i}
            x1={a.x}
            y1={a.y}
            x2={b.x}
            y2={b.y}
            stroke={l.live ? nodes[l.to].color : "rgba(255,255,255,0.08)"}
            strokeWidth="0.3"
            strokeDasharray={l.live ? "1.5 1.5" : "0.6 0.6"}
            opacity={l.live ? 0.9 : 0.4}
            style={{
              transition: "stroke .3s, opacity .3s",
            }}
          >
            {l.live && (
              <animate
                attributeName="stroke-dashoffset"
                from="0"
                to="-3"
                dur="0.8s"
                repeatCount="indefinite"
              />
            )}
          </line>
        );
      })}
      {Object.entries(nodes).map(([k, n]) => {
        const isCore = k === "core";
        const lit =
          (k === "alpha" && active >= 3) ||
          (k === "beta" && active >= 3) ||
          (k === "gamma" && active >= 3) ||
          (isCore && active >= 0);
        return (
          <g key={k}>
            {lit && (
              <circle
                cx={n.x}
                cy={n.y}
                r={isCore ? 5 : 6}
                fill={n.color}
                opacity="0.15"
              >
                <animate
                  attributeName="r"
                  from={isCore ? 4 : 5}
                  to={isCore ? 8 : 9}
                  dur="1.6s"
                  repeatCount="indefinite"
                />
                <animate
                  attributeName="opacity"
                  from="0.25"
                  to="0"
                  dur="1.6s"
                  repeatCount="indefinite"
                />
              </circle>
            )}
            <circle
              cx={n.x}
              cy={n.y}
              r={isCore ? 3 : 3.6}
              fill={isCore ? "#000" : n.color}
              stroke={n.color}
              strokeWidth="0.4"
              opacity={lit ? 1 : 0.55}
              style={{ transition: "opacity .3s" }}
            />
            <text
              x={n.x}
              y={n.y + 1.4}
              fontSize={isCore ? 2 : 4}
              fontStyle={isCore ? "normal" : "italic"}
              textAnchor="middle"
              fill={isCore ? n.color : "#000"}
              fontWeight={isCore ? 400 : 500}
              style={{ fontFamily: "var(--font-fraunces), serif" }}
            >
              {isCore ? "0G" : n.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function AgentTerminal({
  variant,
  glyph,
  model,
  step,
  live,
  messages,
}: {
  variant: "alpha" | "beta" | "gamma";
  glyph: string;
  model: string;
  step: number;
  live: BackendAgentVote | null;
  messages: string[];
}) {
  // Prefer real backend messages once they start arriving; fall back to canned
  // stream lines so the terminal isn't empty before the agent's first emit.
  const displayLines = messages.length > 0 ? messages : AGENT_STREAMS[variant].slice(0, Math.max(0, step - 2));
  const verdictColor =
    live?.verdict === "approve"
      ? "var(--accent-green)"
      : live?.verdict === "clarify"
      ? "var(--accent-amber)"
      : "var(--accent-rose)";

  return (
    <div className={`terminal-card ${variant}`}>
      <div className="term-head">
        <span>
          agent <b style={{ color: "var(--ink)" }}>{variant}</b>
        </span>
        <span>
          <span className="glyph">{glyph}</span>
          &nbsp;{live?.model ?? model}
        </span>
      </div>
      <div className="term-body">
        {displayLines.map((l, i) => {
          const isAxl = l.startsWith("⇆");
          const isPriors = l.startsWith("⛓");
          const cls = isPriors ? "term-line priors" : isAxl ? "term-line axl" : "term-line";
          return (
            <motion.div
              key={`${i}-${l.slice(0, 12)}`}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.35, ease: "easeOut" }}
              className={cls}
            >
              {l}
            </motion.div>
          );
        })}
        {!live && step >= 3 && (
          <span className="term-cursor">▸</span>
        )}
        {live && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            style={{
              marginTop: "auto",
              paddingTop: 10,
              borderTop: "1px solid var(--line)",
              fontFamily: "var(--font-jetbrains-mono), monospace",
              fontSize: 10.5,
              letterSpacing: "0.18em",
              textTransform: "uppercase",
              color: "var(--ink-faint)",
              display: "flex",
              gap: 10,
              alignItems: "center",
            }}
          >
            <span style={{ color: verdictColor, fontWeight: 500 }}>
              {live.verdict}
            </span>
            <span>· conf {live.confidence.toFixed(2)}</span>
            <span>· {(live.duration_ms / 1000).toFixed(1)}s</span>
          </motion.div>
        )}
      </div>
    </div>
  );
}

const reveal = (delay = 0) => ({
  initial: { opacity: 0, y: 18 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.6, delay, ease: "easeOut" as const },
});

export default function Dashboard() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [step, setStep] = useState(-1);
  const [filename, setFilename] = useState("");
  const [hash, setHash] = useState("0x" + "0".repeat(40));
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [jobId, setJobId] = useState<string | null>(null);
  const [result, setResult] = useState<BackendResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [liveAgents, setLiveAgents] = useState<Record<"alpha" | "beta" | "gamma", BackendAgentVote | null>>({
    alpha: null,
    beta: null,
    gamma: null,
  });
  const [liveMessages, setLiveMessages] = useState<Record<"alpha" | "beta" | "gamma", string[]>>({
    alpha: [],
    beta: [],
    gamma: [],
  });
  const sseRef = useRef<EventSource | null>(null);

  const [letter, setLetter] = useState(DEFAULT_LETTER);
  const [editing, setEditing] = useState(false);
  const [draftLetter, setDraftLetter] = useState("");
  const [hashCopied, setHashCopied] = useState(false);

  // Appeal-to-provider email submission state
  const [providerEmail, setProviderEmail] = useState("");
  const [appealStatus, setAppealStatus] = useState<
    | { phase: "idle" }
    | { phase: "sending" }
    | { phase: "sent"; email: { sent: boolean; provider: string; error?: string | null }; attestation: { live: boolean; tx_hash?: string | null; tx_link?: string | null; executor: string } }
    | { phase: "error"; message: string }
  >({ phase: "idle" });

  const onSendAppeal = useCallback(async () => {
    if (!jobId || !providerEmail.trim()) return;
    setAppealStatus({ phase: "sending" });
    try {
      const r = await fetch(`${API_URL}/api/appeal/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId, recipient_email: providerEmail.trim() }),
      });
      if (!r.ok) {
        const txt = await r.text();
        setAppealStatus({ phase: "error", message: `HTTP ${r.status}: ${txt.slice(0, 160)}` });
        return;
      }
      const data = await r.json();
      setAppealStatus({
        phase: "sent",
        email: data.email,
        attestation: data.attestation,
      });
    } catch (e) {
      setAppealStatus({ phase: "error", message: e instanceof Error ? e.message : String(e) });
    }
  }, [jobId, providerEmail]);

  const onEditStart = useCallback(() => {
    setDraftLetter(letter);
    setEditing(true);
  }, [letter]);

  const onEditSave = useCallback(() => {
    setLetter(draftLetter);
    setEditing(false);
  }, [draftLetter]);

  const onEditCancel = useCallback(() => {
    setEditing(false);
  }, []);

  const onCopyHash = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(hash);
      setHashCopied(true);
      setTimeout(() => setHashCopied(false), 1500);
    } catch {
      /* clipboard API unavailable — silently no-op */
    }
  }, [hash]);

  const onDownloadPdf = useCallback(async () => {
    const { jsPDF } = await import("jspdf");
    const doc = new jsPDF({ unit: "pt", format: "letter" });
    doc.setFont("times", "bold");
    doc.setFontSize(14);
    doc.text("Formal dispute · medical bill review", 72, 72);
    doc.setFont("times", "normal");
    doc.setFontSize(10.5);
    const wrap = doc.splitTextToSize(letter.trim(), 460);
    doc.text(wrap, 72, 110);
    doc.setFontSize(8.5);
    doc.setTextColor(120);
    doc.text(`anchor sha256: ${hash}`, 72, 740);
    doc.text(`network: 0g galileo testnet · executor: keeperhub`, 72, 752);
    doc.text(`audited via lethe · forgotten by design`, 72, 764);
    const safe = (filename || "bill").replace(/[^a-z0-9._-]/gi, "_");
    doc.save(`lethe-dispute-${safe}.pdf`);
  }, [letter, hash, filename]);

  const onDownloadReceipt = useCallback(async () => {
    if (!result) return;
    const c = result.consensus;
    const p = result.proof;
    const oc = p?.onchain;

    // ASCII-only — jsPDF's built-in Courier is a Type 1 font (Latin-1).
    // Unicode box-drawing characters render as garbage; stick to plain ASCII.
    const W = 56;
    const RULE = "-".repeat(W);
    const DOUBLE = "=".repeat(W);
    const center = (s: string) => {
      const pad = Math.max(0, Math.floor((W - s.length) / 2));
      return " ".repeat(pad) + s;
    };
    const row = (k: string, v: string) => {
      const space = Math.max(1, W - k.length - v.length);
      return `${k}${" ".repeat(space)}${v}`;
    };

    // FIGlet "Standard" Lethe — pure ASCII (no Unicode box chars).
    // String.raw to avoid escaping the backslashes in the source.
    const RAW_LOGO = String.raw`
  _          _   _
 | |    ___ | |_| |__   ___
 | |   / _ \| __| '_ \ / _ \
 | |__|  __/| |_| | | |  __/
 |_____\___| \__|_| |_|\___|
`.split("\n").filter((line) => line.length > 0);
    // Center the logo as a block so each row keeps its relative alignment.
    const logoWidth = Math.max(...RAW_LOGO.map((l) => l.length));
    const logoPad = " ".repeat(Math.max(0, Math.floor((W - logoWidth) / 2)));
    const LOGO = RAW_LOGO.map((l) => logoPad + l);

    const verdictLabel = c.verdict === "approve" ? "APPROVED"
                       : c.verdict === "dispute" ? "DISPUTE"
                       : "CLARIFY";

    const now = new Date();
    const stamp = now.toISOString().replace("T", " ").slice(0, 19) + " UTC";

    const lines: string[] = [];
    lines.push(...LOGO);
    lines.push("");
    lines.push(center("medical bills, audited by AI consensus"));
    lines.push(center("forgotten by design"));
    lines.push("");
    lines.push(DOUBLE);
    lines.push(center("AUDIT RECEIPT"));
    lines.push(DOUBLE);
    lines.push("");
    lines.push(row("date issued", stamp));
    lines.push(row("file", result.filename || "-"));
    lines.push("");
    lines.push(RULE);
    lines.push(center(`VERDICT * ${verdictLabel}`));
    lines.push(RULE);
    lines.push(row("agents in agreement", `${c.agree_count} of ${c.total_agents}`));
    lines.push(row("mean confidence",     c.mean_confidence.toFixed(2)));
    lines.push(row("consensus findings",  String(c.findings.length)));
    lines.push(row("flagged total",       `$${c.flagged_total_usd.toFixed(2)}`));
    lines.push(row("disputed total",      `$${c.disputed_total_usd.toFixed(2)}`));
    if (c.aligned_total_usd) {
      lines.push(row("aligned total",     `$${c.aligned_total_usd.toFixed(2)}`));
    }
    lines.push("");

    if (c.findings.length > 0) {
      lines.push(RULE);
      lines.push(center("LINE ITEMS"));
      lines.push(RULE);
      for (const f of c.findings) {
        const sev = (f.severity ?? "info").toUpperCase().padEnd(6).slice(0, 6);
        const code = String(f.code ?? "?").padEnd(16, " ").slice(0, 16);
        const action = (f.action ?? "").padEnd(8).slice(0, 8);
        const amt = `$${(f.amount_usd ?? 0).toFixed(2)}`.padStart(10, " ");
        lines.push(`${sev} ${code} ${action} ${amt}`);
        if (f.description) {
          const desc = f.description.replace(/\s+/g, " ").replace(/[^\x20-\x7E]/g, " ").trim();
          let i = 0;
          while (i < desc.length) {
            let take = Math.min(W - 2, desc.length - i);
            if (i + take < desc.length) {
              const space = desc.lastIndexOf(" ", i + take);
              if (space > i) take = space - i;
            }
            lines.push(`  ${desc.slice(i, i + take).trim()}`);
            i += take + (desc[i + take] === " " ? 1 : 0);
          }
        }
      }
      lines.push("");
    }

    lines.push(RULE);
    lines.push(center("ON-CHAIN ANCHOR"));
    lines.push(RULE);
    lines.push(row("network", p?.network ?? "-"));
    if (p?.chain_id) lines.push(row("chain id", String(p.chain_id)));
    if (p?.registry_address) {
      // address is 42 chars — split if too long for one line
      lines.push("registry");
      lines.push(`  ${p.registry_address}`);
    }
    if (p?.anchor_tx) {
      lines.push("tx hash");
      lines.push(`  ${p.anchor_tx}`);
      const tx = p.anchor_tx.startsWith("0x") ? p.anchor_tx : `0x${p.anchor_tx}`;
      lines.push("verify on chainscan:");
      lines.push(`  https://chainscan-galileo.0g.ai/tx/${tx}`);
    }
    if (p?.block_number != null) lines.push(row("block", `#${p.block_number}`));
    if (oc) {
      const ts = new Date(oc.anchored_at * 1000).toISOString().replace("T", " ").slice(0, 19) + " UTC";
      lines.push(row("anchored at", ts));
      lines.push("anchored by");
      lines.push(`  ${oc.anchored_by}`);
      lines.push(row("on-chain vote", `${oc.verdict} ${oc.agree_count}/${oc.total_agents}`));
    }
    lines.push("");

    if (p?.patterns?.live) {
      lines.push(RULE);
      lines.push(center("PATTERN INDEX (0G)"));
      lines.push(RULE);
      lines.push(row("patterns indexed", String(p.patterns.patterns_indexed)));
      if (p.patterns.registry_address) {
        lines.push("registry");
        lines.push(`  ${p.patterns.registry_address}`);
      }
      if (p.patterns.tx) {
        lines.push("index tx");
        lines.push(`  ${p.patterns.tx}`);
        const tx = p.patterns.tx.startsWith("0x") ? p.patterns.tx : `0x${p.patterns.tx}`;
        lines.push("verify on chainscan:");
        lines.push(`  https://chainscan-galileo.0g.ai/tx/${tx}`);
      }
      if (p.patterns.block_number != null) lines.push(row("block", `#${p.patterns.block_number}`));
      lines.push("");
    }

    const st = p?.patterns?.storage;
    if (st?.live && st.root_hash) {
      lines.push(RULE);
      lines.push(center("0G STORAGE (anonymized record)"));
      lines.push(RULE);
      lines.push(row("executor", st.executor));
      if (st.schema) lines.push(row("schema", st.schema));
      if (typeof st.bytes === "number") lines.push(row("bytes", String(st.bytes)));
      lines.push("merkle root");
      lines.push(`  ${st.root_hash}`);
      if (st.tx_hash) {
        lines.push("commitment tx");
        lines.push(`  ${st.tx_hash}`);
      }
      if (st.tx_link) {
        lines.push("verify on chainscan:");
        lines.push(`  ${st.tx_link}`);
      }
      lines.push("");
    }

    if (p?.mirror?.live) {
      const isDup = p.mirror.status === "duplicate";
      lines.push(RULE);
      lines.push(center(isDup ? "SEPOLIA MIRROR (already anchored)" : "SEPOLIA MIRROR (KeeperHub)"));
      lines.push(RULE);
      lines.push(row("network", `${p.mirror.network} (${p.mirror.chain_id ?? "?"})`));
      lines.push(row("executor", p.mirror.executor));
      lines.push(row("status", p.mirror.status ?? "?"));
      if (p.mirror.registry_address) {
        lines.push("registry");
        lines.push(`  ${p.mirror.registry_address}`);
      }
      if (p.mirror.tx_hash) {
        lines.push(isDup ? "original mirror tx" : "mirror tx");
        lines.push(`  ${p.mirror.tx_hash}`);
        lines.push("verify on etherscan:");
        const tx = p.mirror.tx_hash.startsWith("0x") ? p.mirror.tx_hash : `0x${p.mirror.tx_hash}`;
        lines.push(`  https://sepolia.etherscan.io/tx/${tx}`);
      } else if (isDup && p.mirror.registry_address) {
        lines.push("verify via registry events:");
        lines.push(`  https://sepolia.etherscan.io/address/${p.mirror.registry_address}#events`);
      }
      if (p.mirror.note) {
        lines.push(`  (${p.mirror.note})`);
      }
      if (p.mirror.execution_id) lines.push(row("kh exec id", p.mirror.execution_id));
      lines.push("");
    }

    const df = p?.dispute_filing;
    if (df?.live && df.tx_hash) {
      lines.push(RULE);
      lines.push(center("DISPUTE FILED (KeeperHub workflow #2)"));
      lines.push(RULE);
      lines.push(row("executor", df.executor));
      lines.push(row("status", df.status ?? "?"));
      if (df.network) lines.push(row("network", `${df.network} (${df.chain_id ?? "?"})`));
      if (df.function_name) lines.push(row("function", df.function_name));
      if (df.registry_address) {
        lines.push("dispute registry");
        lines.push(`  ${df.registry_address}`);
      }
      lines.push("filing tx");
      lines.push(`  ${df.tx_hash}`);
      if (df.tx_link) {
        lines.push("verify on etherscan:");
        lines.push(`  ${df.tx_link}`);
      }
      if (df.execution_id) lines.push(row("kh exec id", df.execution_id));
      lines.push("");
    }

    lines.push(RULE);
    lines.push(center("VERIFY ANY TIME"));
    lines.push(RULE);
    lines.push("re-hash this bill (sha256) and call:");
    lines.push("  BillRegistry.anchors(<hash>)");
    lines.push(`  on ${p?.network ?? "0g-galileo-testnet"}${p?.chain_id ? ` (${p.chain_id})` : ""}`);
    lines.push("");
    lines.push("or open in any browser:");
    const origin = typeof window !== "undefined" ? window.location.origin : "";
    lines.push(`  ${origin}/verify?sha=${hash}`);
    lines.push("");
    lines.push(RULE);
    lines.push(center("BILL HASH (sha-256)"));
    lines.push(RULE);
    const h = hash.startsWith("0x") ? hash.slice(2) : hash;
    lines.push(`  ${h.slice(0, 32)}`);
    lines.push(`  ${h.slice(32)}`);
    lines.push("");
    lines.push(DOUBLE);
    lines.push(center("forgotten by design"));
    lines.push(center(origin || "lethe"));
    lines.push(DOUBLE);

    // Render to PDF with jsPDF in monospace
    const { jsPDF } = await import("jspdf");
    // Narrow page (~4.5" × dynamic) — receipt-tape vibe
    const PT_PER_IN = 72;
    const pageW = 4.5 * PT_PER_IN;
    const margin = 18;
    const fontSize = 8;
    const lineHeight = fontSize * 1.2;
    const pageH = margin * 2 + lines.length * lineHeight + 40;

    const doc = new jsPDF({ unit: "pt", format: [pageW, pageH] });
    doc.setFont("courier", "normal");
    doc.setFontSize(fontSize);

    let y = margin + fontSize;
    for (const line of lines) {
      doc.text(line, margin, y);
      y += lineHeight;
    }

    const safe = (filename || "bill").replace(/[^a-z0-9._-]/gi, "_");
    doc.save(`lethe-receipt-${safe}-${hash.slice(2, 10)}.pdf`);
  }, [result, hash, filename]);

  // morphing hash during processing (visual flair only)
  useEffect(() => {
    if (phase !== "processing") return;
    const id = window.setInterval(() => {
      setHash("0x" + randomHex(40));
    }, 60);
    return () => window.clearInterval(id);
  }, [phase]);

  // Subscribe to the backend's SSE stream once we have a job_id and are processing.
  useEffect(() => {
    if (phase !== "processing" || !jobId) return;

    const sse = new EventSource(`${API_URL}/api/jobs/${jobId}/stream`);
    sseRef.current = sse;

    const onStepCompleted = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        const idx = PIPELINE.findIndex((p) => p.id === data.step);
        if (idx >= 0) setStep(idx);
      } catch {}
    };
    const onAgentMessage = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        const name = data.agent as "alpha" | "beta" | "gamma";
        const line = String(data.line ?? "");
        if ((name === "alpha" || name === "beta" || name === "gamma") && line) {
          setLiveMessages((prev) => ({ ...prev, [name]: [...prev[name], line] }));
        }
      } catch {}
    };
    // Real AXL P2P chatter: surface each sidecar broadcast (sender's view)
    // and each /recv read (recipient's view). The sender event is emitted
    // when the agent broadcasts its OWN findings; the recipient event is
    // emitted when that agent's sidecar inbox actually delivers them.
    const GLYPH = { alpha: "α", beta: "β", gamma: "γ" } as const;

    const onAxlFindingsSent = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        const sender = data.agent as "alpha" | "beta" | "gamma";
        const recipients = (data.delivered_to as string[]) ?? [];
        const fcount = Number(data.finding_count ?? 0);
        const bytes = Number(data.payload_bytes ?? 0);
        const peerId = String(data.from_peer_id ?? "");
        const peerShort = peerId ? peerId.slice(0, 8) : "?";
        if (!(sender in GLYPH)) return;
        const recipGlyphs = recipients
          .filter((r): r is "alpha" | "beta" | "gamma" => r in GLYPH)
          .map((r) => GLYPH[r as "alpha" | "beta" | "gamma"])
          .join(" ");
        const senderLine = `⇆ axl · broadcasting ${fcount} findings (${bytes}B) → ${recipGlyphs} · ed25519:${peerShort}`;
        setLiveMessages((prev) => ({
          ...prev,
          [sender]: [...prev[sender], senderLine],
        }));
      } catch {}
    };

    const onAxlFindingsReceived = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        const recipient = data.agent as "alpha" | "beta" | "gamma";
        const fromAgent = data.from_agent as "alpha" | "beta" | "gamma";
        const fcount = Number(data.finding_count ?? 0);
        const verdict = String(data.verdict ?? "");
        const peerId = String(data.from_peer_id ?? "");
        const peerShort = peerId ? peerId.slice(0, 8) : "?";
        if (!(recipient in GLYPH) || !(fromAgent in GLYPH)) return;
        const line = `⇆ axl · received ${fcount} findings · verdict=${verdict} · from ${GLYPH[fromAgent]} · ed25519:${peerShort}`;
        setLiveMessages((prev) => ({
          ...prev,
          [recipient]: [...prev[recipient], line],
        }));
      } catch {}
    };

    // Round-2 reflection: each agent revisits its vote after seeing peer findings.
    // Emit a styled banner showing what changed.
    const onAgentReflectStarted = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        const name = data.agent as "alpha" | "beta" | "gamma";
        const ftotal = Number(data.peer_finding_total ?? 0);
        if (!(name in GLYPH)) return;
        const line = `⇆ reflecting on ${ftotal} peer findings · round 2 begins`;
        setLiveMessages((prev) => ({
          ...prev,
          [name]: [...prev[name], line],
        }));
      } catch {}
    };

    // The on-chain pattern read-back: agents pull prior dispute/clarify rates
    // from the 0G Galileo PatternRegistry before reasoning. Show this happening
    // in all three terminals — the priors are shared, but each agent sees them.
    const onPatternsPriorLoaded = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        const codeCount = Number(data.code_count ?? 0);
        const totalObs = Number(data.total_observations ?? 0);
        const regShort = String(data.registry_short ?? "");
        const top = (data.top_codes as Array<{
          code: string;
          n_observations: number;
          dispute_rate: number;
        }>) ?? [];
        const headerLine = `⛓ priors loaded · ${codeCount} codes · ${totalObs} obs · 0G PatternRegistry${regShort ? ` ${regShort}` : ""}`;
        const topLine = top.length
          ? `⛓ top: ${top
              .map((t) => `${t.code} (n=${t.n_observations}, ${Math.round(t.dispute_rate * 100)}% dispute)`)
              .join(" · ")}`
          : "";
        setLiveMessages((prev) => {
          const next = { ...prev };
          (["alpha", "beta", "gamma"] as const).forEach((k) => {
            const additions = topLine ? [headerLine, topLine] : [headerLine];
            next[k] = [...next[k], ...additions];
          });
          return next;
        });
      } catch {}
    };

    const onAgentRevised = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        const name = data.agent as "alpha" | "beta" | "gamma";
        const r1v = String(data.round1_verdict ?? "");
        const r2v = String(data.round2_verdict ?? "");
        const r1f = Number(data.round1_finding_count ?? 0);
        const r2f = Number(data.round2_finding_count ?? 0);
        const r2c = Number(data.round2_confidence ?? 0);
        const r2dur = Number(data.round2_duration_ms ?? data.duration_ms ?? 0);
        const changed = Boolean(data.verdict_changed);
        if (!(name in GLYPH)) return;
        const verdictDisplay = changed ? `${r1v} → ${r2v}` : `${r2v} (held)`;
        const line = `⇆ revised · verdict ${verdictDisplay} · findings ${r1f}→${r2f} · conf ${r2c.toFixed(2)}`;
        setLiveMessages((prev) => ({
          ...prev,
          [name]: [...prev[name], line],
        }));
        // The agent card's vote + confidence chip reflects round-2 once it
        // arrives — otherwise it'd freeze at the round-1 vote and look stale
        // even after the agent revised based on peer findings.
        setLiveAgents((prev) => {
          const cur = prev[name];
          return {
            ...prev,
            [name]: {
              agent: name,
              model: cur?.model ?? "",
              verdict: r2v || cur?.verdict || "",
              confidence: r2c || cur?.confidence || 0,
              findings: cur?.findings ?? [],
              notes: cur?.notes ?? "",
              duration_ms: r2dur || cur?.duration_ms || 0,
            },
          };
        });
      } catch {}
    };
    const onAgentCompleted = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        const name = data.agent as "alpha" | "beta" | "gamma";
        if (name === "alpha" || name === "beta" || name === "gamma") {
          setLiveAgents((prev) => ({
            ...prev,
            [name]: {
              agent: name,
              model: data.model ?? "",
              verdict: data.verdict ?? "",
              confidence: Number(data.confidence ?? 0),
              findings: [],
              notes: "",
              duration_ms: Number(data.duration_ms ?? 0),
            },
          }));
        }
      } catch {}
    };
    const onDone = async () => {
      try {
        const r = await fetch(`${API_URL}/api/jobs/${jobId}`);
        if (r.ok) {
          const body = await r.json();
          if (body.result) {
            setResult(body.result as BackendResult);
            setHash("0x" + (body.sha256 || body.result.sha256));
            // Seed the letter with the real drafted body if present.
            if (body.result.dispute?.body) {
              setLetter(body.result.dispute.body);
            }
            setPhase("complete");
          } else {
            setErrorMsg("done event received but no result body");
          }
        } else {
          setErrorMsg(`fetch result failed: ${r.status}`);
        }
      } catch (err) {
        setErrorMsg(`fetch result failed: ${(err as Error).message}`);
      }
      sse.close();
    };
    const onErr = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        setErrorMsg(`pipeline error: ${data.error ?? "unknown"}`);
      } catch {
        setErrorMsg("pipeline error");
      }
      sse.close();
    };

    sse.addEventListener("step.completed", onStepCompleted as EventListener);
    sse.addEventListener("agent.message", onAgentMessage as EventListener);
    sse.addEventListener("axl.findings_sent", onAxlFindingsSent as EventListener);
    sse.addEventListener("axl.findings_received", onAxlFindingsReceived as EventListener);
    sse.addEventListener("patterns.prior_loaded", onPatternsPriorLoaded as EventListener);
    sse.addEventListener("agent.reflect_started", onAgentReflectStarted as EventListener);
    sse.addEventListener("agent.revised", onAgentRevised as EventListener);
    sse.addEventListener("agent.completed", onAgentCompleted as EventListener);
    sse.addEventListener("done", onDone as EventListener);
    sse.addEventListener("error", onErr as EventListener);
    sse.onerror = () => {
      // Browser-level SSE error (network drop, CORS, etc.). Don't immediately
      // bail — the backend's `done` event closes the stream cleanly.
      if (sse.readyState === EventSource.CLOSED) {
        // already handled
      }
    };

    return () => {
      sse.close();
      sseRef.current = null;
    };
  }, [phase, jobId]);

  const reset = useCallback(() => {
    sseRef.current?.close();
    sseRef.current = null;
    setPhase("idle");
    setStep(-1);
    setFilename("");
    setHash("0x" + "0".repeat(40));
    setJobId(null);
    setResult(null);
    setErrorMsg(null);
    setLiveAgents({ alpha: null, beta: null, gamma: null });
    setLiveMessages({ alpha: [], beta: [], gamma: [] });
    setLetter(DEFAULT_LETTER);
    setEditing(false);
  }, []);

  const startUpload = useCallback(async (file: File) => {
    setFilename(file.name);
    setStep(-1);
    setHash("0x" + "0".repeat(40));
    setResult(null);
    setErrorMsg(null);
    setLiveAgents({ alpha: null, beta: null, gamma: null });
    setLiveMessages({ alpha: [], beta: [], gamma: [] });
    setPhase("processing");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await fetch(`${API_URL}/api/jobs`, { method: "POST", body: fd });
      if (!r.ok) {
        const txt = await r.text().catch(() => "");
        throw new Error(`${r.status} ${txt}`.slice(0, 200));
      }
      const body = await r.json();
      setJobId(body.job_id);
    } catch (err) {
      setErrorMsg((err as Error).message);
    }
  }, []);

  const startSample = useCallback(async (name: string, ext: string) => {
    setFilename(`${name}.${ext}`);
    setStep(-1);
    setHash("0x" + "0".repeat(40));
    setResult(null);
    setErrorMsg(null);
    setLiveAgents({ alpha: null, beta: null, gamma: null });
    setLiveMessages({ alpha: [], beta: [], gamma: [] });
    setPhase("processing");
    try {
      const r = await fetch(`${API_URL}/api/samples/${name}/run`, { method: "POST" });
      if (!r.ok) {
        const txt = await r.text().catch(() => "");
        throw new Error(`${r.status} ${txt}`.slice(0, 200));
      }
      const body = await r.json();
      setJobId(body.job_id);
    } catch (err) {
      setErrorMsg((err as Error).message);
    }
  }, []);

  const onFile = useCallback(
    (file: File | null) => {
      if (!file) return;
      const ok = /\.(pdf|txt|png|jpg|jpeg|webp)$/i.test(file.name);
      if (!ok) return;
      void startUpload(file);
    },
    [startUpload]
  );

  const onDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragging(false);
      const f = e.dataTransfer?.files?.[0];
      if (f) onFile(f);
    },
    [onFile]
  );

  const progress = useMemo(() => {
    if (phase === "idle") return 0;
    if (phase === "complete") return 100;
    return ((step + 1) / PIPELINE.length) * 100;
  }, [phase, step]);

  return (
    <>
      <NavBar
        subBrand="dashboard"
        cta={
          phase === "idle" ? (
            <Link className="cta" href="/">
              ← Back to home
            </Link>
          ) : (
            <button className="cta" onClick={reset}>
              ⤺ New analysis
            </button>
          )
        }
      />

      <div className="dash-page">
        <AnimatePresence mode="wait">
          {phase === "idle" && (
            <motion.div
              key="idle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.4 }}
            >
              <section className="dash-hero">
                <motion.div className="dash-eyebrow" {...reveal(0)}>
                  <span className="pulse-dot" />
                  <span className="pill">coordinator · live</span>
                  <span>zero retention</span>
                  <span>·</span>
                  <span>3 / 3 agents online</span>
                </motion.div>

                <motion.h1 className="dash-headline" {...reveal(0.05)}>
                  Drop a bill.<br />
                  <em>We&apos;ll do the rest.</em>
                </motion.h1>

                <motion.p className="dash-sub" {...reveal(0.15)}>
                  Three independent AI agents reach consensus over a peer-to-peer
                  mesh. Your file lives in coordinator memory long enough for the
                  pipeline to run, then it&apos;s gone.
                </motion.p>

                <motion.div
                  className={`upload-stage${dragging ? " dragging" : ""}`}
                  {...reveal(0.25)}
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragging(true);
                  }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={onDrop}
                >
                  <div className="up-glyph">+</div>
                  <div className="up-h">Drop a file or click to choose</div>
                  <div className="up-p">
                    Parsed and redacted locally before any agent sees it. Original is never written to disk.
                  </div>
                  <div className="upload-types">
                    <span>pdf</span>
                    <span>txt</span>
                    <span>png</span>
                    <span>jpg</span>
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.txt,.png,.jpg,.jpeg,.webp"
                    style={{ display: "none" }}
                    onChange={(e: ChangeEvent<HTMLInputElement>) =>
                      onFile(e.target.files?.[0] ?? null)
                    }
                  />
                </motion.div>

                <motion.div className="sample-row" {...reveal(0.35)}>
                  <span className="sample-label">— or try a sample —</span>
                  <div className="sample-chips">
                    {SAMPLE_BILLS.map((s) => (
                      <button
                        key={s.name}
                        className="sample-chip"
                        onClick={() => startSample(s.name, s.ext)}
                      >
                        {s.name}
                        <span className="ext">{s.ext}</span>
                      </button>
                    ))}
                  </div>
                </motion.div>

                <motion.div className="privacy-line" {...reveal(0.45)}>
                  <span><b>ttl</b> 30s</span>
                  <span className="div">·</span>
                  <span><b>3</b> independent llms</span>
                  <span className="div">·</span>
                  <span>axl <b>p2p</b> consensus</span>
                  <span className="div">·</span>
                  <span>anchored on <b>0g</b></span>
                </motion.div>
              </section>
            </motion.div>
          )}

          {phase === "processing" && (
            <motion.div
              key="proc"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.4 }}
            >
              <div className="proc-status">
                <div className="grp">
                  <span className="live-dot" />
                  pipeline <b>{errorMsg ? "failed" : "running"}</b>
                </div>
                <div className="grp">
                  file <b>{filename || "—"}</b>
                </div>
                <div className="grp">
                  job <b>{jobId ? jobId.slice(0, 8) : "—"}</b>
                </div>
                <div className="grp">
                  step <b>{Math.max(0, step + 1)} / {PIPELINE.length}</b>
                </div>
                <div className="grp">
                  current <b style={{ color: "var(--accent-violet)" }}>
                    {step >= 0 ? PIPELINE[Math.min(step, PIPELINE.length - 1)].name : "—"}
                  </b>
                </div>
                <div className="progbar">
                  <span>progress</span>
                  <div className="bar">
                    <span style={{ width: `${progress}%` }} />
                  </div>
                  <b>{Math.round(progress)}%</b>
                </div>
              </div>
              {errorMsg && (
                <div
                  style={{
                    margin: "16px 40px 0",
                    padding: "14px 18px",
                    border: "1px solid var(--accent-rose)",
                    borderRadius: 6,
                    background: "rgba(248,113,113,0.06)",
                    color: "var(--accent-rose)",
                    fontFamily: "var(--font-jetbrains-mono), monospace",
                    fontSize: 12,
                    letterSpacing: "0.05em",
                  }}
                >
                  ⚠ {errorMsg}
                  <button
                    className="btn-sm"
                    onClick={reset}
                    style={{ marginLeft: 16 }}
                  >
                    Reset
                  </button>
                </div>
              )}

              <div className="proc-shell">
                <motion.div className="hash-stage" {...reveal(0)}>
                  <span className="hash-label">
                    <span className="hash-pulse" />
                    computing sha-256 · zero-retention proof
                  </span>
                  <span className="hash-text">{hash}</span>
                  <div className="hash-progress">
                    <div
                      className="hash-progress-bar"
                      style={{
                        width: `${Math.min(100, Math.round((step / Math.max(1, PIPELINE.length - 1)) * 100))}%`,
                      }}
                    />
                  </div>
                  <div className="hash-status">
                    <span className="hash-stage-name">
                      {step < PIPELINE.length
                        ? `stage ${String(step + 1).padStart(2, "0")} / ${PIPELINE.length} · ${PIPELINE[step]?.name ?? ""}`
                        : "finalizing"}
                    </span>
                    <span className="hash-eta">analysis can take up to 3 minutes</span>
                  </div>
                  <div className="hash-meta">
                    <span>network <b>0g galileo</b></span>
                    <span>executor <b>keeperhub</b></span>
                    <span>peers <b>α · β · γ</b></span>
                  </div>
                </motion.div>

                <div className="proc-grid">
                  <motion.div className="pipeline-rail" {...reveal(0.1)}>
                    {PIPELINE.map((p, i) => {
                      const state =
                        i < step ? "done" : i === step ? "active" : "pending";
                      return (
                        <div key={p.id} className={`pl-step ${state}`}>
                          <span className="pl-num">{String(i + 1).padStart(2, "0")}</span>
                          <div className="pl-body">
                            <span className="pl-name">{p.name}</span>
                            <span className="pl-detail">{p.detail}</span>
                          </div>
                          <span className="pl-state">
                            {state === "done"
                              ? "done"
                              : state === "active"
                              ? "running"
                              : "queued"}
                          </span>
                        </div>
                      );
                    })}
                  </motion.div>

                  <div className="proc-right">
                    <motion.div className="mesh-stage" {...reveal(0.15)}>
                      <div className="mesh-label">axl mesh · live peer graph</div>
                      <MeshSvg active={step} />
                    </motion.div>

                    <motion.div className="terminal-stack" {...reveal(0.2)}>
                      <AgentTerminal
                        variant="alpha"
                        glyph="α"
                        model="gpt-4o"
                        step={step}
                        live={liveAgents.alpha}
                        messages={liveMessages.alpha}
                      />
                      <AgentTerminal
                        variant="beta"
                        glyph="β"
                        model="claude"
                        step={step}
                        live={liveAgents.beta}
                        messages={liveMessages.beta}
                      />
                      <AgentTerminal
                        variant="gamma"
                        glyph="γ"
                        model="gemini"
                        step={step}
                        live={liveAgents.gamma}
                        messages={liveMessages.gamma}
                      />
                    </motion.div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {phase === "complete" && (
            <motion.div
              key="done"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5 }}
            >
              <section className="verdict-hero">
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5 }}
                  className="verdict-eyebrow"
                  style={{
                    color:
                      result?.consensus.verdict === "approve"
                        ? "var(--accent-green)"
                        : result?.consensus.verdict === "clarify"
                        ? "var(--accent-amber)"
                        : result?.consensus.verdict === "dispute"
                        ? "var(--accent-rose)"
                        : "var(--ink-faint)",
                  }}
                >
                  consensus reached · {result?.consensus.agree_count ?? "—"} / {result?.consensus.total_agents ?? "—"} · {result?.consensus.verdict ?? "—"}
                </motion.div>
                <motion.h1
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.7, delay: 0.05 }}
                  className="verdict-title"
                >
                  {(() => {
                    const v = result?.consensus.verdict;
                    if (v === "approve") {
                      return <>Bill <em>approved.</em></>;
                    }
                    if (v === "clarify") {
                      return <>Clarify <em>${(result?.consensus.flagged_total_usd ?? 0).toFixed(2)}</em></>;
                    }
                    if (v === "dispute") {
                      return <>Dispute <em>${(result?.consensus.flagged_total_usd ?? 0).toFixed(2)}</em></>;
                    }
                    return <>—</>;
                  })()}
                </motion.h1>
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.5, delay: 0.15 }}
                  className="verdict-sub"
                >
                  {(() => {
                    const v = result?.consensus.verdict;
                    const agree = result?.consensus.agree_count ?? 0;
                    const total = result?.consensus.total_agents ?? 0;
                    const aligned = result?.consensus.aligned_count ?? 0;
                    const actionable = result?.consensus.actionable_count ?? 0;
                    if (v === "approve") {
                      return `${agree} of ${total} agents reviewed the bill and found no actionable disputes${
                        aligned ? ` (${aligned} line${aligned > 1 ? "s" : ""} confirmed aligned).` : "."
                      } No appeal letter needed.`;
                    }
                    if (v === "clarify") {
                      return `${agree} of ${total} agents recommend clarification before disputing. ${actionable} item${actionable === 1 ? "" : "s"} to follow up on.`;
                    }
                    if (v === "dispute") {
                      return `${agree} of ${total} agents flagged charges as billing errors. Findings are below; a draft appeal letter is ready for your review.`;
                    }
                    return "";
                  })()}
                </motion.p>
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.5, delay: 0.25 }}
                  className="verdict-hash"
                >
                  <span style={{ color: "var(--accent-green)" }}>●</span>
                  anchored <b>{hash.slice(0, 10)}…{hash.slice(-6)}</b>
                  <span style={{ color: "var(--ink-faint)" }}>· 0g chain</span>
                </motion.div>
              </section>

              <motion.div
                className="verdict-stats"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5, delay: 0.35 }}
              >
                <div className="verdict-stat">
                  <span className="stat-num"><em>{result?.consensus.agree_count ?? "—"} / {result?.consensus.total_agents ?? "—"}</em></span>
                  <span className="stat-label">Agent vote</span>
                </div>
                <div className="verdict-stat">
                  <span className="stat-num">{result?.consensus.findings.length ?? 0}</span>
                  <span className="stat-label">Findings</span>
                </div>
                <div className="verdict-stat">
                  <span className="stat-num">{(result?.consensus.mean_confidence ?? 0).toFixed(2)}</span>
                  <span className="stat-label">Mean confidence</span>
                </div>
                <div className="verdict-stat">
                  <span className="stat-num">{result ? (result.total_runtime_ms / 1000).toFixed(1) + "s" : "—"}</span>
                  <span className="stat-label">Total runtime</span>
                </div>
              </motion.div>

              <div className="results-shell">
                <motion.section
                  className="results-section"
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: 0.4 }}
                >
                  <div className="section-head">
                    <span className="section-num">[ findings ]</span>
                    <h2 className="section-title">
                      What the agents <span className="em">flagged.</span>
                    </h2>
                    <p className="section-kicker">
                      Each line is traceable to the agents that voted for it and the regulatory citation behind it.
                    </p>
                  </div>
                  <div className="findings">
                    <div className="findings-head">
                      <span>Severity</span>
                      <span>Code</span>
                      <span>Description</span>
                      <span style={{ textAlign: "right" }}>Amount</span>
                      <span style={{ textAlign: "right" }}>Action</span>
                    </div>
                    {(result?.consensus.findings ?? []).map((f, i) => {
                      const sev = (f.severity ?? "info").toLowerCase();
                      const sevClass = sev === "high" ? "high" : sev === "medium" || sev === "med" ? "med" : "info";
                      const sevLabel = sev === "high" ? "High" : sev === "medium" || sev === "med" ? "Medium" : "Info";
                      return (
                        <motion.div
                          key={i}
                          initial={{ opacity: 0, y: 8 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ duration: 0.4, delay: 0.5 + i * 0.07 }}
                          className="finding-row"
                        >
                          <span className={`sev ${sevClass}`}>{sevLabel}</span>
                          <span className="code">{f.code ?? "—"}</span>
                          <span className="desc">{f.description ?? ""}</span>
                          <span className="amt">${(f.amount_usd ?? 0).toFixed(2)}</span>
                          <span className="action">{f.action ?? ""}</span>
                        </motion.div>
                      );
                    })}
                    {(result?.consensus.findings.length ?? 0) === 0 && (
                      <div className="finding-row">
                        <span className="sev info">—</span>
                        <span className="code">—</span>
                        <span className="desc" style={{ color: "var(--ink-faint)" }}>
                          No findings reached the 2/3 quorum.
                        </span>
                        <span className="amt">$0.00</span>
                        <span className="action">—</span>
                      </div>
                    )}
                  </div>
                </motion.section>

                <motion.section
                  className="results-section"
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: 0.55 }}
                >
                  <div className="section-head">
                    <span className="section-num">[ reasoning ]</span>
                    <h2 className="section-title">
                      How the agents <span className="em">talked it out.</span>
                    </h2>
                    <p className="section-kicker">
                      Three model providers, three independent log streams. Each agent reasoned over the redacted payload and posted its trace to the AXL mesh.
                    </p>
                  </div>
                  <div className="conv-row">
                    <ConvCard
                      variant="alpha"
                      vote={result?.consensus.agents.find(a => a.agent === "alpha") ?? null}
                      fallbackStream={AGENT_STREAMS.alpha}
                    />
                    <ConvCard
                      variant="beta"
                      vote={result?.consensus.agents.find(a => a.agent === "beta") ?? null}
                      fallbackStream={AGENT_STREAMS.beta}
                    />
                    <ConvCard
                      variant="gamma"
                      vote={result?.consensus.agents.find(a => a.agent === "gamma") ?? null}
                      fallbackStream={AGENT_STREAMS.gamma}
                    />
                  </div>
                </motion.section>

                <motion.section
                  className="results-section"
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: 0.7 }}
                >
                  <div className="dash-bottom">
                    {result?.consensus.verdict === "approve" ? (
                      <div className="dispute-card">
                        <div className="panel-label">
                          No dispute needed
                        </div>
                        <div className="dispute-letter">
                          <p>
                            <b>{result.consensus.agree_count} of {result.consensus.total_agents} agents reviewed this bill and found no actionable disputes.</b>
                          </p>
                          {result.consensus.aligned_count ? (
                            <p>
                              {result.consensus.aligned_count} line {result.consensus.aligned_count === 1 ? "item was" : "items were"} explicitly confirmed as correctly billed (${(result.consensus.aligned_total_usd ?? 0).toFixed(2)} aligned).
                            </p>
                          ) : null}
                          <p style={{ color: "var(--ink-faint)" }}>
                            The bill hash is anchored on 0G Chain for your records — useful as a receipt that you had the bill audited, even though no appeal letter was generated.
                          </p>
                        </div>
                        <div className="dispute-actions">
                          <button className="btn-sm solid" onClick={onDownloadReceipt}>
                            Download receipt
                          </button>
                          <button className="btn-sm" onClick={reset}>
                            Run another bill →
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="dispute-card">
                        <div className="panel-label">
                          Drafted dispute · review &amp; approve
                          {editing && <span className="panel-tag">editing</span>}
                        </div>
                        {editing ? (
                          <textarea
                            className="dispute-editor"
                            value={draftLetter}
                            onChange={(e) => setDraftLetter(e.target.value)}
                            spellCheck={false}
                          />
                        ) : (
                          <div className="dispute-letter">
                            {letter
                              .trim()
                              .split(/\n\s*\n/)
                              .map((para, i) => (
                                <p key={i}>{para}</p>
                              ))}
                          </div>
                        )}
                        <div className="dispute-actions">
                          {editing ? (
                            <>
                              <button className="btn-sm solid" onClick={onEditSave}>
                                Save changes
                              </button>
                              <button className="btn-sm" onClick={onEditCancel}>
                                Cancel
                              </button>
                            </>
                          ) : (
                            <>
                              <button className="btn-sm" onClick={onEditStart}>
                                Edit draft
                              </button>
                              <button className="btn-sm" onClick={onDownloadPdf}>
                                Download PDF
                              </button>
                              <button className="btn-sm" onClick={onDownloadReceipt}>
                                Download receipt
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    )}

                    <div className="proof-card">
                      <div className="panel-label">On-chain proof</div>
                      <div className="proof-row">
                        <span className="k">Bill hash</span>
                        <span className="v">
                          <Link
                            href={`/verify?sha=${hash}`}
                            target="_blank"
                            style={{ color: "var(--ink)", borderBottom: "1px dotted var(--ink-faint)" }}
                            title="Open the public verify page for this hash"
                          >
                            {hash.slice(0, 10)} {hash.slice(10, 14)} {hash.slice(14, 18)} … {hash.slice(-6)}
                          </Link>
                        </span>
                      </div>
                      <div className="proof-row">
                        <span className="k">Network</span>
                        <span className="v dim">{result?.proof?.network ?? "—"}</span>
                      </div>
                      <div className="proof-row">
                        <span className="k">Anchor tx</span>
                        <span className="v">
                          {result?.proof?.anchor_tx
                            ? `${result.proof.anchor_tx.slice(0, 10)} ${result.proof.anchor_tx.slice(10, 14)} … ${result.proof.anchor_tx.slice(-6)}`
                            : "—"}
                        </span>
                      </div>
                      <div className="proof-row">
                        <span className="k">Executor</span>
                        <span className="v dim">{result?.proof?.executor ?? "—"}</span>
                      </div>
                      <div className="proof-row">
                        <span className="k">This run</span>
                        <span className="v">
                          {result?.consensus.verdict ?? "—"} · {result?.consensus.agree_count ?? "—"} / {result?.consensus.total_agents ?? "—"} · sha-256 verified
                        </span>
                      </div>
                      {result?.proof?.onchain && (
                        <>
                          <div className="proof-row">
                            <span className="k">Canonical (on-chain)</span>
                            <span
                              className="v"
                              style={{
                                color:
                                  result.proof.onchain.verdict === "approve"
                                    ? "var(--accent-green)"
                                    : result.proof.onchain.verdict === "clarify"
                                    ? "var(--accent-amber)"
                                    : "var(--accent-rose)",
                                textTransform: "capitalize",
                                fontWeight: 500,
                              }}
                            >
                              {result.proof.onchain.verdict} · {result.proof.onchain.agree_count}/{result.proof.onchain.total_agents}
                            </span>
                          </div>
                          {result?.consensus && (
                            result.proof.onchain.verdict !== result.consensus.verdict ||
                            result.proof.onchain.agree_count !== result.consensus.agree_count ||
                            result.proof.onchain.total_agents !== result.consensus.total_agents
                          ) && (
                            <div className="proof-row">
                              <span className="k"></span>
                              <span className="v dim" style={{ fontSize: 11, fontStyle: "italic", lineHeight: 1.5 }}>
                                On-chain record differs from this run because this bill's SHA-256 was previously anchored. <code>BillRegistry</code> rejects duplicate writes by design — the canonical record is whatever the first audit produced and is immutable.
                              </span>
                            </div>
                          )}
                          {result.proof.block_number && (
                            <div className="proof-row">
                              <span className="k">Block</span>
                              <span className="v dim">
                                #{result.proof.block_number}
                                {result.proof.gas_used ? ` · ${result.proof.gas_used.toLocaleString()} gas` : ""}
                              </span>
                            </div>
                          )}
                          <div className="proof-row">
                            <span className="k">Anchored at</span>
                            <span className="v dim">
                              {new Date(result.proof.onchain.anchored_at * 1000).toLocaleString()}
                            </span>
                          </div>
                        </>
                      )}
                      {result?.proof?.patterns?.live && (
                        <>
                          <div className="proof-row">
                            <span className="k">Patterns indexed</span>
                            <span className="v">
                              <a
                                href={`${EXPLORER_URL}/${result.proof.patterns.tx}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                style={{
                                  color: "var(--accent-violet)",
                                  borderBottom: "1px dotted var(--ink-faint)",
                                }}
                              >
                                {result.proof.patterns.patterns_indexed} on PatternRegistry ↗
                              </a>
                            </span>
                          </div>
                          <div className="proof-row">
                            <span className="k">Pattern registry</span>
                            <span className="v dim" style={{ wordBreak: "break-all", fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: 11 }}>
                              {result.proof.patterns.registry_address}
                            </span>
                          </div>
                        </>
                      )}
                      {(() => {
                        const m = result?.proof?.mirror;
                        const isDuplicate = m?.live && m?.status === "duplicate";
                        const hasFreshTx = m?.live && m?.tx_hash && !isDuplicate;
                        const hasOriginalTx = isDuplicate && m?.tx_hash;
                        if (hasFreshTx || hasOriginalTx) {
                          const tx = m!.tx_hash!;
                          const link = m!.tx_link ?? `https://sepolia.etherscan.io/tx/${tx}`;
                          return (
                            <>
                              <div className="proof-row">
                                <span className="k">Sepolia mirror</span>
                                <span className="v">
                                  <a
                                    href={link}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{
                                      color: "var(--accent-amber)",
                                      borderBottom: "1px dotted var(--ink-faint)",
                                    }}
                                  >
                                    {isDuplicate ? "✓ already anchored ↗" : "via KeeperHub ↗"}
                                  </a>
                                </span>
                              </div>
                              <div className="proof-row">
                                <span className="k">{isDuplicate ? "Original mirror tx" : "Mirror tx"}</span>
                                <span className="v dim" style={{ wordBreak: "break-all", fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: 11 }}>
                                  {tx}
                                </span>
                              </div>
                              {isDuplicate && m?.note && (
                                <div className="proof-row">
                                  <span className="k"></span>
                                  <span className="v dim" style={{ fontSize: 11, fontStyle: "italic" }}>
                                    {m.note}
                                  </span>
                                </div>
                              )}
                            </>
                          );
                        }
                        if (isDuplicate && !m?.tx_hash) {
                          return (
                            <div className="proof-row">
                              <span className="k">Sepolia mirror</span>
                              <span className="v">
                                <a
                                  href={m?.tx_link ?? `https://sepolia.etherscan.io/address/${m?.registry_address ?? ""}#events`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  style={{ color: "var(--accent-amber)", borderBottom: "1px dotted var(--ink-faint)" }}
                                >
                                  ✓ already anchored — view registry events ↗
                                </a>
                              </span>
                            </div>
                          );
                        }
                        const exec = m?.executor ?? "";
                        const isStub = !m?.live;
                        return (
                          <div className="proof-row">
                            <span className="k">Sepolia mirror</span>
                            <span className="v dim" style={{ fontSize: 12, fontStyle: "italic" }}>
                              {isStub
                                ? `via KeeperHub — not yet wired (${exec || "stub"})`
                                : `via KeeperHub — ${exec || "in flight"}`}
                            </span>
                          </div>
                        );
                      })()}
                      <div className="proof-actions">
                        <a
                          className="btn-sm"
                          href={`${EXPLORER_URL}/${result?.proof?.anchor_tx ?? ANCHOR_TX}`}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          View on explorer ↗
                        </a>
                        <button
                          className={`btn-sm${hashCopied ? " flashed" : ""}`}
                          onClick={onCopyHash}
                        >
                          {hashCopied ? "Copied ✓" : "Copy hash"}
                        </button>
                      </div>
                    </div>

                    {/* Appeal submission — send the drafted letter + chain
                        verification to the provider's email. Fires the third
                        KeeperHub workflow on success (records on-chain that
                        the appeal was sent). */}
                    <div
                      className="proof-card"
                      style={{ marginTop: 18, borderColor: "var(--accent-amber)" }}
                    >
                      <div className="panel-label">Send to provider</div>
                      <p style={{ color: "var(--ink-dim)", fontSize: 13, margin: "8px 0 14px", lineHeight: 1.6 }}>
                        Email the drafted appeal letter <em>plus</em> every chain-verifiable artifact
                        (Galileo anchor, pattern index, Storage commitment, Sepolia mirror, dispute
                        filing) to the provider's billing department. After delivery, KeeperHub
                        records the send on-chain — recipient address is keccak-hashed, never
                        plaintext.
                      </p>
                      <div style={{ display: "flex", gap: 8, alignItems: "stretch", flexWrap: "wrap" }}>
                        <input
                          type="email"
                          value={providerEmail}
                          onChange={(e) => setProviderEmail(e.target.value)}
                          placeholder="billing@provider.example"
                          disabled={appealStatus.phase === "sending"}
                          style={{
                            flex: "1 1 280px",
                            padding: "8px 12px",
                            border: "1px solid var(--line-strong)",
                            borderRadius: 4,
                            fontFamily: "var(--font-jetbrains-mono), monospace",
                            fontSize: 13,
                            background: "var(--paper)",
                            color: "var(--ink)",
                          }}
                        />
                        <button
                          className="btn-sm solid"
                          onClick={onSendAppeal}
                          disabled={
                            !providerEmail.trim() ||
                            appealStatus.phase === "sending"
                          }
                        >
                          {appealStatus.phase === "sending" ? "Sending…" :
                           appealStatus.phase === "sent" ? "Send again" :
                           "Send appeal"}
                        </button>
                      </div>

                      {appealStatus.phase === "sent" && (
                        <div style={{ marginTop: 14, fontSize: 12, fontFamily: "var(--font-jetbrains-mono), monospace", lineHeight: 1.7 }}>
                          <div style={{ color: appealStatus.email.sent ? "var(--accent-green)" : "var(--accent-amber)" }}>
                            email · {appealStatus.email.provider}
                            {appealStatus.email.sent ? " · delivered" : " · stub (no provider configured)"}
                            {appealStatus.email.error && (
                              <span style={{ color: "var(--accent-rose)" }}> · {appealStatus.email.error}</span>
                            )}
                          </div>
                          <div style={{ color: appealStatus.attestation.live ? "var(--accent-green)" : "var(--ink-faint)" }}>
                            keeperhub workflow #3 · {appealStatus.attestation.executor}
                            {appealStatus.attestation.live && appealStatus.attestation.tx_hash && (
                              <>
                                {" · "}
                                <a
                                  href={appealStatus.attestation.tx_link ?? `https://sepolia.etherscan.io/tx/${appealStatus.attestation.tx_hash}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  style={{ color: "var(--accent-amber)", borderBottom: "1px dotted var(--ink-faint)" }}
                                >
                                  {appealStatus.attestation.tx_hash.slice(0, 14)}…{appealStatus.attestation.tx_hash.slice(-8)} ↗
                                </a>
                              </>
                            )}
                          </div>
                        </div>
                      )}

                      {appealStatus.phase === "error" && (
                        <div style={{ marginTop: 14, fontSize: 12, color: "var(--accent-rose)" }}>
                          ⚠ {appealStatus.message}
                        </div>
                      )}
                    </div>
                  </div>
                </motion.section>

                <div className="results-actions">
                  <button className="btn-sm solid" onClick={reset}>
                    Run another bill →
                  </button>
                  <Link className="btn-sm" href="/">
                    Back to home
                  </Link>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </>
  );
}
