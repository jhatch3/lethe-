"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { useEffect, useState } from "react";
import { NavBar } from "@/components/NavBar";
import { useWallet, shortenAddress, loadAudits, type LocalAudit } from "@/components/useWallet";

const reveal = (delay = 0) => ({
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5, delay, ease: "easeOut" as const },
});

export default function MyAuditsPage() {
  const { address, connect, connecting } = useWallet();
  const [audits, setAudits] = useState<LocalAudit[]>([]);

  useEffect(() => {
    setAudits(loadAudits(address));
  }, [address]);

  return (
    <>
      <NavBar subBrand="my audits" />
      <div className="dash-page">
        <section className="dash-hero" style={{ paddingBottom: 24 }}>
          <motion.div className="dash-eyebrow" {...reveal(0)}>
            <span className="pulse-dot" />
            <span className="pill">your audits</span>
            <span>{address ? shortenAddress(address) : "wallet not connected"}</span>
          </motion.div>

          <motion.h1 className="dash-headline" {...reveal(0.05)}>
            Your audit history.<br />
            <em>Forgotten by us, kept by you.</em>
          </motion.h1>

          <motion.p className="dash-sub" {...reveal(0.12)}>
            Every audit you run while your wallet is connected gets indexed in
            this browser. The bills themselves are gone — only the SHA-256, the
            verdict, and the on-chain anchor link remain. Verify any of them on
            the chain forever, even after Lethe shuts down.
          </motion.p>

          {!address && (
            <motion.div {...reveal(0.2)} style={{ marginTop: 24, textAlign: "center" }}>
              <button
                onClick={() => void connect()}
                disabled={connecting}
                className="btn-sm solid"
                style={{ fontSize: 14, padding: "10px 18px" }}
              >
                {connecting ? "Connecting…" : "Connect wallet"}
              </button>
              <div style={{ marginTop: 12, fontSize: 12, color: "var(--ink-faint)" }}>
                Browser wallet (MetaMask, Rabby, etc.) — Lethe never custodies funds, only reads your address.
              </div>
            </motion.div>
          )}
        </section>

        {address && (
          <section className="results-shell" style={{ paddingTop: 0 }}>
            <motion.div {...reveal(0.25)} style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 18 }}>
              <h2 className="panel-title" style={{ margin: 0 }}>
                Audits <em>· {audits.length}</em>
              </h2>
              <Link href="/dashboard" className="btn-sm">+ New audit</Link>
            </motion.div>

            {audits.length === 0 ? (
              <motion.div {...reveal(0.3)} style={{
                padding: 32,
                border: "1px dashed var(--line-strong)",
                borderRadius: 6,
                color: "var(--ink-faint)",
                textAlign: "center",
                fontFamily: "var(--font-jetbrains-mono), monospace",
                fontSize: 13,
                lineHeight: 1.7,
              }}>
                <div style={{ marginBottom: 10 }}>no audits yet</div>
                <div style={{ fontSize: 11 }}>
                  Run an audit on the <Link href="/dashboard" style={{ color: "var(--accent-violet)", borderBottom: "1px dotted var(--ink-faint)" }}>dashboard</Link> while your wallet is connected — it'll show up here.
                </div>
              </motion.div>
            ) : (
              <motion.div {...reveal(0.3)} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {audits.map((a) => {
                  const verdictColor =
                    a.verdict === "approve" ? "var(--accent-green)"
                    : a.verdict === "clarify" ? "var(--accent-amber)"
                    : "var(--accent-rose)";
                  return (
                    <Link
                      key={a.sha}
                      href={`/verify?sha=${a.sha}`}
                      style={{
                        display: "grid",
                        gridTemplateColumns: "1fr auto auto",
                        gap: 14,
                        padding: "14px 18px",
                        border: "1px solid var(--line)",
                        borderRadius: 6,
                        background: "var(--paper)",
                        textDecoration: "none",
                        color: "inherit",
                        alignItems: "center",
                      }}
                    >
                      <div>
                        <div style={{ fontSize: 13, color: "var(--ink)", marginBottom: 4 }}>
                          {a.filename ?? "Bill audit"}
                        </div>
                        <div style={{ fontSize: 11, fontFamily: "var(--font-jetbrains-mono), monospace", color: "var(--ink-faint)", wordBreak: "break-all" }}>
                          {a.sha.slice(0, 14)}…{a.sha.slice(-8)}
                        </div>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <div style={{ color: verdictColor, fontSize: 13, fontWeight: 500, textTransform: "capitalize" }}>
                          {a.verdict ?? "unknown"}
                        </div>
                        <div style={{ fontSize: 10, color: "var(--ink-faint)", fontFamily: "var(--font-jetbrains-mono), monospace" }}>
                          {a.agree_count ?? "?"}/{a.total_agents ?? "?"} · {new Date(a.ts).toLocaleDateString()}
                        </div>
                      </div>
                      <div style={{ color: "var(--accent-violet)", fontSize: 16 }}>↗</div>
                    </Link>
                  );
                })}
              </motion.div>
            )}
          </section>
        )}
      </div>
    </>
  );
}
