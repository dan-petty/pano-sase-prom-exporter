"""CLI entry point for the Prisma SASE Prometheus Exporter."""

import logging
import sys

import typer
from rich.console import Console
from rich.table import Table

from pano_sase_prom_exporter import __version__
from pano_sase_prom_exporter.client import PrismaSaseClient
from pano_sase_prom_exporter.collector import PrismaSaseCollector
from pano_sase_prom_exporter.config import Settings
from pano_sase_prom_exporter.server import ExporterServer

app = typer.Typer(
    name="pano-sase-prom-exporter",
    help="Prometheus exporter for Palo Alto Networks Prisma SASE and SD-WAN ION devices.",
    add_completion=False,
)
console = Console()


def configure_logging(level_name: str) -> None:
    """Configure python root logging with formatting."""
    numeric_level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


@app.command("serve")
def serve(
    host: str | None = typer.Option(
        None,
        "--host",
        "-h",
        help="Host address to bind to (overrides EXPORTER_HOST env var).",
    ),
    port: int | None = typer.Option(
        None,
        "--port",
        "-p",
        help="Port to listen for metrics scraping (overrides EXPORTER_PORT env var).",
    ),
    log_level: str | None = typer.Option(
        None,
        "--log-level",
        "-l",
        help="Logging level: DEBUG, INFO, WARNING, ERROR.",
    ),
) -> None:
    """Start the Prometheus metrics exporter HTTP server."""
    settings = Settings()
    if host:
        settings.exporter_host = host
    if port:
        settings.exporter_port = port
    if log_level:
        settings.log_level = log_level

    configure_logging(settings.log_level)

    try:
        settings.validate_auth()
    except ValueError as err:
        console.print(f"[bold red]Configuration Error:[/bold red] {err}")
        sys.exit(1)

    server = ExporterServer(settings)
    server.start()


@app.command("test")
def test_scrape(
    log_level: str = typer.Option("INFO", "--log-level", "-l", help="Logging level."),
) -> None:
    """Perform a dry-run test scrape against Prisma SASE and display collected metrics."""
    configure_logging(log_level)
    settings = Settings()

    try:
        settings.validate_auth()
    except ValueError as err:
        console.print(f"[bold red]Configuration Error:[/bold red] {err}")
        sys.exit(1)

    console.print("[bold cyan]Connecting to Prisma SASE API...[/bold cyan]")
    client = PrismaSaseClient(settings)
    collector = PrismaSaseCollector(client)

    metrics = list(collector.collect())
    console.print(
        f"[bold green]Successfully collected {len(metrics)} metric families:[/bold green]\n"
    )

    table = Table(title="Collected Metrics Sample")
    table.add_column("Metric Name", style="cyan")
    table.add_column("Documentation", style="magenta")
    table.add_column("Samples Count", style="green")

    for m in metrics:
        table.add_row(m.name, m.documentation, str(len(m.samples)))

    console.print(table)


@app.command("version")
def version() -> None:
    """Show the exporter version."""
    console.print(f"[bold]pano-sase-prom-exporter[/bold] version [green]{__version__}[/green]")


def main() -> None:
    """Entry point wrapper."""
    app()


if __name__ == "__main__":
    main()
