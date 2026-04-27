<div align="center">

<img src="./assets/banner.png" alt="Lethe banner" width="100%" />

<h3>Medical bills, audited by AI consensus.<br/>Forgotten by design.</h3>

<p>
  Your bill is parsed and redacted locally. The AI never sees your PHI.<br/>
  Three independent agents vote on the redacted payload over a real Gensyn AXL mesh. Anything they agree is wrong is drafted into an appeal.<br/>
  The original bill is held in coordinator memory only — never written to disk, never persisted on-chain.
</p>

<p>
  <a href="./SETUP.md"><img src="https://img.shields.io/badge/Setup_Guide-22c55e?style=for-the-badge&logoColor=white" alt="Setup Guide" /></a>
  <a href="https://ethglobal.com/events/openagents"><img src="https://img.shields.io/badge/ETHGlobal-OpenAgents-a78bfa?style=for-the-badge" alt="ETHGlobal OpenAgents" /></a>
</p>

<p>
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License" />
  <img src="https://img.shields.io/badge/status-hackathon--build-orange.svg" alt="Status" />
  <img src="https://img.shields.io/badge/PHI-zero%20retention-22c55e.svg" alt="Zero Retention" />
  <img src="https://img.shields.io/badge/agents-3%20independent%20LLMs-fbbf24.svg" alt="Agents" />
  <img src="https://img.shields.io/badge/transport-Gensyn%20AXL-c084fc.svg" alt="Transport" />
</p>

<br />

<img src="./assets/dash.png" alt="Lethe dashboard" width="90%" />

</div>

<br />

---

## 🩺 The problem

<table>
<tr>
<td width="33%" valign="top">

### 80% of bills overcharge
Surveys consistently find that the majority of itemized hospital bills contain at least one error in the patient's disfavor: duplicated codes, wrong modifiers, services that never happened.

</td>
<td width="33%" valign="top">

### Disputing is brutal
The standard process means hours on the phone, navigating insurer portals, drafting appeal letters, and waiting weeks for a response. Most patients never start.

</td>
<td width="33%" valign="top">

### The few tools that exist store everything
Existing services upload your records to a central database and keep them indefinitely. That's the opposite of what a HIPAA-anxious patient wants.

</td>
</tr>
</table>

---

## ✨ What Lethe does

