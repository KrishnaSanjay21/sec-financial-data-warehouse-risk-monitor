# SEC Financial Data Warehouse & Risk Monitor

A portfolio-grade data engineering project that incrementally ingests real public-company filings and XBRL facts from the SEC EDGAR APIs, models them in PostgreSQL, validates accounting relationships, and exposes analytics-ready views for Power BI.

> **Data source:** Public SEC EDGAR data. This project is for analytical demonstration only and is not investment advice.

## Target architecture

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

## Planned capabilities

- Configurable 100–500 company universe
- Rate-limited API ingestion with retries and an identifying User-Agent
- Idempotent incremental loads and raw-response lineage
- Filing/restatement history without silently overwriting prior values
- Accounting reconciliation and freshness/duplicate checks
- Revenue, profitability, liquidity, leverage, and filing-trend marts
- Scheduled GitHub Actions refresh and a source-controlled Power BI starter

Implementation is delivered in milestone commits; see the commit history for the build progression.

