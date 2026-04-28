# Lethe — pre-submission roadmap

Living checklist of everything we agreed to ship before submitting to the three sponsor tracks. Items get crossed out as they land. Born out of the three-track audit on 2026-04-27.

## Status legend

- `[ ]` — not started
- `[~]` — in progress
- `[x]` — done (also rendered with ~~strikethrough~~)

---

## Critical fixes from audit (do first)

- [x] ~~Flip `LETHE_AXL_ENABLED` default to `True` in `src/coordinator/config.py`~~ — done, harmonizes with `.env.example:85`. Track 1 no longer silently degrades when judges run `uvicorn` without a `.env`.
- [ ] **$500 KeeperHub Builder Feedback Bounty assets.** README.md:379 and :392 link to files that don't exist in the repo:
  - `docs/keeperhub-feedback/empty-project-state.png`
  - `docs/keeperhub-feedback/right-panel-close-bug.mp4`
  - **Action:** capture the screenshot + screen recording (user task — Claude can't capture images). Once they exist, this item is done.
- [ ] Smoke-test KeeperHub MCP path end-to-end with `LETHE_KEEPERHUB_USE_MCP=true` to confirm the guessed tool names (`execute_contract_call`, `get_direct_execution_status`) match the live KH MCP server. Falls back to REST if not, but Track 3 strict-reading claim depends on this working.

---

## Tier 1 — high prize value, modest effort

### Track 2 · Use 0G Storage for something real
- [x] ~~Built `storage_sidecar.ts` — Node service on `:8788` wrapping `@0glabs/0g-ts-sdk`. POST a JSON blob, get back `{root_hash, tx_hash}` from the on-chain commitment. Same ergonomic pattern as the 0G Compute headers sidecar.~~
- [x] ~~Added `chain/zerog_blob.py` — Python client that POSTs the anonymized pattern record to the sidecar. Stub-fallback when sidecar URL is blank or unreachable.~~
- [x] ~~Wired into `pipeline/runner.py` `patterns` stage — runs in parallel with `index_patterns` on the chain side via `asyncio.gather`. Both layers, one stage.~~
- [x] ~~`storage.uploaded` SSE event emits `root_hash`, `tx_hash`, `bytes` when live.~~
- [x] ~~`/api/status` reports `pattern_storage: "0g-storage-sidecar" | "stub"` honestly.~~
- [x] ~~`.env.example` documents `LETHE_0G_STORAGE_SIDECAR_URL` with the launch command.~~
- [ ] Surface the storage `root_hash` + tx link in the dashboard receipt UI (frontend work — currently the data flows into `proof.patterns.storage` but isn't rendered).
- [ ] Update README Track 2 section: lead with **0G Chain + 0G Storage + 0G Compute** three-pillars framing.
- [ ] Reading back from 0G Storage during pattern read-back loop (currently reads from chain events only — could enrich priors with full structured records when storage is live).

### Track 2 · Pre-seed `PatternRegistry`
- [x] ~~Script `data-gen/scripts/seed_patterns.py` writes ~20 anonymized historical patterns to PatternRegistry. Realistic spread (CPT 99213/99214 downcodes, 74177 unbundling, J3490 modifier, ER 99284/99285, lab duplicates, REV 0450/0301/0250). Per-audit batch sizes 1–3 findings; deterministic synthetic SHAs so re-runs don't collide. Reuses `chain/zerog_storage.index_patterns` so the on-chain shape is identical to a real audit.~~
- [x] ~~Dry-run verified: `python data-gen/scripts/seed_patterns.py --dry-run --count 5` prints the planned writes without touching chain.~~
- [ ] Run once against Galileo (blocked: needs ~0.02 OG total gas across 20 audits, wallet currently 0.052 OG with 0.1 OG floor for Compute provisioning — could run pre-seed *first* before provisioning since it doesn't need the ledger).
- [ ] Verify via `/api/patterns` that aggregates show non-zero observations.

### Track 3 · Use KeeperHub beyond the mirror anchor — THREE workflows
- [x] ~~**Workflow #2: dispute auto-file** — when consensus = `dispute`, fire a second KH Direct Execution against a configurable Sepolia DisputeRegistry, recording `recordDispute(bytes32 billHash, uint8 reason, string note)`.~~
- [x] ~~**Workflow #3: appeal-sent attestation** — when the user clicks "Send to provider" with an email address, the coordinator (a) emails the appeal letter + chain verification table via `email_delivery/sender.py` (resend / smtp / stub), and (b) fires `attest_appeal_sent_via_keeperhub()` to call `recordAppealSent(billHash, recipientHash)` on a Sepolia `AppealRegistry`. Recipient address is keccak-hashed before going on-chain.~~
- [x] ~~`AppealRegistry.sol` — minimal contract with `recordAppealSent` + `appealCount` view + indexed `AppealSent` event.~~
- [x] ~~Email pipeline: `email_delivery/template.py` builds inline-styled HTML (appeal letter + chain verification rows linking to chainscan + etherscan), `email_delivery/sender.py` dispatches via Resend SDK / SMTP / stub.~~
- [x] ~~New router `routers/appeal.py` with `POST /api/appeal/submit` — looks up job result, sends email, fires KH attestation, returns combined status.~~
- [x] ~~Dashboard form: email input + "Send appeal" button after consensus, status display showing `email · provider · delivered` and `keeperhub workflow #3 · executor · tx_hash ↗`.~~
- [x] ~~`/api/status` exposes `keeperhub_dispute_filer` + `keeperhub_appeal_attestor` + `email_provider` + `email_configured`.~~
- [x] ~~`.env.example` documents `LETHE_DISPUTE_REGISTRY_ADDRESS_SEPOLIA`, `LETHE_APPEAL_REGISTRY_ADDRESS_SEPOLIA`, and the email provider env block (resend + smtp).~~
- [x] ~~Deployed `DisputeRegistry` (`0xbdb8282aCD9b542b8302d872Fb9BD28B0b5e5290`) + `AppealRegistry` (`0x69166ACC4718a0062540673F5Cae26997BaB064e`) on Sepolia. Both verified on-chain. Tx: [dispute](https://sepolia.etherscan.io/tx/0x9f2c796732880a2de2d9dcdd11bd494cd347d98d0bb92b18459e677ef5ba589d) · [appeal](https://sepolia.etherscan.io/tx/0x64b62d070eaf7e8de02cf7804d0b66cf36dae9fdab1902142bf08d58b7606c06). Once the addresses are pasted into `.env`, both KH workflows go live.~~
- [ ] Set `LETHE_EMAIL_PROVIDER=resend` + `LETHE_RESEND_API_KEY=re_...` (free tier, signup at resend.com) for the demo to actually deliver mail.
- [ ] Update SETUP.md §KeeperHub with the new contracts + email provisioning.

### Track 1 · Live AXL message stream in the frontend
- [x] ~~Add a server-side ring buffer in `transport_axl.py` that records every send + recv with size, sender→receiver pubkey pair, latency, byte count, finding count, ok/error.~~
- [x] ~~Extend `/api/axl` to return `messages` array (last 200, most-recent-first).~~
- [x] ~~Frontend `/axl` page renders a `MessageLog` panel below the peer roster — color-coded send/recv, ed25519 pubkey shorts, latency + bytes + finding count, ok/error badge. Polls on the existing 5s loop.~~
- [ ] Verify on demo: run an audit, watch packets flow live in the panel. (Requires a real audit run with AXL up — defer until faucet/docker session.)

---

## Tier 2 — bigger swings worth taking

### Track 2 · iNFT — receipt-as-iNFT — DEFERRED
> Researched 2026-04-27. Key finding: 0G's "iNFT Innovations" prize scores against **ERC-7857** specifically (an EIP authored by 0G Labs themselves, reference impl at `github.com/0glabs/0g-agent-nft@eip-7857-draft`). NOT Alethea AI's older standard.
>
> Judges grep for three things: (1) encrypted metadata off-chain in 0G Storage with only the hash on-chain, (2) `transfer(from,to,id,sealedKey,proof)` actually re-encrypts via TEE/ZKP oracle, (3) `authorizeUsage(tokenId, delegate)` runs inference (not just exposes data). Pointer-NFTs get downgraded.
>
> Estimated ~650 LOC across Solidity (~270, including ERC-7857 interface + mock TEE oracle) + Python minting + frontend receipt page. ~6–8 hours of focused work.
>
> Full design + reasoning saved in memory at `~/.claude/projects/C--Users-Justin-lethe-/memory/inft_erc7857.md`.
- [ ] **Deferred** — pick this up after Tier 1 lands cleanly and the rest of the demo is rock-solid. Half-done iNFT is worse than no iNFT for prize judging.

### Track 1 · Network partition demo
- [ ] Test killing `axl-beta` mid-audit. Currently behavior is undefined — runner may hang on `recv`.
- [ ] Add timeout + skip-and-record-degraded-mode logic in `_exchange()` and `_reflect_all()` in `pipeline/runner.py`.
- [ ] Surface "1 peer offline · degraded to 2-of-2" in the UI when it happens.
- [ ] Demo script: kill a sidecar live, run an audit, show graceful degradation. This is the kind of thing that flips a "Best Application" judgment.

### Track 1 · Signature verification in UI
- [ ] Confirm AXL messages are actually signed end-to-end (read sidecar config + `transport_axl.py` send path).
- [ ] If yes: surface ✅ verified / ❌ failed badge next to each message in the live log.
- [ ] If no: add ed25519 signing on send + verification on receive. This converts "we used AXL's API" into "we used AXL's security guarantees" — load-bearing for "Best Application of AXL."

---

## Tier 3 — polish, nice-to-haves

- [ ] More on-chain events: emit per-vote events on Galileo (not just the final verdict). The chain becomes the audit log.
- [ ] KeeperHub MCP for *user queries* (not just transport): expose a tool like `query_audits_by_cpt(code)` so someone in Claude Desktop can ask "show me audits with disputed CPT 99213" and get on-chain data back. This makes MCP a feature, not just an alternate transport.
- [x] ~~Document bootstrap-peer provenance in `infra/axl/README.md`. Added a section explaining the role of `34.46.48.224` and `136.111.135.206` as Gensyn-operated mesh entry points (analogous to Bitcoin DNS seeds / libp2p bootstrap peers), how to verify peering, and how to switch to an offline-only mesh.~~
- [x] ~~Loud startup banner in `main.py` lifespan when `axl.is_enabled()==false` — explicit reason (env-off / peer_ids missing / sidecar URLs missing) and a one-line "to enable: docker compose up" hint. Track 1 claim is now impossible to silently bypass.~~
- [x] ~~Galileo "view chainscan" links in the dashboard receipt for the BillRegistry anchor tx and the PatternRegistry index tx (Sepolia mirror + KH dispute already had etherscan links).~~
- [x] ~~Pattern read-back honesty: enhanced the empty-state on `/patterns` with an explicit "first audit · no on-chain history yet" callout, plain explanation of what that means for the priors loop, and a copy-paste pre-seed command.~~
- [ ] Faucet recovery: get the 0G Compute provisioning unblocked once wallet hits ≥0.105 OG. (`npm run check:0g` then `npm run provision:0g`.)

---

## Submission-day pre-flight (run all of these before the deadline)

- [ ] `npm run check:0g` — confirm wallet, ledger, provider all OK
- [ ] `docker compose up --build` — three sidecars + coordinator + frontend
- [ ] `/api/status` — every config flag honest, every track shows live (not stub)
- [ ] `/api/axl` — three real `/topology` responses, matching pubkeys
- [ ] Run an audit end-to-end. Verify:
  - Agents stream tokens
  - Findings broadcast over AXL with verified signatures
  - Round-2 reflection fires per agent
  - Consensus tally is honest (no insertion-order tiebreak)
  - Galileo + Sepolia tx hashes both in receipt
  - iNFT minted, token URI resolves
  - Pattern record landed on 0G Storage (if Tier 1 done)
  - Dispute auto-filed via KH workflow (if Track 3 expansion done)
- [ ] Block-explorer spot-check: each tx visible, contract addresses match `.env.example`
- [ ] Strip every TODO that didn't ship from README — be honest about what's there
