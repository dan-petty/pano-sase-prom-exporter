"""Prisma SASE / CloudGenix SDK Client wrapper for Prometheus Exporter."""

import logging
from typing import Any

import prisma_sase

from pano_sase_prom_exporter.config import Settings

logger = logging.getLogger(__name__)


class PrismaSaseClient:
    """Client wrapper for interacting with Prisma SASE & SD-WAN APIs."""

    def __init__(self, settings: Settings, sdk: prisma_sase.API | None = None) -> None:
        self.settings = settings
        self.sdk = sdk or prisma_sase.API(
            controller=settings.prisma_sase_controller,
            ssl_verify=True,
        )
        self.authenticated = False

    def authenticate(self) -> bool:
        """Authenticate against Prisma SASE using service account or auth token."""
        logger.info("Authenticating with Prisma SASE API...")

        if self.settings.prisma_sase_client_id and self.settings.prisma_sase_client_secret:
            logger.debug("Using OAuth2 Service Account credentials.")
            status = self.sdk.interactive.login_secret(
                client_id=self.settings.prisma_sase_client_id,
                client_secret=self.settings.prisma_sase_client_secret,
                tsg_id=self.settings.prisma_sase_tsg_id,
            )
            self.authenticated = bool(status)
            if not self.authenticated:
                logger.error("OAuth2 service account authentication failed.")
                return False

        elif self.settings.prisma_sase_auth_token:
            logger.debug("Using static auth token.")
            self.sdk.parse_auth_token(self.settings.prisma_sase_auth_token)
            self.authenticated = True
        else:
            logger.error("No valid credentials supplied for Prisma SASE.")
            self.authenticated = False
            return False

        logger.info(
            "Successfully authenticated with Prisma SASE (Tenant: %s)",
            getattr(self.sdk, "tenant_name", "Unknown"),
        )
        return True

    def _extract_items(self, response: Any) -> list[dict[str, Any]]:
        """Safely extract list of item dicts from SDK response."""
        if response is None:
            return []
        if hasattr(response, "sdk_content") and isinstance(response.sdk_content, dict):
            items = response.sdk_content.get("items", [])
            if isinstance(items, list):
                return items
        elif hasattr(response, "sdk_content") and isinstance(response.sdk_content, list):
            return response.sdk_content
        elif isinstance(response, dict):
            items = response.get("items", [])
            if isinstance(items, list):
                return items
        elif isinstance(response, list):
            return response
        return []

    def get_sites(self) -> list[dict[str, Any]]:
        """Fetch all sites configured in the tenant."""
        try:
            resp = self.sdk.get.sites()
            return self._extract_items(resp)
        except Exception as err:
            logger.error("Failed to retrieve sites: %s", err)
            return []

    def get_elements(self) -> list[dict[str, Any]]:
        """Fetch all ION elements (appliances) in the tenant."""
        try:
            resp = self.sdk.get.elements()
            return self._extract_items(resp)
        except Exception as err:
            logger.error("Failed to retrieve elements: %s", err)
            return []

    def get_element_status(self) -> list[dict[str, Any]]:
        """Fetch real-time status of all ION elements."""
        try:
            resp = self.sdk.get.status_e()
            return self._extract_items(resp)
        except Exception as err:
            logger.error("Failed to retrieve element status: %s", err)
            return []

    def get_interfaces(self, site_id: str, element_id: str) -> list[dict[str, Any]]:
        """Fetch interfaces for a specific element at a site."""
        try:
            resp = self.sdk.get.interfaces(site_id=site_id, element_id=element_id)
            return self._extract_items(resp)
        except Exception as err:
            logger.error(
                "Failed to retrieve interfaces for site %s / element %s: %s",
                site_id,
                element_id,
                err,
            )
            return []

    def get_wan_interfaces(self, site_id: str) -> list[dict[str, Any]]:
        """Fetch WAN interfaces for a specific site."""
        try:
            resp = self.sdk.get.waninterfaces(site_id=site_id)
            return self._extract_items(resp)
        except Exception as err:
            logger.error("Failed to retrieve WAN interfaces for site %s: %s", site_id, err)
            return []

    def get_vpn_links_status(self) -> list[dict[str, Any]]:
        """Fetch operational status of VPN overlay links across the topology."""
        try:
            resp = self.sdk.get.status_vpnlinks()
            return self._extract_items(resp)
        except Exception as err:
            logger.error("Failed to retrieve VPN links status: %s", err)
            return []

    def get_bgp_peers_status(self) -> list[dict[str, Any]]:
        """Fetch status of BGP routing peer sessions."""
        try:
            resp = self.sdk.get.status_bgppeers()
            return self._extract_items(resp)
        except Exception as err:
            logger.error("Failed to retrieve BGP peers status: %s", err)
            return []
