"use client";

import Link from "next/link";
import { motion, useScroll, useTransform } from "framer-motion";
import { NavBar } from "@/components/NavBar";

const scrollTo = (id: string) => () => {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
};

const reveal = {
  initial: { opacity: 0, y: 24 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, amount: 0.2 },
  transition: { duration: 0.7, ease: "easeOut" as const },
};

export default function Home() {
  const { scrollY } = useScroll();
  const wordmarkY = useTransform(scrollY, [0, 600], [0, -80]);
  const wordmarkOpacity = useTransform(scrollY, [0, 500], [1, 0.15]);
  const heroFade = useTransform(scrollY, [0, 400], [1, 0]);

  return (
    <>
      <NavBar />

      <section className="hero">
        <motion.div
          // initial={{ opacity: 0, y: 6 }}
          // animate={{ opacity: 1, y: 0 }}
          // transition={{ duration: 0.6 }}
          // className="eyebrow"
        >
          <span className="pulse" />
          {/* <span className="pill">ETHGlobal · OpenAgents 2026</span> */}
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.1, ease: "easeOut" }}
          style={{ y: wordmarkY, opacity: wordmarkOpacity }}
          className="wordmark"
          aria-label="Lethe"
        >
          <span className="l l1">L</span>
          <span className="l l2">e</span>
          <span className="l l3">t</span>
          <span className="l l4">h</span>
          <span className="l l5">e</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.4 }}
          className="headline"
        >
          Medical bills, audited by AI consensus.
          <br />
          <span className="em">Forgotten by design.</span>
        </motion.p>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.55 }}
          className="sub"
        >
          Three independent AI agents review every bill, then talk it over peer-to-peer
          on a Gensyn AXL mesh and revise their votes with each other&apos;s findings as
          context. Anything they still agree is wrong gets drafted into an appeal.
          Your bill never touches storage and never reaches a model provider.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.7 }}
          style={{ opacity: heroFade }}
          className="hero-ctas"
        >
          <Link className="btn btn-primary" href="/dashboard">
            Get started <span className="arr">→</span>
          </Link>
          <Link className="btn btn-ghost" href="/verify">
            Verify a bill
          </Link>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.7, delay: 0.95 }}
          style={{ opacity: heroFade }}
          className="hero-foot"
        >
          <span><b>Zero</b> retention</span>
          <span><b>3</b> independent LLMs</span>
          <span><b>2-round</b> AXL P2P consensus</span>
          <span><b>0G</b>: Chain · Storage · Compute</span>
          <span><b>KH</b>: 2 workflows</span>
        </motion.div>
      </section>

      <section id="problem" className="band">
        <div className="container">
          <motion.div className="section-head" {...reveal}>
            <span className="section-num">[ 01 ]</span>
            <h2 className="section-title">
              The <span className="em">problem</span>
            </h2>
            <p className="section-kicker">
              Most patients pay bills they shouldn&apos;t. The few tools that exist make the privacy problem worse.
            </p>
          </motion.div>
          <motion.div className="problem-grid" {...reveal}>
            <div className="problem-cell">
              <div className="problem-stat">~80<span className="pct">%</span></div>
              <h3 className="problem-h">of medical bills contain errors</h3>
              <p className="problem-p">
                Approximately 80% of U.S. medical bills contain some kind of error — duplicated codes, wrong modifiers, services that never happened. Hospital billing errors result in overcharges of 26 percent on average in those bills that contained errors.
              </p>
              <div className="source">[1] Aptarro · 2026 stats &nbsp; [2] Coronis Health / NerdWallet</div>
            </div>
            <div className="problem-cell">
              <div className="problem-stat">~75<span className="pct">%</span></div>
              <h3 className="problem-h">of disputes succeed — when patients file</h3>
              <p className="problem-p">
                Disputing bills leads to corrections in nearly 75% of cases. The catch: 40% of adults who did not appeal were uncertain about how to go about doing so or who to contact.
              </p>
              <div className="source">[3] Solace Health &nbsp; [4] AJMC 2026 survey</div>
            </div>
            <div className="problem-cell">
              <div className="problem-stat">∞</div>
              <h3 className="problem-h">retention by default</h3>
              <p className="problem-p">
                Existing services upload your records to a central database and keep them indefinitely. The CFPB has estimated that roughly $88 billion in medical debt appears on Americans&apos; credit reports — debt that is &ldquo;often confusing and erroneous.&rdquo;
              </p>
              <div className="source">[5] Hathr.AI / CFPB</div>
            </div>
          </motion.div>
        </div>
      </section>

      <section id="features" className="band">
        <div className="container">
          <motion.div className="section-head" {...reveal}>
            <span className="section-num">[ 02 ]</span>
            <h2 className="section-title">
              Built around <span className="em">what you don&apos;t keep.</span>
            </h2>
            <p className="section-kicker">
              Privacy isn&apos;t a setting; it&apos;s the architecture. Nothing about Lethe works if we hold your bill.
            </p>
          </motion.div>
          <motion.div className="feat-grid" {...reveal}>
            <div className="feat green">
              <div className="label">Zero retention</div>
              <h3>Memory-only, then gone.</h3>
              <p>
                Your bill lives in coordinator memory for the ~60 seconds it takes the pipeline to run, then it&apos;s zeroed. Never written to disk, never persisted on 0G, never sent to a model provider. We can&apos;t leak what we don&apos;t hold.
              </p>
              <div className="tick">— bill bytes · in-memory only</div>
            </div>
            <div className="feat amber">
              <div className="label">3-agent consensus</div>
              <h3>GPT-4o · Claude · Gemini.</h3>
              <p>
                Three independent models reason in parallel over the same redacted payload, then vote. A finding only enters the result if 2 of 3 agree on the canonical billing code. 1-1-1 splits fall back to clarify rather than letting registration order silently pick.
              </p>
              <div className="tick">— quorum 2/3 · clarify on tie</div>
            </div>
            <div className="feat violet">
              <div className="label">Real AXL P2P mesh</div>
              <h3>Three peers, one Yggdrasil.</h3>
              <p>
                Each agent has its own Gensyn AXL sidecar Docker container running the upstream Go <code>node</code> binary, with a unique ed25519 peer ID joined to the public Gensyn mesh. Real <code>POST /send</code>, real <code>GET /recv</code> — verifiable on the live mesh page.
              </p>
              <div className="tick">— ed25519 · yggdrasil · public peers</div>
            </div>
            <div className="feat pink">
              <div className="label">Round-2 reflection</div>
              <h3>Consensus through conversation.</h3>
              <p>
                After round 1, every agent broadcasts its findings over AXL and drains its peer inbox. Then each one runs a <em>second</em> LLM call with the others&apos; findings as context — adding what it missed, downgrading what peers convinced it was wrong. The final tally runs on round-2 votes, so every verdict survived peer scrutiny.
              </p>
              <div className="tick">— round 1 → axl exchange → round 2</div>
            </div>
            <div className="feat rose">
              <div className="label">Three pillars on 0G</div>
              <h3>Chain · Storage · Compute.</h3>
              <p>
                Every audit hits the full 0G stack: <strong>Chain</strong> anchors the SHA-256 + verdict to BillRegistry and indexes findings to PatternRegistry. <strong>Storage</strong> holds the full schema-versioned audit blob with merkle root + commitment tx in the receipt. <strong>Compute</strong> (optional) runs agent γ on decentralized inference via the broker SDK with per-request signed headers.
              </p>
              <div className="tick">— 0g chain · 0g storage · 0g compute</div>
            </div>
            <div className="feat cyan">
              <div className="label">KeeperHub — two workflows</div>
              <h3>Mirror anchor + dispute filing.</h3>
              <p>
                Every audit fires KH twice: a <strong>mirror anchor</strong> writes the SHA-256 + verdict to a Sepolia BillRegistry, and on consensus = dispute a <strong>second</strong> KH execution calls <code>recordDispute</code> on a configurable DisputeRegistry. Both REST and MCP transports are implemented; "already anchored" duplicates are detected and the receipt links the original tx, not "pending".
              </p>
              <div className="tick">— mirror · dispute · rest + mcp</div>
            </div>
            <div className="feat ink">
              <div className="label">Pattern read-back</div>
              <h3>Each audit is smarter than the last.</h3>
              <p>
                Anonymized findings are written to PatternRegistry on 0G Chain in parallel with uploading the full record to 0G Storage. Before each new audit, the coordinator queries <code>eth_getLogs</code> and feeds prior dispute / clarify rates into agent prompts as priors. A pre-seed script bootstraps ~20 historical patterns so the very first demo audit shows the priors loop firing.
              </p>
              <div className="tick">— learn from past · zero PHI</div>
            </div>
            <div className="feat ink">
              <div className="label">Auto-drafted appeal</div>
              <h3>Letter, you review.</h3>
              <p>
                A fourth agent (Claude, separately prompted) takes the consensus findings and writes a formal appeal letter with regulatory citations. The dashboard renders it as an ASCII-bordered receipt PDF. Lethe never auto-submits to an insurer — you stay in the loop.
              </p>
              <div className="tick">— draft → review → download</div>
            </div>
          </motion.div>
        </div>
      </section>

      <section id="tracks" className="band">
        <div className="container">
          <motion.div className="section-head" {...reveal}>
            <span className="section-num">[ 03 ]</span>
            <h2 className="section-title">
              Built on <span className="em">three rails.</span>
            </h2>
            <p className="section-kicker">
              Each sponsor handles a different piece — agent memory, agent communication, agent execution.
            </p>
          </motion.div>
          <motion.div className="tracks" {...reveal}>
            <div className="track a">
              <div className="role">/ track · 01</div>
              <div className="name">0G — <em>chain · storage · compute</em></div>
              <p>
                Three pillars on 0G: <strong>Chain</strong> (BillRegistry anchors + PatternRegistry events on Galileo, chain 16602), <strong>Storage</strong> (full schema-versioned audit blob via <code>@0glabs/0g-ts-sdk</code>, merkle root in receipt), and <strong>Compute</strong> (γ-agent on decentralized inference with per-request signed headers via <code>@0glabs/0g-serving-broker</code>).
              </p>
              <p className="pitch">
                Ephemeral PHI, persistent learning — agents get smarter without anyone&apos;s records being recoverable.
              </p>
            </div>
            <div className="track b">
              <div className="role">/ track · 02</div>
              <div className="name">Gensyn AXL — <em>mesh</em></div>
              <p>
                Each of the three agents has its own AXL sidecar Docker container running the upstream Gensyn <code>node</code> binary, joined to the public Gensyn mesh via TLS. Real ed25519 peer IDs, real <code>POST /send</code> broadcasts, real <code>GET /recv</code> drains.
              </p>
              <p className="pitch">
                The mesh is load-bearing — round-2 reflection won&apos;t fire without peer findings actually crossing it.
              </p>
            </div>
            <div className="track c">
              <div className="role">/ track · 03</div>
              <div className="name">KeeperHub — <em>workflow execution</em></div>
              <p>
                Two distinct KH workflows fire per audit: a <strong>mirror anchor</strong> writes the SHA-256 + verdict to a Sepolia BillRegistry, and on consensus = dispute a <strong>second</strong> KH execution calls <code>recordDispute</code> on a configurable DisputeRegistry. Both REST and MCP transports implemented.
              </p>
              <p className="pitch">
                If one chain falls, the proof still lives on the other.
              </p>
            </div>
          </motion.div>
        </div>
      </section>

      {/* <section id="sources" className="band">
        <div className="container">
          <div className="section-head">
            <span className="section-num">[ 04 ]</span>
            <h2 className="section-title">
              Sources <span className="em">&amp; citations</span>
            </h2>
            <p className="section-kicker">
              Every stat on this page comes from named, dated industry research and government data.
            </p>
          </div>
          <div className="sources-list">
            <div className="src-item">
              <div className="src-num">[1]</div>
              <div className="src-body">
                <p className="claim">&ldquo;Approximately 80% of U.S. medical bills contain some kind of error.&rdquo;</p>
                <p className="cite">
                  Aptarro — <i>40+ Medical Billing Stats 2026</i>
                  <br />
                  <a href="https://www.aptarro.com/insights/medical-billing-stats" target="_blank" rel="noopener noreferrer">
                    aptarro.com/insights/medical-billing-stats
                  </a>
                </p>
              </div>
            </div>
            <div className="src-item">
              <div className="src-num">[2]</div>
              <div className="src-body">
                <p className="claim">&ldquo;Hospital billing errors resulted in overcharges of 26 percent on average in those bills that contained errors.&rdquo;</p>
                <p className="cite">
                  Coronis Health, citing NerdWallet study
                  <br />
                  <a href="https://www.coronishealth.com/blog/are-medical-billing-errors-reaching-a-new-high" target="_blank" rel="noopener noreferrer">
                    coronishealth.com
                  </a>
                </p>
              </div>
            </div>
            <div className="src-item">
              <div className="src-num">[3]</div>
              <div className="src-body">
                <p className="claim">&ldquo;Disputing bills leads to corrections in nearly 75% of cases.&rdquo;</p>
                <p className="cite">
                  Solace Health — <i>How to Dispute Your Medical Bill</i> (May 2025)
                  <br />
                  <a href="https://www.solace.health/articles/how-to-dispute-a-medical-bill" target="_blank" rel="noopener noreferrer">
                    solace.health/articles/how-to-dispute-a-medical-bill
                  </a>
                </p>
              </div>
            </div>
            <div className="src-item">
              <div className="src-num">[4]</div>
              <div className="src-body">
                <p className="claim">&ldquo;40% of adults who did not appeal were uncertain about how to go about doing so.&rdquo;</p>
                <p className="cite">
                  AJMC / Commonwealth Fund survey (Feb 2026)
                  <br />
                  <a href="https://www.ajmc.com/view/survey-exposes-pervasive-billing-errors-aggressive-tactics-in-us-health-insurance" target="_blank" rel="noopener noreferrer">
                    ajmc.com
                  </a>
                </p>
              </div>
            </div>
            <div className="src-item">
              <div className="src-num">[5]</div>
              <div className="src-body">
                <p className="claim">&ldquo;$88 billion in medical debt appears on Americans&apos; credit reports — often confusing and erroneous.&rdquo;</p>
                <p className="cite">
                  Consumer Financial Protection Bureau, via Hathr.AI
                  <br />
                  <a href="https://www.hathr.ai/blogs/medical-billing-errors-ai-automation" target="_blank" rel="noopener noreferrer">
                    hathr.ai/blogs/medical-billing-errors-ai-automation
                  </a>
                </p>
              </div>
            </div>
            <div className="src-item">
              <div className="src-num">[6]</div>
              <div className="src-body">
                <p className="claim">Federal patient-provider dispute resolution: $400-over-estimate threshold.</p>
                <p className="cite">
                  Centers for Medicare &amp; Medicaid Services
                  <br />
                  <a href="https://www.cms.gov/medical-bill-rights/help/dispute-a-bill" target="_blank" rel="noopener noreferrer">
                    cms.gov/medical-bill-rights
                  </a>
                </p>
              </div>
            </div>
            <div className="src-item">
              <div className="src-num">[7]</div>
              <div className="src-body">
                <p className="claim">&ldquo;As many as 80 percent of hospital bills contain errors.&rdquo;</p>
                <p className="cite">
                  Healthline — <i>Hospital Bills and Overcharging</i>
                  <br />
                  <a href="https://www.healthline.com/health-news/80-percent-hospital-bills-have-errors-are-you-being-overcharged" target="_blank" rel="noopener noreferrer">
                    healthline.com
                  </a>
                </p>
              </div>
            </div>
            <div className="src-item">
              <div className="src-num">[8]</div>
              <div className="src-body">
                <p className="claim">&ldquo;38% of individuals who contested medical bills saw their balances reduced or eliminated.&rdquo;</p>
                <p className="cite">
                  AJMC / Commonwealth Fund 2026
                  <br />
                  <a href="https://www.ajmc.com/view/survey-exposes-pervasive-billing-errors-aggressive-tactics-in-us-health-insurance" target="_blank" rel="noopener noreferrer">
                    ajmc.com
                  </a>
                </p>
              </div>
            </div>
          </div>
        </div>
      </section> */}
      

      <section id="demo" className="cta-band">
        <motion.h2 {...reveal}>
          Drop a bill.<br />
          <em>We&apos;ll handle the rest.</em>
        </motion.h2>
        <motion.p {...reveal} transition={{ ...reveal.transition, delay: 0.08 }}>
          Sample bills are loaded in the dashboard. Watch three agents reach consensus over the AXL mesh — live, in your browser.
        </motion.p>
        <motion.div className="hero-ctas" {...reveal} transition={{ ...reveal.transition, delay: 0.16 }}>
          <Link className="btn btn-primary" href="/dashboard">
            Open dashboard <span className="arr">→</span>
          </Link>
          <Link className="btn btn-ghost" href="/dashboard">
            Try a sample bill
          </Link>
        </motion.div>
      </section>

      <footer className="foot">
        <div className="foot-grid">
          <div>
            <div className="foot-brand">Lethe</div>
            <div className="foot-tag">
              Medical bills, audited by AI consensus. Forgotten by design. Built at ETHGlobal OpenAgents — April 24 to May 3, 2026.
            </div>
          </div>
          <div className="foot-col">
            <h4>Product</h4>
            <Link href="/dashboard">Dashboard</Link>
            <Link href="/verify">Verify a bill</Link>
            <Link href="/patterns">Patterns</Link>
            <Link href="/axl">Mesh viz</Link>
            <Link href="/tech-stack">Tech stack</Link>
            <a onClick={scrollTo("features")}>Features</a>
            <a onClick={scrollTo("tracks")}>Tracks</a>
          </div>
          <div className="foot-col">
            <h4>Resources</h4>
            <a href="#">README</a>
            <a href="#">Roadmap</a>
            <a onClick={scrollTo("sources")}>Sources</a>
          </div>
          <div className="foot-col">
            <h4>Sponsors</h4>
            <a href="https://0g.ai" target="_blank" rel="noopener noreferrer">0G</a>
            <a href="https://blog.gensyn.ai/introducing-axl/" target="_blank" rel="noopener noreferrer">Gensyn AXL</a>
            <a href="https://keeperhub.com" target="_blank" rel="noopener noreferrer">KeeperHub</a>
          </div>
        </div>
        <div className="foot-bottom">
          <span>MIT · 2026</span>
          <span className="disclaimer">
            Lethe is a hackathon project and is not yet a production medical service. Disputes drafted by Lethe should be reviewed by a human before submission to a real insurer.
          </span>
        </div>
      </footer>
    </>
  );
}
