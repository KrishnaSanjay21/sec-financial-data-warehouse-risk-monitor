// Parameterize these values in Power BI Desktop before publishing.
let
    ServerName = "localhost:5432",
    DatabaseName = "sec_risk",
    Source = PostgreSQL.Database(ServerName, DatabaseName, [CreateNavigationProperties=false]),
    RiskMonitor = Source{[Schema="public", Item="mart_company_risk_monitor"]}[Data]
in
    RiskMonitor

// Repeat the final navigation line for vw_restatements, fact_filing,
// dim_company, dq_result, and ingestion_run as separate named queries.

