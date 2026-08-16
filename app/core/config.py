from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "quant-market-intelligence"
    app_env: str = "development"
    debug: bool = True

    # Database
    postgres_user: str = "qmi_user"
    postgres_password: str = "changeme_in_production"
    postgres_db: str = "qmi_db"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str | None = None

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    @property
    def resolved_database_url(self) -> str:
        """Return the database URL, using constructed URL if not explicitly set."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
