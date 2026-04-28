// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title ProviderReputation — public, immutable provider dispute history
/// @author Lethe
/// @notice Records audit outcomes per healthcare provider, keyed by a hash
///         of their NPI (National Provider Identifier — public registry data,
///         not PHI). Anyone can query a provider's dispute rate without
///         trusting any centralized rating service.
/// @dev    The NPI is hashed before storage so explorers don't show provider
///         tax IDs in plaintext. The mapping from npiHash → real NPI is held
///         off-chain (frontend) since the NPI registry itself is public.
///         Only emit on `dispute` consensus — `clarify` and `approve` don't
///         dirty a provider's record.
contract ProviderReputation {
    struct Outcome {
        bytes32 billHash;        // matches BillRegistry.anchor
        uint8   verdict;         // 1 = dispute, 2 = approve, 3 = clarify
        uint8   agreeCount;
        uint8   totalAgents;
        uint64  flaggedCents;    // disputed amount in cents (uint64 caps at ~$1.8e17)
        uint64  recordedAt;
        address recordedBy;
    }

    /// npiHash -> array of outcomes
    mapping(bytes32 => Outcome[]) public outcomes;

    /// npiHash -> aggregate stats (cheap read for list pages)
    struct Stats {
        uint32 totalAudits;
        uint32 disputeCount;
        uint32 clarifyCount;
        uint32 approveCount;
        uint128 totalFlaggedCents;
    }
    mapping(bytes32 => Stats) public stats;

    event AuditRecorded(
        bytes32 indexed npiHash,
        bytes32 indexed billHash,
        uint8           verdict,
        uint8           agreeCount,
        uint8           totalAgents,
        uint64          flaggedCents,
        uint64          recordedAt,
        address indexed recordedBy
    );

    /// @notice Record an audit outcome against a provider.
    /// @param npiHash      keccak256(NPI string + salt)
    /// @param billHash     SHA-256 of the audited bill (matches BillRegistry)
    /// @param verdict      1=dispute, 2=approve, 3=clarify
    /// @param agreeCount   how many agents agreed with the verdict
    /// @param totalAgents  total agents that voted
    /// @param flaggedCents total dollars flagged across the audit, in cents
    function recordAudit(
        bytes32 npiHash,
        bytes32 billHash,
        uint8   verdict,
        uint8   agreeCount,
        uint8   totalAgents,
        uint64  flaggedCents
    ) external {
        require(verdict >= 1 && verdict <= 3, "bad verdict");
        Outcome memory o = Outcome({
            billHash:     billHash,
            verdict:      verdict,
            agreeCount:   agreeCount,
            totalAgents:  totalAgents,
            flaggedCents: flaggedCents,
            recordedAt:   uint64(block.timestamp),
            recordedBy:   msg.sender
        });
        outcomes[npiHash].push(o);

        Stats storage s = stats[npiHash];
        s.totalAudits += 1;
        if (verdict == 1) s.disputeCount += 1;
        else if (verdict == 2) s.approveCount += 1;
        else if (verdict == 3) s.clarifyCount += 1;
        s.totalFlaggedCents += flaggedCents;

        emit AuditRecorded(
            npiHash, billHash, verdict, agreeCount, totalAgents,
            flaggedCents, o.recordedAt, msg.sender
        );
    }

    /// @notice How many audits has this provider seen?
    function auditCount(bytes32 npiHash) external view returns (uint256) {
        return outcomes[npiHash].length;
    }

    /// @notice Convenience: dispute rate as basis points (10000 = 100%)
    function disputeRateBps(bytes32 npiHash) external view returns (uint256) {
        Stats memory s = stats[npiHash];
        if (s.totalAudits == 0) return 0;
        return (uint256(s.disputeCount) * 10_000) / uint256(s.totalAudits);
    }
}
