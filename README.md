# Prisma SASE & SD-WAN Prometheus Exporter (`pano-sase-prom-exporter`)

A high-reliability Prometheus metrics exporter for **Palo Alto Networks Prisma SASE** and **Prisma SD-WAN ION appliances**, built on top of the official `prisma-sase 6.8.1b1` Python SDK.

---

## Features

- **ION Element Metrics**: Tracks appliance online/offline connectivity status, operational states, CPU utilization, memory utilization, and system uptime.
- **Site Inventory & Status**: Exposes Prisma SD-WAN site health, admin state (`active`, `bound`, `up`), and service bindings.
- **VPN Overlay & Paths**: Monitors site-to-site VPN link statuses, latency indicators, and mesh connectivity.
- **BGP Peer Monitoring**: Tracks routing session states (`established`, `active`, `idle`) across WAN edge devices.
- **Flexible Authentication**: Supports Prisma SASE Service Accounts (OAuth2 `client_id`, `client_secret`, `tsg_id`) as well as static JWT tokens.
- **Standard Prometheus HTTP Server**: Exposes metrics on standard `/metrics` endpoint (default port: `9850`).
- **CLI & Test Tooling**: Provides `pano-sase-prom-exporter test` for dry-run validation and `pano-sase-prom-exporter serve` for daemon deployment.

---

## Installation & Setup

This repository uses [`uv`](https://docs.astral.sh/uv/) for Python package and dependency management.

### 1. Clone & Sync Dependencies

```bash
cd /workspaces/devops-cli/repos/dan-petty/pano-sase-prom-exporter
uv sync
```

### 2. Configure Credentials

Copy the `.env.example` template:

```bash
cp .env.example .env
```

Set your credentials in `.env` or as environment variables:

```ini
# Option 1: Service Account (Recommended)
PRISMA_SASE_CLIENT_ID="your-service-account-client-id"
PRISMA_SASE_CLIENT_SECRET="your-service-account-client-secret"
PRISMA_SASE_TSG_ID="your-tsg-id"

# Server options
EXPORTER_HOST=0.0.0.0
EXPORTER_PORT=9850
LOG_LEVEL=INFO
```

---

## Usage

### Run Exporter Daemon

```bash
uv run pano-sase-prom-exporter serve --host 0.0.0.0 --port 9850
```

### Dry-Run Test Scrape

Validate API connectivity and view a sample of collected metrics:

```bash
uv run pano-sase-prom-exporter test
```

### Run with Docker

Build and run the containerized exporter:

```bash
# Build the Docker image
docker build -t pano-sase-prom-exporter:latest .

# Run container with environment file
docker run -d \
  --name pano-sase-prom-exporter \
  --restart unless-stopped \
  -p 9850:9850 \
  --env-file .env \
  pano-sase-prom-exporter:latest
```

### Full Monitoring Stack with Docker Compose

Launch the complete observability stack (**Exporter + Prometheus + Grafana** with auto-provisioned dashboards and datasources):

```bash
# Start all services in the background
docker compose up -d

# Check service logs
docker compose logs -f

# Access web interfaces:
# - Exporter metrics: http://localhost:9850/metrics
# - Prometheus UI:    http://localhost:9090
# - Grafana UI:       http://localhost:3000 (admin / admin)
```

---

## Exported Metrics Catalog

| Metric Name | Type | Description | Labels |
| :--- | :--- | :--- | :--- |
| `prisma_sase_element_info` | Gauge | ION device metadata & software info | `element_id`, `element_name`, `model_name`, `serial_number`, `site_id`, `site_name`, `software_version`, `role` |
| `prisma_sase_element_connected` | Gauge | Cloud controller connection state (1=connected, 0=disconnected) | `element_id`, `element_name`, `site_name` |
| `prisma_sase_element_operational_state` | Gauge | Appliance operational state (1=online, 0=offline) | `element_id`, `element_name`, `operational_state`, `site_name` |
| `prisma_sase_element_uptime_seconds` | Gauge | Appliance system uptime in seconds | `element_id`, `element_name`, `site_name` |
| `prisma_sase_element_cpu_utilization_percent` | Gauge | Current CPU utilization percentage | `element_id`, `element_name`, `site_name` |
| `prisma_sase_element_memory_utilization_percent` | Gauge | Current memory utilization percentage | `element_id`, `element_name`, `site_name` |
| `prisma_sase_site_info` | Gauge | Site metadata and configuration states | `site_id`, `site_name`, `admin_state`, `service_binding_state` |
| `prisma_sase_site_admin_up` | Gauge | Site admin status (1=active, 0=inactive) | `site_id`, `site_name` |
| `prisma_sase_vpn_link_status` | Gauge | VPN overlay link operational state (1=up, 0=down) | `link_id`, `source_site`, `target_site`, `state` |
| `prisma_sase_bgp_peer_state` | Gauge | BGP peer session state (1=established, 0=other) | `peer_ip`, `peer_asn`, `site_name`, `state` |
| `prisma_sase_scrape_success` | Gauge | Exporter scrape outcome (1=success, 0=failure) | None |
| `prisma_sase_scrape_duration_seconds` | Gauge | Total duration of the Prisma SASE scrape | None |

---

## Prometheus Scrape Configuration

Add the target to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: "prisma-sdwan"
    scrape_interval: 60s
    scrape_timeout: 30s
    static_configs:
      - targets: ["localhost:9850"]
```

---

## Grafana Dashboard

A ready-to-import Grafana dashboard JSON is located at [`dashboards/prisma_sdwan_overview.json`](dashboards/prisma_sdwan_overview.json).

### Dashboard Panels & Features:
- **Executive KPIs**: Active sites count, online/offline ION appliances, overlay VPN health %, BGP peer session health %, scrape state.
- **Resource Utilization**: CPU and Memory utilization (%) time series charts with configurable warning/critical thresholds.
- **Inventory Matrix**: Sortable table with site names, element IDs, hardware models, serial numbers, software versions, and live connection states.
- **Network & Routing**: Overlay VPN channel states and BGP neighbor peering tables.
- **Dynamic Templating**: Filters metrics dynamically by Site and Element/ION appliance.

To import:
1. Open Grafana → **Dashboards** → **New** → **Import**.
2. Upload [`dashboards/prisma_sdwan_overview.json`](dashboards/prisma_sdwan_overview.json) or paste its contents.
3. Select your Prometheus data source when prompted.

---

## Development & Testing

Run unit tests and linters:

```bash
uv run pytest
uv run ruff check .
uv run mypy src
```
