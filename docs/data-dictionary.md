# Data dictionary

## `dim_company`

One row per SEC registrant. `cik` is the natural key; ticker and company metadata are refreshed from the submissions response.

## `dim_reporting_period`

Unique XBRL reporting contexts. A missing `period_start` marks an instant balance-sheet fact; duration facts retain both start and end dates. Fiscal year/period and SEC frame are kept because calendar and company fiscal periods do not always align.

## `fact_filing`

One row per accession number from the submissions feed. `is_amendment` identifies forms ending in `/A`; the original and amended filings remain separate.

## `fact_financial_fact`

One row per reported fact version. Important fields:

| Field | Meaning |
|---|---|
| `fact_fingerprint` | SHA-256 identity used for idempotency |
| `taxonomy` / `concept_tag` | Original XBRL concept identity |
| `unit` | SEC-reported measurement unit |
| `numeric_value` | Numeric fact value; no scaling is applied |
| `filed_date` | Date this version became public |
| `accession_number` | Filing that supplied the observation |
| `source_run_id` | Ingestion lineage |

## `raw_api_response`

Immutable changed API payloads. Duplicate endpoint/checksum combinations are ignored, enabling safe incremental reruns.

## `dq_result`

Persisted result for every check and run, including severity, pass/fail status, counts, and up to ten sample failures.

## Analytics views

| View | Grain and purpose |
|---|---|
| `vw_financial_fact_versions` | Every fact version with latest-version rank |
| `vw_financial_fact_current` | Current version of each fact context |
| `vw_restatements` | Changed current/prior versions for the same context |
| `vw_canonical_financial_fact` | Preferred source tag per canonical metric |
| `mart_company_financials` | Company/reporting-period wide financials |
| `mart_company_risk_monitor` | Financials plus margins, liquidity, leverage, cash conversion, and growth |

