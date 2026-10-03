"""Idempotent PostgreSQL loaders for transformed SEC records."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from psycopg import Connection
from psycopg.types.json import Jsonb

from .sec_client import SecResponse


def start_run(connection: Connection, companies_requested: int) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO ingestion_run (status, companies_requested)
               VALUES ('running', %s) RETURNING run_id""",
            (companies_requested,),
        )
        run_id = cursor.fetchone()[0]
    connection.commit()
    return run_id


def finish_run(
    connection: Connection,
    run_id: int,
    status: str,
    companies_succeeded: int,
    rows_loaded: int,
    error_message: str | None = None,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """UPDATE ingestion_run
               SET completed_at = now(), status = %s, companies_succeeded = %s,
                   rows_loaded = %s, error_message = %s
               WHERE run_id = %s""",
            (status, companies_succeeded, rows_loaded, error_message, run_id),
        )
    connection.commit()


def store_raw_response(
    connection: Connection, run_id: int, response: SecResponse, cik: int | None = None
) -> bool:
    """Persist immutable API evidence; return False for an unchanged payload."""

    with connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO raw_api_response
                   (run_id, endpoint, cik, payload_sha256, payload, etag, last_modified, fetched_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (endpoint, payload_sha256) DO NOTHING
               RETURNING raw_response_id""",
            (
                run_id,
                response.endpoint,
                cik,
                response.sha256,
                Jsonb(response.payload),
                response.etag,
                response.last_modified,
                response.fetched_at,
            ),
        )
        inserted = cursor.fetchone() is not None
    connection.commit()
    return inserted


def upsert_company(connection: Connection, company: dict[str, Any]) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO dim_company
                   (cik, ticker, company_name, exchange, sic, sic_description,
                    fiscal_year_end, entity_type)
               VALUES (%(cik)s, %(ticker)s, %(company_name)s, %(exchange)s, %(sic)s,
                       %(sic_description)s, %(fiscal_year_end)s, %(entity_type)s)
               ON CONFLICT (cik) DO UPDATE SET
                   ticker = EXCLUDED.ticker,
                   company_name = EXCLUDED.company_name,
                   exchange = EXCLUDED.exchange,
                   sic = EXCLUDED.sic,
                   sic_description = EXCLUDED.sic_description,
                   fiscal_year_end = EXCLUDED.fiscal_year_end,
                   entity_type = EXCLUDED.entity_type,
                   is_active = true,
                   last_seen_at = now()
               RETURNING company_id""",
            company,
        )
        company_id = cursor.fetchone()[0]
    return company_id


def upsert_filings(
    connection: Connection, company_id: int, run_id: int, filings: Iterable[dict[str, Any]]
) -> int:
    parameters = [
        {**filing, "company_id": company_id, "run_id": run_id} for filing in filings
    ]
    if not parameters:
        return 0
    with connection.cursor() as cursor:
        cursor.executemany(
            """INSERT INTO fact_filing
                   (accession_number, company_id, filing_date, report_date,
                    acceptance_datetime, form, file_number, primary_document,
                    primary_doc_description, is_amendment, source_run_id)
               VALUES (%(accession_number)s, %(company_id)s, %(filing_date)s,
                       %(report_date)s, %(acceptance_datetime)s, %(form)s,
                       %(file_number)s, %(primary_document)s,
                       %(primary_doc_description)s, %(is_amendment)s, %(run_id)s)
               ON CONFLICT (accession_number) DO UPDATE SET
                   report_date = EXCLUDED.report_date,
                   acceptance_datetime = EXCLUDED.acceptance_datetime,
                   primary_document = EXCLUDED.primary_document,
                   primary_doc_description = EXCLUDED.primary_doc_description""",
            parameters,
        )
        return cursor.rowcount


def _reporting_period_id(connection: Connection, fact: dict[str, Any]) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO dim_reporting_period
                   (period_start, period_end, fiscal_year, fiscal_period, frame, is_instant)
               VALUES (%(period_start)s, %(period_end)s, %(fiscal_year)s,
                       %(fiscal_period)s, %(frame)s, %(is_instant)s)
               ON CONFLICT (period_start, period_end, fiscal_year, fiscal_period, frame, is_instant)
               DO UPDATE SET period_end = EXCLUDED.period_end
               RETURNING reporting_period_id""",
            fact,
        )
        return cursor.fetchone()[0]


def upsert_financial_facts(
    connection: Connection, company_id: int, run_id: int, facts: Iterable[dict[str, Any]]
) -> int:
    period_cache: dict[tuple[Any, ...], int] = {}
    parameters: list[dict[str, Any]] = []
    for fact in facts:
        period_key = (
            fact["period_start"],
            fact["period_end"],
            fact["fiscal_year"],
            fact["fiscal_period"],
            fact["frame"],
            fact["is_instant"],
        )
        if period_key not in period_cache:
            period_cache[period_key] = _reporting_period_id(connection, fact)
        parameters.append(
            {
                **fact,
                "company_id": company_id,
                "period_id": period_cache[period_key],
                "run_id": run_id,
            }
        )
    if not parameters:
        return 0

    with connection.cursor() as cursor:
        cursor.executemany(
            """INSERT INTO fact_financial_fact
                   (fact_fingerprint, company_id, reporting_period_id, accession_number,
                    taxonomy, concept_tag, concept_label, concept_description, unit,
                    numeric_value, filed_date, form, source_run_id)
               VALUES (%(fact_fingerprint)s, %(company_id)s, %(period_id)s,
                       %(accession_number)s, %(taxonomy)s, %(concept_tag)s,
                       %(concept_label)s, %(concept_description)s, %(unit)s,
                       %(numeric_value)s, %(filed_date)s, %(form)s, %(run_id)s)
               ON CONFLICT (fact_fingerprint) DO NOTHING""",
            parameters,
        )
        return cursor.rowcount

