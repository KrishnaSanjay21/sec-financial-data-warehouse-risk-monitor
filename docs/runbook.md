# Operations and troubleshooting runbook

## First run

1. Copy `.env.example` to `.env`.
2. Replace the placeholder `SEC_USER_AGENT` with your name or organization and contact email.
3. Run `docker compose up -d postgres`.
4. Run `docker compose --profile pipeline run --rm pipeline run-all`.
5. Review `ingestion_run` and `dq_result` before connecting Power BI.

Start with `SEC_COMPANY_LIMIT=3`; expand to 100 only after the smoke test passes.

## Failure modes

### HTTP 403 or 429

- Confirm the User-Agent clearly identifies the requester.
- Keep the configured request rate at or below 10 requests per second.
- Do not add parallel download workers without a shared rate limiter.
- Wait before retrying repeated access-policy responses.

### A company fails but the batch continues

The run ends in `failed` status and records each company error, while successful company transactions remain committed. Correct the cause and rerun; fingerprints and upserts make the retry idempotent.

### Balance-sheet reconciliation warnings

Inspect the source concepts and reporting contexts. Common causes include partial taxonomy coverage, noncontrolling interests, presentation differences, or selecting facts from different contexts. Never force the equation to balance by altering source values.

### Unexpected revenue duplicates

Compare taxonomy, tag, unit, period start/end, fiscal period, form, frame, and accession. The canonical view prioritizes common tags, but issuer-specific reporting patterns may require a reviewed mapping update.

### Power BI refresh failure

- Verify the PostgreSQL connector and gateway are online.
- Test the database credential in Service settings.
- Confirm the views exist and the latest ingestion run succeeded.
- Review scheduled-refresh history. GitHub ingestion success does not prove Power BI refresh success.

## Recovery

- Rerun the same load safely; identical endpoint payloads are skipped.
- To investigate source lineage, join facts to `ingestion_run` and inspect `raw_api_response` for the company and run.
- Back up PostgreSQL before destructive maintenance. This project never deletes historical fact versions during normal refresh.

