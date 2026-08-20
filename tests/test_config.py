"""Tests for exporter configuration validation."""

import pytest

from pano_sase_prom_exporter.config import Settings


def test_settings_validation_missing_auth() -> None:
    settings = Settings(
        prisma_sase_client_id=None,
        prisma_sase_client_secret=None,
        prisma_sase_tsg_id=None,
        prisma_sase_auth_token=None,
    )
    with pytest.raises(ValueError, match="Missing Prisma SASE credentials"):
        settings.validate_auth()


def test_settings_validation_service_account() -> None:
    settings = Settings(
        prisma_sase_client_id="client-123",
        prisma_sase_client_secret="secret-456",
        prisma_sase_tsg_id="tsg-789",
    )
    # Should not raise
    settings.validate_auth()
    assert settings.exporter_port == 9850


def test_settings_validation_auth_token() -> None:
    settings = Settings(
        prisma_sase_auth_token="jwt-token-xyz",
    )
    # Should not raise
    settings.validate_auth()
