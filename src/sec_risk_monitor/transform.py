"""Pure transformations from SEC columnar JSON into warehouse records."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable


def _columnar_rows(columns: dict[str, list[Any]]) -> Iterable[dict[str, Any]]:
    if not columns:
        return []
    width = max((len(values) for values in columns.values()), default=0)
    return (
        {key: values[index] if index < len(values) else None for key, values in columns.items()}
        for index in range(width)
    )


def parse_company(submissions: dict[str, Any], ticker: str | None = None) -> dict[str, Any]:
    tickers = submissions.get("tickers") or []
    exchanges = submissions.get("exchanges") or []
    return {
        "cik": int(submissions["cik"]),
        "ticker": ticker or (tickers[0] if tickers else "UNKNOWN"),
        "company_name": submissions.get("name") or "Unknown company",
        "exchange": exchanges[0] if exchanges else None,
        "sic": submissions.get("sic"),
        "sic_description": submissions.get("sicDescription"),
        "fiscal_year_end": submissions.get("fiscalYearEnd"),
        "entity_type": submissions.get("entityType"),
    }


def parse_filings(submissions: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse the recent-filing column arrays from a submissions response."""

    recent = submissions.get("filings", {}).get("recent", {})
    parsed: list[dict[str, Any]] = []
    for row in _columnar_rows(recent):
        accession = row.get("accessionNumber")
        filing_date = row.get("filingDate")
        form = row.get("form")
        if not accession or not filing_date or not form:
            continue
        acceptance = row.get("acceptanceDateTime")
        if acceptance and len(acceptance) == 14:
            acceptance = datetime.strptime(acceptance, "%Y%m%d%H%M%S").isoformat()
        parsed.append(
            {
                "accession_number": accession,
                "filing_date": filing_date,
                "report_date": row.get("reportDate") or None,
                "acceptance_datetime": acceptance or None,
                "form": form,
                "file_number": row.get("fileNumber") or None,
                "primary_document": row.get("primaryDocument") or None,
                "primary_doc_description": row.get("primaryDocDescription") or None,
                "is_amendment": form.endswith("/A"),
            }
        )
    return parsed


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _fingerprint(parts: dict[str, Any]) -> str:
    stable = json.dumps(parts, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def parse_company_facts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten taxonomy/concept/unit nesting while retaining every filed version."""

    parsed: list[dict[str, Any]] = []
    for taxonomy, concepts in payload.get("facts", {}).items():
        for concept_tag, concept in concepts.items():
            for unit, observations in concept.get("units", {}).items():
                for item in observations:
                    if not item.get("end") or not item.get("filed") or not item.get("form"):
                        continue
                    period = {
                        "period_start": item.get("start"),
                        "period_end": item["end"],
                        "fiscal_year": item.get("fy"),
                        "fiscal_period": item.get("fp"),
                        "frame": item.get("frame"),
                        "is_instant": not bool(item.get("start")),
                    }
                    identity = {
                        "taxonomy": taxonomy,
                        "concept_tag": concept_tag,
                        "unit": unit,
                        "accession_number": item.get("accn"),
                        "filed_date": item["filed"],
                        "form": item["form"],
                        "period": period,
                        "value": item.get("val"),
                    }
                    parsed.append(
                        {
                            "fact_fingerprint": _fingerprint(identity),
                            "accession_number": item.get("accn"),
                            "taxonomy": taxonomy,
                            "concept_tag": concept_tag,
                            "concept_label": concept.get("label"),
                            "concept_description": concept.get("description"),
                            "unit": unit,
                            "numeric_value": _decimal_or_none(item.get("val")),
                            "filed_date": item["filed"],
                            "form": item["form"],
                            **period,
                        }
                    )
    return parsed

