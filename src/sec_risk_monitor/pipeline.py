"""End-to-end incremental ingestion orchestration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from psycopg import Connection

from .config import Settings, load_tickers
from .loader import (
    finish_run,
    start_run,
    store_raw_response,
    upsert_company,
    upsert_filings,
    upsert_financial_facts,
)
from .sec_client import SecClient, resolve_universe
from .transform import parse_company, parse_company_facts, parse_filings

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineResult:
    run_id: int
    companies_requested: int
    companies_succeeded: int
    rows_loaded: int
    failures: tuple[str, ...]


def run_incremental_ingestion(
    connection: Connection,
    settings: Settings,
    limit: int | None = None,
) -> PipelineResult:
    """Fetch only configured companies and skip unchanged endpoint payloads."""

    requested = load_tickers(limit=limit or settings.sec_company_limit)
    run_id = start_run(connection, len(requested))
    succeeded = 0
    rows_loaded = 0
    failures: list[str] = []

    try:
        with SecClient(settings) as client:
            ticker_response = client.company_tickers()
            store_raw_response(connection, run_id, ticker_response)
            companies = resolve_universe(ticker_response.payload, requested)

            for resolved in companies:
                ticker = resolved["ticker"].upper().replace(".", "-")
                cik = int(resolved["cik_str"])
                try:
                    submissions = client.submissions(cik)
                    facts = client.company_facts(cik)
                    submissions_changed = store_raw_response(
                        connection, run_id, submissions, cik
                    )
                    facts_changed = store_raw_response(connection, run_id, facts, cik)

                    company = parse_company(submissions.payload, ticker=ticker)
                    company_id = upsert_company(connection, company)

                    if submissions_changed:
                        rows_loaded += upsert_filings(
                            connection, company_id, run_id, parse_filings(submissions.payload)
                        )
                    if facts_changed:
                        rows_loaded += upsert_financial_facts(
                            connection,
                            company_id,
                            run_id,
                            parse_company_facts(facts.payload),
                        )
                    connection.commit()
                    succeeded += 1
                    LOGGER.info("Loaded %s (CIK %010d)", ticker, cik)
                except Exception as exc:  # keep a large batch moving, but report every failure
                    connection.rollback()
                    message = f"{ticker}: {type(exc).__name__}: {exc}"
                    failures.append(message)
                    LOGGER.exception("Company ingestion failed: %s", ticker)

        status = "succeeded" if not failures else "failed"
        finish_run(
            connection,
            run_id,
            status,
            succeeded,
            rows_loaded,
            "\n".join(failures) or None,
        )
    except Exception as exc:
        connection.rollback()
        finish_run(connection, run_id, "failed", succeeded, rows_loaded, str(exc))
        raise

    return PipelineResult(run_id, len(requested), succeeded, rows_loaded, tuple(failures))

