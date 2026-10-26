# Dormeo US weekly deck — Monday runbook

Builds the 17-slide Weekly Business Review (FSG branding, the layout of the "Dormeo Weekly Amazon Business Review" sample)
for the week that ended on Saturday, and publishes it to `dormeo-us/deck/` in this repo
(https://reports.flagshipgrowth.com/dormeo-us/deck/manifest.json). The Flagship Insights brand page reads that manifest
for its **Weekly deck** tab. Only ever commit `dormeo-us/deck/` and this folder.

Week = Sunday–Saturday. "This week" = the last complete week; "prior week" = the one before it.

## Steps

1. **Get the repo.** `git pull --rebase origin main`. The Monday daily dashboard refresh must already have run:
   `_tools/dormeo-us-dashboard/data/pnl_ads.json` → `CAMP_META.weekStart` must be last Sunday and `ADS` must reach Saturday.
   If not, run `_tools/dormeo-us-dashboard/RUNBOOK.md` first (it pulls the week's campaign/keyword data).
2. **Pull the deck extras from Sellerise** (account "Dormeo", marketplace "US"; make the calls in parallel) and save them as
   `/tmp/deck/extra.json` in exactly the shape of `example/extra.json`. Copy numbers exactly; never estimate.
   - `weeks`: 4 entries, oldest first, one per Sun–Sat week ending this Saturday. Each from `get_account_metrics` groupBy `none`
     for that week: revenue, units, orders, `ppc.impressions`, `ppc.clicks`, `refundAmount` (= refundUnits), refundRate,
     `ppc.spend`, `ppc.sales` (adSales), `ppc.acos`, `ppc.tacos`. Label like `"Oct 18 – 24"`. The last entry also needs
     net, refunds (money), `ppc.orders` (adOrders), `ppc.cpc`, cvr (= adOrders ÷ clicks × 100).
   - `mtd`: `get_account_metrics` groupBy `none` from the 1st of the month to yesterday (`days` = yesterday's day of month).
     `mtdLY`: the same dates one year earlier.
   - `daily`: `get_account_metrics` groupBy `day` for the two weeks: `[date, revenue, ppcSpend, ppcSales, orders, ppcOrders]`, 14 rows.
   - `searchTerms`: `get_ads_search_term_insights` mode `top_sales` limit 25 for this week. `total` = summary.matchedSearchTerms;
     `winners`, `harvest` (= harvest_exact_candidate), `negative` (= negative_candidate), `noPurchase` (= clicks_no_purchase)
     from summary.reasonCounts. `rows` = top 8 queries containing "dormeo"; `category` = top 5 without it.
     Row = `[query, adProduct, impressions, clicks, orders, spend, sales]`.
   - `targets`: `get_ads_targeting_insights` mode `needs_attention` limit 10. `total` = matchedTargets, `winners`/`highAcos`/
     `noSales` (waste_no_sales)/`lowCtr` from reasonCounts, `needsAttention` = modeMatchedTargets. `rows` = top 5:
     `[target, Match, "Brand"|"Category", spend, sales, acos or null, clicks, orders]`.
   - `reviews`: `get_review_insights` last 90 days → `{"available": false}` if no rows, else the rating/review counts.
   - `alerts`: `get_alert_summary` last 30 days → total, actionable (actionableTotal), critical, warning, and `byType` with plain labels.
   - `invRisk`: `get_inventory_risks` limit 15 → `total` = page.total; `rows` = top 8 `[short name, asin, stock, units30, revenue30, daysSupply, "Out of stock"|"Low stock"]`.
3. **Event days.** If this month has a sales event (Prime Day, Prime Big Deal Days, BF/CM), list its dates in `deck_config.json`
   `eventDays`; month pacing then counts those days once. Leave last year's dates in; only this month's are used.
4. **Numbers:** `python3 compute.py ../dormeo-us-dashboard /tmp/deck/deck_data.json deck_config.json`
5. **Commentary:** write `/tmp/deck/notes.json` with every key of `example/notes.json` (that file is Week 43's: rewrite all of it).
   Read `deck_data.json` and `extra.json` first. Rules: plain English, short sentences, one idea per line; only numbers that are in
   those two files (or simple sums/ratios of them); name the product lines and targets that actually moved this week; never copy
   last week's story. `recommendations` = 5–8 rows `[area, action, owner team, timing]`, specific to this week's numbers.
   `reviews_*`: if reviews are unavailable say so plainly, as Week 43 does. Slides 9, 12 and 14 have no written read-out (charts and tables only).
6. **Build:** `python3 build_slides.py /tmp/deck/deck_data.json /tmp/deck/extra.json /tmp/deck/notes.json /tmp/deck/deck.pptx`
   then render and look at it: `soffice --headless --convert-to pdf --outdir /tmp/deck /tmp/deck/deck.pptx` and
   `pdftoppm -r 40 -jpeg /tmp/deck/deck.pdf /tmp/deck/s`. Open every slide image; fix overflowing or overlapping text by
   shortening notes, then rebuild.
7. **Publish:** `python3 publish_deck.py /tmp/deck/deck.pptx /tmp/deck/deck_data.json ../../dormeo-us`
   (prints `DECK_PUBLISHED`), then
   `git add ../../dormeo-us/deck . && git commit -m "Dormeo US weekly deck: week <N> (<label>)" && git push origin main`
   (on a rejected push: `git pull --rebase origin main`, push again).
8. **Google Slides: not run.** The deck is delivered through the Weekly deck tab in Flagship Insights (it reads
   `dormeo-us/deck/manifest.json`). Syncing slides through Claude cost too many tokens per brand, so it is off.
   `gslides_sync.py` stays here in case it is needed again; don't run it as part of the Monday routine.
9. **Report:** send `/tmp/deck/deck.pptx` to the user (SendUserFile) with a two-line summary of the week.

## If something fails
- A Sellerise call fails: leave that block as `example/extra.json` shapes it but with this week's values you do have, and say in
  the notes which slide is missing data. Never reuse last week's numbers.
- The build or publish fails: publish nothing, report why. The Insights tab keeps showing last week's deck.

## Files
- `compute.py` — every deck number from the dashboard data (`_tools/dormeo-us-dashboard/data`, `raw/`).
- `build_slides.py` — the 17 slides (python-pptx; charts drawn as shapes so the file stays small and converts cleanly to Google Slides).
- `publish_deck.py` — PowerPoint + PDF + one JPG per slide into `dormeo-us/deck/<week end>/`, updates `manifest.json` (keeps 26 weeks).
- `gslides_sync.py` + `gslides_state.json` — Google Slides sync, switched off (see step 8).
- `upload_slides.py` — not used (needs a service account): replaces one Google Slides file's content via the Drive API (needs a service account and Google API access).
- `example/` — Week 43's `extra.json` and `notes.json`, the reference shapes.
