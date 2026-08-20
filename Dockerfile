# Build & Runtime stage for Prisma SASE Prometheus Exporter
FROM python:3.12-slim-bookworm AS final

# Install uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Security: install curl/ca-certificates, clean cache, and create non-root user
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -u 10001 -r -s /bin/false -d /app appuser

WORKDIR /app

# Configure environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Copy dependency manifests first for layer caching
COPY pyproject.toml uv.lock README.md ./

# Install project dependencies without editable project code
RUN uv sync --frozen --no-install-project --no-dev

# Copy application source code
COPY src/ ./src/

# Install the application package
RUN uv sync --frozen --no-dev

# Set permissions for non-root execution
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose standard Prometheus exporter port
EXPOSE 9850

# Container healthcheck querying the /metrics endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:9850/metrics > /dev/null 2>&1 || exit 1

# Default command to start the exporter
ENTRYPOINT ["pano-sase-prom-exporter"]
CMD ["serve", "--host", "0.0.0.0", "--port", "9850"]
