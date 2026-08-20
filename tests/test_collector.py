"""Tests for Prometheus metrics collector."""

from unittest.mock import MagicMock

from pano_sase_prom_exporter.client import PrismaSaseClient
from pano_sase_prom_exporter.collector import PrismaSaseCollector
from pano_sase_prom_exporter.config import Settings


def test_collector_yields_expected_metrics() -> None:
    settings = Settings(prisma_sase_auth_token="jwt-sample")
    mock_sdk = MagicMock()
    mock_sdk.get.sites.return_value = {
        "items": [
            {
                "id": "site-101",
                "name": "Site-NYC",
                "admin_state": "active",
                "service_binding_state": "bound",
            }
        ]
    }
    mock_sdk.get.elements.return_value = {
        "items": [
            {
                "id": "elem-201",
                "name": "ION-NYC-01",
                "model_name": "ION 3000",
                "serial_number": "SN12345",
                "site_id": "site-101",
                "software_version": "6.1.1",
                "role": "spoke",
            }
        ]
    }
    mock_sdk.get.status_e.return_value = {
        "items": [
            {
                "id": "elem-201",
                "connected": True,
                "operational_state": "online",
                "system_up_time": 86400,
                "cpu_utilization": 24.5,
                "memory_utilization": 42.0,
            }
        ]
    }
    mock_sdk.get.status_vpnlinks.return_value = {
        "items": [
            {
                "id": "vpn-301",
                "site_id": "site-101",
                "peer_site_id": "site-102",
                "state": "up",
            }
        ]
    }
    mock_sdk.get.status_bgppeers.return_value = {
        "items": [
            {
                "site_id": "site-101",
                "peer_ip": "10.0.0.1",
                "peer_asn": "65001",
                "state": "established",
            }
        ]
    }

    client = PrismaSaseClient(settings, sdk=mock_sdk)
    collector = PrismaSaseCollector(client)

    metrics = list(collector.collect())
    metric_names = {m.name for m in metrics}

    assert "prisma_sase_site_info" in metric_names
    assert "prisma_sase_site_admin_up" in metric_names
    assert "prisma_sase_element_info" in metric_names
    assert "prisma_sase_element_connected" in metric_names
    assert "prisma_sase_element_operational_state" in metric_names
    assert "prisma_sase_element_uptime_seconds" in metric_names
    assert "prisma_sase_element_cpu_utilization_percent" in metric_names
    assert "prisma_sase_element_memory_utilization_percent" in metric_names
    assert "prisma_sase_vpn_link_status" in metric_names
    assert "prisma_sase_bgp_peer_state" in metric_names
    assert "prisma_sase_scrape_success" in metric_names
    assert "prisma_sase_scrape_duration_seconds" in metric_names
