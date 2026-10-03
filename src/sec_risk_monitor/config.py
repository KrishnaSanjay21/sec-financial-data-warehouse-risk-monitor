"""Runtime settings and project configuration helpers."""

from __future__ import annotations

import csv
from pathlib import Path

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Environment-driven application settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    sec_user_agent: str = Field(min_length=8)
    database_url: str = "postgresql://sec_user:sec_password@localhost:5432/sec_risk"
    sec_requests_per_second: float = 8.0
    sec_company_limit: int = 100
    sec_base_url: str = "https://data.sec.gov"
    sec_www_url: str = "https://www.sec.gov"

    @field_validator("sec_user_agent")
    @classmethod
    def identifiable_user_agent(cls, value: str) -> str:
        if "@" not in value or "example.com" in value.lower():
            raise ValueError(
                "SEC_USER_AGENT must identify you with a real contact email, "
                'for example "Your Name you@domain.com"'
            )
        return value

    @field_validator("sec_requests_per_second")
    @classmethod
    def safe_rate(cls, value: float) -> float:
        if not 0 < value <= 10:
            raise ValueError("SEC_REQUESTS_PER_SECOND must be between 0 and 10")
        return value

    @field_validator("sec_company_limit")
    @classmethod
    def supported_universe_size(cls, value: int) -> int:
        if not 1 <= value <= 500:
            raise ValueError("SEC_COMPANY_LIMIT must be between 1 and 500")
        return value


def load_tickers(path: Path | None = None, limit: int | None = None) -> list[str]:
    """Load and normalize the configured company universe."""

    source = path or PROJECT_ROOT / "config" / "company_universe.csv"
    with source.open(newline="", encoding="utf-8") as handle:
        tickers = [row["ticker"].strip().upper() for row in csv.DictReader(handle)]
    unique = list(dict.fromkeys(tickers))
    return unique[:limit] if limit is not None else unique


def load_metric_map(path: Path | None = None) -> dict:
    source = path or PROJECT_ROOT / "config" / "metric_map.yml"
    with source.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)["metrics"]

