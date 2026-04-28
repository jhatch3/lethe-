"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { NavBar } from "@/components/NavBar";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const CHAINSCAN = "https://chainscan-galileo.0g.ai";

type Rule = {
  id: number;
  version: number;
  kind: string;
  cpt_a: string;
  cpt_b: string;
  modifier: string;
  units_cap_per_day: number;
  citation: string;
};

type RulesData = {
  configured: boolean;
  version?: number;
  count?: number;
  rules?: Rule[];
  registry_address?: string;
  error?: string;
};

const reveal = (delay = 0) => ({
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5, delay, ease: "easeOut" as const },
});

const KIND_COLORS: Record<string, string> = {
  mutually_exclusive: "var(--accent-rose)",
  bundled_into_column1: "var(--accent-amber)",
  modifier_required: "var(--accent-violet)",
  units_cap: "var(--accent-cyan, #22d3ee)",
  modifier_abuse_flag: "var(--accent-pink, #f472b6)",
};

export default function RulesPage() {
  const [data, setData] = useState<RulesData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/api/rules`)
      .then((r) => r.json())
      .then((d) => setData(d))
      .catch((e) => setData({ configured: true, error: String(e) }))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <NavBar subBrand="rules" />
      <div className="dash-page">
        <section className="dash-hero" style={{ paddingBottom: 24 }}>
          <motion.div className="dash-eyebrow" {...reveal(0)}>
            <span className="pulse-dot" />
            <span className="pill">NCCI rulebook · on-chain</span>
            <span>{data?.version ? `v${data.version}` : "loading…"}</span>
          </motion.div>

          <motion.h1 className="dash-headline" {...reveal(0.05)}>
            Coding rules,<br />
            <em>queryable by anyone.</em>
          </motion.h1>

          <motion.p className="dash-sub" {...reveal(0.12)}>
            CMS publishes the NCCI (National Correct Coding Initiative) ruleset
            quarterly. Lethe codifies the active rules in an on-chain
            <code style={{ fontFamily: "var(--font-jetbrains-mono), monospace", padding: "0 6px" }}>NCCIRulebook</code>
            contract on 0G Galileo. Audit agents query this contract at
            reasoning time, so every audit is grounded in the same canonical
            ruleset — no hidden vendor configuration.
          </motion.p>
        </section>

        <section className="results-shell" style={{ paddingTop: 0 }}>
          {loading && <div style={{ color: "var(--ink-faint)", textAlign: "center", padding: 40 }}>loading…</div>}

          {!loading && data && data.configured && data.rules && data.rules.length > 0 && (
            <>
              <motion.div {...reveal(0.18)} style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 18 }}>
                <h2 className="panel-title" style={{ margin: 0 }}>
                  Active ruleset <em>· v{data.version} · {data.count} rules</em>
                </h2>
                {data.registry_address && (
                  <a
                    href={`${CHAINSCAN}/address/${data.registry_address}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-sm"
                    style={{ color: "var(--accent-violet)" }}
                  >
                    View contract ↗
                  </a>
                )}
              </motion.div>

              <motion.div {...reveal(0.25)} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {data.rules.map((r) => {
                  const color = KIND_COLORS[r.kind] || "var(--ink-faint)";
                  return (
                    <div key={r.id} style={{
                      display: "grid",
                      gridTemplateColumns: "auto 1fr auto",
                      gap: 16,
                      padding: "12px 16px",
                      border: "1px solid var(--line)",
                      borderRadius: 6,
                      background: "var(--paper)",
                      alignItems: "center",
                    }}>
                      <div style={{ fontSize: 10, fontFamily: "var(--font-jetbrains-mono), monospace", color: "var(--ink-faint)", minWidth: 32 }}>
                        #{r.id}
                      </div>
                      <div>
                        <div style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: 13, color: "var(--ink)" }}>
                          <span style={{ color }}>{r.kind.replace(/_/g, " ")}</span>
                          {": "}
                          <strong>{r.cpt_a}</strong>
                          {r.cpt_b && <> ↔ <strong>{r.cpt_b}</strong></>}
                          {r.modifier && <span style={{ color: "var(--ink-faint)" }}> · mod {r.modifier}</span>}
                          {r.units_cap_per_day > 0 && <span style={{ color: "var(--ink-faint)" }}> · ≤{r.units_cap_per_day} units/day</span>}
                        </div>
                        {r.citation && (
                          <div style={{ fontSize: 11, color: "var(--ink-faint)", marginTop: 4, fontStyle: "italic" }}>
                            {r.citation}
                          </div>
                        )}
                      </div>
                      <div style={{ fontSize: 10, color: "var(--ink-faint)", fontFamily: "var(--font-jetbrains-mono), monospace" }}>
                        v{r.version}
                      </div>
                    </div>
                  );
                })}
              </motion.div>

              <motion.div {...reveal(0.35)} style={{
                marginTop: 20,
                padding: 14,
                border: "1px dashed var(--line-strong)",
                borderRadius: 6,
                fontSize: 11,
                color: "var(--ink-dim)",
                lineHeight: 1.7,
                fontFamily: "var(--font-jetbrains-mono), monospace",
              }}>
                <div style={{ color: "var(--ink-faint)", letterSpacing: "0.18em", textTransform: "uppercase", fontSize: 10, marginBottom: 6 }}>
                  Why on-chain?
                </div>
                Versioning, governance, and auditability are coordination problems —
                exactly what a chain solves. Every rule update emits an event;
                every audit queries the active version; an insurer wanting to
                contest an audit can fetch the exact rule that triggered it,
                forever, without trusting Lethe&apos;s database.
              </motion.div>
            </>
          )}

          {!loading && data && (!data.configured || (data.rules?.length ?? 0) === 0) && (
            <div style={{
              padding: 32,
              border: "1px dashed var(--line-strong)",
              borderRadius: 6,
              textAlign: "center",
              fontFamily: "var(--font-jetbrains-mono), monospace",
              fontSize: 13,
              color: "var(--ink-faint)",
              lineHeight: 1.7,
            }}>
              <div style={{ marginBottom: 10 }}>NCCI rulebook not yet seeded</div>
              <div style={{ fontSize: 11 }}>
                Deploy <code>NCCIRulebook.sol</code> on Galileo and run{" "}
                <code style={{ color: "var(--accent-violet)" }}>python data-gen/scripts/seed_ncci_rules.py --publish</code>
                {" "}to populate the active version.
              </div>
            </div>
          )}

          {!loading && data?.error && (
            <div style={{ color: "var(--accent-rose)", textAlign: "center", padding: 32 }}>⚠ {data.error}</div>
          )}
        </section>
      </div>
    </>
  );
}
