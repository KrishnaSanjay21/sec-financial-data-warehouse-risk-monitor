import json
from decimal import Decimal
from pathlib import Path

from sec_risk_monitor.transform import parse_company, parse_company_facts, parse_filings

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_parse_company_and_filings() -> None:
    payload = load_fixture("submissions.json")
    company = parse_company(payload)
    filings = parse_filings(payload)

    assert company["cik"] == 320193
    assert company["ticker"] == "AAPL"
    assert len(filings) == 2
    assert filings[0]["acceptance_datetime"] == "2024-11-01T16:30:00-04:00"
    assert filings[1]["is_amendment"] is True


def test_parse_company_facts_preserves_duration_and_instant_contexts() -> None:
    facts = parse_company_facts(load_fixture("companyfacts.json"))

    assert len(facts) == 2
    revenue = next(fact for fact in facts if fact["concept_tag"].startswith("Revenue"))
    assets = next(fact for fact in facts if fact["concept_tag"] == "Assets")
    assert revenue["numeric_value"] == Decimal(391035000000)
    assert revenue["is_instant"] is False
    assert assets["is_instant"] is True
    assert len(revenue["fact_fingerprint"]) == 64


def test_fact_fingerprint_is_deterministic() -> None:
    payload = load_fixture("companyfacts.json")
    assert parse_company_facts(payload)[0]["fact_fingerprint"] == parse_company_facts(payload)[0][
        "fact_fingerprint"
    ]

