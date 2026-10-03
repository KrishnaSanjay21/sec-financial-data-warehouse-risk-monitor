# Power BI implementation kit

This folder contains source-controlled inputs for the SEC Risk Monitor report. It is deliberately described as an **implementation kit**, not a deployed `.pbix`: a binary report has not been opened, credentialed, or refresh-verified in Power BI Desktop in this repository.

## Build the report

1. Start PostgreSQL and complete an ingestion run.
2. In Power BI Desktop, choose **Get data → PostgreSQL database**.
3. Connect to `localhost:5432`, database `sec_risk`, and select:
   - `mart_company_risk_monitor`
   - `vw_restatements`
   - `fact_filing`
   - `dim_company`
   - `dq_result`
   - `ingestion_run`
4. Use Import mode for the portfolio version. Use `queries.pq` as the Power Query reference.
5. Add the measures from `measures.dax`, import `theme.json`, then build the pages in `dashboard-spec.md`.
6. Save from Desktop as a Power BI Project (`.pbip`) to source-control the generated report and semantic-model definitions.

After publishing, configure the PostgreSQL gateway/credentials and test scheduled refresh in the Power BI Service. Do not describe refresh as automated until the Service refresh history shows a successful run.

