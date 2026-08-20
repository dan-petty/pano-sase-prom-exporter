"""Tests for PrismaSaseClient."""

from unittest.mock import MagicMock

from pano_sase_prom_exporter.client import PrismaSaseClient
from pano_sase_prom_exporter.config import Settings


def test_client_authenticate_service_account() -> None:
    settings = Settings(
        prisma_sase_client_id="cid",
        prisma_sase_client_secret="sec",
        prisma_sase_tsg_id="tsg",
    )
    mock_sdk = MagicMock()
    mock_sdk.interactive.login_secret.return_value = True
    client = PrismaSaseClient(settings, sdk=mock_sdk)

    assert client.authenticate() is True
    assert client.authenticated is True
    mock_sdk.interactive.login_secret.assert_called_once_with(
        client_id="cid", client_secret="sec", tsg_id="tsg"
    )


def test_client_authenticate_token() -> None:
    settings = Settings(
        prisma_sase_auth_token="jwt-sample",
    )
    mock_sdk = MagicMock()
    client = PrismaSaseClient(settings, sdk=mock_sdk)

    assert client.authenticate() is True
    assert client.authenticated is True
    mock_sdk.parse_auth_token.assert_called_once_with("jwt-sample")


def test_client_get_sites_and_elements() -> None:
    settings = Settings(prisma_sase_auth_token="jwt-sample")
    mock_sdk = MagicMock()
    mock_sdk.get.sites.return_value = {"items": [{"id": "s1", "name": "Branch-1"}]}
    mock_sdk.get.elements.return_value = {"items": [{"id": "e1", "name": "ION-1", "site_id": "s1"}]}
    mock_sdk.get.status_e.return_value = {"items": [{"id": "e1", "operational_state": "online"}]}

    client = PrismaSaseClient(settings, sdk=mock_sdk)
    sites = client.get_sites()
    elements = client.get_elements()
    statuses = client.get_element_status()

    assert len(sites) == 1
    assert sites[0]["name"] == "Branch-1"
    assert len(elements) == 1
    assert elements[0]["name"] == "ION-1"
    assert len(statuses) == 1
    assert statuses[0]["operational_state"] == "online"
