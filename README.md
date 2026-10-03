# SEC Financial Data Warehouse & Risk Monitor

[![CI](https://github.com/KrishnaSanjay21/sec-financial-data-warehouse-risk-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/KrishnaSanjay21/sec-financial-data-warehouse-risk-monitor/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB)](https://www.python.org/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-4169E1)](https://www.postgresql.org/)

A portfolio-grade data engineering project that incrementally ingests real public-company filings and XBRL facts from the SEC EDGAR APIs, models them in PostgreSQL, validates accounting relationships, and exposes analytics-ready views for Power BI.

> **Data source:** Public SEC EDGAR data. This project is for analytical demonstration only and is not investment advice.

## What this project demonstrates

- Incremental ingestion for a configurable **100–500 company** universe
- SEC-compliant identification, request throttling, retries, and changed-payload detection
- PostgreSQL dimensional modeling with filing, company, reporting-period, and financial-fact tables
- Idempotent batch upserts, immutable raw lineage, duplicate handling, and retained restatements
- Accounting reconciliation, integrity, freshness, and completeness controls
- Analytics marts for revenue, margins, liquidity, leverage, cash conversion, and filing trends
- Docker-based local execution, CI tests, and scheduled GitHub Actions orchestration
- A Power BI implementation kit with queries, DAX measures, theme, and four-page report specification

## Architecture

```text
SEC Submissions + Company Facts APIs
              |
       polite Python client
              |
   immutable raw response audit
              |
 incremental parse + PostgreSQL upsert
              |
 dimensions / facts / current-version views
              |
 DQ reconciliation + risk-monitoring marts
              |
          Power BI
```

The detailed architecture, scale path, and decisions are in [docs/architecture.md](docs/architecture.md).

## Quick start

### 1. Configure the SEC identity

```powershell
Copy-Item .env.example .env
```

Edit `.env` and provide a real identifying contact. The SEC does not require an API key, but automated clients must follow its access policy.

```dotenv
SEC_USER_AGENT="Your Name your.email@domain.com"
SEC_COMPANY_LIMIT=3
```

### 2. Run PostgreSQL and the pipeline

```powershell
docker compose up -d postgres
docker compose --profile pipeline run --rm pipeline run-all
```

Use three companies for the smoke test, then raise the limit to 100. The CLI can also run directly:

```powershell
python -m pip install -e ".[dev]"
sec-risk init-db
sec-risk ingest --limit 3
sec-risk quality
```

### 3. Build the Power BI report

Follow [powerbi/README.md](powerbi/README.md). The repository contains source-controlled implementation assets; it does **not** claim that a Power BI Service refresh is deployed or verified.

## Warehouse outputs

| Object | Purpose |
|---|---|
| `fact_filing` | Filing history keyed by accession number |
| `fact_financial_fact` | Append-only, fingerprinted XBRL observations |
| `vw_financial_fact_current` | Latest version of each financial context |
| `vw_restatements` | Prior/current values that changed across filings |
| `mart_company_financials` | Canonical wide financial statements |
| `mart_company_risk_monitor` | Growth, profitability, liquidity, leverage, and cash-conversion KPIs |
| `dq_result` | Auditable results from every data-quality run |

See the complete [data dictionary](docs/data-dictionary.md) and [operations runbook](docs/runbook.md).

## Testing

```powershell
ruff check src tests
pytest
```

The deterministic test suite uses small SEC-shaped fixtures and a mocked HTTP transport; it never needs to call the live SEC service. CI additionally creates PostgreSQL 16 and validates every migration.

## Repository map

```text
config/                 company universe and canonical concept mapping
docs/                   architecture, data dictionary, and runbook
powerbi/                Power Query, DAX, theme, and dashboard specification
scripts/                operator entry points
sql/                    PostgreSQL schema and analytical views
src/sec_risk_monitor/   API client, transforms, loaders, quality, and CLI
tests/                  deterministic unit tests and SEC-shaped fixtures
.github/workflows/      CI and scheduled incremental refresh
```

## Data-source notes

The project uses the official [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces). The submissions endpoint supplies filing history and company metadata; the Company Facts endpoint supplies standardized XBRL observations. SEC data can contain taxonomy and reporting-context differences, so the canonical mapping is transparent and all source fields remain auditable.

The scheduled workflow requires repository secrets named `DATABASE_URL` and `SEC_USER_AGENT`. It is configuration-ready but should not be described as an operating production refresh until those secrets are configured and successful workflow history exists.

## Responsible use

This project is an engineering portfolio demonstration using public regulatory data. Ratios and anomaly flags are screening indicators—not credit ratings, audit conclusions, or investment recommendations.

