// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title DisputeRegistry — on-chain record of disputes filed by Lethe audits
/// @author Lethe
/// @notice Records that a Lethe consensus reached `dispute` for a given bill
///         hash. Called by KeeperHub Direct Execution (workflow #2) right
///         after the canonical BillRegistry mirror anchor whenever the
///         consensus verdict is `dispute`.
/// @dev    Mirror of the AppealRegistry pattern but a different gate (consensus
///         verdict vs user-clicked "send"). The `note` field carries the short
///         findings summary built in `pipeline/runner.py` (PHI-redacted by
///         construction — codes + actions only, capped at 512 chars).
contract DisputeRegistry {
    struct Dispute {
        uint8   reason;     // 1 = dispute (room for future expansion)
        string  note;       // short anonymized findings summary
        uint64  filedAt;    // block.timestamp
        address filedBy;    // msg.sender (KH-managed wallet)
    }

    /// billHash -> array of dispute filings (a bill can be disputed multiple
    /// times if re-audited and re-filed, though contract doesn't enforce that)
    mapping(bytes32 => Dispute[]) public disputes;

    event DisputeFiled(
        bytes32 indexed billHash,
        uint8           reason,
        string          note,
        uint64          filedAt,
        address indexed filedBy,
        uint256         disputeIndex
    );

    /// @notice Record that a Lethe consensus disputed this bill.
    /// @param billHash SHA-256 of the original bill (matches BillRegistry)
    /// @param reason   1 = dispute (only value used today)
    /// @param note     short anonymized findings summary, ≤512 chars
    function recordDispute(bytes32 billHash, uint8 reason, string calldata note) external {
        require(bytes(note).length <= 512, "note too long");
        Dispute memory d = Dispute({
            reason:  reason,
            note:    note,
            filedAt: uint64(block.timestamp),
            filedBy: msg.sender
        });
        disputes[billHash].push(d);
        emit DisputeFiled(
            billHash,
            reason,
            note,
            d.filedAt,
            d.filedBy,
            disputes[billHash].length - 1
        );
    }

    /// @notice How many dispute filings exist for this bill?
    function disputeCount(bytes32 billHash) external view returns (uint256) {
        return disputes[billHash].length;
    }
}