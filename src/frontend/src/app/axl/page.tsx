"use client";

import { motion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";
import { NavBar } from "@/components/NavBar";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type AxlPeer = {
  expected_pubkey: string;
  sidecar_url: string;
  topology: {
    our_public_key?: string;
    peers?: Array<{ public_key?: string; addr?: string }>;
    error?: string;
  };
};

type AxlMessage = {
  ts: number;
  kind: "send" | "recv";
  from_agent: string;
  to_agent: string;
  from_peer_id?: string;
  to_peer_id?: string;
  bytes: number;
  latency_ms?: number;
  ok: boolean;
  error?: string;
  job_id?: string | null;
  finding_count?: number;
};

type AxlResponse = {
  enabled: boolean;
  reason?: string;
  peers?: Record<"alpha" | "beta" | "gamma", AxlPeer>;
  messages?: AxlMessage[];
};

const reveal = (delay = 0) => ({
  initial: { opacity: 0, y: 18 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.6, delay, ease: "easeOut" as const },
});

const AGENT_COLORS: Record<string, string> = {
  alpha: "var(--accent-violet)",
  beta:  "var(--accent-amber)",
  gamma: "var(--accent-green)",
};

function PeerNode({
  variant,
  peer,
  enabled,
}: {
  variant: "alpha" | "beta" | "gamma";
  peer?: AxlPeer;
  enabled: boolean;
}) {
  const accent = AGENT_COLORS[variant];
  const expected = peer?.expected_pubkey ?? "";
  const observed = peer?.topology.our_public_key ?? "";
  const peerCount = peer?.topology.peers?.length ?? 0;
  const err = peer?.topology.error;

  const live = enabled && observed && observed.toLowerCase() === expected.toLowerCase();
  const status = !enabled
    ? { label: "scaffolded · sidecar offline", color: "var(--accent-rose)" }
    : err
    ? { label: "sidecar unreachable", color: "var(--accent-rose)" }
    : live
    ? { label: "online · pubkey verified", color: "var(--accent-green)" }
    : { label: "online · pubkey mismatch", color: "var(--accent-amber)" };

  return (
    <div
      className="conv-card"
      style={{ borderColor: accent }}
    >
      <div className="conv-head">
        <span className="conv-glyph" style={{ color: accent }}>
          {variant === "alpha" ? "α" : variant === "beta" ? "β" : "γ"}
        </span>
        <div className="conv-meta">
          <div className="conv-model">{variant}</div>
          <div className="conv-runtime">ed25519 peer</div>
        </div>
        <span
          className="conv-vote"
          style={{ color: status.color, borderColor: status.color }}
        >
          {status.label}
        </span>
      </div>
      <div className="conv-stats">
        <span>{peerCount} mesh peers</span>
        <span className="div">·</span>
        <span>{peer?.sidecar_url ?? "—"}</span>
      </div>
      <div className="conv-body">
        <div className="conv-line" style={{ borderLeftColor: accent }}>
          <span style={{ color: "var(--ink-faint)" }}>expected:</span>
        </div>
        <div
          className="conv-line"
          style={{
            fontFamily: "var(--font-jetbrains-mono), monospace",
            wordBreak: "break-all",
            paddingLeft: 16,
          }}
        >
          {expected}
        </div>
        <div className="conv-line" style={{ borderLeftColor: accent }}>
          <span style={{ color: "var(--ink-faint)" }}>observed:</span>
        </div>
        <div
          className="conv-line"
          style={{
            fontFamily: "var(--font-jetbrains-mono), monospace",
            wordBreak: "break-all",
            paddingLeft: 16,
            color: live ? "var(--accent-green)" : "var(--ink-faint)",
          }}
        >
          {observed || "(no response)"}
        </div>
        {err && (
          <div
            className="conv-line"
            style={{
              borderLeftColor: "var(--accent-rose)",
              color: "var(--accent-rose)",
              fontSize: 10,
            }}
          >
            {err}
          </div>
        )}
      </div>
    </div>
  );
}

function MeshDiagram({
  enabled,
  peers,
}: {
  enabled: boolean;
  peers?: Record<string, AxlPeer>;
}) {
  // Three nodes in a triangle; coordinator in the middle.
  const n: Record<string, { x: number; y: number; color: string; label: string }> = {
    alpha: { x: 20, y: 26, color: "#a78bfa", label: "α" },
    beta:  { x: 80, y: 26, color: "#fbbf24", label: "β" },
    gamma: { x: 50, y: 86, color: "#22c55e", label: "γ" },
    coord: { x: 50, y: 56, color: "#f5f5f0", label: "coord" },
  };

  return (
    <svg viewBox="0 0 100 100" style={{ width: "100%", height: 320, maxWidth: 480 }}>
      {/* Coordinator → each sidecar */}
      {(["alpha", "beta", "gamma"] as const).map((v) => (
        <line
          key={`c-${v}`}
          x1={n.coord.x}
          y1={n.coord.y}
          x2={n[v].x}
          y2={n[v].y}
          stroke={enabled ? n[v].color : "rgba(255,255,255,0.12)"}
          strokeWidth="0.3"
          strokeDasharray={enabled ? "1.5 1.5" : "0.6 0.6"}
          opacity={enabled ? 0.85 : 0.35}
        >
          {enabled && (
            <animate attributeName="stroke-dashoffset" from="0" to="-3" dur="1s" repeatCount="indefinite" />
          )}
        </line>
      ))}
      {/* Sidecar mesh edges (alpha-beta, beta-gamma, gamma-alpha) */}
      {[
        ["alpha", "beta"],
        ["beta", "gamma"],
        ["gamma", "alpha"],
      ].map(([a, b]) => (
        <line
          key={`${a}-${b}`}
          x1={n[a as "alpha"].x}
          y1={n[a as "alpha"].y}
          x2={n[b as "alpha"].x}
          y2={n[b as "alpha"].y}
          stroke={enabled ? "rgba(255,255,255,0.45)" : "rgba(255,255,255,0.08)"}
          strokeWidth="0.25"
          strokeDasharray="1.2 1.2"
          opacity={enabled ? 0.7 : 0.3}
        >
          {enabled && (
            <animate attributeName="stroke-dashoffset" from="0" to="-2.4" dur="1.4s" repeatCount="indefinite" />
          )}
        </line>
      ))}
      {/* Nodes */}
      {Object.entries(n).map(([k, node]) => (
        <g key={k}>
          {enabled && (
            <circle cx={node.x} cy={node.y} r="6" fill={node.color} opacity="0.18">
              <animate attributeName="r" from="5" to="9" dur="1.6s" repeatCount="indefinite" />
              <animate attributeName="opacity" from="0.25" to="0" dur="1.6s" repeatCount="indefinite" />
            </circle>
          )}
          <circle
            cx={node.x}
            cy={node.y}
            r={k === "coord" ? 3.4 : 3.8}
            fill={k === "coord" ? "#000" : node.color}
            stroke={node.color}
            strokeWidth="0.4"
          />
          <text
            x={node.x}
            y={node.y + 1.4}
            fontSize={k === "coord" ? 1.8 : 4}
            fontStyle={k === "coord" ? "normal" : "italic"}
            textAnchor="middle"
            fill={k === "coord" ? node.color : "#000"}
            fontWeight={500}
            style={{ fontFamily: "var(--font-fraunces), serif" }}
          >
            {node.label}
          </text>
        </g>
      ))}
    </svg>
  );
}

function MessageLog({ messages }: { messages: AxlMessage[] }) {
  if (messages.length === 0) {
    return (
      <div
        style={{
          padding: 20,
          border: "1px dashed var(--line-strong)",
          borderRadius: 6,
          fontFamily: "var(--font-jetbrains-mono), monospace",
          fontSize: 11,
          color: "var(--ink-faint)",
          textAlign: "center",
        }}
      >
        no AXL traffic yet · run an audit on /dashboard
      </div>
    );
  }
  return (
    <div
      style={{
        border: "1px solid var(--line-strong)",
        borderRadius: 6,
        background: "rgba(0,0,0,0.02)",
        fontFamily: "var(--font-jetbrains-mono), monospace",
        fontSize: 11,
        maxHeight: 320,
        overflowY: "auto",
      }}
    >
      {messages.map((m, i) => {
        const arrow = m.kind === "send" ? "→" : "←";
        const accent = m.kind === "send" ? "var(--accent-violet)" : "var(--accent-green)";
        const status = m.ok
          ? { color: "var(--accent-green)", label: "ok" }
          : { color: "var(--accent-rose)", label: m.error ?? "fail" };
        const ts = new Date(m.ts * 1000).toLocaleTimeString(undefined, {
          hour12: false,
          minute: "2-digit",
          second: "2-digit",
        });
        const pubkeyShort = (k?: string) => (k ? `${k.slice(0, 8)}…` : "?");
        return (
          <div
            key={`${m.ts}-${i}`}
            style={{
              padding: "8px 14px",
              borderBottom: i === messages.length - 1 ? "none" : "1px solid var(--line)",
              display: "grid",
              gridTemplateColumns: "60px 60px 1fr auto auto",
              gap: 12,
              alignItems: "center",
              color: "var(--ink-dim)",
            }}
          >
            <span style={{ color: "var(--ink-faint)" }}>{ts}</span>
            <span style={{ color: accent, fontWeight: 600 }}>
              {m.kind === "send" ? "send" : "recv"}
            </span>
            <span>
              <span style={{ color: "var(--ink)" }}>{m.from_agent}</span>
              <span style={{ color: "var(--ink-faint)" }}> · ed25519:{pubkeyShort(m.from_peer_id)}</span>
              <span style={{ color: accent, margin: "0 6px" }}>{arrow}</span>
              <span style={{ color: "var(--ink)" }}>{m.to_agent}</span>
              <span style={{ color: "var(--ink-faint)" }}> · ed25519:{pubkeyShort(m.to_peer_id)}</span>
            </span>
            <span style={{ color: "var(--ink-faint)" }}>
              {m.bytes}B
              {typeof m.finding_count === "number" && m.finding_count > 0 && (
                <span> · {m.finding_count} finding{m.finding_count === 1 ? "" : "s"}</span>
              )}
              {typeof m.latency_ms === "number" && (
                <span> · {m.latency_ms}ms</span>
              )}
            </span>
            <span style={{ color: status.color }}>{status.label}</span>
          </div>
        );
      })}
    </div>
  );
}

export default function AxlPage() {
  const [data, setData] = useState<AxlResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setBusy(true);
    setErr(null);
    try {
      const r = await fetch(`${API_URL}/api/axl`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setData((await r.json()) as AxlResponse);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [load]);

  const enabled = !!data?.enabled;

  return (
    <>
      <NavBar subBrand="mesh" />

      <div className="dash-page">
        <section className="dash-hero" style={{ paddingBottom: 24 }}>
          <motion.div className="dash-eyebrow" {...reveal(0)}>
            <span
              className="pulse-dot"
              style={{
                background: enabled ? "var(--accent-green)" : "var(--accent-rose)",
              }}
            />
            <span className="pill">Gensyn AXL</span>
            <span>{enabled ? "live mesh · 3 ed25519 peers" : "scaffolded · run docker compose to enable"}</span>
          </motion.div>

          <motion.h1 className="dash-headline" {...reveal(0.05)}>
            Three peers, <em>one mesh.</em>
          </motion.h1>

          <motion.p className="dash-sub" {...reveal(0.15)} style={{ marginBottom: 24 }}>
            Each audit agent runs in its own AXL sidecar with its own ed25519
            keypair. The redacted payload is broadcast peer-to-peer over the
            Yggdrasil mesh — agents communicate directly, not through a central
            broker. <code style={{ fontFamily: "var(--font-jetbrains-mono), monospace", color: "var(--ink)" }}>curl localhost:9002/topology</code> on
            any sidecar to verify the public keys below.
          </motion.p>

          <motion.div {...reveal(0.25)} style={{ display: "flex", justifyContent: "center", marginBottom: 24 }}>
            <MeshDiagram enabled={enabled} peers={data?.peers} />
          </motion.div>

          {!enabled && (
            <motion.div
              {...reveal(0.3)}
              style={{
                width: "100%",
                maxWidth: 720,
                padding: 16,
                border: "1px dashed var(--accent-amber)",
                borderRadius: 6,
                background: "rgba(251,191,36,0.05)",
                fontFamily: "var(--font-jetbrains-mono), monospace",
                fontSize: 11,
                color: "var(--ink-dim)",
                lineHeight: 1.7,
              }}
            >
              <div style={{ color: "var(--accent-amber)", fontWeight: 600, marginBottom: 8 }}>
                ⚠ AXL_ENABLED=false — the coordinator is currently using asyncio.gather (in-process).
              </div>
              The three ed25519 peer IDs below are real and committed in{" "}
              <code>infra/axl/keys/peer_ids.json</code>. To bring the sidecars online:
              <pre style={{ color: "var(--ink)", marginTop: 8, whiteSpace: "pre-wrap" }}>
{`docker compose build axl-alpha axl-beta axl-gamma
docker compose up -d axl-alpha axl-beta axl-gamma
# Then in .env:
LETHE_AXL_ENABLED=true
# Restart uvicorn`}
              </pre>
            </motion.div>
          )}
        </section>

        <section className="results-shell" style={{ paddingTop: 0 }}>
          <motion.div
            {...reveal(0.35)}
            style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 18 }}
          >
            <h2 className="panel-title" style={{ margin: 0 }}>
              Peer roster <em>· ed25519 identities</em>
            </h2>
            <button className="btn-sm" onClick={load} disabled={busy}>
              {busy ? "polling…" : "Refresh topology"}
            </button>
          </motion.div>

          {err && (
            <div
              style={{
                padding: 16,
                border: "1px solid var(--accent-rose)",
                borderRadius: 6,
                background: "rgba(248,113,113,0.06)",
                color: "var(--accent-rose)",
                fontFamily: "var(--font-jetbrains-mono), monospace",
                fontSize: 12,
              }}
            >
              ⚠ {err}
            </div>
          )}

          {data?.peers && (
            <motion.div className="conv-row" {...reveal(0.45)} style={{ marginBottom: 28 }}>
              <PeerNode variant="alpha" peer={data.peers["alpha" as "alpha"]} enabled={enabled} />
              <PeerNode variant="beta"  peer={data.peers["beta"  as "alpha"]} enabled={enabled} />
              <PeerNode variant="gamma" peer={data.peers["gamma" as "alpha"]} enabled={enabled} />
            </motion.div>
          )}

          <motion.div {...reveal(0.55)} style={{ marginBottom: 28 }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 12 }}>
              <h2 className="panel-title" style={{ margin: 0 }}>
                Live message log <em>· last {data?.messages?.length ?? 0}</em>
              </h2>
              <span style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: 11, color: "var(--ink-faint)" }}>
                ring buffer · 200 max
              </span>
            </div>
            <MessageLog messages={data?.messages ?? []} />
          </motion.div>

          <div
            style={{
              padding: "16px 18px",
              border: "1px dashed var(--line-strong)",
              borderRadius: 6,
              fontFamily: "var(--font-jetbrains-mono), monospace",
              fontSize: 11,
              letterSpacing: "0.05em",
              color: "var(--ink-dim)",
              lineHeight: 1.7,
            }}
          >
            <strong style={{ color: "var(--ink)", letterSpacing: "0.18em", textTransform: "uppercase", fontSize: 10 }}>
              what happens during an audit (when LETHE_AXL_ENABLED=true)
            </strong>
            <br />
            <span style={{ color: "var(--ink-faint)" }}>1.</span> redact stage finishes → coordinator gets the redacted_payload
            <br />
            <span style={{ color: "var(--ink-faint)" }}>2.</span> for each agent, coordinator <code>POST /send</code> to the
            agent&apos;s local AXL sidecar with <code>X-Destination-Peer-Id</code> = next peer&apos;s pubkey
            <br />
            <span style={{ color: "var(--ink-faint)" }}>3.</span> sidecar relays bytes through Yggdrasil mesh →
            recipient sidecar exposes via <code>GET /recv</code>
            <br />
            <span style={{ color: "var(--ink-faint)" }}>4.</span> coordinator emits <code>axl.broadcast</code> SSE event with
            <code> delivered_to=[beta, gamma]</code> + <code>from_peer_id</code>
            <br />
            <span style={{ color: "var(--ink-faint)" }}>5.</span> each agent calls its LLM provider; the consensus tally is
            still centralized (would require BFT votes for full P2P consensus)
          </div>
        </section>
      </div>
    </>
  );
}