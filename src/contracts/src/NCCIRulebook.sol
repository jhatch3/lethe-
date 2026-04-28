// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title NCCIRulebook — versioned medical-coding rules on-chain
/// @author Lethe
/// @notice CMS publishes National Correct Coding Initiative (NCCI) edits
///         quarterly. Codifying them on-chain means agents query a single
///         canonical ruleset, anyone can audit the rule set, and updates
///         can be governance-voted instead of pushed by a vendor.
/// @dev    Each rule is a struct keyed by `ruleId`. The contract maintains
///         a `currentVersion` counter; rules are tagged with the version
///         they belong to so historical lookups still work after updates.
///         Owner-gated writes for now — DAO/multisig in V2.
contract NCCIRulebook {
    enum RuleKind {
        Unknown,
        MutuallyExclusive,    // CPT_A and CPT_B can't both bill same date
        BundledIntoColumn1,   // Column 2 code is bundled into Column 1
        ModifierRequired,     // Pair allowed only with a specific modifier
        UnitsCap,             // Max units per day for a CPT
        ModifierAbuseFlag     // Modifier-25 abuse with E/M codes
    }

    struct Rule {
        uint16  id;
        uint16  version;       // CMS quarterly version (e.g. 26 = 2026 Q2)
        RuleKind kind;
        bytes32 cptA;          // primary code (left-padded ASCII like "CPT 99213")
        bytes32 cptB;          // secondary code (zero if N/A)
        bytes16 mod;           // required modifier (e.g. "59", "25") or empty
        uint32  unitsCapPerDay; // for UnitsCap rules; 0 otherwise
        string  citation;      // CMS source — chapter/section reference
    }

    address public owner;
    uint16  public currentVersion;
    uint16  public nextRuleId;

    mapping(uint16 => Rule) public rules;
    /// version -> rule ids in that version
    mapping(uint16 => uint16[]) public ruleIdsByVersion;

    event RuleAdded(
        uint16 indexed id,
        uint16 indexed version,
        RuleKind kind,
        bytes32 cptA,
        bytes32 cptB,
        bytes16 mod_
    );
    event VersionPublished(uint16 indexed version, uint16 ruleCount);
    event OwnerTransferred(address indexed from, address indexed to);

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
        currentVersion = 1;
        nextRuleId = 1;
    }

    /// @notice Add a rule to the current draft version.
    function addRule(
        RuleKind kind,
        bytes32 cptA,
        bytes32 cptB,
        bytes16 mod_,
        uint32 unitsCapPerDay,
        string calldata citation
    ) external onlyOwner returns (uint16 id) {
        id = nextRuleId++;
        Rule memory r = Rule({
            id: id,
            version: currentVersion,
            kind: kind,
            cptA: cptA,
            cptB: cptB,
            mod: mod_,
            unitsCapPerDay: unitsCapPerDay,
            citation: citation
        });
        rules[id] = r;
        ruleIdsByVersion[currentVersion].push(id);
        emit RuleAdded(id, currentVersion, kind, cptA, cptB, mod_);
    }

    /// @notice Bump the version counter — used when the next CMS quarter ships.
    function publishVersion() external onlyOwner {
        uint16 v = currentVersion;
        emit VersionPublished(v, uint16(ruleIdsByVersion[v].length));
        currentVersion = v + 1;
    }

    /// @notice How many rules in a given version?
    function ruleCount(uint16 version) external view returns (uint256) {
        return ruleIdsByVersion[version].length;
    }

    /// @notice Get a rule by id (returns zeroed struct if not present).
    function getRule(uint16 id) external view returns (Rule memory) {
        return rules[id];
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "zero addr");
        emit OwnerTransferred(owner, newOwner);
        owner = newOwner;
    }
}