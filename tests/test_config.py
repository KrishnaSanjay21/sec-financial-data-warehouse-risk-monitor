from pathlib import Path

import pytest

from sec_risk_monitor.config import Settings, load_metric_map, load_tickers


def test_company_universe_has_100_unique_tickers() -> None:
    tickers = load_tickers()
    assert len(tickers) == 100
    assert len(tickers) == len(set(tickers))
    assert tickers[:3] == ["AAPL", "MSFT", "GOOGL"]


def test_ticker_limit_and_metric_map() -> None:
    assert len(load_tickers(limit=12)) == 12
    assert "RevenueFromContractWithCustomerExcludingAssessedTax" in load_metric_map()[
        "revenue"
    ]["tags"]


def test_settings_reject_unsafe_rate() -> None:
    with pytest.raises(ValueError):
        Settings(sec_user_agent="Owner owner@domain.com", sec_requests_per_second=11)


def test_settings_requires_real_sec_contact() -> None:
    with pytest.raises(ValueError):
        Settings(sec_user_agent="SEC Risk Monitor contact@example.com")


def test_custom_ticker_file(tmp_path: Path) -> None:
    path = tmp_path / "companies.csv"
    path.write_text("ticker\nAAPL\naapl\nMSFT\n", encoding="utf-8")
    assert load_tickers(path) == ["AAPL", "MSFT"]

