"""Tests for CLI application."""

from typer.testing import CliRunner

from pano_sase_prom_exporter.main import app

runner = CliRunner()


def test_cli_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "pano-sase-prom-exporter version" in result.stdout


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Prometheus exporter for Palo Alto Networks Prisma SASE" in result.stdout
