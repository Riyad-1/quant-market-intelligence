"""Tests for application configuration."""

import os

from app.core.config import Settings


def test_settings_default_values() -> None:
    """Test that settings have correct default values when no env vars are set."""
    # Create a fresh settings instance with no environment overrides
    settings = Settings.model_construct()
    
    assert settings.app_name == "quant-market-intelligence"
    assert settings.app_env == "development"
    assert settings.debug is True
    assert settings.postgres_port == 5432


def test_settings_database_url_construction() -> None:
    """Test that database URL is constructed correctly from components."""
    settings = Settings(
        postgres_user="test_user",
        postgres_password="test_pass",
        postgres_db="test_db",
        postgres_host="localhost",
        postgres_port=5433,
    )
    
    expected = "postgresql+asyncpg://test_user:test_pass@localhost:5433/test_db"
    assert settings.resolved_database_url == expected


def test_settings_explicit_database_url_takes_precedence() -> None:
    """Test that explicit DATABASE_URL takes precedence over constructed URL."""
    settings = Settings(
        database_url="postgresql+asyncpg://explicit:pass@host:1234/db",
        postgres_user="test_user",
        postgres_password="test_pass",
        postgres_db="test_db",
    )
    
    assert settings.resolved_database_url == "postgresql+asyncpg://explicit:pass@host:1234/db"
