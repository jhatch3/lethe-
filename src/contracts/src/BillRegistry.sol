// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title  BillRegistry
/// @notice Anchors a SHA-256 hash + consensus verdict for an audited medical bill.
///         No PHI is ever written here; only the hash, the verdict (dispute/approve/clarify),
///         and the agent agreement count.
/// @dev    The `anchor` function reverts on duplicate writes so the same bill cannot be
///         re-anchored under a different verdict.
contract BillRegistry {
    enum Verdict { None, Dispute, Approve, Clarify }

    struct Anchor {
        Verdict  verdict;
        uint8    agreeCount;     // number of agents that voted with the majority
        uint8    totalAgents;
        uint64   anchoredAt;     // block timestamp
        address  anchoredBy;
    }

    mapping(bytes32 => Anchor) public anchors;

    event Anchored(
        bytes32 indexed sha256Hash,
        Verdict        verdict,
        uint8          agreeCount,
        uint8          totalAgents,
        uint64         anchoredAt,
        address        indexed anchoredBy
    );

    /// @notice Anchor a bill audit result.
    /// @param sha256Hash The SHA-256 of the original bill bytes (computed pre-redaction).
    /// @param verdict 1=Dispute, 2=Approve, 3=Clarify.
    /// @param agreeCount Number of agents that voted with the majority.
    /// @param totalAgents Total agents that participated in the vote.
    function anchor(
        bytes32 sha256Hash,
        uint8   verdict,
        uint8   agreeCount,
        uint8   totalAgents
    ) external {
        require(verdict >= 1 && verdict <= 3, "BillRegistry: invalid verdict");
        require(agreeCount > 0 && agreeCount <= totalAgents, "BillRegistry: bad counts");
        require(anchors[sha256Hash].anchoredAt == 0, "BillRegistry: already anchored");

        Anchor memory a = Anchor({
            verdict:      Verdict(verdict),
            agreeCount:   agreeCount,
            totalAgents:  totalAgents,
            anchoredAt:   uint64(block.timestamp),
            anchoredBy:   msg.sender
        });
        anchors[sha256Hash] = a;

        emit Anchored(sha256Hash, a.verdict, agreeCount, totalAgents, a.anchoredAt, msg.sender);
    }

    /// @notice True if a hash has been anchored.
    function isAnchored(bytes32 sha256Hash) external view returns (bool) {
        return anchors[sha256Hash].anchoredAt != 0;
    }
}