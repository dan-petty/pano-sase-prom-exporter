"""Prometheus Custom Collector for Prisma SASE SD-WAN ION Devices."""

import logging
import time
from collections.abc import Iterator

from prometheus_client.core import GaugeMetricFamily, Metric
from prometheus_client.registry import Collector

from pano_sase_prom_exporter.client import PrismaSaseClient

logger = logging.getLogger(__name__)


class PrismaSaseCollector(Collector):
    """Custom Prometheus collector gathering metrics from Prisma SASE APIs."""

    def __init__(self, client: PrismaSaseClient) -> None:
        self.client = client

    def collect(self) -> Iterator[Metric]:
        """Collect all metrics from Prisma SASE APIs and yield Prometheus Metric instances."""
        start_time = time.time()
        scrape_success = 1.0

        try:
            if not self.client.authenticated:
                if not self.client.authenticate():
                    logger.error("Authentication failed during scrape collection.")
                    scrape_success = 0.0
                    duration = time.time() - start_time
                    yield GaugeMetricFamily(
                        "prisma_sase_scrape_success",
                        "Indicates whether the Prisma SASE scrape succeeded (1=success, 0=failure)",
                        value=scrape_success,
                    )
                    yield GaugeMetricFamily(
                        "prisma_sase_scrape_duration_seconds",
                        "Duration of the Prisma SASE metrics scrape in seconds",
                        value=duration,
                    )
                    return

            # Fetch inventory and topological state
            sites = self.client.get_sites()
            site_lookup: dict[str, str] = {
                s.get("id", ""): s.get("name", s.get("id", "Unknown")) for s in sites if s.get("id")
            }

            elements = self.client.get_elements()
            element_statuses = self.client.get_element_status()
            status_by_element_id: dict[str, dict[str, object]] = {
                str(st.get("id") or st.get("element_id") or ""): st for st in element_statuses
            }

            # 1. Site Metrics
            yield from self._collect_site_metrics(sites)

            # 2. Element (ION Device) Metrics
            yield from self._collect_element_metrics(elements, site_lookup, status_by_element_id)

            # 3. VPN Link Status Metrics
            yield from self._collect_vpn_metrics(site_lookup)

            # 4. BGP Peer Metrics
            yield from self._collect_bgp_metrics(site_lookup)

        except Exception as exc:
            logger.exception("Unexpected error during metrics scrape: %s", exc)
            scrape_success = 0.0

        duration = time.time() - start_time
        yield GaugeMetricFamily(
            "prisma_sase_scrape_success",
            "Indicates whether the Prisma SASE scrape succeeded (1=success, 0=failure)",
            value=scrape_success,
        )
        yield GaugeMetricFamily(
            "prisma_sase_scrape_duration_seconds",
            "Duration of the Prisma SASE metrics scrape in seconds",
            value=duration,
        )

    def _collect_site_metrics(self, sites: list[dict[str, object]]) -> Iterator[Metric]:
        """Generate site inventory and status metrics."""
        site_info = GaugeMetricFamily(
            "prisma_sase_site_info",
            "Prisma SD-WAN site metadata and state",
            labels=["site_id", "site_name", "admin_state", "service_binding_state"],
        )
        site_up = GaugeMetricFamily(
            "prisma_sase_site_admin_up",
            "Prisma SD-WAN site admin operational state (1=active/online, 0=inactive)",
            labels=["site_id", "site_name"],
        )

        for site in sites:
            site_id = str(site.get("id", ""))
            site_name = str(site.get("name", site_id))
            admin_state = str(site.get("admin_state", "unknown")).lower()
            binding_state = str(site.get("service_binding_state", "unknown"))

            site_info.add_metric(
                [site_id, site_name, admin_state, binding_state],
                1.0,
            )
            is_up = 1.0 if admin_state in ("active", "bound", "online", "up") else 0.0
            site_up.add_metric([site_id, site_name], is_up)

        yield site_info
        yield site_up

    def _collect_element_metrics(
        self,
        elements: list[dict[str, object]],
        site_lookup: dict[str, str],
        status_by_element_id: dict[str, dict[str, object]],
    ) -> Iterator[Metric]:
        """Generate ION element appliance metrics."""
        elem_info = GaugeMetricFamily(
            "prisma_sase_element_info",
            "Prisma SD-WAN ION element metadata",
            labels=[
                "element_id",
                "element_name",
                "model_name",
                "serial_number",
                "site_id",
                "site_name",
                "software_version",
                "role",
            ],
        )
        elem_connected = GaugeMetricFamily(
            "prisma_sase_element_connected",
            "Connection status of ION element to Cloud Controller (1=connected, 0=disconnected)",
            labels=["element_id", "element_name", "site_name"],
        )
        elem_oper_state = GaugeMetricFamily(
            "prisma_sase_element_operational_state",
            "Operational state of ION element (1=online, 0=offline/degraded)",
            labels=["element_id", "element_name", "operational_state", "site_name"],
        )
        elem_uptime = GaugeMetricFamily(
            "prisma_sase_element_uptime_seconds",
            "System uptime of the ION appliance in seconds",
            labels=["element_id", "element_name", "site_name"],
        )
        elem_cpu = GaugeMetricFamily(
            "prisma_sase_element_cpu_utilization_percent",
            "Current CPU utilization percentage of the ION appliance",
            labels=["element_id", "element_name", "site_name"],
        )
        elem_memory = GaugeMetricFamily(
            "prisma_sase_element_memory_utilization_percent",
            "Current memory utilization percentage of the ION appliance",
            labels=["element_id", "element_name", "site_name"],
        )

        for elem in elements:
            elem_id = str(elem.get("id", ""))
            elem_name = str(elem.get("name", elem_id))
            model_name = str(elem.get("model_name", "ION-Unknown"))
            serial = str(elem.get("serial_number", "Unknown"))
            site_id = str(elem.get("site_id", ""))
            site_name = site_lookup.get(site_id, "Unassigned")
            sw_ver = str(elem.get("software_version", "Unknown"))
            role = str(elem.get("role", "spoke"))

            elem_info.add_metric(
                [elem_id, elem_name, model_name, serial, site_id, site_name, sw_ver, role],
                1.0,
            )

            status = status_by_element_id.get(elem_id, {})
            connected = status.get("connected", elem.get("connected", False))
            is_conn = 1.0 if connected in (True, "true", "True", 1) else 0.0
            elem_connected.add_metric([elem_id, elem_name, site_name], is_conn)

            oper_state = str(status.get("operational_state", elem.get("state", "unknown"))).lower()
            is_online = 1.0 if oper_state in ("online", "active", "bound", "up") else 0.0
            elem_oper_state.add_metric([elem_id, elem_name, oper_state, site_name], is_online)

            uptime_val = status.get("system_up_time") or status.get("uptime")
            if uptime_val is not None:
                try:
                    elem_uptime.add_metric([elem_id, elem_name, site_name], float(str(uptime_val)))
                except (ValueError, TypeError):
                    pass

            cpu_val = status.get("cpu_utilization") or status.get("cpu_percent")
            if cpu_val is not None:
                try:
                    elem_cpu.add_metric([elem_id, elem_name, site_name], float(str(cpu_val)))
                except (ValueError, TypeError):
                    pass

            mem_val = status.get("memory_utilization") or status.get("memory_percent")
            if mem_val is not None:
                try:
                    elem_memory.add_metric([elem_id, elem_name, site_name], float(str(mem_val)))
                except (ValueError, TypeError):
                    pass

        yield elem_info
        yield elem_connected
        yield elem_oper_state
        yield elem_uptime
        yield elem_cpu
        yield elem_memory

    def _collect_vpn_metrics(self, site_lookup: dict[str, str]) -> Iterator[Metric]:
        """Generate VPN link overlay status metrics."""
        vpn_status = GaugeMetricFamily(
            "prisma_sase_vpn_link_status",
            "Status of VPN Overlay Link (1=up, 0=down/degraded)",
            labels=["link_id", "source_site", "target_site", "state"],
        )

        links = self.client.get_vpn_links_status()
        for link in links:
            link_id = str(link.get("id", ""))
            src_id = str(link.get("site_id") or link.get("source_site_id") or "")
            dst_id = str(link.get("peer_site_id") or link.get("target_site_id") or "")
            src_name = site_lookup.get(src_id, src_id or "Unknown")
            dst_name = site_lookup.get(dst_id, dst_id or "Unknown")
            state = str(link.get("state", link.get("status", "unknown"))).lower()

            is_up = 1.0 if state in ("up", "active", "established", "online") else 0.0
            vpn_status.add_metric([link_id, src_name, dst_name, state], is_up)

        yield vpn_status

    def _collect_bgp_metrics(self, site_lookup: dict[str, str]) -> Iterator[Metric]:
        """Generate BGP peer session status metrics."""
        bgp_state = GaugeMetricFamily(
            "prisma_sase_bgp_peer_state",
            "BGP Peer Session State (1=Established, 0=Active/Idle/Connect/Open)",
            labels=["peer_ip", "peer_asn", "site_name", "state"],
        )

        peers = self.client.get_bgp_peers_status()
        for peer in peers:
            peer_ip = str(peer.get("peer_ip") or peer.get("ip_address") or "unknown")
            peer_asn = str(peer.get("peer_asn") or peer.get("asn") or "unknown")
            site_id = str(peer.get("site_id", ""))
            site_name = site_lookup.get(site_id, site_id or "Unknown")
            state = str(peer.get("state") or peer.get("session_state") or "unknown").lower()

            is_established = 1.0 if state == "established" else 0.0
            bgp_state.add_metric([peer_ip, peer_asn, site_name, state], is_established)

        yield bgp_state
