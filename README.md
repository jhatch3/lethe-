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
- [✨ What Lethe does](#-what-lethe-does)
- [🏗️ Architecture](#%EF%B8%8F-architecture)
- [🎯 Features](#-features-as-of-april-27-2026)
- [🛠️ Built with](#%EF%B8%8F-built-with)
- [⛓️ On-chain artifacts](#%EF%B8%8F-on-chain-artifacts)
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
        ZGChain["0G Chain · Galileo<br><sub>BillRegistry + PatternRegistry</sub>"]
        ZGStorage["0G Storage<br><sub>via storage sidecar :8788</sub>"]
    end

    %% === Subgraph: Execution Layer ===
    subgraph Exec["🔁 KeeperHub · Workflow Execution"]
        KH["Direct Execution REST + MCP Transport"]
    end

    %% === Subgraph: Ethereum ===
    subgraph Sep["⛓️ Ethereum Sepolia"]
        direction TB
        SepMirror["BillRegistry Mirror · WF #1"]
        SepDispute["DisputeRegistry · WF #2"]
        SepAppeal["AppealRegistry · WF #3"]
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
    Tally ==>|"Anchor + (if dispute) File"| KH ==> SepMirror
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

## 🎯 Features (as of April 27, 2026)

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
Before each new audit, the coordinator queries `eth_getLogs` on the `PatternRegistry` and formats prior dispute / clarify rates per code into the agents' system prompts. The next run's reasoning shifts based on what previous runs found. A pre-seed script (`data-gen/scripts/seed_patterns.py`) bootstraps ~20 historical patterns so the very first demo audit shows real on-chain priors firing.

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

### 💚 KeeperHub — two distinct workflows
Every audit fires KH **twice**: a **mirror anchor** writes the same SHA-256 + verdict to a Sepolia `BillRegistry`, *and* on `dispute` consensus a second KH execution calls `recordDispute(billHash, reason, note)` on a configurable `DisputeRegistry`. Different contracts, different methods, different verdict gates — KH is doing real workflow orchestration. Both REST and MCP transports implemented; "already anchored" duplicates are detected and the receipt links the original tx via Sepolia event lookup, not "pending".

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

Every Lethe audit produces records on two independent blockchains. Anyone with a bill's SHA-256 can verify the audit from either explorer using just the public address.

| Contract | Network | Address | Explorer |
|----------|---------|---------|----------|
| `BillRegistry` (canonical anchor) | 0G Galileo testnet (chain id 16602) | `0xf6B4C9CA2e8C8a3CE2DE77baa119004d6B51B457` | [chainscan-galileo.0g.ai](https://chainscan-galileo.0g.ai/address/0xf6B4C9CA2e8C8a3CE2DE77baa119004d6B51B457) |
| `PatternRegistry` (priors index) | 0G Galileo testnet | `0x7665c9692b1c4e6ef90495a584288604b735e23f` | [chainscan-galileo.0g.ai](https://chainscan-galileo.0g.ai/address/0x7665c9692b1c4e6ef90495a584288604b735e23f) |
| `BillRegistry` (Sepolia mirror) | Ethereum Sepolia | `0xf6B4C9CA2e8C8a3CE2DE77baa119004d6B51B457` | [sepolia.etherscan.io](https://sepolia.etherscan.io/address/0xf6B4C9CA2e8C8a3CE2DE77baa119004d6B51B457) |
| `DisputeRegistry` (KH workflow #2 target) | Ethereum Sepolia | `0xbdb8282aCD9b542b8302d872Fb9BD28B0b5e5290` | [sepolia.etherscan.io](https://sepolia.etherscan.io/address/0xbdb8282aCD9b542b8302d872Fb9BD28B0b5e5290) |
| `AppealRegistry` (KH workflow #3 target) | Ethereum Sepolia | `0x69166ACC4718a0062540673F5Cae26997BaB064e` | [sepolia.etherscan.io](https://sepolia.etherscan.io/address/0x69166ACC4718a0062540673F5Cae26997BaB064e) |

In addition, every audit's full anonymized record is uploaded to **0G Storage**, which returns a merkle root + on-chain commitment tx. Both are surfaced in the dashboard receipt next to the chain anchors.

Solidity sources: [`BillRegistry.sol`](./src/contracts/src/BillRegistry.sol), [`PatternRegistry.sol`](./src/contracts/src/PatternRegistry.sol), [`DisputeRegistry.sol`](./src/contracts/src/DisputeRegistry.sol), [`AppealRegistry.sol`](./src/contracts/src/AppealRegistry.sol). Deploy script (`py-solc-x` + `web3.py`, no Foundry): [`src/contracts/deploy.py`](./src/contracts/deploy.py).

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

- **0G Chain.** `BillRegistry` anchors SHA-256 + verdict for every audited bill. `PatternRegistry` indexes anonymized findings (canonical code · action · severity · amount · voters) as on-chain events. The coordinator reads these back via `eth_getLogs` (cached 120s) and feeds aggregate dispute/clarify rates into agent prompts as priors. **Each new audit gets smarter via on-chain shared memory.**
- **0G Storage.** Every audit's full anonymized record is written as a JSON blob via `@0glabs/0g-ts-sdk` (through a local Node sidecar) — returns a merkle root + on-chain commitment tx, both surfaced in the receipt next to the chain anchors.
- **0G Compute.** Agent γ can run on a **decentralized inference node** instead of Google Gemini. The coordinator routes through a Node sidecar that signs each request body hash via the broker SDK — 0G Compute auth is per-request, not a static bearer token. `/api/status` reports `zg_compute_transport: "sidecar"` when this path is live.

**Swarm coordination:**
- Three independent LLM agents reason in parallel during round 1 (different SDKs, different keys, different system prompts).
- Findings broadcast over Gensyn AXL (see Track 1).
- Round-2 reflection per agent with peer findings as context — agents may revise verdict, add findings, downgrade contested ones.
- 2-of-3 quorum on canonical billing code; 1-1-1 splits resolve to "clarify" (no silent registration-order tiebreak).

**Code:** [`chain/zerog.py`](./src/coordinator/chain/zerog.py) (anchor writes), [`chain/zerog_storage.py`](./src/coordinator/chain/zerog_storage.py) (pattern indexer), [`chain/zerog_blob.py`](./src/coordinator/chain/zerog_blob.py) (0G Storage uploader), [`chain/patterns.py`](./src/coordinator/chain/patterns.py) (read-back + caching), [`agents/audit_0g.py`](./src/coordinator/agents/audit_0g.py) (γ on 0G Compute), [`scripts/storage_sidecar.ts`](./src/coordinator/scripts/storage_sidecar.ts) and [`scripts/headers_sidecar.ts`](./src/coordinator/scripts/headers_sidecar.ts) (Node bridges to 0G TS SDKs).

---

### 💚 Track 3 — KeeperHub · Best Innovative Use of KeeperHub

**How we use KeeperHub — three distinct workflows.** KeeperHub is the execution platform that turns one consensus into multiple chain-verifiable side effects:

1. **Sepolia mirror anchor (every audit).** KH Direct Execution writes the SHA-256 + verdict to a Sepolia `BillRegistry` mirror via `POST /api/execute/contract-call`. Same record as 0G Galileo, two independent chains. Already-anchored duplicates are detected and the receipt links the original tx via Sepolia event lookup, not "pending".
2. **Dispute auto-file (consensus = `dispute`).** A second KH execution fires against [`DisputeRegistry`](https://sepolia.etherscan.io/address/0xbdb8282aCD9b542b8302d872Fb9BD28B0b5e5290), calling `recordDispute(billHash, reason, note)` with a redacted findings summary. Different contract, different method, different verdict gate.
3. **Appeal-sent attestation (user click).** When the user types a provider email and clicks **Send appeal**, the coordinator emails the appeal letter + chain verification table, then a third KH execution fires against [`AppealRegistry`](https://sepolia.etherscan.io/address/0x69166ACC4718a0062540673F5Cae26997BaB064e), calling `recordAppealSent(billHash, recipientHash)`. Recipient address is keccak-hashed before going on-chain.

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
│   │   └── src/app/{dashboard,axl,patterns,verify,tech-stack}/page.tsx
│   ├── coordinator/           # FastAPI orchestrator
│   │   ├── main.py            # app entry + CORS + sweeper + AXL-off startup banner
│   │   ├── routers/           # jobs, samples, status, verify, appeal (email + KH workflow #3)
│   │   ├── pipeline/          # runner, parser, redactor, consensus, dispute drafter
│   │   ├── agents/            # audit_{openai,anthropic,google,0g}, drafter, transport_axl, prompts
│   │   ├── chain/             # zerog (anchor) · zerog_storage (patterns) · zerog_blob (0G Storage)
│   │   │                      # keeperhub (REST) · keeperhub_mcp (MCP transport) · patterns (read-back)
│   │   ├── email_delivery/    # sender (resend / smtp / stub) + HTML template builder
│   │   ├── scripts/           # Node helpers — provision:0g · headers:0g · storage:0g · check:0g
│   │   ├── samples/           # 5 example bills used by the dashboard chips
│   │   └── store/             # in-memory job store + sweeper, rolling stats
│   └── contracts/             # BillRegistry · PatternRegistry · DisputeRegistry · AppealRegistry
│                              # deployed via deploy.py (py-solc-x + web3.py, no Foundry)
├── infra/
│   └── axl/                   # Dockerfile, configs/{alpha,beta,gamma}.json, keys/peer_ids.json
├── data-gen/                  # Bill PDF generator + PatternRegistry pre-seed script
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
