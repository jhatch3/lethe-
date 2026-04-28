from pathlib import Path
from typing import List

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_REPO_ROOT_ENV = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    # Look in repo root first (where .env.example lives), then in cwd as override.
    model_config = SettingsConfigDict(
        env_prefix="LETHE_",
        env_file=(str(_REPO_ROOT_ENV), ".env"),
        extra="ignore",
    )

    cors_origins: List[str] = ["http://localhost:3000"]

    # Real LLM streaming + 2 chain writes can push the pipeline past 90s.
    # 240s default = comfortable headroom; the post-completion result_ttl
    # below extends the lifetime once status flips to done.
    job_ttl_seconds: int = 240
    job_ttl_buffer_seconds: int = 30
    # how long the result is retrievable after the pipeline finishes
    result_ttl_seconds: int = 300
    max_upload_bytes: int = 10 * 1024 * 1024

    stage_delays_ms: dict = {
        "parse": 1100,
        "redact": 800,
        "broadcast": 600,
        "reason": 1400,
        "exchange": 0,
        "reflect": 0,
        "consensus": 700,
        "anchor": 900,
        "patterns": 0,
        "draft": 0,
    }

    stats_window: int = 50

    samples_dir: Path = Path(__file__).parent / "samples"

    # === 0G Chain anchor ===
    zg_rpc_url: str = Field(
        default="https://evmrpc-testnet.0g.ai",
        validation_alias=AliasChoices("LETHE_ZG_RPC_URL", "ZG_RPC_URL"),
    )
    zg_chain_id: int = Field(
        default=16602,
        validation_alias=AliasChoices("LETHE_ZG_CHAIN_ID", "ZG_CHAIN_ID"),
    )
    zg_private_key: str = Field(
        default="",
        validation_alias=AliasChoices("LETHE_ZG_PRIVATE_KEY", "ZG_PRIVATE_KEY"),
    )
    bill_registry_address: str = Field(
        default="",
        validation_alias=AliasChoices("LETHE_BILL_REGISTRY_ADDRESS", "BILL_REGISTRY_ADDRESS"),
    )
    # Consolidated registry (Galileo). Replaces the 5-contract surface
    # (BillRegistry + PatternRegistry + StorageIndex + ProviderReputation +
    # NCCIRulebook) with one address. When unset, code paths fall back to the
    # legacy bill_registry_address so the cutover can be staged.
    lethe_registry_address: str = Field(
        default="",
        validation_alias=AliasChoices("LETHE_REGISTRY_ADDRESS"),
    )
    pattern_registry_address: str = Field(
        default="",
        validation_alias=AliasChoices("LETHE_PATTERN_REGISTRY_ADDRESS", "PATTERN_REGISTRY_ADDRESS"),
    )
    # 0G Storage sidecar URL — the Node service in src/coordinator/scripts/
    # that wraps `@0glabs/0g-ts-sdk` (Python SDK is broken upstream). When set,
    # every audit's anonymized pattern record is also uploaded to 0G Storage,
    # giving us a third 0G pillar (Chain + Storage + optional Compute).
    # Stays a stub when blank, so the pipeline runs unchanged without it.
    zg_storage_sidecar_url: str = Field(
        default="",
        validation_alias=AliasChoices("LETHE_0G_STORAGE_SIDECAR_URL", "ZG_STORAGE_SIDECAR_URL"),
    )
    # On-chain pointer: the StorageIndex contract on Galileo records every
    # (billHash → storageRoot) pairing emitted by the storage sidecar. Lets
    # the coordinator query recent roots via eth_getLogs and pull blobs back
    # for richer agent priors. Stays a stub if the contract isn't deployed.
    storage_index_address: str = Field(
        default="",
        validation_alias=AliasChoices("LETHE_STORAGE_INDEX_ADDRESS", "STORAGE_INDEX_ADDRESS"),
    )
    # Provider reputation contract — public dispute rate per NPI hash.
    # Records `recordAudit(npiHash, billHash, verdict, agreeCount, totalAgents,
    # flaggedCents)` after every audit when an NPI is extractable from the bill.
    # Stays a stub when blank.
    provider_reputation_address: str = Field(
        default="",
        validation_alias=AliasChoices("LETHE_PROVIDER_REPUTATION_ADDRESS", "PROVIDER_REPUTATION_ADDRESS"),
    )
    # NCCI Rulebook contract — versioned medical-coding rules on-chain so
    # agents can query the active ruleset at audit time. Owner-gated for
    # writes. Stays a stub when blank.
    ncci_rulebook_address: str = Field(
        default="",
        validation_alias=AliasChoices("LETHE_NCCI_RULEBOOK_ADDRESS", "NCCI_RULEBOOK_ADDRESS"),
    )
    # Payer integration adapter — "stub" (default), "stedi", "availity", "ch",
    # or "fhir". Today only stub is wired; the others are scaffolded but
    # require sandbox credentials + per-payer mapping work.
    payer_adapter: str = Field(
        default="stub",
        validation_alias=AliasChoices("LETHE_PAYER_ADAPTER", "PAYER_ADAPTER"),
    )

    # === KeeperHub mirror anchor (Sepolia) ===
    keeperhub_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("LETHE_KEEPERHUB_API_KEY", "KEEPERHUB_API_KEY"),
    )
    keeperhub_base_url: str = Field(
        default="https://app.keeperhub.com",
        validation_alias=AliasChoices("LETHE_KEEPERHUB_BASE_URL", "KEEPERHUB_BASE_URL"),
    )
    # When true, the mirror anchor goes through KeeperHub's MCP server instead
    # of the Direct Execution REST API. Strict reading of the prize description
    # ("MCP server or CLI") wants MCP. Falls back to REST if MCP fails.
    keeperhub_use_mcp: bool = Field(
        default=False,
        validation_alias=AliasChoices("LETHE_KEEPERHUB_USE_MCP", "KEEPERHUB_USE_MCP"),
    )
    # Hosted MCP HTTP endpoint. Override only if running a self-hosted MCP server.
    keeperhub_mcp_url: str = Field(
        default="https://app.keeperhub.com/mcp",
        validation_alias=AliasChoices("LETHE_KEEPERHUB_MCP_URL", "KEEPERHUB_MCP_URL"),
    )
    bill_registry_address_sepolia: str = Field(
        default="",
        validation_alias=AliasChoices(
            "LETHE_BILL_REGISTRY_ADDRESS_SEPOLIA", "BILL_REGISTRY_ADDRESS_SEPOLIA",
        ),
    )
    # Consolidated registry on Sepolia. Same source as lethe_registry_address
    # (Galileo) but a separate deployment. KH workflows on Sepolia target this
    # contract's anchor / recordDispute / recordAppealSent methods.
    lethe_registry_address_sepolia: str = Field(
        default="",
        validation_alias=AliasChoices("LETHE_REGISTRY_ADDRESS_SEPOLIA"),
    )
    # Public Sepolia RPC. Used to look up the original Anchored tx hash when
    # KeeperHub reports "already anchored" (KH itself doesn't surface the
    # original tx for duplicates). Defaults to publicnode — no key required.
    sepolia_rpc_url: str = Field(
        default="https://ethereum-sepolia-rpc.publicnode.com",
        validation_alias=AliasChoices("LETHE_SEPOLIA_RPC_URL", "SEPOLIA_RPC_URL"),
    )
    # Optional second KeeperHub workflow: when consensus = "dispute", KH fires
    # a Direct Execution against this contract to record the dispute filing.
    # When blank, the dispute filer is a stub (still surfaces in the receipt
    # so judges see the code path). Wire to any Sepolia contract exposing
    # `recordDispute(bytes32 billHash, uint8 reason, string note)` — or change
    # `dispute_function_name` to match your contract.
    dispute_registry_address_sepolia: str = Field(
        default="",
        validation_alias=AliasChoices(
            "LETHE_DISPUTE_REGISTRY_ADDRESS_SEPOLIA", "DISPUTE_REGISTRY_ADDRESS_SEPOLIA",
        ),
    )
    dispute_function_name: str = Field(
        default="recordDispute",
        validation_alias=AliasChoices(
            "LETHE_DISPUTE_FUNCTION_NAME", "DISPUTE_FUNCTION_NAME",
        ),
    )
    # Third KH workflow: when the user clicks "Send to provider" in the
    # dashboard, KH calls `recordAppealSent(billHash, recipientHash)` on this
    # contract on Sepolia after the email is dispatched. Stub-fallback when
    # the address is blank (still emits the SSE event and tries the email).
    appeal_registry_address_sepolia: str = Field(
        default="",
        validation_alias=AliasChoices(
            "LETHE_APPEAL_REGISTRY_ADDRESS_SEPOLIA", "APPEAL_REGISTRY_ADDRESS_SEPOLIA",
        ),
    )

    # Public-facing URL of the Lethe dashboard. Used by outbound emails to
    # construct the "verify this audit" link that goes to /verify?sha=...
    # Defaults to localhost so dev demos work; override in production.
    public_url: str = Field(
        default="http://localhost:3000",
        validation_alias=AliasChoices("LETHE_PUBLIC_URL", "PUBLIC_URL"),
    )

    # === Email delivery (appeal letter to provider) ===
    # Provider switch — `resend` (recommended), `smtp`, or `stub` (default).
    # Stub mode logs the email body but doesn't send, so demo flow still works
    # without email creds.
    email_provider: str = Field(
        default="stub",
        validation_alias=AliasChoices("LETHE_EMAIL_PROVIDER", "EMAIL_PROVIDER"),
    )
    email_from: str = Field(
        default="Lethe <noreply@lethe.local>",
        validation_alias=AliasChoices("LETHE_EMAIL_FROM", "EMAIL_FROM"),
    )
    email_resend_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("LETHE_RESEND_API_KEY", "RESEND_API_KEY"),
    )
    email_smtp_host: str = Field(
        default="",
        validation_alias=AliasChoices("LETHE_SMTP_HOST", "SMTP_HOST"),
    )
    email_smtp_port: int = Field(
        default=587,
        validation_alias=AliasChoices("LETHE_SMTP_PORT", "SMTP_PORT"),
    )
    email_smtp_user: str = Field(
        default="",
        validation_alias=AliasChoices("LETHE_SMTP_USER", "SMTP_USER"),
    )
    email_smtp_password: str = Field(
        default="",
        validation_alias=AliasChoices("LETHE_SMTP_PASSWORD", "SMTP_PASSWORD"),
    )

    # === 0G Compute Network (decentralized inference) ===
    # When set, agent γ runs on 0G Compute instead of Google Gemini —
    # demonstrating real use of 0G's inference layer (not just 0G Chain).
    # Provision via the TypeScript `0g-compute-cli` — see SETUP.md.
    # Providers expose OpenAI-compatible /v1/proxy endpoints, so we use the
    # stock `openai` Python SDK with a custom base_url + bearer token.
    zg_compute_endpoint: str = Field(
        default="",
        validation_alias=AliasChoices("LETHE_0G_COMPUTE_ENDPOINT", "ZG_COMPUTE_ENDPOINT"),
    )
    zg_compute_token: str = Field(
        default="",
        validation_alias=AliasChoices("LETHE_0G_COMPUTE_TOKEN", "ZG_COMPUTE_TOKEN"),
    )
    zg_compute_model: str = Field(
        default="GLM-5-FP8",
        validation_alias=AliasChoices("LETHE_0G_COMPUTE_MODEL", "ZG_COMPUTE_MODEL"),
    )
    zg_compute_provider_address: str = Field(
        default="",
        validation_alias=AliasChoices("LETHE_0G_COMPUTE_PROVIDER", "ZG_COMPUTE_PROVIDER"),
    )
    # 0G Compute auth headers are signed per-request, not a static bearer.
    # When true, /api/status reports γ as "via sidecar" so judges/users know
    # auth is being signed locally by src/coordinator/scripts/headers_sidecar.ts.
    zg_compute_sidecar: bool = Field(
        default=False,
        validation_alias=AliasChoices("LETHE_0G_COMPUTE_SIDECAR", "ZG_COMPUTE_SIDECAR"),
    )

    # === Gensyn AXL P2P transport ===
    # When enabled, every agent's redacted_payload is broadcast across the
    # AXL mesh via its local sidecar before the LLM call. The coordinator
    # checks topology of each sidecar at startup to confirm 3 distinct peers.
    # Default true so a judge running `uvicorn main:app` without a .env file
    # still gets the AXL transport when sidecars are up. Even with this true,
    # transport_axl.is_enabled() additionally requires non-empty PEER_IDS and
    # all three sidecar URLs reachable — so it fails closed when sidecars are
    # absent rather than silently falling back to asyncio.gather.
    axl_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("LETHE_AXL_ENABLED", "AXL_ENABLED"),
    )
    axl_alpha_url: str = Field(
        default="http://localhost:9002",
        validation_alias=AliasChoices("LETHE_AXL_ALPHA_URL", "AXL_ALPHA_URL"),
    )
    axl_beta_url: str = Field(
        default="http://localhost:9012",
        validation_alias=AliasChoices("LETHE_AXL_BETA_URL", "AXL_BETA_URL"),
    )
    axl_gamma_url: str = Field(
        default="http://localhost:9022",
        validation_alias=AliasChoices("LETHE_AXL_GAMMA_URL", "AXL_GAMMA_URL"),
    )

    # === Agent configuration ===
    # When a key is set, the corresponding agent runs against the real LLM.
    # When empty, the agent falls back to its predictable stub.
    # Accepts both standard names (OPENAI_API_KEY) and prefixed (LETHE_OPENAI_API_KEY).
    openai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("LETHE_OPENAI_API_KEY", "OPENAI_API_KEY"),
    )
    anthropic_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("LETHE_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"),
    )
    google_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("LETHE_GOOGLE_API_KEY", "GOOGLE_API_KEY"),
    )

    # Names of registered audit agents to skip at runtime (csv via env).
    # Example: LETHE_DISABLED_AGENTS=gamma  → only alpha + beta vote.
    disabled_agents: List[str] = []

    @field_validator("cors_origins", "disabled_agents", mode="before")
    @classmethod
    def _split_csv(cls, v):
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v


settings = Settings()
