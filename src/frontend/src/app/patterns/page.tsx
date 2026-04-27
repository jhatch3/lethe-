"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const CHAINSCAN = "https://chainscan-galileo.0g.ai";

type Pattern = {
  code: string;
  n_observations: number;
  dispute_count: number;
  clarify_count: number;
  aligned_count: number;
  dispute_rate: number;
  clarify_rate: number;
  mean_amount_usd: number;
  first_block: number | null;
  last_block: number | null;
};

type PatternsResponse = {
  registry_address: string;
  network: string;
  chain_id: number;
  code_count: number;
  total_observations: number;
  patterns: Pattern[];
};

const reveal = (delay = 0) => ({
  initial: { opacity: 0, y: 18 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.6, delay, ease: "easeOut" as const },
});

export default function PatternsPage() {
  const [data, setData] = useState<PatternsResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async (force = false) => {
    setBusy(true);
    setErr(null);
    try {
      const r = await fetch(`${API_URL}/api/patterns${force ? "?refresh=true" : ""}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setData((await r.json()) as PatternsResponse);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void load(false);
  }, [load]);

  return (
    <>
      <nav className="nav-top">
        <div className="brand">
          <span className="dot" />
          Lethe
          <span className="brand-sub">/ patterns</span>
        </div>
        <div className="links">
          <Link href="/">Home</Link>
          <Link href="/dashboard">Dashboard</Link>
          <Link href="/verify">Verify</Link>
        </div>
        <Link className="cta" href="/">
          ← Back to home
        </Link>
      </nav>

      <div className="dash-page">
        <section className="dash-hero" style={{ paddingBottom: 30 }}>
          <motion.div className="dash-eyebrow" {...reveal(0)}>
            <span className="pulse-dot" />
            <span className="pill">on-chain · public · anonymized</span>
            <span>0G Galileo · PatternRegistry</span>
          </motion.div>

          <motion.h1 className="dash-headline" {...reveal(0.05)}>
            What we&apos;ve <em>learned.</em>
          </motion.h1>

          <motion.p className="dash-sub" {...reveal(0.15)} style={{ marginBottom: 28 }}>
            Every audit emits one event per consensus finding to the on-chain
            PatternRegistry. Future audits read these stats as priors — agents
            see &quot;CPT 99214 has 100% historical dispute rate&quot; and calibrate
            their confidence accordingly. Zero PHI; only billing codes, actions,
            severities, and counts.
          </motion.p>

          <motion.div {...reveal(0.25)} style={{ width: "100%", maxWidth: 1100 }}>
            {data && (
              <div className="verdict-stats" style={{ borderTop: "1px solid var(--line)" }}>
                <div className="verdict-stat">
                  <span className="stat-num">{data.code_count}</span>
                  <span className="stat-label">Unique codes</span>
                </div>
                <div className="verdict-stat">
                  <span className="stat-num">{data.total_observations}</span>
                  <span className="stat-label">Total observations</span>
                </div>
                <div className="verdict-stat">
                  <span className="stat-num">
                    <em>{data.network === "0g-galileo-testnet" ? "0G" : data.network}</em>
                  </span>
                  <span className="stat-label">Network · chain {data.chain_id}</span>
                </div>
                <div className="verdict-stat">
                  <span className="stat-num" style={{ fontSize: 16, fontFamily: "var(--font-jetbrains-mono), monospace" }}>
                    <a
                      href={`${CHAINSCAN}/address/${data.registry_address}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: "var(--ink)", borderBottom: "1px dotted var(--ink-faint)" }}
                    >
                      {data.registry_address.slice(0, 8)}…{data.registry_address.slice(-6)}
                    </a>
                  </span>
                  <span className="stat-label">Registry contract</span>
                </div>
              </div>
            )}
          </motion.div>
        </section>

        <section className="results-shell" style={{ paddingTop: 0 }}>
          <motion.div
            {...reveal(0.35)}
            style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 18 }}
          >
            <h2 className="panel-title" style={{ margin: 0 }}>
              Top codes <em>· by observations</em>
            </h2>
            <button
              className="btn-sm"
              onClick={() => load(true)}
              disabled={busy}
            >
              {busy ? "refreshing…" : "Refresh from chain"}
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

          {data && data.patterns.length === 0 && !err && (
            <div
              style={{
                padding: 32,
                border: "1px solid var(--line)",
                borderRadius: 6,
                color: "var(--ink-faint)",
                textAlign: "center",
                fontFamily: "var(--font-jetbrains-mono), monospace",
                fontSize: 13,
              }}
            >
              registry empty — run a few audits in the dashboard to populate the index.
            </div>
          )}

          {data && data.patterns.length > 0 && (
            <motion.div className="findings" {...reveal(0.45)}>
              <div
                className="findings-head"
                style={{ gridTemplateColumns: "minmax(170px,1.6fr) 70px 110px 110px 110px 130px" }}
              >
                <span>Code</span>
                <span style={{ textAlign: "right" }}>n</span>
                <span style={{ textAlign: "right" }}>dispute</span>
                <span style={{ textAlign: "right" }}>clarify</span>
                <span style={{ textAlign: "right" }}>aligned</span>
                <span style={{ textAlign: "right" }}>mean amount</span>
              </div>

              {data.patterns.map((p) => {
                const top =
                  p.dispute_rate > p.clarify_rate
                    ? "dispute"
                    : p.clarify_rate > p.dispute_rate
                    ? "clarify"
                    : "split";
                const accent =
                  top === "dispute"
                    ? "var(--accent-rose)"
                    : top === "clarify"
                    ? "var(--accent-amber)"
                    : "var(--ink-dim)";
                return (
                  <motion.div
                    key={p.code}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.35 }}
                    className="finding-row"
                    style={{ gridTemplateColumns: "minmax(170px,1.6fr) 70px 110px 110px 110px 130px" }}
                  >
                    <span className="code" style={{ color: accent, fontWeight: 500 }}>
                      {p.code}
                    </span>
                    <span style={{ textAlign: "right", fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: 13 }}>
                      {p.n_observations}
                    </span>
                    <span
                      className="action"
                      style={{ color: "var(--accent-rose)" }}
                    >
                      {Math.round(p.dispute_rate * 100)}% ({p.dispute_count})
                    </span>
                    <span
                      className="action"
                      style={{ color: "var(--accent-amber)" }}
                    >
                      {Math.round(p.clarify_rate * 100)}% ({p.clarify_count})
                    </span>
                    <span
                      className="action"
                      style={{ color: "var(--accent-green)" }}
                    >
                      {Math.round(
                        ((p.n_observations - p.dispute_count - p.clarify_count) / Math.max(1, p.n_observations)) *
                          100
                      )}
                      % ({p.aligned_count})
                    </span>
                    <span className="amt">${p.mean_amount_usd.toFixed(2)}</span>
                  </motion.div>
                );
              })}
            </motion.div>
          )}

          <div
            style={{
              marginTop: 28,
              padding: "16px 18px",
              border: "1px dashed var(--line-strong)",
              borderRadius: 6,
              fontFamily: "var(--font-jetbrains-mono), monospace",
              fontSize: 11,
              letterSpacing: "0.05em",
              color: "var(--ink-dim)",
              lineHeight: 1.6,
            }}
          >
            <strong style={{ color: "var(--ink)", letterSpacing: "0.18em", textTransform: "uppercase", fontSize: 10 }}>
              how this powers the loop
            </strong>
            <br />
            <span style={{ color: "var(--ink-faint)" }}>1.</span> consensus finding lands → coordinator calls{" "}
            <code>PatternRegistry.indexBatch()</code> on 0G Galileo
            <br />
            <span style={{ color: "var(--ink-faint)" }}>2.</span> events emitted on chain (this table reflects all of them)
            <br />
            <span style={{ color: "var(--ink-faint)" }}>3.</span> next audit → coordinator fetches via{" "}
            <code>eth_getLogs</code>, formats as a prior-stats block
            <br />
            <span style={{ color: "var(--ink-faint)" }}>4.</span> block injected into each agent&apos;s system prompt — they
            see &quot;CPT 99214 has 100% dispute rate (n=2)&quot; before reasoning
            <br />
            <span style={{ color: "var(--ink-faint)" }}>5.</span> richer priors with every audit · no PHI · zero off-chain
            cache · works without lethe servers
          </div>
        </section>
      </div>
    </>
  );
}
