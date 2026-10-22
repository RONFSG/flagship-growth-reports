# Dormeo US dashboard — daily refresh runbook

Live page: https://reports.flagshipgrowth.com/dormeo-us/ (file `dormeo-us/index.html` in this repo).
This folder rebuilds it every morning from **Sellerise** (sales, ads, campaigns, keywords, SQP) and the
**FSG Combined Report pages** already in this repo (`dormeo-us-inventory/`, `dormeo-us-reconciliation/`,
built from the Dormeo US sheet's Inventory Tracker and Reconciliation Update tabs).

Only ever commit `dormeo-us/index.html` and this folder. Never touch any other report.

## Steps

1. **Get the repo.** Clone or pull `RONFSG/flagship-growth-reports` (`git pull --rebase origin main`), `cd _tools/dormeo-us-dashboard`.
2. **Plan.** `python3 update_data.py plan` prints today's Sellerise calls (dates are worked out for you; the run day is
   the America/Los_Angeles date and data runs through yesterday). Make every call listed, with exactly the args shown,
   account "Dormeo", marketplace "US". Calls are independent: make them in parallel.
3. **Save each response** as a small JSON file (e.g. `/tmp/ads.json`) in the shape below, then run the `save_with`
   command shown in the plan, replacing `<raw>` with the file path, e.g. `python3 update_data.py ads /tmp/ads.json`.
   Copy numbers exactly from the tool result; never estimate. If a response has `page.hasMore: true`, fetch the next
   page with `offset` and include those rows too. Aliases like `p1`/`c1` are per response: map them through that
   response's `entities`.

   | command | tool | file shape |
   |---|---|---|
   | `ads` | get_account_metrics, groupBy day | `[[day, revenue, ppcSpend, ppcSales, ppcOrders], ...]` from `rows` (day as `20261022`) |
   | `month MM` / `week YYYY-MM-DD` | get_products | month: `[[asin, revenue, units, sessions, ppcSpend, ppcSales], ...]`; week: `[[asin, revenue, units], ...]`. revenue/units/sessions from `salesProfitSummaryByAsin.rows` (one row per ASIN); ppcSpend/ppcSales from the main `rows`, mapped pid→asin with `entities.products` and summed per ASIN (null if the ASIN has no ad row) |
   | `pl MM` / `meta YYYY-MM-DD` | get_account_metrics, groupBy none | the object `totalsByCurrency[0].metrics`, copied as is |
   | `camp YYYY-MM-DD` | get_ppc_efficiency | `{"names": {campaignId: campaignName}, "rows": [[campaignId, type, spend, sales, impressions, clicks, orders], ...]}`, campaign id/name from `entities.campaigns` (`cid` → `[id, name, asin]`), every page |
   | `kw YYYY-MM-DD` | get_ads_targeting_insights | `{"tot": {"spend","sales","orders","clicks","impressions"}, "R": [[adProduct, keyword, match, spend, sales, clicks, orders, impressions, units, topOfSearchPct or null], ...]}`; keyword targets only (skip ASIN/category/product targets); `tot` = the response's SP+SB totals if given, else the sum of the rows |
   | `sqp YYYY-MM-DD` | get_sqp_report (ASIN B07WFHMD2V) | `[[query, qv, imt, im, cvt, cv], ...]` (query volume, total impressions, ASIN impressions, total purchases, ASIN purchases) |

4. **Build.** `./run.sh`. It reads the inventory/reconciliation pages, rebuilds campaigns/keywords/SQP/inventory weeks,
   renders `dormeo-us/index.html` and validates it. It prints `BUILD_OK` only if the page passed every check.
5. **Publish.** If `BUILD_OK`:
   `git add ../../dormeo-us/index.html data raw && git commit -m "Dormeo US dashboard: daily refresh, data through <YYYY-MM-DD>"`
   then `git push origin main` (on a rejected push: `git pull --rebase origin main` and push again).
   If the build failed: `git checkout -- ../../dormeo-us/index.html data raw`, push nothing, and report why.

## If something fails
- A Sellerise call fails or returns nothing: skip that one save, keep going (yesterday's numbers stay for that block),
  and list it in the commit message and the final report.
- Sellerise not connected / GitHub push refused: stop and report it plainly; the live page keeps yesterday's version.
- Never invent or carry forward numbers by hand; never edit `template.html` or other reports during a refresh.

## Files
- `template.html` — the dashboard layout (from the Forgotten Skincare dashboard, FSG branding) with `{{PLACEHOLDERS}}`.
- `render.py` — fills the template from `data/`; dates, labels, notes and restock tasks are worked out from the data.
- `update_data.py` — plans the day's pulls and turns saved Sellerise responses into `data/*.json`; responses kept in `raw/`.
- `parse_sheet_pages.py` — reads `dormeo-us-inventory/` and `dormeo-us-reconciliation/` into `data/inv_sheet.json`, `data/rec.json`.
- `validate.py` — syntax, placeholder and sanity checks before publishing.
- `data/groups.json` (8 product lines), `data/tasks.json` (task list; restock tasks are regenerated daily from the inventory sheet).

The template and calendar logic cover 2026. In January 2027 the year labels and 2025/2026 comparisons need a one-time update.
