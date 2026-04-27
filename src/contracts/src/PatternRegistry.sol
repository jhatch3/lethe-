// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title  PatternRegistry
/// @notice Indexes anonymized billing-error patterns observed by Lethe.
/// @dev    No PHI is ever written. Only canonical billing codes (CPT/HCPCS/REV/etc.),
///         the consensus action (dispute/clarify/approve/aligned), severity, and a
///         reference to the bill's SHA-256 anchor.
///
///         These events build a public index of "common dispute-worthy patterns" that
///         any future audit (Lethe or otherwise) can query without touching patient data.
///         Events are cheap (no storage write) and indexable on chainscan-galileo.
contract PatternRegistry {
    /// @notice Emitted for each finding that reached consensus quorum.
    /// @param  billHash    SHA-256 of the bill the pattern was observed in (links to BillRegistry).
    /// @param  code        Indexed billing code (e.g. "CPT 99214"). Bytes32 = up to 32 ASCII chars.
    /// @param  action      "dispute" | "clarify" | "aligned" — the agents' recommended action.
    /// @param  severity    "high" | "medium" | "low".
    /// @param  amountUsd   Dollar amount in USD cents (so $185.00 → 18500). Avoids floats.
    /// @param  voters      Bitmask: bit 0 = alpha voted, bit 1 = beta, bit 2 = gamma. Future-proof up to 8 agents.
    /// @param  indexedBy   Wallet that submitted the pattern (the coordinator).
    /// @param  indexedAt   Block timestamp.
    event PatternIndexed(
        bytes32 indexed billHash,
        bytes32 indexed code,
        bytes16        action,
        bytes8         severity,
        uint64         amountUsd,
        uint8          voters,
        address indexed indexedBy,
        uint64         indexedAt
    );

    /// @notice Optional batch counter — readable, useful for "patterns seen so far".
    uint64 public totalPatterns;

    /// @notice Index a pattern. No access control: any caller can submit, but the indexed
    ///         submitter address makes the event filterable by trusted coordinator.
    function indexPattern(
        bytes32 billHash,
        bytes32 code,
        bytes16 action,
        bytes8  severity,
        uint64  amountUsd,
        uint8   voters
    ) external {
        unchecked { totalPatterns += 1; }
        emit PatternIndexed(
            billHash,
            code,
            action,
            severity,
            amountUsd,
            voters,
            msg.sender,
            uint64(block.timestamp)
        );
    }

    /// @notice Index a batch of patterns from a single audit (cheaper for multiple findings).
    function indexBatch(
        bytes32 billHash,
        bytes32[] calldata codes,
        bytes16[] calldata actions,
        bytes8[]  calldata severities,
        uint64[]  calldata amountsUsd,
        uint8[]   calldata voters
    ) external {
        require(
            codes.length == actions.length &&
            codes.length == severities.length &&
            codes.length == amountsUsd.length &&
            codes.length == voters.length,
            "PatternRegistry: length mismatch"
        );
        for (uint256 i = 0; i < codes.length; i++) {
            unchecked { totalPatterns += 1; }
            emit PatternIndexed(
                billHash,
                codes[i],
                actions[i],
                severities[i],
                amountsUsd[i],
                voters[i],
                msg.sender,
                uint64(block.timestamp)
            );
        }
    }
}
