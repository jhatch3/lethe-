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

        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.55 }}
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
          transition={{ duration: 0.7, delay: 0.7 }}
          style={{ opacity: heroFade }}
          className="hero-foot"
        >
          <span><b>Zero</b> retention</span>
          <span><b>3</b> independent LLMs</span>
          <span><b>2-round</b> AXL P2P consensus</span>
          <span><b>0G</b>: Chain · Storage · Compute</span>
          <span><b>KH</b>: 3 workflows</span>
          <span><b>1</b> contract per chain</span>
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
              Medical billing errors cost Americans <strong>$125 billion</strong> every year. Most of that money is paid by patients who never know they were overcharged.
            </p>
          </motion.div>
          <motion.div className="problem-grid" {...reveal}>
            <div className="problem-cell">
              <div className="problem-stat">$125<span className="pct">B</span></div>
              <h3 className="problem-h">lost to billing errors every year</h3>
              <p className="problem-p">
                ~80% of U.S. medical bills contain at least one error — duplicate codes, wrong modifiers, phantom services — and hospital errors push individual bills 26% above what was actually owed on average. The errors aren&apos;t rare; they&apos;re the default. The cost lands on patients, employers, and premiums.
              </p>
              <div className="source">[1] HealthSureHub · medical billing error statistics &nbsp; [2] Aptarro · 2026 stats</div>
            </div>
            <div className="problem-cell">
              <div className="problem-stat">$88<span className="pct">B</span></div>
              <h3 className="problem-h">in medical debt on credit reports</h3>
              <p className="problem-p">
                The CFPB estimates roughly $88B of medical debt sits on Americans&apos; credit reports — debt the agency calls &ldquo;often confusing and erroneous.&rdquo; Bills that may not even be valid still tank credit scores, block apartments, deny auto loans, and disqualify job applications. ~75% of disputes succeed when patients file — but 40% of adults don&apos;t know how to start.
              </p>
              <div className="source">[3] CFPB / Hathr.AI &nbsp; [4] Solace Health · dispute success rates &nbsp; [5] AJMC 2026 survey</div>
            </div>
            <div className="problem-cell">
              <div className="problem-stat">$31<span className="pct">B</span></div>
              <h3 className="problem-h">in improper federal payments / year</h3>
              <p className="problem-p">
                CMS reports $31B+ in improper Medicare/Medicaid payments annually — separate from the $125B private-pay figure above. That&apos;s taxpayer money flowing to bills that shouldn&apos;t have been paid. ~50% of denied claims are never even resubmitted because the appeal process is too slow.
              </p>
              <div className="source">[6] CMS · FY2024 improper payments fact sheet &nbsp; [7] PCG Software · financial impact of billing errors</div>
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
          </motion.div>
          <motion.p className="section-prose" {...reveal}>
            Your bill enters coordinator memory, gets parsed and redacted, then disappears — never written to disk, never logged, never sent to a model provider, never persisted on-chain. Three independent agents (GPT-4o, Claude, Gemini) reason over the redacted payload, broadcast findings across a real peer-to-peer mesh, and re-vote with each other&apos;s reasoning as context; two of three must agree or the system says <em>clarify</em>. What stays is the proof — a SHA-256, a verdict, and anonymized findings anchored to <code>LetheRegistry</code>{" "}on 0G Galileo and mirrored to Ethereum Sepolia — plus, on dispute, a fourth agent drafts an appeal letter you review and send. Privacy isn&apos;t a setting; it&apos;s the architecture.
          </motion.p>
        </div>
      </section>

      <section id="infrastructure" className="band">
        <div className="container">
          <motion.div className="section-head" {...reveal}>
            <span className="section-num">[ 03 ]</span>
            <h2 className="section-title">
              Built on <span className="em">three pillars.</span>
            </h2>
            <p className="section-kicker">
              Memory, communication, execution — each handled by purpose-built decentralized infrastructure.
            </p>
          </motion.div>
          <motion.div className="tracks" {...reveal}>
            <div className="track a">
              <div className="role">/ memory</div>
              <div className="name">0G — <em>chain · storage · compute</em></div>
              <p>
                Three layers handle different jobs: <strong>Chain</strong> anchors the SHA-256 + verdict of every audit and indexes anonymized findings as on-chain events. <strong>Storage</strong> holds the full schema-versioned audit record off-chain but provably linked. <strong>Compute</strong> can run one of the agents on decentralized inference instead of a closed model API.
              </p>
              <p className="pitch">
                Ephemeral PHI, persistent learning. Agents get smarter without anyone&apos;s records being recoverable.
              </p>
            </div>
            <div className="track b">
              <div className="role">/ communication</div>
              <div className="name">Gensyn AXL — <em>peer-to-peer mesh</em></div>
              <p>
                Each agent has its own cryptographic identity and runs in its own container, joined to a public encrypted mesh. Findings travel directly between agents over the overlay — there is no central message broker, no orchestrator silently nudging the answer, no single point of compromise.
              </p>
              <p className="pitch">
                Independence is verifiable, not just claimed. The mesh is load-bearing — peer review does not happen without it.
              </p>
            </div>
            <div className="track c">
              <div className="role">/ execution</div>
              <div className="name">KeeperHub — <em>workflow orchestration</em></div>
              <p>
                Three workflows fire per audit: mirror the anchor to a second chain, file the dispute on a separate on-chain registry when consensus disagrees, and attest when an appeal letter is sent. Retries, gas optimization, and an audit log are handled automatically.
              </p>
              <p className="pitch">
                If one chain has issues, the proof still lives on the other. Every appeal sent has an immutable receipt.
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
              Medical bills, audited by AI consensus. Forgotten by design.
            </div>
          </div>
          <div className="foot-col">
            <h4>Product</h4>
            <Link href="/dashboard">Dashboard</Link>
            <Link href="/verify">Verify a bill</Link>
            <Link href="/patterns">Patterns</Link>
            <Link href="/my-audits">My audits</Link>
            <Link href="/rules">Rulebook</Link>
            <a onClick={scrollTo("features")}>Features</a>
            <a onClick={scrollTo("infrastructure")}>Infrastructure</a>
          </div>
          <div className="foot-col">
            <h4>Resources</h4>
            <a href="https://github.com/jhatch3/lethe-" target="_blank" rel="noopener noreferrer">GitHub</a>
            <Link href="/axl">AXL mesh</Link>
            <Link href="/tech-stack">Tech stack</Link>
          </div>
          <div className="foot-col">
            <h4>Infrastructure</h4>
            <a href="https://0g.ai" target="_blank" rel="noopener noreferrer">0G</a>
            <a href="https://blog.gensyn.ai/introducing-axl/" target="_blank" rel="noopener noreferrer">Gensyn AXL</a>
            <a href="https://keeperhub.com" target="_blank" rel="noopener noreferrer">KeeperHub</a>
          </div>
        </div>
        <div className="foot-bottom">
          <span>MIT · 2026</span>
          <span className="disclaimer">
            Lethe is in active development. Drafted appeal letters should be reviewed by a human before submission to an insurer.
          </span>
        </div>
      </footer>
    </>
  );
}
