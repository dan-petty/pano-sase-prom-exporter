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

            # 1. Fetch site topology
            sites = self.client.get_sites()
            site_lookup: dict[str, str] = {
                str(s.get("id", "")): str(s.get("name", s.get("id", "Unknown")))
                for s in sites
                if s.get("id")
            }

            # 2. Fetch element inventory
            elements = self.client.get_elements()

            # 3. Yield site metrics
            yield from self._collect_site_metrics(sites)

            # 4. Yield element (ION device) metrics
            yield from self._collect_element_metrics(elements, site_lookup)

            # 5. Yield WAN interface metrics per site
            yield from self._collect_wan_metrics(sites)

            # 6. Yield BGP peer routing metrics
            yield from self._collect_bgp_metrics(elements, site_lookup)

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
            "Operational state of ION element (1=online/active/bound, 0=offline/degraded)",
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

            connected = elem.get("connected", False)
            is_conn = 1.0 if connected in (True, "true", "True", 1) else 0.0
            elem_connected.add_metric([elem_id, elem_name, site_name], is_conn)

            oper_state = str(elem.get("state", elem.get("operational_state", "unknown"))).lower()
            is_online = 1.0 if oper_state in ("online", "active", "bound", "up") else 0.0
            elem_oper_state.add_metric([elem_id, elem_name, oper_state, site_name], is_online)

            uptime_val = elem.get("system_up_time") or elem.get("uptime")
            if uptime_val is not None:
                try:
                    elem_uptime.add_metric([elem_id, elem_name, site_name], float(str(uptime_val)))
                except (ValueError, TypeError):
                    pass

            cpu_val = elem.get("cpu_utilization") or elem.get("cpu_percent")
            if cpu_val is not None:
                try:
                    elem_cpu.add_metric([elem_id, elem_name, site_name], float(str(cpu_val)))
                except (ValueError, TypeError):
                    pass

            mem_val = elem.get("memory_utilization") or elem.get("memory_percent")
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

    def _collect_wan_metrics(self, sites: list[dict[str, object]]) -> Iterator[Metric]:
        """Generate WAN interface operational status and bandwidth metrics."""
        wan_status = GaugeMetricFamily(
            "prisma_sase_wan_interface_status",
            "Operational state of WAN interface (1=up/operational, 0=down)",
            labels=["site_id", "site_name", "waninterface_id", "type"],
        )
        wan_bw_down = GaugeMetricFamily(
            "prisma_sase_wan_interface_bandwidth_down_mbps",
            "Configured downlink bandwidth in Mbps for WAN interface",
            labels=["site_id", "site_name", "waninterface_id", "type"],
        )
        wan_bw_up = GaugeMetricFamily(
            "prisma_sase_wan_interface_bandwidth_up_mbps",
            "Configured uplink bandwidth in Mbps for WAN interface",
            labels=["site_id", "site_name", "waninterface_id", "type"],
        )

        for site in sites:
            site_id = str(site.get("id", ""))
            site_name = str(site.get("name", site_id))
            if not site_id:
                continue

            wan_interfaces = self.client.get_wan_interfaces(site_id)
            for wan in wan_interfaces:
                wan_id = str(wan.get("id", ""))
                wan_type = str(wan.get("type", "publicwan"))
                if not wan_id:
                    continue

                status = self.client.get_wan_interface_status(site_id, wan_id)
                oper_state = status.get("operational_state", False)
                is_up = 1.0 if oper_state in (True, "true", "True", 1) else 0.0
                wan_status.add_metric([site_id, site_name, wan_id, wan_type], is_up)

                bw_down = wan.get("link_bw_down")
                if bw_down is not None:
                    try:
                        wan_bw_down.add_metric(
                            [site_id, site_name, wan_id, wan_type], float(str(bw_down))
                        )
                    except (ValueError, TypeError):
                        pass

                bw_up = wan.get("link_bw_up")
                if bw_up is not None:
                    try:
                        wan_bw_up.add_metric(
                            [site_id, site_name, wan_id, wan_type], float(str(bw_up))
                        )
                    except (ValueError, TypeError):
                        pass

        yield wan_status
        yield wan_bw_down
        yield wan_bw_up

    def _collect_bgp_metrics(
        self,
        elements: list[dict[str, object]],
        site_lookup: dict[str, str],
    ) -> Iterator[Metric]:
        """Generate BGP peer session status metrics."""
        bgp_state = GaugeMetricFamily(
            "prisma_sase_bgp_peer_state",
            "BGP Peer Session State (1=Established, 0=Active/Idle/Connect/Open)",
            labels=["site_name", "element_name", "peer_name", "peer_ip", "peer_asn", "state"],
        )

        for elem in elements:
            elem_id = str(elem.get("id", ""))
            elem_name = str(elem.get("name", elem_id))
            site_id = str(elem.get("site_id", ""))
            site_name = site_lookup.get(site_id, "Unassigned")
            if not site_id or not elem_id:
                continue

            peers = self.client.get_bgp_peers(site_id, elem_id)
            if not peers:
                continue

            peer_statuses = self.client.get_bgp_peers_status(site_id, elem_id)
            status_map = {str(st.get("id", "")): st for st in peer_statuses}

            for peer in peers:
                peer_id = str(peer.get("id", ""))
                peer_name = str(peer.get("name", peer_id))
                peer_ip = str(peer.get("peer_ip", "unknown"))
                peer_asn = str(peer.get("remote_as_num", "unknown"))

                st = status_map.get(peer_id, {})
                state = str(st.get("state", "unknown")).lower()

                is_established = 1.0 if state == "established" else 0.0
                bgp_state.add_metric(
                    [site_name, elem_name, peer_name, peer_ip, peer_asn, state],
                    is_established,
                )

        yield bgp_state
