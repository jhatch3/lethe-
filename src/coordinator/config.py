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
    pattern_registry_address: str = Field(
        default="",
        validation_alias=AliasChoices("LETHE_PATTERN_REGISTRY_ADDRESS", "PATTERN_REGISTRY_ADDRESS"),
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
    bill_registry_address_sepolia: str = Field(
        default="",
        validation_alias=AliasChoices(
            "LETHE_BILL_REGISTRY_ADDRESS_SEPOLIA", "BILL_REGISTRY_ADDRESS_SEPOLIA",
        ),
    )

    # === Gensyn AXL P2P transport ===
    # When enabled, every agent's redacted_payload is broadcast across the
    # AXL mesh via its local sidecar before the LLM call. The coordinator
    # checks topology of each sidecar at startup to confirm 3 distinct peers.
    axl_enabled: bool = Field(
        default=False,
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
