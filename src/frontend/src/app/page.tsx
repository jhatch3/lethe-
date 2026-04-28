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
                Your bill is held in coordinator memory only for the ~60 seconds the audit takes, then zeroed. Nothing is written to disk, nothing reaches a model provider, nothing about the original bill is persisted on-chain. The privacy guarantee is the architecture — not a policy you have to trust.
              </p>
              <div className="tick">— never written · never logged · never sent</div>
            </div>
            <div className="feat amber">
              <div className="label">3-agent independent consensus</div>
              <h3>Three minds, one verdict.</h3>
              <p>
                GPT-4o, Claude, and Gemini reason over the redacted payload independently — different training data, different blind spots, no shared scratchpad. A finding only enters the result when at least two of three agree on the canonical billing code. If they split three ways, the system says &ldquo;clarify&rdquo; instead of pretending to be sure.
              </p>
              <div className="tick">— quorum 2/3 · clarify on tie</div>
            </div>
            <div className="feat violet">
              <div className="label">Decentralized agents</div>
              <h3>No central broker.</h3>
              <p>
                Each agent runs in its own container with its own cryptographic identity, joined to a peer-to-peer mesh. Findings travel agent-to-agent over an encrypted overlay network — there&apos;s no orchestrator nudging the answer and no single point an attacker could compromise to silently sway a verdict.
              </p>
              <div className="tick">— ed25519 identity · encrypted mesh</div>
            </div>
            <div className="feat pink">
              <div className="label">Consensus through debate</div>
              <h3>Agents that change their minds.</h3>
              <p>
                After the first independent vote, every agent sees its peers&apos; findings and runs a second pass — adding evidence it missed, dropping claims peers convinced it were wrong, or holding firm. The final verdict runs on the post-debate votes; nothing makes it through that didn&apos;t survive peer review.
              </p>
              <div className="tick">— vote → exchange → reflect → tally</div>
            </div>
            <div className="feat rose">
              <div className="label">Verifiable on-chain</div>
              <h3>One registry, two chains.</h3>
              <p>
                Every audit&apos;s SHA-256, verdict, finding events, provider stats, and storage pointer are anchored on a single deployed contract per chain — canonical on 0G Galileo, mirrored to Ethereum Sepolia. Three workflow methods (anchor, dispute filing, appeal-sent attestation) on the same address. Anyone with the bill&apos;s hash can verify the full audit trail from either explorer, forever.
              </p>
              <div className="tick">— LetheRegistry · canonical + mirror</div>
            </div>
            <div className="feat cyan">
              <div className="label">Smarter every audit</div>
              <h3>Memory that compounds.</h3>
              <p>
                Anonymized findings from past audits live on-chain as Finding events; the full schema-versioned audit blob lives in 0G Storage with the merkle root anchored alongside the bill. Future runs query both layers and feed dispute / clarify rates per code into the agents&apos; priors. The system gets sharper without ever knowing whose bills produced the patterns.
              </p>
              <div className="tick">— learn from past · zero PHI</div>
            </div>
            <div className="feat ink">
              <div className="label">Auto-drafted appeal</div>
              <h3>A letter, ready when you are.</h3>
              <p>
                When consensus lands on dispute, a separate model drafts a formal appeal letter with regulatory citations. You review it, edit it, choose who to send it to — Lethe never auto-submits to an insurer. The letter plus full chain verification can be emailed to the provider&apos;s billing department directly from the dashboard.
              </p>
              <div className="tick">— draft → review → send when you&apos;re ready</div>
            </div>
            <div className="feat amber">
              <div className="label">On-chain provider reputation</div>
              <h3>Patterns by NPI, not by patient.</h3>
              <p>
                Each audit&apos;s provider NPI is salted-hashed and rolled into a public dispute-rate aggregate on the same contract. Visit <code>/providers/&lt;npi&gt;</code> for any provider&apos;s running stats — total audits, dispute rate, total flagged dollars — read directly from chain. Individual bills aren&apos;t linkable; the pattern is.
              </p>
              <div className="tick">— salted NPI hash · per-provider stats</div>
            </div>
            <div className="feat green">
              <div className="label">File with the insurer</div>
              <h3>One click, structured claim.</h3>
              <p>
                After consensus, the dashboard can dispatch the disputed-codes packet directly to the insurance payer or clearinghouse via X12 837 / FHIR Claim. Five adapters registered (Stedi · Availity · Change Healthcare · direct FHIR · stub). The provider gets the appeal letter; the payer gets a formal claim — both with the same on-chain receipt.
              </p>
              <div className="tick">— X12 837 · FHIR · pluggable adapters</div>
            </div>
            <div className="feat violet">
              <div className="label">Audit history, your wallet</div>
              <h3>Every receipt, scoped to you.</h3>
              <p>
                Connect a wallet (any EIP-1193 — MetaMask, Rabby, Coinbase) and the dashboard remembers every audit you&apos;ve run. Bill SHA, verdict, chain tx, and timestamp persist locally per wallet address — never sent to a server, switchable across wallets, removable on disconnect. Strictly opt-in personal index.
              </p>
              <div className="tick">— EIP-1193 · localStorage · zero-server</div>
            </div>
            <div className="feat pink">
              <div className="label">Versioned coding rules</div>
              <h3>NCCI rulebook, anchored.</h3>
              <p>
                CMS&apos;s NCCI coding rules (bundling pairs, modifier requirements, units caps) live as a JSON manifest in 0G Storage; the manifest hash is anchored on-chain so every audit ties to a specific rules version. The rules update once per quarter via one tx — no contract redeploy, no coordinator restart.
              </p>
              <div className="tick">— rules JSON in 0G Storage · manifest hash on-chain</div>
            </div>
          </motion.div>
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
