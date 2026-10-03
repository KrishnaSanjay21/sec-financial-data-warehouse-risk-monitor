import httpx

from sec_risk_monitor.config import Settings
from sec_risk_monitor.sec_client import SecApiError, SecClient, resolve_universe


def test_client_identifies_itself_and_hashes_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["user-agent"] == "Portfolio Owner owner@example.com"
        return httpx.Response(200, json={"ok": True}, headers={"etag": "abc"})

    settings = Settings(
        sec_user_agent="Portfolio Owner owner@example.com", sec_requests_per_second=10
    )
    with SecClient(settings, transport=httpx.MockTransport(handler)) as client:
        response = client.get_json("https://data.sec.gov/example.json")

    assert response.payload == {"ok": True}
    assert response.etag == "abc"
    assert len(response.sha256) == 64


def test_resolve_universe_preserves_order() -> None:
    payload = {
        "0": {"ticker": "MSFT", "cik_str": 789019, "title": "MICROSOFT CORP"},
        "1": {"ticker": "AAPL", "cik_str": 320193, "title": "Apple Inc."},
    }
    result = resolve_universe(payload, ["AAPL", "MSFT"])
    assert [row["ticker"] for row in result] == ["AAPL", "MSFT"]


def test_resolve_universe_rejects_missing_ticker() -> None:
    try:
        resolve_universe({}, ["AAPL"])
    except SecApiError as exc:
        assert "AAPL" in str(exc)
    else:
        raise AssertionError("Expected SecApiError")

