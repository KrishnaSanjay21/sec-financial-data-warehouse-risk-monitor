"""Executable data-quality and financial-reconciliation controls."""

from __future__ import annotations

from dataclasses import dataclass

from psycopg import Connection
from psycopg.types.json import Jsonb


@dataclass(frozen=True)
class CheckResult:
    name: str
    severity: str
    records_checked: int
    failures_found: int
    sample: tuple[dict, ...] = ()

    @property
    def passed(self) -> bool:
        return self.failures_found == 0


CHECKS = {
    "company_required_fields": (
        "error",
        "SELECT cik, ticker FROM dim_company WHERE cik IS NULL OR ticker IS NULL OR company_name IS NULL",
        "SELECT count(*) FROM dim_company",
    ),
    "duplicate_filing_accessions": (
        "error",
        """SELECT accession_number, count(*) AS duplicate_count
             FROM fact_filing GROUP BY accession_number HAVING count(*) > 1""",
        "SELECT count(*) FROM fact_filing",
    ),
    "orphan_company_facts": (
        "error",
        """SELECT ff.financial_fact_id
             FROM fact_financial_fact ff
             LEFT JOIN dim_company c USING (company_id)
             WHERE c.company_id IS NULL""",
        "SELECT count(*) FROM fact_financial_fact",
    ),
    "invalid_numeric_values": (
        "error",
        """SELECT financial_fact_id, concept_tag
             FROM fact_financial_fact
             WHERE numeric_value IS NULL""",
        "SELECT count(*) FROM fact_financial_fact",
    ),
    "balance_sheet_reconciliation": (
        "warning",
        """SELECT cik, ticker, period_end, assets, liabilities, equity,
                    assets - (liabilities + equity) AS difference
             FROM mart_company_financials
             WHERE assets IS NOT NULL AND liabilities IS NOT NULL AND equity IS NOT NULL
               AND abs(assets - (liabilities + equity)) > greatest(1000000, abs(assets) * 0.01)""",
        """SELECT count(*) FROM mart_company_financials
             WHERE assets IS NOT NULL AND liabilities IS NOT NULL AND equity IS NOT NULL""",
    ),
    "stale_company_filings": (
        "warning",
        """SELECT c.cik, c.ticker, max(f.filing_date) AS latest_filing
             FROM dim_company c
             LEFT JOIN fact_filing f ON f.company_id = c.company_id
                                    AND regexp_replace(f.form, '/A$', '') IN ('10-K', '10-Q', '20-F', '40-F')
             WHERE c.is_active
             GROUP BY c.cik, c.ticker
             HAVING max(f.filing_date) IS NULL OR max(f.filing_date) < current_date - 450""",
        "SELECT count(*) FROM dim_company WHERE is_active",
    ),
}


def run_quality_checks(connection: Connection, run_id: int | None = None) -> list[CheckResult]:
    """Run all controls, persist their outcomes, and return structured results."""

    with connection.cursor() as cursor:
        if run_id is None:
            cursor.execute("SELECT max(run_id) FROM ingestion_run")
            row = cursor.fetchone()
            run_id = row[0] if row else None
        if run_id is None:
            raise RuntimeError("No ingestion run exists; ingest data before running quality checks")

        results: list[CheckResult] = []
        for name, (severity, failure_sql, count_sql) in CHECKS.items():
            cursor.execute(count_sql)
            records_checked = cursor.fetchone()[0]
            cursor.execute(failure_sql)
            columns = [column.name for column in cursor.description]
            failure_rows = cursor.fetchall()
            sample = tuple(dict(zip(columns, row, strict=True)) for row in failure_rows[:10])
            result = CheckResult(name, severity, records_checked, len(failure_rows), sample)
            results.append(result)
            cursor.execute(
                """INSERT INTO dq_result
                       (run_id, check_name, severity, status, records_checked,
                        failures_found, details)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (
                    run_id,
                    name,
                    severity,
                    "pass" if result.passed else "fail",
                    records_checked,
                    result.failures_found,
                    Jsonb({"sample": list(sample)}),
                ),
            )
    connection.commit()
    return results


def has_blocking_failures(results: list[CheckResult]) -> bool:
    return any(not result.passed and result.severity == "error" for result in results)

