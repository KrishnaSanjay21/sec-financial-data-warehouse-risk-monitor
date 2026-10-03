"""Command-line interface for operators and scheduled jobs."""

from __future__ import annotations

import logging

import typer

from .config import Settings
from .database import connect, migrate
from .pipeline import run_incremental_ingestion
from .quality import has_blocking_failures, run_quality_checks

app = typer.Typer(no_args_is_help=True, help="SEC warehouse ingestion and quality controls")


@app.command("init-db")
def init_db() -> None:
    """Create or update PostgreSQL warehouse objects."""

    settings = Settings()
    with connect(settings.database_url) as connection:
        migrate(connection)
    typer.echo("Warehouse migrations applied.")


@app.command()
def ingest(limit: int | None = typer.Option(None, min=1, max=500)) -> None:
    """Run an incremental SEC submissions and company-facts load."""

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings()
    with connect(settings.database_url) as connection:
        result = run_incremental_ingestion(connection, settings, limit=limit)
    typer.echo(
        f"Run {result.run_id}: {result.companies_succeeded}/"
        f"{result.companies_requested} companies; {result.rows_loaded} rows loaded"
    )
    if result.failures:
        for failure in result.failures:
            typer.echo(f"FAILED {failure}", err=True)
        raise typer.Exit(code=1)


@app.command()
def quality() -> None:
    """Execute warehouse integrity and financial reconciliation checks."""

    settings = Settings()
    with connect(settings.database_url) as connection:
        results = run_quality_checks(connection)
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        typer.echo(
            f"{status:4} {result.name}: {result.failures_found}/"
            f"{result.records_checked} failures"
        )
    if has_blocking_failures(results):
        raise typer.Exit(code=2)


@app.command("run-all")
def run_all(limit: int | None = typer.Option(None, min=1, max=500)) -> None:
    """Initialize the database and run incremental ingestion."""

    init_db()
    ingest(limit=limit)
    quality()

