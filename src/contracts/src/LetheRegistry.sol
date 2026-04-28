// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title  LetheRegistry — unified anchor + findings + dispute + appeal + rulebook pointer
/// @author Lethe
/// @notice Single contract replacing BillRegistry + PatternRegistry + StorageIndex +
///         DisputeRegistry + AppealRegistry + ProviderReputation + on-chain rule storage.
///         Same product surface, one address per chain.
///
///         Deployed on 0G Galileo (canonical) and Ethereum Sepolia (KeeperHub-mirrored).
///         The Sepolia instance only ever sees `anchor`, `recordDispute`, `recordAppealSent`
///         calls from KH workflows. The Galileo instance additionally receives
///         `indexFindings` and `publishRulebook` calls from the coordinator.
///
///         Rulebook *content* lives in 0G Storage; only the manifest root is anchored
///         here so coordinator + agents can verify which rules version produced which
///         audit without paying gas to read rule rows.
contract LetheRegistry {
    enum Verdict { None, Dispute, Approve, Clarify }

    struct Anchor {
        Verdict verdict;
        uint8   agreeCount;
        uint8   totalAgents;
        bytes32 npiHash;          // salted SHA-256 of provider NPI (zero if unknown)
        bytes32 storageRoot;      // 0G Storage merkle root for the full audit blob (zero if not uploaded)
        uint16  rulebookVersion;  // which NCCIRulebook manifest this audit ran against
        uint64  anchoredAt;       // block.timestamp
        address anchoredBy;       // msg.sender
    }

    /// Aggregate stats per provider — cheap read for /providers/<npi> without a subgraph.
    /// Updated atomically inside `anchor()`.
    struct ProviderStats {
        uint32  totalAudits;
        uint32  disputeCount;
        uint32  clarifyCount;
        uint32  approveCount;
        uint128 totalFlaggedCents;
    }

    address public owner;
    uint16  public currentRulebookVersion;

    mapping(bytes32 => Anchor)         public anchors;            // billHash -> anchor
    mapping(bytes32 => ProviderStats)  public providerStats;      // npiHash -> stats
    mapping(uint16  => bytes32)        public rulebookManifest;   // version -> 0G Storage root for rules JSON

    // === Events ===

    event BillAnchored(
        bytes32 indexed billHash,
        bytes32 indexed npiHash,
        Verdict         verdict,
        uint8           agreeCount,
        uint8           totalAgents,
        bytes32         storageRoot,
        uint16          rulebookVersion,
        uint64          flaggedCents,
        uint64          anchoredAt,
        address indexed anchoredBy
    );

    event Finding(
        bytes32 indexed billHash,
        bytes32 indexed code,
        bytes16         action,        // "dispute" | "clarify" | "aligned"
        bytes8          severity,      // "high" | "medium" | "low"
        uint64          amountCents,
        uint8           voters,        // bitmask: bit 0 = α, bit 1 = β, bit 2 = γ
        address indexed indexedBy,
        uint64          indexedAt
    );

    event DisputeFiled(
        bytes32 indexed billHash,
        uint8           reason,
        string          note,
        uint64          filedAt,
        address indexed filedBy
    );

    event AppealSent(
        bytes32 indexed billHash,
        bytes32 indexed recipientHash,
        uint64          sentAt,
        address indexed sentBy
    );

    event RulebookPublished(
        uint16  indexed version,
        bytes32         manifestRoot,
        uint64          publishedAt,
        address indexed publishedBy
    );

    event OwnerTransferred(address indexed from, address indexed to);

    modifier onlyOwner() {
        require(msg.sender == owner, "LetheRegistry: not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
        currentRulebookVersion = 1;
    }

    // === Core anchor (called by coordinator on Galileo, by KH workflow #1 on Sepolia) ===

    /// @notice Anchor a bill audit. Reverts on duplicate billHash.
    /// @param  billHash         SHA-256 of the original bill bytes (computed pre-redaction).
    /// @param  verdict          1=Dispute, 2=Approve, 3=Clarify.
    /// @param  agreeCount       agents that voted with the majority.
    /// @param  totalAgents      total agents that participated.
    /// @param  npiHash          salted SHA-256 of provider NPI; pass zero if unknown.
    /// @param  storageRoot      0G Storage merkle root for the full audit blob; zero if not uploaded.
    /// @param  rulebookVersion  which rulebook version this audit used.
    /// @param  flaggedCents     total disputed dollars across the audit, in cents (uint64 caps ~$1.8e17).
    function anchor(
        bytes32 billHash,
        uint8   verdict,
        uint8   agreeCount,
        uint8   totalAgents,
        bytes32 npiHash,
        bytes32 storageRoot,
        uint16  rulebookVersion,
        uint64  flaggedCents
    ) external {
        require(verdict >= 1 && verdict <= 3, "LetheRegistry: invalid verdict");
        require(agreeCount > 0 && agreeCount <= totalAgents, "LetheRegistry: bad counts");
        require(anchors[billHash].anchoredAt == 0, "LetheRegistry: already anchored");

        Anchor memory a = Anchor({
            verdict:         Verdict(verdict),
            agreeCount:      agreeCount,
            totalAgents:     totalAgents,
            npiHash:         npiHash,
            storageRoot:     storageRoot,
            rulebookVersion: rulebookVersion,
            anchoredAt:      uint64(block.timestamp),
            anchoredBy:      msg.sender
        });
        anchors[billHash] = a;

        // Provider aggregate stats — only roll up if an NPI was extracted.
        if (npiHash != bytes32(0)) {
            ProviderStats storage s = providerStats[npiHash];
            s.totalAudits += 1;
            if (verdict == 1) s.disputeCount += 1;
            else if (verdict == 2) s.approveCount += 1;
            else                   s.clarifyCount += 1;
            s.totalFlaggedCents += flaggedCents;
        }

        emit BillAnchored(
            billHash,
            npiHash,
            a.verdict,
            agreeCount,
            totalAgents,
            storageRoot,
            rulebookVersion,
            flaggedCents,
            a.anchoredAt,
            msg.sender
        );
    }

    // === Findings (PatternRegistry replacement; called once per audit on the canonical chain) ===

    /// @notice Emit a batch of findings as events. Anchor must already exist.
    function indexFindings(
        bytes32 billHash,
        bytes32[] calldata codes,
        bytes16[] calldata actions,
        bytes8[]  calldata severities,
        uint64[]  calldata amountsCents,
        uint8[]   calldata voters
    ) external {
        require(anchors[billHash].anchoredAt != 0, "LetheRegistry: bill not anchored");
        require(
            codes.length == actions.length &&
            codes.length == severities.length &&
            codes.length == amountsCents.length &&
            codes.length == voters.length,
            "LetheRegistry: findings length mismatch"
        );
        uint64 ts = uint64(block.timestamp);
        for (uint256 i = 0; i < codes.length; i++) {
            emit Finding(
                billHash,
                codes[i],
                actions[i],
                severities[i],
                amountsCents[i],
                voters[i],
                msg.sender,
                ts
            );
        }
    }

    // === KH workflow #2: dispute filing (only valid when verdict == Dispute) ===

    function recordDispute(bytes32 billHash, uint8 reason, string calldata note) external {
        require(bytes(note).length <= 512, "LetheRegistry: note too long");
        require(anchors[billHash].verdict == Verdict.Dispute, "LetheRegistry: bill not in dispute");
        emit DisputeFiled(billHash, reason, note, uint64(block.timestamp), msg.sender);
    }

    // === KH workflow #3: appeal-sent attestation (user-clicked) ===

    function recordAppealSent(bytes32 billHash, bytes32 recipientHash) external {
        require(anchors[billHash].anchoredAt != 0, "LetheRegistry: bill not anchored");
        emit AppealSent(billHash, recipientHash, uint64(block.timestamp), msg.sender);
    }

    // === Rulebook manifest pointer (rules JSON lives in 0G Storage) ===

    /// @notice Anchor a rulebook version's manifest hash. The actual rule rows live in
    ///         0G Storage — agents pull `manifestRoot` and verify the JSON against it.
    function publishRulebook(uint16 version, bytes32 manifestRoot) external onlyOwner {
        require(version > 0, "LetheRegistry: version must be >= 1");
        rulebookManifest[version] = manifestRoot;
        if (version > currentRulebookVersion) {
            currentRulebookVersion = version;
        }
        emit RulebookPublished(version, manifestRoot, uint64(block.timestamp), msg.sender);
    }

    // === Read helpers ===

    function isAnchored(bytes32 billHash) external view returns (bool) {
        return anchors[billHash].anchoredAt != 0;
    }

    /// @notice Dispute rate as basis points (10000 = 100%).
    function disputeRateBps(bytes32 npiHash) external view returns (uint256) {
        ProviderStats memory s = providerStats[npiHash];
        if (s.totalAudits == 0) return 0;
        return (uint256(s.disputeCount) * 10_000) / uint256(s.totalAudits);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "LetheRegistry: zero addr");
        emit OwnerTransferred(owner, newOwner);
        owner = newOwner;
    }
}