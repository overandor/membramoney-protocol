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

    jwt_secret: str = "change-me"
    hmac_pepper: str = "change-me"
    claim_salt: str = "change-me"

    database_url: str = "postgresql+asyncpg://membra:membra@localhost:5432/membramoney"
    redis_url: str = "redis://localhost:6379/0"

    solana_rpc_url: str = "https://api.devnet.solana.com"
    anchor_program_id: str = "EXNLzDxRPN81NtxZKzNBKweG93R9FWUq8gfGoFGzxYYw"
    anchor_program_id_mainnet: str = ""

    # Fee sponsoring (gasless transfers)
    fee_sponsoring_enabled: bool = False
    fee_sponsor_wallet: str = ""

    risk_disclosure_version: str = "v1.0.0-devnet"
    log_level: str = "info"
    structlog: bool = False


settings = Settings()
