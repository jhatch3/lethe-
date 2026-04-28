// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title AppealRegistry — on-chain attestation that an appeal letter was sent
/// @author Lethe
/// @notice Records that a Lethe-audited bill's appeal letter + chain verification
///         was emailed to a specific provider. The recipient address is hashed
///         on-chain (never stored plaintext) for privacy + GDPR-friendliness.
/// @dev    Called by KeeperHub Direct Execution as the THIRD KH workflow per audit
///         (after the BillRegistry mirror anchor and the optional DisputeRegistry
///         filing). Same execution-platform pattern; different verdict gate
///         (only fires on user-clicked send, not auto).
contract AppealRegistry {
    struct Appeal {
        bytes32 recipientHash;   // keccak256(email | salt) — opaque
        uint64  sentAt;          // block.timestamp
        address sentBy;          // msg.sender (the KH-managed wallet)
    }

    /// billHash -> array of appeal-send attestations (a bill can be appealed
    /// to multiple providers / multiple times)
    mapping(bytes32 => Appeal[]) public appeals;

    event AppealSent(
        bytes32 indexed billHash,
        bytes32 indexed recipientHash,
        uint64          sentAt,
        address indexed sentBy,
        uint256         appealIndex
    );

    /// @notice Record that an appeal letter was sent for a given bill audit.
    /// @param billHash      SHA-256 of the original bill (matches BillRegistry)
    /// @param recipientHash keccak256 of the recipient email + a salt
    function recordAppealSent(bytes32 billHash, bytes32 recipientHash) external {
        Appeal memory a = Appeal({
            recipientHash: recipientHash,
            sentAt:        uint64(block.timestamp),
            sentBy:        msg.sender
        });
        appeals[billHash].push(a);
        emit AppealSent(
            billHash,
            recipientHash,
            a.sentAt,
            a.sentBy,
            appeals[billHash].length - 1
        );
    }

    /// @notice How many appeals have been sent for this bill?
    function appealCount(bytes32 billHash) external view returns (uint256) {
        return appeals[billHash].length;
    }
}
