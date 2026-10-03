BEGIN;

CREATE OR REPLACE VIEW vw_financial_fact_versions AS
SELECT
    ff.*,
    rp.period_start,
    rp.period_end,
    rp.fiscal_year,
    rp.fiscal_period,
    rp.frame,
    regexp_replace(ff.form, '/A$', '') AS base_form,
    row_number() OVER (
        PARTITION BY ff.company_id, ff.taxonomy, ff.concept_tag, ff.unit,
                     rp.period_start, rp.period_end, rp.fiscal_year, rp.fiscal_period,
                     regexp_replace(ff.form, '/A$', '')
        ORDER BY ff.filed_date DESC, ff.accession_number DESC NULLS LAST,
                 ff.financial_fact_id DESC
    ) AS version_rank,
    count(*) OVER (
        PARTITION BY ff.company_id, ff.taxonomy, ff.concept_tag, ff.unit,
                     rp.period_start, rp.period_end, rp.fiscal_year, rp.fiscal_period,
                     regexp_replace(ff.form, '/A$', '')
    ) AS version_count
FROM fact_financial_fact ff
JOIN dim_reporting_period rp USING (reporting_period_id);

CREATE OR REPLACE VIEW vw_financial_fact_current AS
SELECT *
FROM vw_financial_fact_versions
WHERE version_rank = 1;

CREATE OR REPLACE VIEW vw_restatements AS
SELECT
    c.cik,
    c.ticker,
    c.company_name,
    current_fact.concept_tag,
    current_fact.unit,
    current_fact.period_end,
    current_fact.base_form,
    current_fact.numeric_value AS current_value,
    prior_fact.numeric_value AS prior_value,
    current_fact.numeric_value - prior_fact.numeric_value AS absolute_change,
    CASE
        WHEN prior_fact.numeric_value = 0 THEN NULL
        ELSE (current_fact.numeric_value - prior_fact.numeric_value)
             / abs(prior_fact.numeric_value)
    END AS percent_change,
    current_fact.accession_number AS current_accession,
    prior_fact.accession_number AS prior_accession,
    current_fact.filed_date AS current_filed_date,
    prior_fact.filed_date AS prior_filed_date
FROM vw_financial_fact_versions current_fact
JOIN vw_financial_fact_versions prior_fact
  ON prior_fact.company_id = current_fact.company_id
 AND prior_fact.taxonomy = current_fact.taxonomy
 AND prior_fact.concept_tag = current_fact.concept_tag
 AND prior_fact.unit = current_fact.unit
 AND prior_fact.period_end = current_fact.period_end
 AND prior_fact.fiscal_year IS NOT DISTINCT FROM current_fact.fiscal_year
 AND prior_fact.fiscal_period IS NOT DISTINCT FROM current_fact.fiscal_period
 AND prior_fact.base_form = current_fact.base_form
 AND prior_fact.version_rank = 2
JOIN dim_company c ON c.company_id = current_fact.company_id
WHERE current_fact.version_rank = 1
  AND current_fact.numeric_value IS DISTINCT FROM prior_fact.numeric_value;

