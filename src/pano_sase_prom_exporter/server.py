"""HTTP metrics server and life-cycle management for the Prometheus exporter."""

import logging
import signal
import time

from prometheus_client import CollectorRegistry, start_http_server

from pano_sase_prom_exporter.client import PrismaSaseClient
from pano_sase_prom_exporter.collector import PrismaSaseCollector
from pano_sase_prom_exporter.config import Settings

logger = logging.getLogger(__name__)


class ExporterServer:
    """HTTP Prometheus Exporter Server."""

    def __init__(self, settings: Settings, client: PrismaSaseClient | None = None) -> None:
        self.settings = settings
        self.client = client or PrismaSaseClient(settings)
        self.registry = CollectorRegistry(auto_describe=True)
        self.collector = PrismaSaseCollector(self.client)
        self.registry.register(self.collector)
        self._running = False

    def start(self) -> None:
        """Start the Prometheus metrics HTTP server."""
        logger.info(
            "Starting Prisma SASE Prometheus Exporter on http://%s:%d/metrics",
            self.settings.exporter_host,
            self.settings.exporter_port,
        )

        start_http_server(
            port=self.settings.exporter_port,
            addr=self.settings.exporter_host,
            registry=self.registry,
        )

        self._running = True
        logger.info("Exporter server is running. Press Ctrl+C to terminate.")

        def _handle_signal(sig: int, frame: object) -> None:
            logger.info("Received termination signal (%s), shutting down...", sig)
            self._running = False

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        while self._running:
            time.sleep(1)

        logger.info("Exporter server stopped.")
