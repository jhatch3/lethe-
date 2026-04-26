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

type Phase = "idle" | "processing" | "complete";

const PIPELINE = [
  { id: "parse", name: "Parse", detail: "extracting line items" },
  { id: "redact", name: "Redact PHI", detail: "stripping identifiers" },
  { id: "broadcast", name: "Broadcast", detail: "AXL · 3 peers" },
  { id: "reason", name: "Reason", detail: "α · β · γ analyzing" },
  { id: "consensus", name: "Consensus", detail: "tallying votes" },
  { id: "anchor", name: "Anchor", detail: "0G chain · sha-256" },
] as const;

const STEP_DURATION = 1100;
const HEX = "0123456789abcdef";
const FINAL_HASH =
  "0xab129f4c7e30b81a2f8e0d4c91e7d3a5e2f8c4d8";

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
  stream,
}: {
  variant: "alpha" | "beta" | "gamma";
  stream: string[];
}) {
  const m = AGENT_META[variant];
  return (
    <div className={`conv-card ${variant}`}>
      <div className="conv-head">
        <span className="conv-glyph">{m.glyph}</span>
        <div className="conv-meta">
          <div className="conv-model">{m.model}</div>
          <div className="conv-runtime">agent {variant} · {m.runtime}</div>
        </div>
        <span className="conv-vote">dispute</span>
      </div>
      <div className="conv-stats">
        <span>{m.findings} findings</span>
        <span className="div">·</span>
        <span>conf {m.confidence.toFixed(2)}</span>
      </div>
      <div className="conv-body">
        {stream.map((line, i) => (
          <div key={i} className="conv-line">{line}</div>
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
}: {
  variant: "alpha" | "beta" | "gamma";
  glyph: string;
  model: string;
  step: number;
}) {
  const lines = AGENT_STREAMS[variant];
  // Reveal one line per step starting at step 3 (reason). Map steps 3,4,5 to lines.
  // Better: reveal incrementally over the duration of the "reason" step.
  const visible = step < 3 ? 0 : Math.min(lines.length, step - 2);
  return (
    <div className={`terminal-card ${variant}`}>
      <div className="term-head">
        <span>
          agent <b style={{ color: "var(--ink)" }}>{variant}</b>
        </span>
        <span>
          <span className="glyph">{glyph}</span>
          &nbsp;{model}
        </span>
      </div>
      <div className="term-body">
        {lines.slice(0, visible).map((l, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
            className="term-line"
          >
            {l}
          </motion.div>
        ))}
        {step >= 3 && step < 5 && visible < lines.length && (
          <span className="term-cursor">▸</span>
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

  const [letter, setLetter] = useState(DEFAULT_LETTER);
  const [editing, setEditing] = useState(false);
  const [draftLetter, setDraftLetter] = useState("");
  const [hashCopied, setHashCopied] = useState(false);
  const [submitState, setSubmitState] = useState<"idle" | "submitted">("idle");

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

  const onApproveSubmit = useCallback(() => {
    setSubmitState("submitted");
    setTimeout(() => setSubmitState("idle"), 2400);
  }, []);

  // morphing hash during processing
  useEffect(() => {
    if (phase !== "processing") return;
    const id = window.setInterval(() => {
      setHash("0x" + randomHex(40));
    }, 60);
    return () => window.clearInterval(id);
  }, [phase]);

  // pipeline progression
  useEffect(() => {
    if (phase !== "processing") return;
    let cancelled = false;
    const run = async () => {
      for (let i = 0; i < PIPELINE.length; i++) {
        if (cancelled) return;
        setStep(i);
        await new Promise((r) => setTimeout(r, STEP_DURATION));
      }
      if (cancelled) return;
      setHash(FINAL_HASH);
      setPhase("complete");
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [phase]);

  const start = useCallback((name: string) => {
    setFilename(name);
    setStep(-1);
    setHash("0x" + "0".repeat(40));
    setPhase("processing");
  }, []);

  const reset = useCallback(() => {
    setPhase("idle");
    setStep(-1);
    setFilename("");
    setHash("0x" + "0".repeat(40));
  }, []);

  const onFile = useCallback(
    (file: File | null) => {
      if (!file) return;
      const ok = /\.(pdf|txt|png|jpg|jpeg|webp)$/i.test(file.name);
      if (!ok) return;
      start(file.name);
    },
    [start]
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
      <nav className="nav-top">
        <div className="brand">
          <span className="dot" />
          Lethe
          <span className="brand-sub">/ dashboard</span>
        </div>
        <div className="links">
          <Link href="/">Home</Link>
          <Link href="/#features">Features</Link>
          <Link href="/#tracks">Tracks</Link>
        </div>
        {phase === "idle" ? (
          <Link className="cta" href="/">
            ← Back to home
          </Link>
        ) : (
          <button className="cta" onClick={reset}>
            ⤺ New analysis
          </button>
        )}
      </nav>

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
                        onClick={() => start(`${s.name}.${s.ext}`)}
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
                  pipeline <b>running</b>
                </div>
                <div className="grp">
                  file <b>{filename || "—"}</b>
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

              <div className="proc-shell">
                <motion.div className="hash-stage" {...reveal(0)}>
                  <span className="hash-label">computing sha-256 · zero-retention proof</span>
                  <span className="hash-text">{hash}</span>
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
                      />
                      <AgentTerminal
                        variant="beta"
                        glyph="β"
                        model="claude"
                        step={step}
                      />
                      <AgentTerminal
                        variant="gamma"
                        glyph="γ"
                        model="gemini"
                        step={step}
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
                >
                  consensus reached · 3 / 3
                </motion.div>
                <motion.h1
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.7, delay: 0.05 }}
                  className="verdict-title"
                >
                  Dispute <em>$487.20</em>
                </motion.h1>
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.5, delay: 0.15 }}
                  className="verdict-sub"
                >
                  All three agents flagged the same charges as billing errors.
                  Findings are below; a draft appeal letter is ready for your review.
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
                  <span className="stat-num"><em>3 / 3</em></span>
                  <span className="stat-label">Agent vote</span>
                </div>
                <div className="verdict-stat">
                  <span className="stat-num">{FINDINGS.length}</span>
                  <span className="stat-label">Findings</span>
                </div>
                <div className="verdict-stat">
                  <span className="stat-num">0.91</span>
                  <span className="stat-label">Mean confidence</span>
                </div>
                <div className="verdict-stat">
                  <span className="stat-num">5.4s</span>
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
                    {FINDINGS.map((f, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.4, delay: 0.5 + i * 0.07 }}
                        className="finding-row"
                      >
                        <span className={`sev ${f.sev}`}>
                          {f.sev === "high" ? "High" : f.sev === "med" ? "Medium" : "Info"}
                        </span>
                        <span className="code">{f.code}</span>
                        <span className="desc">{f.desc}</span>
                        <span className="amt">{f.amt}</span>
                        <span className="action">{f.action}</span>
                      </motion.div>
                    ))}
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
                    <ConvCard variant="alpha" stream={AGENT_STREAMS.alpha} />
                    <ConvCard variant="beta"  stream={AGENT_STREAMS.beta}  />
                    <ConvCard variant="gamma" stream={AGENT_STREAMS.gamma} />
                  </div>
                </motion.section>

                <motion.section
                  className="results-section"
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: 0.7 }}
                >
                  <div className="dash-bottom">
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
                            <button
                              className={`btn-sm solid${submitState === "submitted" ? " flashed" : ""}`}
                              onClick={onApproveSubmit}
                              disabled={submitState === "submitted"}
                            >
                              {submitState === "submitted" ? "Submitted ✓" : "Approve & submit →"}
                            </button>
                            <button className="btn-sm" onClick={onEditStart}>
                              Edit draft
                            </button>
                            <button className="btn-sm" onClick={onDownloadPdf}>
                              Download PDF
                            </button>
                          </>
                        )}
                      </div>
                    </div>

                    <div className="proof-card">
                      <div className="panel-label">On-chain proof</div>
                      <div className="proof-row">
                        <span className="k">Bill hash</span>
                        <span className="v">{hash.slice(0, 10)} {hash.slice(10, 14)} {hash.slice(14, 18)} … {hash.slice(-6)}</span>
                      </div>
                      <div className="proof-row">
                        <span className="k">Network</span>
                        <span className="v dim">0G Galileo testnet</span>
                      </div>
                      <div className="proof-row">
                        <span className="k">Anchor tx</span>
                        <span className="v">{ANCHOR_TX.slice(0, 10)} {ANCHOR_TX.slice(10, 14)} … {ANCHOR_TX.slice(-6)}</span>
                      </div>
                      <div className="proof-row">
                        <span className="k">Executor</span>
                        <span className="v dim">KeeperHub · job kh_7f3a</span>
                      </div>
                      <div className="proof-row">
                        <span className="k">Vote record</span>
                        <span className="v">3 / 3 · sha-256 verified</span>
                      </div>
                      <div className="proof-actions">
                        <a
                          className="btn-sm"
                          href={`${EXPLORER_URL}/${ANCHOR_TX}`}
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
