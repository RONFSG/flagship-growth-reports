# Weekly dashboard (`<slug>-weekly`) — Claude + Sellerise, no Apps Script

Replaces the Apps Script `generateBrandWeekly` step. Same page design (`style.html` is the old `Weekly_getCSS`;
`build.py` ports `Weekly_buildBrandHTML`). Slack/email are not part of this yet.

**Week = Sunday–Saturday** (same as the old script and Sellerise's own week). Week number = ISO week of the Monday.
Run after Saturday's data is in (Sunday PST or later). Prior week = the 7 days before.

## Per brand (settings in `brands.json`: account, marketplace, currency)

All Sellerise calls use `accountSearch`, `marketplaces`, `targetCurrency` from brands.json.

1. **Week totals** — `get_account_metrics` groupBy none, once for the week and once for the prior week. Keep
   `revenue, salesTaxes, units` and `ppc.spend, ppc.sales, ppc.clicks, ppc.impressions, ppc.orders`.
2. **Daily** — `get_account_metrics` groupBy none for each of the 7 days (groupBy day has no salesTaxes). Keep
   `revenue, salesTaxes`. If any day is missing, stop: do not publish a partial week.
3. **Products** — `get_products` mode top, metric revenue, limit 8, activeOnly false, for the week. From
   `salesProfitSummaryByAsin` keep `asin, revenue, salesTaxes, units, sessions`. Then the same call for the prior
   week with `asins` = those ASINs. Title = Sellerise product name cut at the first `|`.
4. Write `data/<slug>/<weekStart>.json` (copy `data/opopop/2026-10-25.json` for the shape), `insights: null`.
5. `python3 _tools/weekly-dashboard/build.py <slug> <weekStart> --summary` and write the 4 insights from that output
   only (Weekly Highlights / Metrics to Watch / Ad Spend Efficiency / Actions This Week, `**Label —** text`).
   Rules from the old prompt: positive, action-focused tone; specific numbers copied from the summary; CTR is ad CTR
   (never suggest listing/image A/B tests; ad creative tests are fine); never mention Prime Day or any event unless
   it really happened in the week or prior week.
6. `python3 _tools/weekly-dashboard/build.py <slug> <weekStart>` → writes `<slug>-weekly/index.html`.
   Screenshot it and check the numbers before pushing.
7. Commit only `<slug>-weekly/index.html` and `_tools/weekly-dashboard/`, push to main.

## Definitions (computed in build.py from the raw numbers, never taken pre-computed)
- Total Sales = revenue − salesTaxes (matches Amazon Ordered Product Sales / the old sheet within ~0.2%)
- ROAS = ppcSales / ppcSpend · ACOS = ppcSpend / ppcSales · TACoS = ppcSpend / Total Sales
- CTR = clicks / impressions · CVR (KPI) = ad orders / clicks · Organic = Total Sales − ppcSales
- Product CVR = units / sessions
- Money is floored to whole units everywhere. UK: currencySymbol "£" replaces "$" on the page.
