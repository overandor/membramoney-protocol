"""
Membra Money Protocol — Pydantic Settings
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "devnet"
    debug: bool = False

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    jwt_secret: str = "change-me"
    hmac_pepper: str = "change-me"
    claim_salt: str = "change-me"
    admin_api_key: str = "change-me"

    database_url: str = "postgresql+asyncpg://membra:membra@localhost:5432/membramoney"
    redis_url: str = "redis://localhost:6379/0"

    solana_rpc_url: str = "https://api.devnet.solana.com"
    anchor_program_id: str = "EXNLzDxRPN81NtxZKzNBKweG93R9FWUq8gfGoFGzxYYw"
    solana_usdc_mint: str = "DEVNET_USDC_MINT_NOT_CONFIGURED"

    min_micropayment_usd_cents: int = 1
    max_micropayment_usd_cents: int = 10_000
    btc_lightning_enabled: bool = False
    email_provider_enabled: bool = False
    sms_provider_enabled: bool = False
    production_wallet_signature_required: bool = True

    risk_disclosure_version: str = "v1.0.0-devnet"
    log_level: str = "info"
    structlog: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
