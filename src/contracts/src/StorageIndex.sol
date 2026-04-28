// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title StorageIndex — on-chain pointer from a bill audit to its 0G Storage root
/// @author Lethe
/// @notice Records the 0G Storage merkle root that holds the full anonymized
///         audit blob for a given bill. Together with `BillRegistry` and
///         `PatternRegistry` this closes the loop: chain events tell you a
///         bill was audited and what was found at a high level; the storage
///         root lets agents (or anyone) fetch the full structured record.
/// @dev    Called by the coordinator immediately after a successful storage
///         upload, mirroring the same pattern as DisputeRegistry/AppealRegistry.
///         Indexed by both `billHash` and `storageRoot` so judges can grep
///         either way on the explorer.
contract StorageIndex {
    struct Record {
        bytes32 storageRoot;
        uint64  indexedAt;
        address indexedBy;
    }

    /// billHash -> array of storage-root records (a re-audit can produce
    /// a fresh storage root for the same bill).
    mapping(bytes32 => Record[]) public roots;

    event RootIndexed(
        bytes32 indexed billHash,
        bytes32 indexed storageRoot,
        uint64          indexedAt,
        address indexed indexedBy,
        uint256         rootIndex
    );

    /// @notice Record that a bill's audit blob lives at this 0G Storage root.
    /// @param billHash    SHA-256 of the original bill (matches BillRegistry)
    /// @param storageRoot Merkle root returned by the 0G Storage upload
    function recordStorageRoot(bytes32 billHash, bytes32 storageRoot) external {
        Record memory r = Record({
            storageRoot: storageRoot,
            indexedAt:   uint64(block.timestamp),
            indexedBy:   msg.sender
        });
        roots[billHash].push(r);
        emit RootIndexed(
            billHash,
            storageRoot,
            r.indexedAt,
            r.indexedBy,
            roots[billHash].length - 1
        );
    }

    /// @notice How many storage roots are recorded for this bill?
    function rootCount(bytes32 billHash) external view returns (uint256) {
        return roots[billHash].length;
    }
}