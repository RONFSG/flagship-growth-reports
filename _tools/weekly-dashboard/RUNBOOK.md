# Weekly dashboard (`<slug>-weekly`) — Claude + Sellerise, no Apps Script

Replaces the Apps Script `generateBrandWeekly` step. Same page design (`style.html` is the old `Weekly_getCSS`;
`build.py` ports `Weekly_buildBrandHTML`). Slack/email are not part of this yet.

**Week = Sunday–Saturday** (same as the old script and Sellerise's own week). Week number = ISO week of the Monday.
Run after Saturday's data is in (Sunday PST or later). Prior week = the 7 days before.

## Per brand (settings in `brands.json`: account, marketplace, currency)

All Sellerise calls use `accountSearch`, `marketplaces`, `targetCurrency` from brands.json.

1. **Week totals** — `get_account_metrics` groupBy none, once for the week and once for the prior week. Keep
   `productSales, revenue, salesTaxes, units` and `ppc.spend, ppc.sales, ppc.clicks, ppc.impressions, ppc.orders`.
2. **Daily** — `get_account_metrics` groupBy none for each of the 7 days (groupBy day has no productSales). Keep
   `productSales, revenue, salesTaxes`. If any day is missing, stop: do not publish a partial week.
3. **Products** — `get_products` mode top, metric revenue, limit 8, activeOnly false, for the week. From
   `salesProfitSummaryByAsin` keep `asin, revenue, salesTaxes, units, sessions`. Then the same call for the prior
   week with `asins` = those ASINs. Title = Sellerise product name cut at the first `|`.
   get_products has no productSales, so for each of those ASINs also call `get_account_metrics` groupBy none,
   `asin=<ASIN>` (same accountSearch/marketplaces/targetCurrency) for the week and the prior week and store its
   `productSales` (plus revenue/salesTaxes from that call) in the product's `cur`/`prev`. This also handles currency
   conversion (e.g. CA → USD) since get_account_metrics converts to targetCurrency.
4. Write `data/<slug>/<weekStart>.json` (copy `data/opopop/2026-10-25.json` for the shape), `insights: null`.
5. `python3 _tools/weekly-dashboard/build.py <slug> <weekStart> --summary` and write the 4 insights from that output
   only (Weekly Highlights / Metrics to Watch / Ad Spend Efficiency / Actions This Week, `**Label —** text`).
   Rules:
   - **Tone:** positive and action-focused throughout; frame every drop with a "why" and a silver lining.
   - **Specific numbers:** always copy exact figures from the --summary output; never invent or round differently.
   - **CTR** = ad CTR only (clicks ÷ impressions); never suggest listing/image A/B tests; ad creative tests are fine.
   - **Never mention** Prime Day or any seasonal event unless it actually fell in the current or prior week.
   - **Weekly Highlights:** lead with the strongest result (organic growth, top SKU lift, peak day). Celebrate wins first.
   - **Metrics to Watch:** when total sales or a key SKU is down, always explain the primary driver (e.g. reduced ad
     spend, fewer ad impressions, PPC pullback) before citing the number. Then note what held up or improved (organic,
     ROAS, efficiency). Frame as "controlled adjustment" or "efficiency-driven" rather than a plain decline. End with
     one forward-looking sentence about what we are doing to bring it back.
     Example pattern: "The easing in overall sales was primarily driven by a [X]% reduction in ad spend — a deliberate
     efficiency move — while organic revenue held at $Y. We are focusing on [specific SKU/action] to restore volume."
   - **Ad Spend Efficiency:** when ROAS improved or TACoS fell, lead with that win. When both worsened, explain what
     is being corrected and why the spend level was set where it was.
   - **Actions This Week:** 2–3 concrete, specific actions tied directly to the numbers above (SKU name, metric target,
     tactic). Never generic. Must feel like a real plan, not boilerplate.
6. `python3 _tools/weekly-dashboard/build.py <slug> <weekStart>` → writes `<slug>-weekly/index.html`.
   Screenshot it and check the numbers before pushing.
7. Commit only `<slug>-weekly/index.html` and `_tools/weekly-dashboard/`, push to main.

## Definitions (computed in build.py from the raw numbers, never taken pre-computed)
- Total Sales = Sellerise `productSales` = Amazon Ordered Product Sales, exactly (checked against Amazon for Hapad US
  and Dormeo US, Nov 9–15 2026). Do NOT use revenue − salesTaxes: Sellerise revenue is net of promotions, so it runs
  ~6% low on promo-heavy weeks (Dormeo). build.py only falls back to revenue − salesTaxes for old files without
  productSales.
- ROAS = ppcSales / ppcSpend · ACOS = ppcSpend / ppcSales · TACoS = ppcSpend / Total Sales
- CTR = clicks / impressions · CVR (KPI) = ad orders / clicks · Organic = Total Sales − ppcSales
- Product CVR = units / sessions
- Money is floored to whole units everywhere. UK: currencySymbol "£" replaces "$" on the page.
