"""Configuration settings for the Prisma SASE Prometheus Exporter."""


from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Exporter settings loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Prisma SASE Authentication
    prisma_sase_client_id: str | None = Field(
        default=None,
        description="Service account client ID for OAuth2 authentication.",
    )
    prisma_sase_client_secret: str | None = Field(
        default=None,
        description="Service account client secret for OAuth2 authentication.",
    )
    prisma_sase_tsg_id: str | None = Field(
        default=None,
        description="Tenant Service Group ID (TSG ID).",
    )
    prisma_sase_auth_token: str | None = Field(
        default=None,
        description="Pre-generated static JWT auth token.",
    )
    prisma_sase_controller: str | None = Field(
        default=None,
        description="Custom Prisma SASE API Controller URL.",
    )
    prisma_sase_region: str | None = Field(
        default=None,
        description="Target cloud region (e.g. us-east-1).",
    )

    # Exporter HTTP Server
    exporter_host: str = Field(
        default="0.0.0.0",
        description="Host/address to bind the Prometheus metrics HTTP server.",
    )
    exporter_port: int = Field(
        default=9850,
        description="Port to listen for Prometheus scrape requests.",
    )
    scrape_interval: int = Field(
        default=60,
        description="Scrape interval in seconds for background polling (if cached).",
    )
    metrics_timeout: int = Field(
        default=30,
        description="API request timeout in seconds when querying Prisma SASE.",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).",
    )

    def validate_auth(self) -> None:
        """Validate that minimum required authentication settings are present."""
        has_secret_auth = bool(
            self.prisma_sase_client_id
            and self.prisma_sase_client_secret
            and self.prisma_sase_tsg_id
        )
        has_token_auth = bool(self.prisma_sase_auth_token)
        if not (has_secret_auth or has_token_auth):
            raise ValueError(
                "Missing Prisma SASE credentials. Provide either "
                "(PRISMA_SASE_CLIENT_ID, PRISMA_SASE_CLIENT_SECRET, PRISMA_SASE_TSG_ID) "
                "or PRISMA_SASE_AUTH_TOKEN."
            )
