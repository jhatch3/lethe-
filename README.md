<div align="center">

<img src="./assets/banner.png" alt="Lethe banner" width="100%" />

<h4><sub><i>Lethe</i> &nbsp;·&nbsp; <code>/ˈliː.θi/</code> &nbsp;·&nbsp; LEE-thee &nbsp;·&nbsp; the river of forgetfulness in Greek mythology</sub></h4>

<h3>Medical bills, audited by AI consensus.<br/>Forgotten by design.</h3>

<p>
  Your bill is parsed and redacted locally. The AI never sees your PHI.<br/>
  Three independent agents vote on the redacted payload over a real Gensyn AXL mesh. Anything they agree is wrong is drafted into an appeal.<br/>
  The original bill is held in coordinator memory only — never written to disk, never persisted on-chain.
</p>

<p>
  <a href="./SETUP.md"><img src="https://img.shields.io/badge/Setup-22c55e?style=for-the-badge&logoColor=white" alt="Setup Guide" /></a>
  <a href="./whitepaper.pdf"><img src="https://img.shields.io/badge/Whitepaper-0b6cda?style=for-the-badge&logoColor=white" alt="Whitepaper" /></a>
  <a href="https://github.com/jhatch3/lethe-"><img src="https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub" /></a>
</p>

<p>
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License" />
  <img src="https://img.shields.io/badge/PHI-zero%20retention-22c55e.svg" alt="Zero Retention" />
  <img src="https://img.shields.io/badge/agents-3%20independent%20LLMs-fbbf24.svg" alt="Agents" />
  <img src="https://img.shields.io/badge/transport-P2P%20mesh-c084fc.svg" alt="Transport" />
  <img src="https://img.shields.io/badge/consensus-2--round%20peer%20review-f472b6.svg" alt="Two-round consensus" />
  <img src="https://img.shields.io/badge/anchored%20on-2%20chains-0b6cda.svg" alt="Two chains" />
</p>

<br />

<img src="./assets/dash.png" alt="Lethe dashboard" width="90%" />

</div>

<br />

---

## 📑 Table of contents