CREATE OR REPLACE VIEW vw_canonical_financial_fact AS
WITH tagged AS (
    SELECT
        f.*,
        CASE f.concept_tag
            WHEN 'RevenueFromContractWithCustomerExcludingAssessedTax' THEN 'revenue'
            WHEN 'SalesRevenueNet' THEN 'revenue'
            WHEN 'Revenues' THEN 'revenue'
            WHEN 'GrossProfit' THEN 'gross_profit'
            WHEN 'OperatingIncomeLoss' THEN 'operating_income'
            WHEN 'NetIncomeLoss' THEN 'net_income'
            WHEN 'ProfitLoss' THEN 'net_income'
            WHEN 'Assets' THEN 'assets'
            WHEN 'AssetsCurrent' THEN 'current_assets'
            WHEN 'Liabilities' THEN 'liabilities'
            WHEN 'LiabilitiesCurrent' THEN 'current_liabilities'
            WHEN 'StockholdersEquity' THEN 'equity'
            WHEN 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest' THEN 'equity'
            WHEN 'CashAndCashEquivalentsAtCarryingValue' THEN 'cash'
            WHEN 'NetCashProvidedByUsedInOperatingActivities' THEN 'operating_cash_flow'
        END AS metric_name,
        CASE f.concept_tag
            WHEN 'RevenueFromContractWithCustomerExcludingAssessedTax' THEN 1
            WHEN 'SalesRevenueNet' THEN 2
            WHEN 'Revenues' THEN 3
            WHEN 'NetIncomeLoss' THEN 1
            WHEN 'ProfitLoss' THEN 2
            WHEN 'StockholdersEquity' THEN 1
            WHEN 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest' THEN 2
            ELSE 1
        END AS tag_priority
    FROM vw_financial_fact_current f
    WHERE f.taxonomy = 'us-gaap'
      AND f.unit IN ('USD', 'USD/shares', 'shares', 'pure')
), preferred AS (
    SELECT tagged.*,
           row_number() OVER (
               PARTITION BY company_id, metric_name, period_start, period_end,
                            fiscal_year, fiscal_period, base_form, unit
               ORDER BY tag_priority, filed_date DESC, financial_fact_id DESC
           ) AS metric_rank
    FROM tagged
    WHERE metric_name IS NOT NULL
)
SELECT * FROM preferred WHERE metric_rank = 1;

CREATE OR REPLACE VIEW mart_company_financials AS
SELECT
    c.cik,
    c.ticker,
    c.company_name,
    f.period_start,
    f.period_end,
    f.fiscal_year,
    f.fiscal_period,
    f.base_form AS form,
    max(f.numeric_value) FILTER (WHERE metric_name = 'revenue') AS revenue,
    max(f.numeric_value) FILTER (WHERE metric_name = 'gross_profit') AS gross_profit,
    max(f.numeric_value) FILTER (WHERE metric_name = 'operating_income') AS operating_income,
    max(f.numeric_value) FILTER (WHERE metric_name = 'net_income') AS net_income,
    max(f.numeric_value) FILTER (WHERE metric_name = 'assets') AS assets,
    max(f.numeric_value) FILTER (WHERE metric_name = 'current_assets') AS current_assets,
    max(f.numeric_value) FILTER (WHERE metric_name = 'liabilities') AS liabilities,
    max(f.numeric_value) FILTER (WHERE metric_name = 'current_liabilities') AS current_liabilities,
    max(f.numeric_value) FILTER (WHERE metric_name = 'equity') AS equity,
    max(f.numeric_value) FILTER (WHERE metric_name = 'cash') AS cash,
    max(f.numeric_value) FILTER (WHERE metric_name = 'operating_cash_flow') AS operating_cash_flow
FROM vw_canonical_financial_fact f
JOIN dim_company c USING (company_id)
WHERE f.base_form IN ('10-K', '10-Q', '20-F', '40-F')
GROUP BY c.cik, c.ticker, c.company_name, f.period_start, f.period_end,
         f.fiscal_year, f.fiscal_period, f.base_form;

CREATE OR REPLACE VIEW mart_company_risk_monitor AS
SELECT
    financials.*,
    net_income / NULLIF(revenue, 0) AS net_margin,
    operating_income / NULLIF(revenue, 0) AS operating_margin,
    current_assets / NULLIF(current_liabilities, 0) AS current_ratio,
    liabilities / NULLIF(assets, 0) AS liabilities_to_assets,
    operating_cash_flow / NULLIF(net_income, 0) AS cash_conversion,
    revenue / NULLIF(lag(revenue) OVER (
        PARTITION BY cik, form, fiscal_period ORDER BY period_end
    ), 0) - 1 AS revenue_growth
FROM mart_company_financials financials;

COMMIT;

