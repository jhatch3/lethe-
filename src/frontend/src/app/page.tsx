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

        <motion.div
          className="scroll-cue"
          style={{ opacity: heroFade }}
          aria-hidden="true"
        >
          <span className="cue-arrow">↓</span>
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
                Roughly 80% of U.S. medical bills contain at least one error. Duplicate codes, wrong modifiers, phantom services. On the bills that have errors, hospital overcharges average 26% above what was actually owed. The errors aren&apos;t rare. They&apos;re the default. And the cost lands on patients, employers, and premiums.
              </p>
              <div className="source">[1] HealthSureHub · medical billing error statistics &nbsp; [2] Aptarro · 2026 stats</div>
            </div>
            <div className="problem-cell">
              <div className="problem-stat">$88<span className="pct">B</span></div>
              <h3 className="problem-h">in medical debt on credit reports</h3>
              <p className="problem-p">
                The CFPB estimates roughly $88B of medical debt sits on Americans&apos; credit reports. The agency calls a lot of it &ldquo;confusing and erroneous.&rdquo; Bills that may not even be valid still tank credit scores, block apartments, deny auto loans, and disqualify job applications. About 75% of disputes succeed when patients actually file one. The catch: 40% of adults don&apos;t know how to start.
              </p>
              <div className="source">[3] CFPB / Hathr.AI &nbsp; [4] Solace Health · dispute success rates &nbsp; [5] AJMC 2026 survey</div>
            </div>
            <div className="problem-cell">
              <div className="problem-stat">$31<span className="pct">B</span></div>
              <h3 className="problem-h">in improper federal payments / year</h3>
              <p className="problem-p">
                CMS reports $31B+ in improper Medicare/Medicaid payments every year. That&apos;s separate from the $125B private-pay figure above. Taxpayer money, flowing to bills that shouldn&apos;t have been paid. And about half of denied claims never get resubmitted because the appeal process is too slow.
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
            Your bill goes to the coordinator, gets parsed for billing codes, then PHI-redacted before anything leaves that process. The model providers only see the redacted payload: CPT/ICD codes, modifiers, charges, and dates of service. The original PDF stays in coordinator memory and is dropped when the audit ends. From there, three independent agents (GPT-4o, Claude Sonnet 4.5, Gemini Flash) reason over the redacted payload, broadcast their findings across a real Gensyn AXL peer-to-peer mesh, and re-vote with each other&apos;s findings as context. Action only fires when <em>≥2 of 3</em> agree. What we keep is just the proof: a SHA-256 of the original on <code>BillRegistry</code> (0G Galileo), the same record mirrored to Sepolia, anonymized findings on <code>PatternRegistry</code>, and the full audit record (findings, votes, drafts; not the bill) in 0G Storage, pointer-anchored on <code>StorageIndex</code>. If consensus is dispute, a fourth agent drafts an appeal letter you review before it sends. Privacy isn&apos;t a setting. It&apos;s the architecture.
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
              Memory, communication, execution. Each one handled by purpose-built decentralized infrastructure.
            </p>
          </motion.div>
          <motion.div className="tracks" {...reveal}>
            <div className="track a">
              <div className="role">/ memory</div>
              <div className="name">0G <em>· chain, storage, compute</em></div>
              <p>
                Three layers doing three different jobs. <strong>Chain.</strong> <code>BillRegistry</code> on 0G Galileo anchors the SHA-256 and verdict of every audit. <code>PatternRegistry</code> indexes anonymized findings as on-chain events the next audit can learn from. <strong>Storage.</strong> The full audit record (findings, votes, drafts; not the bill) lives on 0G Storage, with a merkle root pointer recorded on the <code>StorageIndex</code> contract so anyone can verify the record they&apos;re reading is the one that was anchored. <strong>Compute.</strong> The 0G compute broker is provisioned so an agent can run on decentralized inference instead of a closed model API.
              </p>
              <p className="pitch">
                Ephemeral PHI, durable proof. The bill is gone. The verdict isn&apos;t.
              </p>
            </div>
            <div className="track b">
              <div className="role">/ communication</div>
              <div className="name">Gensyn AXL <em>· peer-to-peer mesh</em></div>
              <p>
                Each agent has its own ed25519 identity and runs in its own AXL sidecar, joined to an encrypted overlay. Findings travel directly between peers. There&apos;s no central broker, no orchestrator silently nudging the answer toward consensus. Round 2 happens on the mesh: each agent re-votes with the other two&apos;s findings as context, and only then does the coordinator count the votes.
              </p>
              <p className="pitch">
                Independence is verifiable, not just claimed. Peer review does not happen without the mesh. It&apos;s load-bearing, not decoration.
              </p>
            </div>
            <div className="track c">
              <div className="role">/ execution</div>
              <div className="name">KeeperHub <em>· workflow orchestration</em></div>
              <p>
                Three KeeperHub workflows per audit. <strong>(1)</strong> Mirror the 0G anchor to Sepolia. <strong>(2)</strong> When consensus is <em>dispute</em>, file on the Sepolia <code>DisputeRegistry</code>. <strong>(3)</strong> When you click <em>Send appeal</em>, record an attestation on <code>AppealRegistry</code> as the email goes out. Retries, gas, and the run log are handled by the keeper.
              </p>
              <p className="pitch">
                If one chain stalls, the proof lives on the other. Every appeal sent has an immutable receipt.
              </p>
            </div>
          </motion.div>
        </div>
      </section>

      <section id="patterns" className="band">
        <div className="container">
          <motion.div className="section-head" {...reveal}>
            <span className="section-num">[ 04 ]</span>
            <h2 className="section-title">
              Patterns <span className="em">that learn.</span>
            </h2>
            <p className="section-kicker">
              Anonymized findings, anchored on chain, queryable by anyone, and used as priors on the next audit.
            </p>
          </motion.div>
          <motion.div className="split-row" {...reveal}>
            <div className="split-text">
              <p>
                Every audit emits one event per consensus finding to the on-chain <code>PatternRegistry</code> on 0G Galileo. No PHI ever leaves the coordinator. Only the billing code, the action the agents took (<em>dispute</em>, <em>clarify</em>, or <em>aligned</em>), the severity, and the dollar amount.
              </p>
              <p className="dim">
                The next audit reads those stats as priors. Agents see something like <em>&ldquo;CPT 99214 has been disputed 67% of the time across 47 prior audits&rdquo;</em> and calibrate their confidence accordingly. The system gets sharper over time, without anyone&apos;s records being recoverable.
              </p>
              <Link href="/patterns" className="btn btn-ghost split-cta">
                Browse the registry <span className="arr">→</span>
              </Link>
            </div>
            <div className="explain-card">
              <div className="card-eyebrow">PatternRegistry &middot; 0G Galileo</div>
              <div className="pattern-row">
                <span className="p-code">CPT 99214</span>
                <span className="p-desc">Office visit, established patient (moderate complexity)</span>
                <span className="p-amt">$245</span>
              </div>
              <div className="pattern-stats">
                <div className="ps">
                  <span className="ps-num">47</span>
                  <span className="ps-label">Observations</span>
                </div>
                <div className="ps">
                  <span className="ps-num warn">67%</span>
                  <span className="ps-label">Dispute rate</span>
                </div>
                <div className="ps">
                  <span className="ps-num">12%</span>
                  <span className="ps-label">Clarify rate</span>
                </div>
              </div>
              <div className="card-foot">
                Read by every audit before round 1. Written to by every audit after consensus.
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      <section id="rules" className="band">
        <div className="container">
          <motion.div className="section-head" {...reveal}>
            <span className="section-num">[ 05 ]</span>
            <h2 className="section-title">
              Rules <span className="em">anyone can read.</span>
            </h2>
            <p className="section-kicker">
              The same NCCI ruleset CMS publishes, codified on chain so every audit is grounded in the same canonical source.
            </p>
          </motion.div>
          <motion.div className="split-row" {...reveal}>
            <div className="split-text">
              <p>
                CMS publishes the <strong>NCCI</strong> (National Correct Coding Initiative) ruleset quarterly: which codes are mutually exclusive, which require modifiers, which have units caps. Lethe codifies the active rules in an on-chain <code>NCCIRulebook</code> contract on 0G Galileo.
              </p>
              <p className="dim">
                Audit agents query this contract at reasoning time, so every audit is grounded in the same canonical ruleset. <em>No hidden vendor configuration. No opaque overrides.</em> If a ruling looks wrong, you can read the rule that produced it, and the rule&apos;s citation back to CMS.
              </p>
              <Link href="/rules" className="btn btn-ghost split-cta">
                Open the rulebook <span className="arr">→</span>
              </Link>
            </div>
            <div className="explain-card">
              <div className="card-eyebrow">NCCIRulebook &middot; v2025-Q3</div>
              <div className="rule-row">
                <span className="r-kind">modifier_required</span>
                <span className="r-codes">
                  CPT 99213 <span className="arrow">+</span> 11042 <span className="mod">requires modifier 25</span>
                </span>
                <span className="r-cite">When an E&amp;M service is performed same-day as a procedure, modifier 25 is required to indicate it was significant and separately identifiable.</span>
              </div>
              <div className="rule-row">
                <span className="r-kind">mutually_exclusive</span>
                <span className="r-codes">
                  CPT 80061 <span className="arrow">×</span> 82465
                </span>
                <span className="r-cite">A lipid panel already includes total cholesterol; billing both as separate line items is a duplicate.</span>
              </div>
              <div className="card-foot">
                3 rule kinds shown of 5 codified · queryable from any chain
              </div>
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