- [🩺 The problem](#-the-problem)
- [📊 Why this matters (data points)](#-why-this-matters-data-points)
- [✨ What Lethe does](#-what-lethe-does)
- [🏗️ Architecture](#%EF%B8%8F-architecture)
- [🎯 Features](#-features-as-of-april-27-2026)
- [🛠️ Built with](#%EF%B8%8F-built-with)
- [⛓️ On-chain artifacts](#%EF%B8%8F-on-chain-artifacts)
- [📘 Contract reference](#-contract-reference)
- [🏆 Hackathon tracks](#-hackathon-tracks)
- [🎬 Demo](#-demo)
- [📁 Repository structure](#-repository-structure)
- [👥 Team](#-team)
- [🙏 Acknowledgments](#-acknowledgments)
- [📄 License](#-license)

> Setup, env vars, and verification: **[SETUP.md](./SETUP.md)**.

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

## 📊 Why this matters (data points)

### 💸 Financial impact
- **$125B annual U.S. losses** tied to medical billing errors ([HealthSureHub](https://healthsurehub.com/medical-billing-error-statistics/?utm_source=chatgpt.com))
- **38% of people who dispute bills get charges reduced or eliminated** ([AJMC](https://www.ajmc.com/view/survey-exposes-pervasive-billing-errors-aggressive-tactics-in-us-health-insurance?utm_source=chatgpt.com))
- **$31B+ improper Medicare/Medicaid payments per year** ([CMS](https://www.cms.gov/newsroom/fact-sheets/fiscal-year-2024-improper-payments-fact-sheet?utm_source=chatgpt.com))

### ⏱️ Time and friction costs
- **23% of people do not dispute bills because it takes too much time** ([AJMC](https://www.ajmc.com/view/survey-exposes-pervasive-billing-errors-aggressive-tactics-in-us-health-insurance?utm_source=chatgpt.com))
- **~50% of denied claims are never resubmitted** due to process friction ([PCG Software](https://www.pcgsoftware.com/financial-impact-of-medical-billing-errors?utm_source=chatgpt.com))

### 🧠 Supporting context
- **49-80% of medical bills contain errors** ([HealthSureHub](https://healthsurehub.com/medical-billing-error-statistics/?utm_source=chatgpt.com))

---

## ✨ What Lethe does

Drop in a medical bill. A deterministic PDF parser extracts the structured data (CPT/ICD codes, modifiers, charges, dates of service) and a redaction pass strips every piece of PHI (patient name, DOB, address, MRN, account numbers) — *before any AI ever sees the payload*. Three independent AI agents (GPT-4o, Claude Sonnet, Gemini Flash) analyze the bill in parallel; one of them can optionally run on a **decentralized inference node** instead of a closed model API. They **broadcast their own findings** over a [Gensyn AXL](https://blog.gensyn.ai/introducing-axl/) peer-to-peer mesh and run a **round-2 reflection** with their peers' findings as new context — so each agent gets a chance to revise its vote in light of what the other two saw. A finding only enters the final result if at least 2 of 3 agents agree after that reflection round. A fourth agent (Claude) drafts a formal appeal letter from the agreed-on findings.

The original bill never touches storage and never reaches a model provider. It lives in coordinator memory long enough for the parser and redactor to run, then it's discarded. What persists is a SHA-256 + verdict anchored to [0G Galileo](https://0g.ai) (canonical proof of *what was analyzed*), the same record mirrored to Ethereum Sepolia via [KeeperHub](https://keeperhub.com), the full anonymized audit blob written to **0G Storage** with merkle root + commitment tx in the receipt, and an anonymized pattern record on `PatternRegistry` that makes the next user's analysis smarter without anyone's records being recoverable.

When consensus lands on `dispute`, KeeperHub fires a **second** workflow recording the disputed bill on a separate Sepolia `DisputeRegistry`. When the user types a provider's email and clicks **Send**, the coordinator dispatches a formatted appeal letter (with full chain verification) to the provider via a transactional email service, then KeeperHub fires a **third** workflow recording the send on-chain (recipient address keccak-hashed, never plaintext). Three KeeperHub workflows, three independent on-chain records — one immutable audit trail per bill.

---

## 🏗️ Architecture

```mermaid
---
config:
  layout: elk
---
flowchart TB
    %% === Subgraph: Frontend ===
    subgraph FE["💻 Frontend"]
        User["Browser Dashboard"]
    end

    %% === Subgraph: Backend ===
    subgraph BE["⚙️ Backend · FastAPI Coordinator"]
        direction LR
        API["API Gateway + SSE Event Bus"]
        Parse["Parse & Redact PHI<br><sub>parser → regex → LLM sweep</sub>"]
        Tally["Consensus Tally<br><sub>2‑of‑3 quorum</sub>"]
        Drafter["Drafter Agent<br><sub>Claude → appeal letter</sub>"]
    end

    %% === Subgraph: Agent Mesh ===
    subgraph Mesh["🕸️ Agent Mesh"]
        direction TB
        Round1["Round 1 · Independent Agents<br><sub>α GPT‑4o · β Claude · γ Gemini / 0G Compute</sub>"]
        AXL["Gensyn AXL P2P Mesh<br><sub>POST /send · GET /recv</sub>"]
        Round2["Round 2 · Reflect on Peer Findings"]
        ZGC["🧠 0G Compute Provider<br><sub>γ optional · headers sidecar :8787</sub>"]
    end

    %% === Subgraph: Persistence ===
    subgraph Persist["💾 0G Persistence"]
        direction TB
        ZGChain["LetheRegistry · Galileo<br><sub>anchor + Finding events + provider stats + rulebook pointer</sub>"]
        ZGStorage["0G Storage<br><sub>audit blob + rulebook JSON · via sidecar :8788</sub>"]
    end

    %% === Subgraph: Execution Layer ===
    subgraph Exec["🔁 KeeperHub · 3 Workflows"]
        KH["Direct Execution REST + MCP Transport"]
    end

    %% === Subgraph: Ethereum ===
    subgraph Sep["⛓️ Ethereum Sepolia · LetheRegistry"]
        direction TB
        SepAnchor["anchor() · WF #1"]
        SepDispute["recordDispute() · WF #2"]
        SepAppeal["recordAppealSent() · WF #3"]
    end

    %% === Subgraph: Mail ===
    subgraph Mail["📧 Appeal Delivery"]
        direction TB
        Email["Resend / SMTP / Stub"]
        Provider@{ label: "Provider's Billing Inbox", shape: rect }
    end

    %% === Main pipeline (single chain along the spine) ===
    User ==>|Upload PDF| API ==> Parse ==>|Redacted Payload| Round1
    Round1 ==>|Broadcast Findings| AXL ==> Round2 ==>|Revised Votes| Tally
    Tally ==> Drafter ==>|Letter Shown| User

    %% === γ optional decentralized inference ===
    Round1 <-.->|γ Inference| ZGC

    %% === Persistence fan-out from Tally ===
    Tally ==> ZGChain & ZGStorage
    ZGStorage ==>|"merkle root in anchor"| ZGChain
    ZGChain -.->|"read-back priors"| Round1
    Tally ==>|"Anchor + (if dispute) File"| KH ==> SepAnchor
    KH -.-> SepDispute & SepAppeal

    %% === User-initiated appeal send ===
    User -.->|Click Send| Email --> Provider
    Email -.->|After Send| KH

    %% === Styling ===
    class FE tierFE
    class BE tierBE
    class Mesh tierMesh
    class Persist,Sep tierChain
    class Exec tierExec
    class Mail tierMail

    classDef tierFE      fill:#eef2ff,stroke:#818cf8,stroke-width:2px,color:#1e1b4b
    classDef tierBE      fill:#f0fdfa,stroke:#2dd4bf,stroke-width:2px,color:#022c22
    classDef tierMesh    fill:#fff7ed,stroke:#fb923c,stroke-width:2px,color:#431407
    classDef tierChain   fill:#fdf4ff,stroke:#e879f9,stroke-width:2px,color:#4a044e
    classDef tierExec    fill:#f0fdf4,stroke:#4ade80,stroke-width:2px,color:#052e16
    classDef tierMail    fill:#fefce8,stroke:#facc15,stroke-width:2px,color:#422006
```


> 📐 **Setup, env vars, and verification commands** are in [`SETUP.md`](./SETUP.md).

---

## 🎯 Features (as of April 28, 2026)

<table>
<tr>
<td width="50%" valign="top">

### 🔒 Zero retention, zero PHI exposure
A deterministic parser handles PDFs (with image fallback) inside the coordinator. PHI is then stripped by a regex pass plus an LLM redactor sweep, all *before any audit agent sees the payload*. Bill bytes are zeroed from memory immediately after the parse stage; only the redacted payload travels further. SSE events carry only stage names, verdicts, and counts — no bill content.

</td>
<td width="50%" valign="top">

### 🤖 3-agent independent consensus
GPT-4o (α), Claude Sonnet 4.5 (β), and Gemini Flash (γ) each independently analyze the redacted payload — no shared scratchpad, no orchestrator nudge. The verdict is the majority vote; a finding only survives with ≥2-of-3 quorum on the canonical billing code. When no verdict reaches majority (a 1-1-1 split), the system falls back to **clarify** rather than letting registration order silently pick a winner. Confidence is the mean across the winning side.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🕸️ Real Gensyn AXL P2P mesh + live message log
Each of the three agents has its own AXL sidecar Docker container running the upstream Gensyn `node` binary with a unique ed25519 peer ID, joined to the public Gensyn mesh via two TLS bootstrap peers. Real `POST /send` broadcasts and real `GET /recv` inbox drains carry findings across the Yggdrasil overlay. The `/axl` page shows live topology with verified peer keys *plus a live message log* — every send/recv with sender/receiver pubkeys, byte counts, latency, and verified-ok badge. If AXL ever falls back to in-process `asyncio.gather`, a loud uvicorn startup banner makes it impossible to miss.

</td>
<td width="50%" valign="top">

### ⛓️ Three pillars on 0G — Chain + Storage + Compute
Every audit hits the full 0G stack: **0G Chain** anchors the SHA-256 + verdict to `BillRegistry` (Galileo, chain 16602) and indexes anonymized findings to `PatternRegistry`. **0G Storage** holds the full schema-versioned audit blob (more detail than chain bytes32 fields can carry), with merkle root + commitment tx in the receipt. **0G Compute** *(optional)* runs agent γ on decentralized inference via the broker SDK, with per-request signed headers handled transparently by a local Node sidecar. Built-in stub-fallback at every layer.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🧠 Read-back pattern loop
Before each new audit, the coordinator scans `LetheRegistry`'s `Finding` events via `eth_getLogs` (cached 120s) and formats prior dispute / clarify rates per code into the agents' system prompts. The next run's reasoning shifts based on what previous runs found. A pre-seed script bootstraps ~20 historical findings so the very first demo audit shows real on-chain priors firing.

</td>
<td width="50%" valign="top">

### ✍️ Auto-drafted appeal letter
A fourth agent (Claude, separately prompted) takes the consensus findings and writes a formal, citation-bearing appeal letter. The dashboard renders it as an ASCII-bordered receipt PDF you can review and download — Lethe never auto-submits anything to an insurer.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🔁 Round-2 reflection — consensus through conversation
The three agents don't just vote in isolation — they **talk**. Round 1 runs independent LLM calls in parallel. AXL exchange broadcasts each agent's findings to peers via its sidecar. Round 2 runs a *second* LLM call per agent with peers' findings injected — agents add findings they missed, downgrade ones peers convinced them were wrong, or hold their ground. The dashboard streams a one-line summary per agent: `α: approve → dispute · findings 1→3 · conf 0.92`. Consensus runs on round-2 votes — every finding survived peer scrutiny *and* a 2-of-3 majority.

</td>
<td width="50%" valign="top">

### 💚 KeeperHub — three distinct workflows
Every audit fires KH **twice** (mirror anchor + dispute filing on `dispute`) and a **third** time when the user clicks "Send appeal" (appeal-sent attestation). Different contracts, different methods, different gates — KH is doing real workflow orchestration. Both REST and MCP transports implemented; "already anchored" duplicates are detected and the receipt links the original tx via Sepolia event lookup, not "pending".

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🏥 Insurance payer submission
Once consensus lands on `dispute`, a panel on the dashboard lets the patient file the same disputed-codes packet directly with the insurance payer or clearinghouse. `POST /api/payer/submit` builds an X12 837 / FHIR Claim payload from the consensus findings + member info and dispatches through a pluggable adapter table. Five adapters are registered today: **stub** (default — generates a deterministic mock claim id and returns success, so the full flow is demoable end-to-end without sandbox creds), **stedi** (X12 837 over Stedi REST), **availity** (Availity FHIR R4 + Web Services), **change healthcare** (clearinghouse SOAP/REST), and **fhir** (direct payer FHIR endpoint). The adapter is selected by `LETHE_PAYER_ADAPTER` and the dashboard surfaces `live submission` vs `stub mode` in the response. Member ID, plan ID, and DOB are passed through to the adapter and never persisted.

</td>
<td width="50%" valign="top">

### 🩺 On-chain provider reputation
Each audit's NPI is extracted from the bill, salted-SHA-256 hashed, and written to a deployed `ProviderReputation` contract. Anyone can hit `/providers/<npi>` to see that provider's running stats — total audits, dispute rate, total flagged dollars — read directly from chain. The aggregate is keyed by NPI hash so individual bills aren't linkable, but a provider's overall pattern is. The page also links straight to the chainscan address for the reputation registry so the count is independently verifiable.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 📜 Versioned NCCI rulebook on chain
Coding rules (CPT bundling pairs, modifier-required pairings, units-per-day caps, time-overlap conflicts) live as a JSON manifest in **0G Storage**; the per-version manifest hash is anchored on-chain via `LetheRegistry.publishRulebook(version, manifestRoot)`. Bumping a version is one tx, no contract redeploy. The `/rules` page reads the manifest pointer from chain and pulls the JSON via the storage sidecar. Every audit ties to a specific `rulebookVersion` written into its anchor record.

</td>
<td width="50%" valign="top">

### 👛 Wallet connect + per-wallet audit history
Connect MetaMask (or any EIP-1193 wallet) and the dashboard remembers the audits you ran. `/my-audits` lists every bill SHA, verdict, and chain tx the connected wallet has produced — pulled from local storage, scoped per wallet address, never sent to a server. Switch wallets and the list rescopes. The wallet itself isn't required to run an audit; it's strictly an opt-in personal index so you can find your prior receipts later.

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
<tr>
<td align="center"><img src="https://placehold.co/40x40/0f172a/4ade80/png?text=0G" width="40" /><br/><sub><b>0G Chain</b></sub></td>
<td align="center"><img src="https://placehold.co/40x40/0f172a/22d3ee/png?text=0G+S" width="40" /><br/><sub><b>0G Storage<br/><sup>@0glabs/0g-ts-sdk</sup></b></sub></td>
<td align="center"><img src="https://placehold.co/40x40/0f172a/c084fc/png?text=0G+C" width="40" /><br/><sub><b>0G Compute<br/><sup>@0glabs/0g-serving-broker</sup></b></sub></td>
<td align="center"><img src="https://placehold.co/40x40/0f172a/22c55e/png?text=KH" width="40" /><br/><sub><b>KeeperHub<br/><sup>REST + MCP</sup></b></sub></td>
<td align="center"><img src="https://placehold.co/40x40/0f172a/d4a373/png?text=MCP" width="40" /><br/><sub><b>mcp (Python)</b></sub></td>
<td align="center"><img src="https://cdn.simpleicons.org/nodedotjs/5fa04e" width="40" /><br/><sub><b>Node sidecars<br/><sup>tsx + ethers v6</sup></b></sub></td>
</tr>
</table>

<sub>Frontend · Coordinator · Chain & AI · 0G stack · Cross-chain execution</sub>

</div>

---

## ⛓️ On-chain artifacts

One contract per chain — `LetheRegistry` consolidates the anchor, finding events, dispute filings, appeal-sent attestations, provider stats, and rulebook manifest pointer onto a single deployed address. KeeperHub fires three workflows that hit three different methods on the Sepolia instance.

| Contract | Network | Address | Status | Explorer |
|----------|---------|---------|--------|----------|
| `LetheRegistry` (canonical) | 0G Galileo testnet (chain id 16602) | _pending wallet funding_ | ⏳ deploy queued | — |
| `LetheRegistry` (Sepolia mirror · 3 KH workflows) | Ethereum Sepolia (chain id 11155111) | `0x93D691801FE81Fe3aC7187fe1F394f40a045973E` | ✅ deployed | [sepolia.etherscan.io](https://sepolia.etherscan.io/address/0x93D691801FE81Fe3aC7187fe1F394f40a045973E) |

The full anonymized audit record is uploaded to **0G Storage** with a merkle root + commitment tx, and the merkle root is recorded as a field on `LetheRegistry.anchor()` so future audits scan `BillAnchored` events for recent roots and pull blobs back via the storage sidecar's `GET /download` endpoint — agents read priors that are strictly richer than the bytes32-truncated chain events. The NCCI rulebook lives in 0G Storage too; only the per-version manifest hash is anchored on-chain via `LetheRegistry.publishRulebook`.

Solidity source: [`LetheRegistry.sol`](./src/contracts/src/LetheRegistry.sol). Deploy script (`py-solc-x` + `web3.py`, no Foundry): [`src/contracts/deploy.py`](./src/contracts/deploy.py).

---

## 📘 Contract reference

Both deployments (Galileo + Sepolia) run the **same** `LetheRegistry` source. Below is the full surface — every method, every event, with inputs, outputs, gates, and how to call each one. Anything in the contract that isn't in this table doesn't exist.

### ✍️ Write methods (state-changing)

| Method | Inputs | What happens | Gates | Caller in production |
|---|---|---|---|---|
| `anchor` | `billHash bytes32` · `verdict uint8` (1 dispute / 2 approve / 3 clarify) · `agreeCount uint8` · `totalAgents uint8` · `npiHash bytes32` (zero ok) · `storageRoot bytes32` (zero ok) · `rulebookVersion uint16` · `flaggedCents uint64` | Stores the `Anchor` struct, atomically rolls up `providerStats[npiHash]` if non-zero, emits `BillAnchored` | reverts if `verdict ∉ {1,2,3}`, `agreeCount > totalAgents`, or this `billHash` was already anchored | coordinator (Galileo) · KH workflow #1 (Sepolia) |
| `indexFindings` | `billHash bytes32` · 5 parallel arrays — `codes bytes32[]` · `actions bytes16[]` · `severities bytes8[]` · `amountsCents uint64[]` · `voters uint8[]` (bitmask: α=1, β=2, γ=4) | Emits one `Finding` event per finding | reverts if bill not anchored, or arrays are different lengths | coordinator only (Galileo) |
| `recordDispute` | `billHash bytes32` · `reason uint8` · `note string` (≤ 512 chars) | Emits `DisputeFiled` | reverts if `note > 512` chars or anchor's verdict isn't `Dispute` | KH workflow #2 (Sepolia) |
| `recordAppealSent` | `billHash bytes32` · `recipientHash bytes32` (keccak of email + salt) | Emits `AppealSent` | reverts if bill not anchored | KH workflow #3 (Sepolia) |
| `publishRulebook` | `version uint16` (must be ≥ 1) · `manifestRoot bytes32` (0G Storage merkle root for the rules JSON) | Sets `rulebookManifest[version]`, advances `currentRulebookVersion` if `version > current`, emits `RulebookPublished` | `onlyOwner` | coordinator at deploy time + each NCCI quarterly bump |
| `transferOwnership` | `newOwner address` (non-zero) | Updates `owner`, emits `OwnerTransferred` | `onlyOwner`, non-zero new owner | one-time setup or DAO migration |

### 📖 Read methods (free, view, no gas)

| Method | Inputs | Returns |
|---|---|---|
| `anchors(billHash bytes32)` | one bill | full struct: `verdict uint8` · `agreeCount uint8` · `totalAgents uint8` · `npiHash bytes32` · `storageRoot bytes32` · `rulebookVersion uint16` · `anchoredAt uint64` · `anchoredBy address` |
| `isAnchored(billHash bytes32)` | one bill | `bool` — `true` if any anchor exists |
| `providerStats(npiHash bytes32)` | one provider's NPI hash | aggregate: `totalAudits uint32` · `disputeCount uint32` · `clarifyCount uint32` · `approveCount uint32` · `totalFlaggedCents uint128` |
| `disputeRateBps(npiHash bytes32)` | one provider | `uint256` basis points (10000 = 100%); 0 if no audits |
| `rulebookManifest(version uint16)` | rule version number | `bytes32` — 0G Storage merkle root holding the rules JSON for that version |
| `currentRulebookVersion()` | — | `uint16` |
| `owner()` | — | `address` |

### 📡 Events (queryable via `eth_getLogs`)

All events have **indexed topics** marked `[i]` — those are filterable directly in `topics[]`.

| Event | Fields | Indexed | When it fires | Why you'd query it |
|---|---|---|---|---|
| `BillAnchored` | `billHash` · `npiHash` · `verdict` · `agreeCount` · `totalAgents` · `storageRoot` · `rulebookVersion` · `flaggedCents` · `anchoredAt` · `anchoredBy` | `[i] billHash`, `[i] npiHash`, `[i] anchoredBy` | every `anchor()` call | "all audits for this bill" / "all audits this wallet anchored" / "all audits for this provider" |
| `Finding` | `billHash` · `code` · `action` · `severity` · `amountCents` · `voters` · `indexedBy` · `indexedAt` | `[i] billHash`, `[i] code`, `[i] indexedBy` | once per finding inside `indexFindings()` | "all findings for code CPT 99214" — drives the priors loop |
| `DisputeFiled` | `billHash` · `reason` · `note` · `filedAt` · `filedBy` | `[i] billHash`, `[i] filedBy` | every `recordDispute()` | "show me every dispute filing for this bill" |
| `AppealSent` | `billHash` · `recipientHash` · `sentAt` · `sentBy` | `[i] billHash`, `[i] recipientHash`, `[i] sentBy` | every `recordAppealSent()` | "did this bill ever get an appeal sent?" |
| `RulebookPublished` | `version` · `manifestRoot` · `publishedAt` · `publishedBy` | `[i] version`, `[i] publishedBy` | every `publishRulebook()` | rulebook history / audit trail of rule changes |
| `OwnerTransferred` | `from` · `to` | `[i] from`, `[i] to` | rare | governance transfer history |

### 🔧 What you can do with these — quick examples

#### Anchor a new audit (write)
```python
# coordinator does this on Galileo for every audit
contract.functions.anchor(
    bytes.fromhex("a1b2c3...64hex"),  # billHash
    1,                                 # verdict = Dispute
    3, 3,                              # all 3 agents agreed
    bytes.fromhex("3b3d...salted-npi"),
    bytes.fromhex("9f4a...storage-merkle-root"),
    1,                                 # current rulebook version
    24500,                             # $245 flagged
).transact()
```

#### Look up a single audit (read · free)
```python
sha = bytes.fromhex("a1b2c3...64hex")
r = contract.functions.anchors(sha).call()
# r = (1, 3, 3, b'\x3b\x3d…', b'\x9f\x4a…', 1, 1714353600, '0x2b17…E99D')
```
Or hit the dashboard: [`localhost:3000/verify?sha=0xa1b2...`](http://localhost:3000) — same data, rendered.

#### Get a provider's dispute rate (read · free)
```python
npi_hash = sha256(("lethe-npi-v1:" + "1234567890").encode()).digest()
stats = contract.functions.providerStats(npi_hash).call()
# (totalAudits=12, disputeCount=8, clarifyCount=2, approveCount=2, totalFlaggedCents=320000)
rate_bps = contract.functions.disputeRateBps(npi_hash).call()  # 6666 = 66.66%
```

#### Scan all findings for a CPT code (priors loop)
```python
# What did past audits decide about CPT 99214?
code = b"CPT 99214" + b"\x00" * 23     # left-padded to bytes32
logs = w3.eth.get_logs({
    "address": LETHE_REGISTRY,
    "topics": [
        FINDING_TOPIC0,                 # event signature hash
        None,                           # billHash (any)
        "0x" + code.hex(),              # indexed code filter
    ],
    "fromBlock": 0, "toBlock": "latest",
})
# decode `action`, `severity`, `amountCents`, `voters` from each log
```

#### Pull the full audit blob from 0G Storage
```python
# 1. read storageRoot from chain
sha = bytes.fromhex("a1b2c3...")
anchor = contract.functions.anchors(sha).call()
storage_root = "0x" + anchor[4].hex()  # storageRoot is field index 4

# 2. fetch the JSON blob from the storage sidecar
blob = httpx.get(f"http://localhost:8788/download?root={storage_root}").json()
# → full anonymized record with un-truncated code strings, voter agent names,
#   etc. — strictly richer than the bytes32 chain events
```

#### File a dispute (KH workflow #2 on Sepolia)
```python
# fired by KH executor, not the coordinator directly
contract.functions.recordDispute(
    sha,
    1,                                  # reason
    "CPT 99214 bundled into 99213 · CPT 80053 units > MUE cap of 1",
).transact()
```

#### Attest an appeal was sent (KH workflow #3 on Sepolia)
```python
recipient_hash = keccak("billing@hospital.example".encode() + SALT)
contract.functions.recordAppealSent(sha, recipient_hash).transact()
```

#### Bump the NCCI rulebook to a new version (one-tx upgrade · owner-only)
```python
# 1. upload rules JSON to 0G Storage → returns merkle root
manifest_root = upload_to_zg_storage(json.dumps(NEW_RULES_V2).encode())

# 2. anchor the manifest hash on chain (auto-advances currentRulebookVersion)
contract.functions.publishRulebook(2, manifest_root).transact()

# Future audits read the v2 rules:
# - manifest_root = contract.functions.rulebookManifest(2).call()
# - blob = sidecar GET /download?root=manifest_root
```

### 🌐 Two HTTP endpoints if you don't want to write web3 code

The coordinator wraps all the read paths above. Run `uvicorn` and:

| Endpoint | What it does under the hood |
|---|---|
| `GET /api/verify/<sha>` | Reads `anchors(sha)`, scans `Finding`/`DisputeFiled`/`AppealSent` events for that bill on **both** chains, downloads the 0G Storage blob, returns one bundled JSON |
| `GET /api/providers/<npi>` | Hashes the NPI, calls `providerStats(npiHash)`, returns the aggregate |
| `GET /api/rules` | Calls `currentRulebookVersion()`, then `rulebookManifest(v)`, then fetches the JSON from 0G Storage |

---

## 🏆 Hackathon tracks

> Submitted to all three sponsor tracks at [ETHGlobal OpenAgents](https://ethglobal.com/events/openagents). Each track maps to a load-bearing piece of the system, with verifiable on-chain or open-source artifacts.

### 🎖️ Track 1 — Gensyn AXL · Best Application of AXL

**How we use AXL:** Each of the three audit agents has its own AXL sidecar Docker container running the upstream Gensyn `node` binary with a unique ed25519 keypair, joined to the public Gensyn mesh via two TLS bootstrap peers. Agents exchange findings between rounds via real `POST /send` broadcasts and `GET /recv` inbox drains — the round-2 reflection LLM call literally cannot fire without findings arriving across the mesh. The frontend `/axl` page renders **live topology** plus a 200-entry message log (every send/recv with bytes, latency, and signed pubkey pair).

**Cross-node communication proof:**
- Three separate Docker services in [`docker-compose.yml`](./docker-compose.yml) — `axl-alpha`, `axl-beta`, `axl-gamma`
- Three real ed25519 peer IDs in [`infra/axl/keys/peer_ids.json`](./infra/axl/keys/peer_ids.json) (raw 32-byte ed25519 pubkeys derived from PKCS#8 keys, not fabricated strings)
- Live verification at `/axl` shows each sidecar's `/topology` response with verified pubkeys and connections to public Gensyn peers
- No central message broker — `POST /send` from agent X's sidecar to agent Y's sidecar over the encrypted Yggdrasil overlay

**Code:** [`agents/transport_axl.py`](./src/coordinator/agents/transport_axl.py) (HTTP client + 200-entry message ring buffer), [`pipeline/runner.py`](./src/coordinator/pipeline/runner.py) (`_exchange()` and `_reflect_all()` stages), [`infra/axl/`](./infra/axl/) (Dockerfile + per-peer configs).

---

### 🛠️ Track 2 — 0G · Best Autonomous Agents, Swarms & iNFT Innovations

**How we use 0G — three pillars:** Lethe is a 3-agent swarm (GPT-4o · Claude · Gemini) that uses **the entire 0G stack**:

- **0G Chain.** `LetheRegistry` is one contract that owns the full audit surface — anchor record (SHA-256, verdict, NPI hash, storage root, rulebook version), `Finding` events for each consensus finding, aggregate provider stats updated atomically inside `anchor()`, and the rulebook manifest pointer. The coordinator reads `Finding` events back via `eth_getLogs` (cached 120s) and feeds aggregate dispute/clarify rates into agent prompts as priors. **Each new audit gets smarter via on-chain shared memory — and there's exactly one address to verify.**
- **0G Storage — bidirectional.** Every audit's full anonymized record is uploaded as a JSON blob via `@0glabs/0g-ts-sdk` (through a local Node sidecar) — returns a merkle root + on-chain commitment tx. The `(billHash → storageRoot)` pointer is *also* written to a deployed `StorageIndex` contract on Galileo, so future audits query `eth_getLogs` for recent roots and pull blobs back via the sidecar's `GET /download?root=R` endpoint. **The agents read priors from Storage** when blobs are available (full code strings + voter agent names) — strictly richer than the `bytes32`-truncated `PatternRegistry` events. Storage isn't cold archive; it's the primary memory layer.
- **0G Compute.** Agent γ can run on a **decentralized inference node** instead of Google Gemini. The coordinator routes through a Node sidecar that signs each request body hash via the broker SDK — 0G Compute auth is per-request, not a static bearer token. The factory probes the sidecar at startup and silently falls back to Gemini if unreachable, so `/api/status` always honestly reports γ's actual provider.

**Swarm coordination:**
- Three independent LLM agents reason in parallel during round 1 (different SDKs, different keys, different system prompts).
- Findings broadcast over Gensyn AXL (see Track 1).
- Round-2 reflection per agent with peer findings as context — agents may revise verdict, add findings, downgrade contested ones.
- 2-of-3 quorum on canonical billing code; 1-1-1 splits resolve to "clarify" (no silent registration-order tiebreak).

**Code:** [`chain/zerog.py`](./src/coordinator/chain/zerog.py) (anchor writes), [`chain/zerog_storage.py`](./src/coordinator/chain/zerog_storage.py) (PatternRegistry indexer), [`chain/zerog_blob.py`](./src/coordinator/chain/zerog_blob.py) (0G Storage uploader · 4 KB padding · circuit breaker), [`chain/storage_priors.py`](./src/coordinator/chain/storage_priors.py) (StorageIndex pointer write + read-back loop), [`chain/patterns.py`](./src/coordinator/chain/patterns.py) (chain-event priors fallback), [`agents/audit_0g.py`](./src/coordinator/agents/audit_0g.py) (γ on 0G Compute), [`agents/audit_google.py`](./src/coordinator/agents/audit_google.py) (γ factory · auto-fallback to Gemini), [`scripts/storage_sidecar.ts`](./src/coordinator/scripts/storage_sidecar.ts) and [`scripts/headers_sidecar.ts`](./src/coordinator/scripts/headers_sidecar.ts) (Node bridges to 0G TS SDKs).

---

### 💚 Track 3 — KeeperHub · Best Innovative Use of KeeperHub

**How we use KeeperHub — three distinct workflows.** KeeperHub is the execution platform that turns one consensus into multiple chain-verifiable side effects:

All three workflows hit the **same** `LetheRegistry` contract on Sepolia ([`0x93D6…973E`](https://sepolia.etherscan.io/address/0x93D691801FE81Fe3aC7187fe1F394f40a045973E)) — three different methods, three different gates, one address.

1. **Mirror anchor (every audit).** `LetheRegistry.anchor()` via KH Direct Execution `POST /api/execute/contract-call`. Same record as 0G Galileo, written by KH's managed wallet. Already-anchored duplicates are detected and the receipt links the original tx via Sepolia event lookup, not "pending".
2. **Dispute filing (consensus = `dispute`).** A second KH execution fires `LetheRegistry.recordDispute(billHash, reason, note)` with a redacted findings summary. Same contract; different method gated on `verdict == Dispute`.
3. **Appeal-sent attestation (user click).** When the user types a provider email and clicks **Send appeal**, the coordinator emails the appeal letter + chain verification table, then a third KH execution fires `LetheRegistry.recordAppealSent(billHash, recipientHash)`. Recipient address is keccak-hashed before going on-chain.

**Two integration vectors implemented:**
- **Direct Execution REST API** (default for all three workflows)
- **MCP server transport** — `LETHE_KEEPERHUB_USE_MCP=true` switches the mirror anchor through KeeperHub's MCP server using the official `mcp` Python SDK. Falls back to REST if MCP returns a stub. The prize text reads "MCP server or CLI"; this satisfies the strict reading.

**Code:** [`chain/keeperhub.py`](./src/coordinator/chain/keeperhub.py) (REST integration for all three workflows), [`chain/keeperhub_mcp.py`](./src/coordinator/chain/keeperhub_mcp.py) (MCP transport), [`routers/appeal.py`](./src/coordinator/routers/appeal.py) + [`email_delivery/`](./src/coordinator/email_delivery/) (the appeal-send pipeline).

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
│   │   └── src/app/{dashboard,axl,patterns,verify,my-audits,providers/[npi],rules,tech-stack}/page.tsx
│   ├── coordinator/           # FastAPI orchestrator
│   │   ├── main.py            # app entry + CORS + sweeper + AXL-off startup banner
│   │   ├── routers/           # jobs · samples · status · verify · appeal · providers · rules · payer
│   │   ├── pipeline/          # runner, parser, redactor, consensus, dispute drafter
│   │   ├── agents/            # audit_{openai,anthropic,google,0g}, drafter, transport_axl, prompts
│   │   ├── chain/             # lethe_registry (unified anchor + findings + provider stats + rulebook pointer)
│   │   │                      # zerog_blob (0G Storage uploads · audit blobs + rulebook JSON)
│   │   │                      # patterns (chain-event priors fallback)
│   │   │                      # keeperhub (REST · 3 workflows on LetheRegistry/Sepolia) · keeperhub_mcp (MCP transport)
│   │   ├── payer/             # X12 837 / FHIR adapter dispatch — stub · stedi · availity · ch · fhir
│   │   ├── email_delivery/    # sender (resend / smtp / stub) + HTML template builder
│   │   ├── scripts/           # Node helpers — provision:0g · headers:0g · storage:0g · check:0g
│   │   ├── samples/           # example bills used by the dashboard chips
│   │   └── store/             # in-memory job store + sweeper, rolling stats
│   └── contracts/             # LetheRegistry — single contract per chain
│                              # deployed via deploy.py (py-solc-x + web3.py, no Foundry)
├── infra/
│   └── axl/                   # Dockerfile, configs/{alpha,beta,gamma}.json, keys/peer_ids.json
├── data-gen/                  # Bill PDF generator + Finding-event pre-seed script
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
  <a href="https://github.com/Justyhatch3">GitHub</a> · <a href="https://www.linkedin.com/in/justinhatch/">LinkedIn</a><br />
  <sub>Telegram <code>@your-telegram-here</code> · X <code>@your-x-here</code></sub>
</td>
<td align="center" width="50%">
  <img src="https://placehold.co/120x120/1e293b/94a3b8/png?text=DM" width="100" /><br />
  <b>Drew Manley</b><br />
  <a href="https://github.com/drewmanley16">GitHub</a> · <a href="https://www.linkedin.com/in/drewmanley/">LinkedIn</a><br />
  <sub>Telegram <code>@your-telegram-here</code> · X <code>@your-x-here</code></sub>
  <td align="center" width="50%">
  <img src="./assets/cam.jpeg" width="100" /><br />
  <b>Cameron Coleman</b><br />
  <a href="https://github.com/camcoleman">GitHub</a> · <a href="https://www.linkedin.com/in/camcoleman/">LinkedIn</a><br />
  <sub>Telegram <code>@cameroncoleman13</code> · X <code>@cam_coleman1</code></sub>
</td>
</tr>
</table>

> **Note:** Telegram + X handles are placeholders — fill in before submission. 0G's qualification requirements specifically ask for these.

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