Drop in a medical bill. A deterministic PDF parser extracts the structured data (CPT/ICD codes, modifiers, charges, dates of service) and a redaction pass strips every piece of PHI (patient name, DOB, address, MRN, account numbers) — *before any AI ever sees the payload*. Three independent AI agents (GPT-4o, Claude Sonnet, Gemini Flash) — each broadcasting the redacted payload to two real ed25519 peers over a [Gensyn AXL](https://blog.gensyn.ai/introducing-axl/) mesh joined to the public Gensyn network — analyze the bill in parallel. They vote. A finding only enters the final result if at least 2 of 3 agents flag it. A fourth agent (Claude) drafts a formal appeal letter from the agreed-on findings.

The original bill never touches storage and never reaches a model provider. It lives in coordinator memory long enough for the parser and redactor to run, then it's discarded. What persists is a SHA-256 hash anchored on [0G Chain](https://0g.ai) (proof of *what was analyzed*), the same hash mirrored to a Sepolia `BillRegistry` via [KeeperHub](https://keeperhub.com), and an anonymized pattern record on a 0G `PatternRegistry` that makes the next user's analysis smarter without anyone's records being recoverable.

---

## 🏗️ Architecture

```mermaid
flowchart TB
    subgraph Client["🖥️ Client"]
        UI[Next.js Dashboard<br/>upload · SSE viewer · receipt PDF]
    end

    subgraph Coordinator["⚙️ FastAPI Coordinator (single process)"]
        Parse[Parser<br/>PDF / TXT / image → structured]
        Redact[PHI Redactor<br/>regex + LLM sweep]
        AlphaC[Agent α client<br/>GPT-4o]
        BetaC[Agent β client<br/>Claude Sonnet 4.5]
        GammaC[Agent γ client<br/>Gemini Flash]
        Tally[Consensus<br/>2-of-3 quorum]
        Drafter[Drafter<br/>Claude → appeal letter]
    end

    subgraph AXL["🕸️ Gensyn AXL P2P (3 Docker sidecars)"]
        S1[axl-alpha<br/>ed25519 c4737e16…]
        S2[axl-beta<br/>ed25519 fc40f9dd…]
        S3[axl-gamma<br/>ed25519 739dd219…]
        Mesh((Yggdrasil mesh<br/>· public Gensyn peers))
    end

    subgraph LLMs["☁️ Model APIs"]
        OAI[OpenAI]
        ANT[Anthropic]
        GOO[Google]
    end

    subgraph Chain["⛓️ Chain anchors"]
        ZG[0G Galileo<br/>BillRegistry + PatternRegistry]
        KH[KeeperHub<br/>Direct Execution]
        Sep[Sepolia<br/>BillRegistry mirror]
    end

    UI -->|POST /api/jobs| Parse
    Parse -->|in-memory only| Redact
    Redact -->|redacted payload| AlphaC & BetaC & GammaC

    AlphaC <-->|HTTP| S1
    BetaC <-->|HTTP| S2
    GammaC <-->|HTTP| S3
    S1 <-->|TLS| Mesh
    S2 <-->|TLS| Mesh
    S3 <-->|TLS| Mesh

    AlphaC -->|HTTPS| OAI
    BetaC -->|HTTPS| ANT
    GammaC -->|HTTPS| GOO

    AlphaC & BetaC & GammaC --> Tally
    Tally --> Drafter
    Tally -->|sha-256 + verdict| ZG
    Tally -->|same hash| KH
    KH --> Sep
    Tally -->|anonymized findings| ZG

    Drafter --> UI
    Tally -->|SSE events| UI

    classDef client    fill:#0b1220,stroke:#60a5fa,stroke-width:2px,color:#fff
    classDef orch      fill:#0b1220,stroke:#34d399,stroke-width:2px,color:#fff
    classDef axl       fill:#0b1220,stroke:#c084fc,stroke-width:2px,color:#fff
    classDef llm       fill:#0b1220,stroke:#fbbf24,stroke-width:2px,color:#fff
    classDef chain     fill:#0b1220,stroke:#f472b6,stroke-width:2px,color:#fff

    class UI client
    class Parse,Redact,AlphaC,BetaC,GammaC,Tally,Drafter orch
    class S1,S2,S3,Mesh axl
    class OAI,ANT,GOO llm
    class ZG,KH,Sep chain
```

> 📐 **Setup, env vars, and verification commands** are in [`SETUP.md`](./SETUP.md).

---

## 🎯 Features (as of April 26, 2026)

<table>
<tr>
<td width="50%" valign="top">

### 🔒 Zero retention, zero PHI exposure
A deterministic parser handles PDFs (with image fallback) inside the coordinator. PHI is then stripped by a regex pass plus an LLM redactor sweep, all *before any audit agent sees the payload*. Bill bytes are zeroed from memory immediately after the parse stage; only the redacted payload travels further. SSE events carry only stage names, verdicts, and counts — no bill content.

</td>
<td width="50%" valign="top">

### 🤖 3-agent LLM consensus
GPT-4o (α), Claude Sonnet 4.5 (β), and Gemini Flash (γ) each independently analyze the redacted payload. The verdict is the majority vote; a finding only survives with ≥2-of-3 quorum on the canonical billing code. When no verdict reaches majority (a 1-1-1 split), the system honestly falls back to **clarify** rather than letting registration order silently pick a winner. Confidence is the mean across the winning side.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🕸️ Real Gensyn AXL P2P transport
Each of the three agents has its own AXL sidecar Docker container running the upstream Gensyn `node` binary with a unique ed25519 peer ID. Sidecars join the public Gensyn mesh and exchange the redacted payload via real `POST /send` calls before reasoning. The `/axl` page shows live mesh topology with verified peer keys, and during each audit the dashboard streams real broadcast events into the agent terminals (`⇆ axl · sent NB → β γ · ed25519:c4737e16…`) so you can watch the cross-talk happen.

</td>
<td width="50%" valign="top">

### ⛓️ Dual-chain anchor + on-chain priors
Every audit anchors the bill SHA-256 + verdict to a `BillRegistry` on the 0G Galileo testnet (canonical) and mirrors the same record to a Sepolia `BillRegistry` via KeeperHub Direct Execution. Anonymized findings are written to a `PatternRegistry` on 0G — and read back on the next run as priors, so the system literally learns from itself.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🧠 Read-back pattern loop
Before each new audit, the coordinator queries `eth_getLogs` on the `PatternRegistry` and formats prior dispute / clarify rates per code into the agents' system prompts. The next run's reasoning shifts based on what previous runs found.

</td>
<td width="50%" valign="top">

### ✍️ Auto-drafted appeal letter
A fourth agent (Claude, separately prompted) takes the consensus findings and writes a formal, citation-bearing appeal letter. The dashboard renders it as an ASCII-bordered receipt PDF you can review and download — Lethe never auto-submits anything to an insurer.

</td>
</tr>
</table>

---

## 🛠️ Built with

<div align="center">

<table>
<tr>
<td align="center" width="16%"><img src="https://cdn.simpleicons.org/nextdotjs/000000" width="40" /><br/><sub><b>Next.js 16</b></sub></td>
<td align="center" width="16%"><img src="https://cdn.simpleicons.org/react/61dafb" width="40" /><br/><sub><b>React 19</b></sub></td>
<td align="center" width="16%"><img src="https://cdn.simpleicons.org/typescript/3178c6" width="40" /><br/><sub><b>TypeScript</b></sub></td>
<td align="center" width="16%"><img src="https://cdn.simpleicons.org/tailwindcss/06b6d4" width="40" /><br/><sub><b>Tailwind v4</b></sub></td>
<td align="center" width="16%"><img src="https://cdn.simpleicons.org/framer/0055ff" width="40" /><br/><sub><b>Framer Motion</b></sub></td>
<td align="center" width="16%"><img src="https://placehold.co/40x40/0f172a/d4a373/png?text=jsPDF" width="40" /><br/><sub><b>jsPDF</b></sub></td>
</tr>
<tr>
<td align="center"><img src="https://cdn.simpleicons.org/python/3776ab" width="40" /><br/><sub><b>Python 3.11</b></sub></td>
<td align="center"><img src="https://cdn.simpleicons.org/fastapi/009688" width="40" /><br/><sub><b>FastAPI</b></sub></td>
<td align="center"><img src="https://placehold.co/40x40/0f172a/4ade80/png?text=pdf" width="40" /><br/><sub><b>pdfplumber</b></sub></td>
<td align="center"><img src="https://placehold.co/40x40/0f172a/c084fc/png?text=httpx" width="40" /><br/><sub><b>httpx</b></sub></td>
<td align="center"><img src="https://cdn.simpleicons.org/docker/2496ed" width="40" /><br/><sub><b>Docker Compose</b></sub></td>
<td align="center"><img src="https://cdn.simpleicons.org/github/000000" width="40" /><br/><sub><b>GitHub</b></sub></td>
</tr>
<tr>
<td align="center"><img src="https://cdn.simpleicons.org/solidity/363636" width="40" /><br/><sub><b>Solidity</b></sub></td>
<td align="center"><img src="https://cdn.simpleicons.org/ethereum/3c3c3d" width="40" /><br/><sub><b>web3.py</b></sub></td>
<td align="center"><img src="https://cdn.simpleicons.org/openai/000000" width="40" /><br/><sub><b>GPT-4o</b></sub></td>
<td align="center"><img src="https://cdn.simpleicons.org/anthropic/d4a373" width="40" /><br/><sub><b>Claude</b></sub></td>
<td align="center"><img src="https://cdn.simpleicons.org/googlegemini/8e75b2" width="40" /><br/><sub><b>Gemini</b></sub></td>
<td align="center"><img src="https://cdn.simpleicons.org/go/00add8" width="40" /><br/><sub><b>Gensyn AXL (Go)</b></sub></td>
</tr>
</table>

<sub>Frontend · Coordinator · Chain & AI</sub>

</div>

---

## 🏆 Hackathon tracks

Built for [ETHGlobal OpenAgents](https://ethglobal.com/events/openagents), April 24 – May 3, 2026.

<table>
<tr>
<td width="33%" valign="top" align="center">

### [0G](https://0g.ai)
**The blockchain for AI agents**

Lethe deploys two contracts (`BillRegistry`, `PatternRegistry`) to the 0G Galileo testnet and writes to both on every audit. The pattern read-back loop (priors fetched via `eth_getLogs`) is the load-bearing piece: ephemeral PHI, persistent learning.

</td>
<td width="33%" valign="top" align="center">

### [Gensyn AXL](https://blog.gensyn.ai/introducing-axl/)
**Peer-to-peer agent communication**

Three Docker sidecars run the upstream Gensyn `node` binary, each with its own ed25519 keypair, joined to the public Gensyn mesh via two TLS bootstrap peers. Every audit fires real `POST /send` broadcasts before reasoning — verifiable on the `/axl` topology page.

</td>
<td width="33%" valign="top" align="center">

### [KeeperHub](https://keeperhub.com)
**Reliable onchain execution**

Every BillRegistry anchor on 0G Galileo is mirrored via KeeperHub's Direct Execution API to a separate Sepolia `BillRegistry` — same hash, two independent chains. Receipts include both transaction hashes for cross-chain verifiability.

</td>
</tr>
</table>

---

## 🚀 Quick start

```bash
git clone https://github.com/Justyhatch3/lethe-.git
cd lethe-
cp .env.example .env       # then fill in API keys + 0G testnet wallet + KeeperHub key
docker compose up --build
open http://localhost:3000
```

The compose file spins up:
- `axl-alpha`, `axl-beta`, `axl-gamma` — three Gensyn AXL sidecars (Go `node` binary, distinct ed25519 keypairs)
- `coordinator` — FastAPI orchestrator (parser, redactor, agent clients, consensus, drafter, chain writes)
- `frontend` — Next.js dashboard

For full env-var documentation, local-dev (no-Docker) instructions, and verification commands, see [**SETUP.md**](./SETUP.md).

### Try it

1. Open `http://localhost:3000/dashboard`.
2. Click one of the **sample bill chips** (general-hospital ER, imaging-center CT, ortho-clinic MRI, discharge summary, labs itemized) — each ships in `src/coordinator/samples/`.
3. Watch the SSE pipeline run through eight stages: parse → redact → broadcast → reason → consensus → anchor → patterns → draft.
4. During `reason`, each agent terminal shows real AXL chatter (`⇆ axl · sent NB → β γ · ed25519:c4737e16…`) before LLM tokens stream in.
5. After `done`, copy the 0G tx hash and paste it into [chainscan-galileo.0g.ai](https://chainscan-galileo.0g.ai) — or hit the `/verify` page in-app.

### Other in-app pages

| Page | What it shows |
|------|---------------|
| `/dashboard` | Upload + run + live SSE consensus + receipt PDF download |
| `/axl` | Live mesh topology — three peer cards with expected vs observed pubkeys |
| `/patterns` | Anonymized prior-probability table read from `PatternRegistry` on 0G |
| `/verify` | Paste a SHA-256, look up its anchor on 0G Galileo and the Sepolia mirror |

---

## 🎬 Demo

| | |
|---|---|
| 🎥 **Demo video** | [Watch on YouTube →](#) |
| 🌐 **Live demo** | [lethe-demo.vercel.app](#) |
| 📜 **Pitch deck** | [View slides →](#) |
| 📐 **Setup & verification** | [SETUP.md](./SETUP.md) |

<div align="center">
  <img src="https://placehold.co/600x340/0f172a/4ade80/png?text=Upload+Flow" alt="Upload" width="49%" />
  <img src="https://placehold.co/600x340/0f172a/fbbf24/png?text=Live+Consensus" alt="Consensus" width="49%" />
  <br />
  <img src="https://placehold.co/600x340/0f172a/c084fc/png?text=On-Chain+Receipt" alt="Receipt" width="49%" />
  <img src="https://placehold.co/600x340/0f172a/f87171/png?text=Drafted+Dispute" alt="Dispute" width="49%" />
</div>

---

## 📁 Repository structure

```
lethe-/
├── src/
│   ├── frontend/              # Next.js 16 dashboard (App Router, TS, Tailwind v4)
│   │   └── src/app/{dashboard,axl,patterns,verify}/page.tsx
│   ├── coordinator/           # FastAPI orchestrator
│   │   ├── main.py            # app entry + CORS + sweeper
│   │   ├── routers/           # jobs, samples, status, verify
│   │   ├── pipeline/          # runner, parser, redactor, consensus, dispute
│   │   ├── agents/            # audit_{openai,anthropic,google}, drafter, transport_axl, prompts
│   │   ├── chain/             # zerog (anchor), keeperhub (mirror), zerog_storage (patterns)
│   │   ├── samples/           # 5 example bills used by the dashboard chips
│   │   └── store/             # in-memory job store + sweeper, rolling stats
│   └── contracts/             # BillRegistry.sol + PatternRegistry.sol (deployed via deploy.py / py-solc-x)
├── infra/
│   └── axl/                   # Dockerfile, configs/{alpha,beta,gamma}.json, keys/peer_ids.json
├── data-gen/                  # Bill PDF generator (sample creation utility)
├── docker-compose.yml         # axl-alpha, axl-beta, axl-gamma, coordinator, frontend
├── SETUP.md                   # Full setup + verification guide
└── README.md
```

---

## 👥 Team

<table>
<tr>
<td align="center" width="50%">
  <img src="./assets/jmoney.jpg" width="100" /><br />
  <b>Justin Hatch</b><br />
  <a href="https://github.com/Justyhatch3">GitHub</a> · <a href="https://www.linkedin.com/in/justinhatch/">LinkedIn</a>
</td>
<td align="center" width="50%">
  <img src="https://placehold.co/120x120/1e293b/94a3b8/png?text=DM" width="100" /><br />
  <b>Drew Manley</b><br />
  <a href="https://github.com/drewmanley16">GitHub</a> · <a href="https://www.linkedin.com/in/drewmanley/">LinkedIn</a>
</td>
</tr>
</table>

---

## 🙏 Acknowledgments

<table>
<tr>
<td valign="middle" width="20%" align="center" bgcolor="#ffffff">
  <a href="https://www.oregonblockchain.org">
    <img src="./assets/obg.webp" alt="Oregon Blockchain Group" width="100" />
  </a>
</td>
<td valign="middle">

### [Oregon Blockchain Group](https://www.oregonblockchain.org)

Built with support from the **Oregon Blockchain Group** at the University of Oregon, a student-led organization at the heart of the Pacific Northwest blockchain ecosystem and part of the [University Blockchain Research Initiative](https://ripple.com/impact/ubri/).

[Website](https://www.oregonblockchain.org) · [LinkedIn](https://www.linkedin.com/company/oregonblockchain) · [Twitter](https://x.com/oregonblock) · [Instagram](https://www.instagram.com/oregonblockchaingroup/)

</td>
</tr>
</table>

Special thanks to the sponsors of the ETHGlobal OpenAgents tracks: [0G Labs](https://0g.ai), [Gensyn](https://www.gensyn.ai), and [KeeperHub](https://keeperhub.com), for the infrastructure that makes Lethe possible.

---

## 📄 License

[MIT](./LICENSE) © 2026. Built at [ETHGlobal OpenAgents](https://ethglobal.com/events/openagents)

<br />

<div align="center">

<sub>Lethe is a hackathon project and is not yet a production medical service.<br/>
Disputes drafted by Lethe should be reviewed by a human before submission to a real insurer.</sub>

<br /><br />

<a href="#-quick-start"><b>↑ Back to top ↑</b></a>

</div>
