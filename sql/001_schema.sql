BEGIN;

CREATE TABLE IF NOT EXISTS ingestion_run (
    run_id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at        TIMESTAMPTZ,
    status              TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    companies_requested INTEGER NOT NULL DEFAULT 0,
    companies_succeeded INTEGER NOT NULL DEFAULT 0,
    rows_loaded         BIGINT NOT NULL DEFAULT 0,
    error_message       TEXT
);

CREATE TABLE IF NOT EXISTS dim_company (
    company_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cik                 INTEGER NOT NULL UNIQUE,
    ticker              TEXT NOT NULL,
    company_name        TEXT NOT NULL,
    exchange            TEXT,
    sic                 TEXT,
    sic_description     TEXT,
    fiscal_year_end     TEXT,
    entity_type         TEXT,
    is_active           BOOLEAN NOT NULL DEFAULT true,
    first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_company_ticker ON dim_company (ticker);

CREATE TABLE IF NOT EXISTS dim_reporting_period (
    reporting_period_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    period_start        DATE,
    period_end          DATE NOT NULL,
    fiscal_year         INTEGER,
    fiscal_period       TEXT,
    frame               TEXT,
    is_instant          BOOLEAN NOT NULL,
    UNIQUE NULLS NOT DISTINCT
        (period_start, period_end, fiscal_year, fiscal_period, frame, is_instant)
);

CREATE TABLE IF NOT EXISTS fact_filing (
    accession_number    TEXT PRIMARY KEY,
    company_id          BIGINT NOT NULL REFERENCES dim_company(company_id),
    filing_date         DATE NOT NULL,
    report_date         DATE,
    acceptance_datetime TIMESTAMPTZ,
    form                TEXT NOT NULL,
    file_number         TEXT,
    primary_document    TEXT,
    primary_doc_description TEXT,
    is_amendment        BOOLEAN NOT NULL DEFAULT false,
    source_run_id       BIGINT NOT NULL REFERENCES ingestion_run(run_id),
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_filing_company_date
    ON fact_filing (company_id, filing_date DESC);
CREATE INDEX IF NOT EXISTS ix_filing_form ON fact_filing (form);

CREATE TABLE IF NOT EXISTS fact_financial_fact (
    financial_fact_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fact_fingerprint    TEXT NOT NULL UNIQUE,
    company_id          BIGINT NOT NULL REFERENCES dim_company(company_id),
    reporting_period_id BIGINT NOT NULL REFERENCES dim_reporting_period(reporting_period_id),
    accession_number    TEXT,
    taxonomy            TEXT NOT NULL,
    concept_tag         TEXT NOT NULL,
    concept_label       TEXT,
    concept_description TEXT,
    unit                TEXT NOT NULL,
    numeric_value       NUMERIC,
    filed_date          DATE NOT NULL,
    form                TEXT NOT NULL,
    source_run_id       BIGINT NOT NULL REFERENCES ingestion_run(run_id),
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_fact_company_concept_period
    ON fact_financial_fact (company_id, concept_tag, reporting_period_id);
CREATE INDEX IF NOT EXISTS ix_fact_accession ON fact_financial_fact (accession_number);

CREATE TABLE IF NOT EXISTS raw_api_response (
    raw_response_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id              BIGINT NOT NULL REFERENCES ingestion_run(run_id),
    endpoint            TEXT NOT NULL,
    cik                 INTEGER,
    payload_sha256      TEXT NOT NULL,
    payload             JSONB NOT NULL,
    etag                TEXT,
    last_modified       TEXT,
    fetched_at          TIMESTAMPTZ NOT NULL,
    UNIQUE (endpoint, payload_sha256)
);

CREATE TABLE IF NOT EXISTS dq_result (
    dq_result_id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id              BIGINT NOT NULL REFERENCES ingestion_run(run_id),
    check_name          TEXT NOT NULL,
    severity            TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'error')),
    status              TEXT NOT NULL CHECK (status IN ('pass', 'fail')),
    records_checked     BIGINT NOT NULL,
    failures_found      BIGINT NOT NULL,
    details             JSONB NOT NULL DEFAULT '{}'::jsonb,
    checked_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;

