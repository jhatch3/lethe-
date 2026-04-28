"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { NavBar } from "@/components/NavBar";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const CHAINSCAN = "https://chainscan-galileo.0g.ai";

type ProviderStats = {
  configured: boolean;
  npi?: string;
  npi_hash?: string;
  total_audits?: number;
  dispute_count?: number;
  clarify_count?: number;
  approve_count?: number;
  total_flagged_cents?: number;
  total_flagged_usd?: number;
  dispute_rate_pct?: number;
  registry_address?: string;
  error?: string;
};

const reveal = (delay = 0) => ({
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5, delay, ease: "easeOut" as const },
});

export default function ProviderPage() {
  const params = useParams<{ npi: string }>();
  const npi = params?.npi ?? "";
  const [stats, setStats] = useState<ProviderStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!npi || !/^\d{10}$/.test(npi)) {
      setLoading(false);
      return;
    }
    setLoading(true);
    fetch(`${API_URL}/api/providers/${npi}`)
      .then((r) => r.json())
      .then((d) => setStats(d))
      .catch((e) => setStats({ configured: true, error: String(e) }))
      .finally(() => setLoading(false));
  }, [npi]);

  const disputeRate = stats?.dispute_rate_pct ?? 0;
  const rateColor =
    disputeRate >= 50 ? "var(--accent-rose)"
    : disputeRate >= 20 ? "var(--accent-amber)"
    : "var(--accent-green)";

  return (
    <>
      <NavBar subBrand="provider rep" />
      <div className="dash-page">
        <section className="dash-hero" style={{ paddingBottom: 24 }}>
          <motion.div className="dash-eyebrow" {...reveal(0)}>
            <span className="pulse-dot" />
            <span className="pill">provider reputation</span>
            <span>NPI {npi}</span>
          </motion.div>

          <motion.h1 className="dash-headline" {...reveal(0.05)}>
            Public dispute rate.<br />
            <em>Reputation that lives on-chain.</em>
          </motion.h1>

          <motion.p className="dash-sub" {...reveal(0.12)}>
            Every audit Lethe runs against this provider is recorded on the
            <code style={{ fontFamily: "var(--font-jetbrains-mono), monospace", padding: "0 6px" }}>ProviderReputation</code>
            contract on 0G Galileo. NPI is hashed before going on-chain — the
            registry can be queried by anyone, and Lethe can&apos;t fudge the numbers.
          </motion.p>
        </section>

        <section className="results-shell" style={{ paddingTop: 0 }}>
          {loading && (
            <div style={{ color: "var(--ink-faint)", textAlign: "center", padding: 40 }}>loading…</div>
          )}
          {!loading && stats && stats.configured && !stats.error && stats.total_audits !== undefined && (
            <>
              {stats.total_audits === 0 ? (
                <motion.div {...reveal(0.2)} style={{
                  padding: 32,
                  border: "1px dashed var(--line-strong)",
                  borderRadius: 6,
                  textAlign: "center",
                  fontFamily: "var(--font-jetbrains-mono), monospace",
                  fontSize: 13,
                  color: "var(--ink-faint)",
                  lineHeight: 1.7,
                }}>
                  <div style={{ marginBottom: 10 }}>no audits recorded for this provider</div>
                  <div style={{ fontSize: 11 }}>
                    NPI {npi} hasn&apos;t been audited via Lethe yet (or hasn&apos;t reached <code>dispute</code> consensus). The page reflects only audits that produced a verdict.
                  </div>
                </motion.div>
              ) : (
                <>
                  {/* Big top stat */}
                  <motion.div {...reveal(0.15)} style={{
                    padding: 32,
                    border: "1px solid var(--line)",
                    borderRadius: 8,
                    background: "var(--paper)",
                    marginBottom: 18,
                    textAlign: "center",
                  }}>
                    <div style={{ fontSize: 12, letterSpacing: "0.18em", textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: 14 }}>
                      Dispute rate
                    </div>
                    <div style={{ fontSize: "clamp(48px, 8vw, 88px)", fontWeight: 200, color: rateColor, lineHeight: 1 }}>
                      {disputeRate.toFixed(1)}<span style={{ fontSize: "0.4em", color: "var(--ink-faint)" }}>%</span>
                    </div>
                    <div style={{ fontSize: 13, color: "var(--ink-faint)", marginTop: 14 }}>
                      <strong style={{ color: "var(--ink)" }}>{stats.dispute_count}</strong> of{" "}
                      <strong style={{ color: "var(--ink)" }}>{stats.total_audits}</strong> audits
                      reached <em>dispute</em> consensus
                    </div>
                  </motion.div>

                  {/* Detailed counts */}
                  <motion.div {...reveal(0.22)} style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                    gap: 12,
                    marginBottom: 18,
                  }}>
                    {[
                      { label: "Total audits", value: stats.total_audits, color: "var(--ink)" },
                      { label: "Dispute", value: stats.dispute_count, color: "var(--accent-rose)" },
                      { label: "Clarify", value: stats.clarify_count, color: "var(--accent-amber)" },
                      { label: "Approve", value: stats.approve_count, color: "var(--accent-green)" },
                      { label: "Total flagged", value: `$${(stats.total_flagged_usd ?? 0).toLocaleString()}`, color: "var(--accent-rose)" },
                    ].map((c) => (
                      <div key={c.label} style={{
                        padding: 16,
                        border: "1px solid var(--line)",
                        borderRadius: 6,
                        background: "var(--paper)",
                      }}>
                        <div style={{ fontSize: 10, letterSpacing: "0.18em", textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: 8 }}>
                          {c.label}
                        </div>
                        <div style={{ fontSize: 20, color: c.color, fontWeight: 500 }}>{c.value}</div>
                      </div>
                    ))}
                  </motion.div>

                  {/* On-chain reference */}
                  <motion.div {...reveal(0.3)} style={{
                    padding: 16,
                    border: "1px dashed var(--line-strong)",
                    borderRadius: 6,
                    fontFamily: "var(--font-jetbrains-mono), monospace",
                    fontSize: 11,
                    color: "var(--ink-dim)",
                    lineHeight: 1.7,
                  }}>
                    <div style={{ color: "var(--ink-faint)", marginBottom: 6, letterSpacing: "0.1em", textTransform: "uppercase", fontSize: 10 }}>
                      On-chain reference
                    </div>
                    <div>NPI hash: <span style={{ wordBreak: "break-all" }}>{stats.npi_hash}</span></div>
                    <div>Contract: <a
                      href={`${CHAINSCAN}/address/${stats.registry_address}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: "var(--accent-violet)", borderBottom: "1px dotted var(--ink-faint)", wordBreak: "break-all" }}
                    >
                      {stats.registry_address} ↗
                    </a></div>
                    <div style={{ marginTop: 8, fontStyle: "italic", color: "var(--ink-faint)" }}>
                      Verify any of these numbers on-chain — Lethe cannot fudge them. Anyone can call
                      <code style={{ padding: "0 4px" }}>stats(npiHash)</code> on this contract.
                    </div>
                  </motion.div>
                </>
              )}
            </>
          )}
          {!loading && stats?.error && (
            <div style={{ color: "var(--accent-rose)", textAlign: "center", padding: 32, border: "1px solid var(--accent-rose)", borderRadius: 6 }}>
              ⚠ {stats.error}
            </div>
          )}
          {!loading && !npi.match(/^\d{10}$/) && (
            <div style={{ textAlign: "center", padding: 32, color: "var(--ink-faint)" }}>
              NPI must be 10 digits — got “{npi}”
            </div>
          )}
        </section>

        <section style={{ marginTop: 40, paddingBottom: 40, textAlign: "center" }}>
          <Link href="/dashboard" className="btn-sm">← Back to dashboard</Link>
        </section>
      </div>
    </>
  );
}