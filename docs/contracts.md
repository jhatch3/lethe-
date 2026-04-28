# 📘 LetheRegistry — Contract Reference

Both deployments (0G Galileo + Ethereum Sepolia) run the **same** [`LetheRegistry.sol`](../src/contracts/src/LetheRegistry.sol) source. Below is the full surface — every method, every event, with inputs, outputs, gates, and how to call each one. Anything in the contract that isn't in this doc doesn't exist.

> **Deployed addresses** are in the README's [On-chain artifacts](../README.md#%EF%B8%8F-on-chain-artifacts) table.
> **Setup + faucet links** are in [`setup.md`](./setup.md).

---

## Table of contents

- [Write methods](#write-methods)
- [Read methods](#read-methods)
- [Events](#events)
- [Quick examples](#quick-examples)
- [HTTP shortcuts](#http-shortcuts)

---

## Write methods

State-changing. Cost gas. Some are gated.

| Method | Inputs | What happens | Gates | Caller in production |
|---|---|---|---|---|
| `anchor` | `billHash bytes32` · `verdict uint8` (1 dispute / 2 approve / 3 clarify) · `agreeCount uint8` · `totalAgents uint8` · `npiHash bytes32` (zero ok) · `storageRoot bytes32` (zero ok) · `rulebookVersion uint16` · `flaggedCents uint64` | Stores the `Anchor` struct, atomically rolls up `providerStats[npiHash]` if non-zero, emits `BillAnchored` | reverts if `verdict ∉ {1,2,3}`, `agreeCount > totalAgents`, or this `billHash` was already anchored | coordinator (Galileo) · KH workflow #1 (Sepolia) |
| `indexFindings` | `billHash bytes32` · 5 parallel arrays — `codes bytes32[]` · `actions bytes16[]` · `severities bytes8[]` · `amountsCents uint64[]` · `voters uint8[]` (bitmask: α=1, β=2, γ=4) | Emits one `Finding` event per finding | reverts if bill not anchored, or arrays are different lengths | coordinator only (Galileo) |
| `recordDispute` | `billHash bytes32` · `reason uint8` · `note string` (≤ 512 chars) | Emits `DisputeFiled` | reverts if `note > 512` chars or anchor's verdict isn't `Dispute` | KH workflow #2 (Sepolia) |
| `recordAppealSent` | `billHash bytes32` · `recipientHash bytes32` (keccak of email + salt) | Emits `AppealSent` | reverts if bill not anchored | KH workflow #3 (Sepolia) |
| `publishRulebook` | `version uint16` (must be ≥ 1) · `manifestRoot bytes32` (0G Storage merkle root for the rules JSON) | Sets `rulebookManifest[version]`, advances `currentRulebookVersion` if `version > current`, emits `RulebookPublished` | `onlyOwner` | coordinator at deploy time + each NCCI quarterly bump |
| `transferOwnership` | `newOwner address` (non-zero) | Updates `owner`, emits `OwnerTransferred` | `onlyOwner`, non-zero new owner | one-time setup or DAO migration |

---

## Read methods

Free, view, no gas. Anyone can call.

| Method | Inputs | Returns |
|---|---|---|
| `anchors(billHash bytes32)` | one bill | full struct: `verdict uint8` · `agreeCount uint8` · `totalAgents uint8` · `npiHash bytes32` · `storageRoot bytes32` · `rulebookVersion uint16` · `anchoredAt uint64` · `anchoredBy address` |
| `isAnchored(billHash bytes32)` | one bill | `bool` — `true` if any anchor exists |
| `providerStats(npiHash bytes32)` | one provider's NPI hash | aggregate: `totalAudits uint32` · `disputeCount uint32` · `clarifyCount uint32` · `approveCount uint32` · `totalFlaggedCents uint128` |
| `disputeRateBps(npiHash bytes32)` | one provider | `uint256` basis points (10000 = 100%); 0 if no audits |
| `rulebookManifest(version uint16)` | rule version number | `bytes32` — 0G Storage merkle root holding the rules JSON for that version |
| `currentRulebookVersion()` | — | `uint16` |
| `owner()` | — | `address` |

---

## Events

Queryable via `eth_getLogs`. All events have **indexed topics** marked `[i]` — those are filterable directly in `topics[]`.

| Event | Fields | Indexed | When it fires | Why you'd query it |
|---|---|---|---|---|
| `BillAnchored` | `billHash` · `npiHash` · `verdict` · `agreeCount` · `totalAgents` · `storageRoot` · `rulebookVersion` · `flaggedCents` · `anchoredAt` · `anchoredBy` | `[i] billHash`, `[i] npiHash`, `[i] anchoredBy` | every `anchor()` call | "all audits for this bill" / "all audits this wallet anchored" / "all audits for this provider" |
| `Finding` | `billHash` · `code` · `action` · `severity` · `amountCents` · `voters` · `indexedBy` · `indexedAt` | `[i] billHash`, `[i] code`, `[i] indexedBy` | once per finding inside `indexFindings()` | "all findings for code CPT 99214" — drives the priors loop |
| `DisputeFiled` | `billHash` · `reason` · `note` · `filedAt` · `filedBy` | `[i] billHash`, `[i] filedBy` | every `recordDispute()` | "show me every dispute filing for this bill" |
| `AppealSent` | `billHash` · `recipientHash` · `sentAt` · `sentBy` | `[i] billHash`, `[i] recipientHash`, `[i] sentBy` | every `recordAppealSent()` | "did this bill ever get an appeal sent?" |
| `RulebookPublished` | `version` · `manifestRoot` · `publishedAt` · `publishedBy` | `[i] version`, `[i] publishedBy` | every `publishRulebook()` | rulebook history / audit trail of rule changes |
| `OwnerTransferred` | `from` · `to` | `[i] from`, `[i] to` | rare | governance transfer history |

---

## Quick examples

### Anchor a new audit (write)
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

### Look up a single audit (read · free)
```python
sha = bytes.fromhex("a1b2c3...64hex")
r = contract.functions.anchors(sha).call()
# r = (1, 3, 3, b'\x3b\x3d…', b'\x9f\x4a…', 1, 1714353600, '0x2b17…E99D')
```
Or hit the dashboard: [`localhost:3000/verify?sha=0xa1b2...`](http://localhost:3000) — same data, rendered.

### Get a provider's dispute rate (read · free)
```python
npi_hash = sha256(("lethe-npi-v1:" + "1234567890").encode()).digest()
stats = contract.functions.providerStats(npi_hash).call()
# (totalAudits=12, disputeCount=8, clarifyCount=2, approveCount=2, totalFlaggedCents=320000)
rate_bps = contract.functions.disputeRateBps(npi_hash).call()  # 6666 = 66.66%
```

### Scan all findings for a CPT code (priors loop)
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

### Pull the full audit blob from 0G Storage
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

### File a dispute (KH workflow #2 on Sepolia)
```python
# fired by KH executor, not the coordinator directly
contract.functions.recordDispute(
    sha,
    1,                                  # reason
    "CPT 99214 bundled into 99213 · CPT 80053 units > MUE cap of 1",
).transact()
```

### Attest an appeal was sent (KH workflow #3 on Sepolia)
```python
recipient_hash = keccak("billing@hospital.example".encode() + SALT)
contract.functions.recordAppealSent(sha, recipient_hash).transact()
```

### Bump the NCCI rulebook to a new version (one-tx upgrade · owner-only)
```python
# 1. upload rules JSON to 0G Storage → returns merkle root
manifest_root = upload_to_zg_storage(json.dumps(NEW_RULES_V2).encode())

# 2. anchor the manifest hash on chain (auto-advances currentRulebookVersion)
contract.functions.publishRulebook(2, manifest_root).transact()

# Future audits read the v2 rules:
# - manifest_root = contract.functions.rulebookManifest(2).call()
# - blob = sidecar GET /download?root=manifest_root
```

---

## HTTP shortcuts

If you don't want to write web3 code, the coordinator wraps the read paths above. Run `uvicorn` and:

| Endpoint | What it does under the hood |
|---|---|
| `GET /api/verify/<sha>` | Reads `anchors(sha)`, scans `Finding`/`DisputeFiled`/`AppealSent` events for that bill on **both** chains, downloads the 0G Storage blob, returns one bundled JSON |
| `GET /api/providers/<npi>` | Hashes the NPI, calls `providerStats(npiHash)`, returns the aggregate |
| `GET /api/rules` | Calls `currentRulebookVersion()`, then `rulebookManifest(v)`, then fetches the JSON from 0G Storage |
