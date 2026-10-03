# Dashboard specification

## 1. Executive risk overview

- KPI cards: latest revenue, revenue growth, net margin, current ratio, restatement count, DQ pass rate
- Scatterplot: revenue growth vs. net margin; bubble size = assets; company tooltip
- Ranked bar: liabilities-to-assets by company
- Filters: company, form, fiscal year, fiscal period

## 2. Profitability and liquidity

- Small-multiple line charts for revenue, operating income, and net income
- Matrix by company and period with conditional formatting for margins and ratios
- Current ratio trend with a configurable reference line at 1.0
- Cash conversion trend; tooltips must expose missing numerator/denominator values

## 3. Filings and restatements

- Filing-volume trend split by 10-K, 10-Q, 8-K, and amendments
- Restatement table with prior/current value, percentage change, filing dates, and accession numbers
- Filing freshness table showing days since latest periodic filing
- Drill-through from company to filing history

## 4. Data operations

- Latest refresh status, duration, companies succeeded, and rows loaded
- DQ checks by status and severity
- Failure samples from `dq_result.details`
- Raw-response coverage by endpoint and fetch date

## Design rules

- Reserve red for failed controls or high-risk thresholds; do not use it decoratively.
- Display accounting units and fiscal-period context in every financial tooltip.
- Label null ratios as unavailable rather than zero.
- Include a footer: “Source: SEC EDGAR APIs. Analytical demonstration—not investment advice.”

