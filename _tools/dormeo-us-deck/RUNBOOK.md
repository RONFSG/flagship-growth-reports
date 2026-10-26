# Dormeo US weekly deck — Monday runbook (and the Tuesday inventory update)

Builds the 17-slide Weekly Business Review (FSG branding, the layout of the "Dormeo Weekly Amazon Business Review" sample)
for the week that ended on Sunday, and publishes it to `dormeo-us/deck/` in this repo
(https://reports.flagshipgrowth.com/dormeo-us/deck/manifest.json). The Flagship Insights brand page reads that manifest
for its **Weekly deck** tab. Only ever commit `dormeo-us/deck/` and this folder.

**Week = Monday–Sunday** (Ron, 2026-10-27). "This week" = the last complete Mon–Sun week, ending yesterday when the
run is on Monday; "prior week" = the one before it. The dashboards keep their own Sunday–Saturday weeks; the deck's
week comes from `deck_week.py` (step 1b), and `compute.py` uses it whenever `wk/deckweek.json` exists.

## Steps

1. **Get the repo.** `git pull --rebase origin main`. The daily dashboard refresh should have run (month, P&L, SQP and
   ad history still come from `_tools/dormeo-us-dashboard/data`).
1b. **The deck's Mon–Sun week.** `python3 deck_week.py plan` prints the Sellerise calls for this week and the prior week
   (meta, week, camp, kw for each). Make them, save each with `python3 deck_week.py save <kind> <monday> <file>`
   (shapes in the script's header; page `camp` with `offset` until `hasMore` is false), then
   `python3 deck_week.py build <this week's monday>`. This replaces last week's `wk/deckweek.json`; never reuse it.
2. **Pull the deck extras from Sellerise** (account "Dormeo", marketplace "US"; make the calls in parallel) and save them as
   `/tmp/deck/extra.json` in exactly the shape of `example/extra.json`. Copy numbers exactly; never estimate.
   - `weeks`: 4 entries, oldest first, one per Mon–Sun week ending this Sunday. Each from `get_account_metrics` groupBy `none`
     for that week: revenue, units, orders, `ppc.impressions`, `ppc.clicks`, `refundAmount` (= refundUnits), refundRate,
     `ppc.spend`, `ppc.sales` (adSales), `ppc.acos`, `ppc.tacos`. Label like `"Oct 19 – 25"`. The last entry also needs
     net, refunds (money), `ppc.orders` (adOrders), `ppc.cpc`, cvr (= adOrders ÷ clicks × 100).
   - `mtd`: `get_account_metrics` groupBy `none` from the 1st of the month to yesterday (`days` = yesterday's day of month).
     `mtdLY`: the same dates one year earlier.
   - `daily`: `get_account_metrics` groupBy `day` for the two Mon–Sun weeks: `[date, revenue, ppcSpend, ppcSales, orders, ppcOrders]`, 14 rows.
   - `searchTerms`, `targets`: use this Mon–Sun week's dates.
   - `searchTerms`: `get_ads_search_term_insights` mode `top_sales` limit 25 for this week. `total` = summary.matchedSearchTerms;
     `winners`, `harvest` (= harvest_exact_candidate), `negative` (= negative_candidate), `noPurchase` (= clicks_no_purchase)
     from summary.reasonCounts. `rows` = top 8 queries containing "dormeo"; `category` = top 5 without it.
     Row = `[query, adProduct, impressions, clicks, orders, spend, sales]`.
   - `targets`: `get_ads_targeting_insights` mode `needs_attention` limit 10. `total` = matchedTargets, `winners`/`highAcos`/
     `noSales` (waste_no_sales)/`lowCtr` from reasonCounts, `needsAttention` = modeMatchedTargets. `rows` = top 5:
     `[target, Match, "Brand"|"Category", spend, sales, acos or null, clicks, orders]`.
   - `reviews`: `get_review_insights` last 90 days → `{"available": false}` if no rows, else the rating/review counts.
   - `alerts`: `get_alert_summary` last 30 days → total, actionable (actionableTotal), critical, warning, and `byType` with plain labels.
   - Inventory is **not** pulled from Sellerise. Slide 12 uses only the inventory sheet (Inventory Tracker tab, via the
     `dormeo-us-inventory/` page the dashboard refresh reads). On Monday it shows the latest sheet update there is; the
     Tuesday run below refreshes it once the new weekly sheet update is in.
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
   (prints `DECK_PUBLISHED`), then save this week's inputs for the Tuesday run:
   `mkdir -p weeks/<week end> && cp /tmp/deck/extra.json /tmp/deck/notes.json weeks/<week end>/`, then
   `git add ../../dormeo-us/deck . && git commit -m "Dormeo US weekly deck: week <N> (<label>)" && git push origin main`
   (on a rejected push: `git pull --rebase origin main`, push again).
8. **Google Slides (same file and link every week, one call, about a minute).** The deck goes to Google Slides as one
   picture per slide, from the images just published (not editable there; the .pptx is the editable file).
   **Dormeo US's file: `1yhYL8dq-pEwjApvrKG2uapZKmmzc6BPF66746nUlr_k`** (Drive folder "Weekly decks"). Never create a new
   file. After the push, wait about a minute for reports.flagshipgrowth.com to update, then:
   - Google_Slides `read_presentation` on that file with `fields: ["slides.objectId"]` → its current slide ids.
   - `python3 gslides_images.py ../../dormeo-us/deck <those ids, comma-separated>` and pass its output, unchanged, as
     `requests` to Google_Slides `update_presentation` for that file (adds the new slides and deletes the old ones in one
     call). If it says an image can't be fetched, the site hasn't updated yet: wait a minute and send it again.
   - `python3 gslides_images.py link ../../dormeo-us/deck 1yhYL8dq-pEwjApvrKG2uapZKmmzc6BPF66746nUlr_k`, then commit and
     push `../../dormeo-us/deck/manifest.json` (publishing drops the link, so this is needed every time).
9. **Report:** send `/tmp/deck/deck.pptx` to the user (SendUserFile) with a two-line summary of the week.
   Also report the time each part took (run `date` at the start, after the data pulls and at the end): data pulls,
   build and publish.

## Tuesday: inventory update (slide 12 only)

Run by the Tuesday task after the weekly inventory sheet update. No Sellerise calls and no new commentary.
1. `git pull --rebase origin main`. Find this week's folder: the newest `weeks/<week end>/` (it has `extra.json` and `notes.json`).
   If it is missing, the Monday deck didn't publish: stop and report that.
2. Refresh the sheet data: `python3 ../dormeo-us-dashboard/parse_sheet_pages.py ../.. ../dormeo-us-dashboard/data`.
   It prints the sheet's date and week. If that date is not newer than the one on the published slide 12
   (`dormeo-us/deck/manifest.json` → current week's deck; the slide title shows "inventory update (<date>)"), the sheet
   hasn't been updated yet: stop and report "inventory sheet not updated yet", publishing nothing.
3. `python3 compute.py ../dormeo-us-dashboard /tmp/deck/deck_data.json deck_config.json`, then
   `python3 build_slides.py /tmp/deck/deck_data.json weeks/<week end>/extra.json weeks/<week end>/notes.json /tmp/deck/deck.pptx`.
   Render and look at slide 12 (`soffice` + `pdftoppm -f 12 -l 12`).
4. Publish as Monday's step 7: same week end, so it replaces this week's files and keeps the manifest entry. Commit
   `git add ../../dormeo-us/deck ../dormeo-us-dashboard/data/inv_sheet.json . && git commit -m "Dormeo US weekly deck: week <N> inventory update"`, push.
   Then refresh the same Google Slides file as Monday's step 8, so the link shows the new slide 12.
5. Report: one line with the new sheet date and the out-of-stock / low-stock counts.

## If something fails
- A Sellerise call fails: leave that block as `example/extra.json` shapes it but with this week's values you do have, and say in
  the notes which slide is missing data. Never reuse last week's numbers.
- The build or publish fails: publish nothing, report why. The Insights tab keeps showing last week's deck.

## Files
- `compute.py` — every deck number from the dashboard data (`_tools/dormeo-us-dashboard/data`, `raw/`).
- `build_slides.py` — the 17 slides (python-pptx; charts drawn as shapes so the file stays small and converts cleanly to Google Slides).
- `publish_deck.py` — PowerPoint + PDF + one JPG per slide into `dormeo-us/deck/<week end>/`, updates `manifest.json` (keeps 26 weeks).
- `gslides_images.py` — refreshes the brand's one Google Slides file with the slide pictures (step 8). `fix_pptx.py` — keeps the .pptx openable in PowerPoint (run by build_slides.py).
- `gslides_sync.py` + `gslides_state.json` — old editable Google Slides sync, not used (too slow). The state file records
  what the presentation holds; commit it after every sync.
- `upload_slides.py` — not used (needs a service account): replaces one Google Slides file's content via the Drive API (needs a service account and Google API access).
- `example/` — Week 43's `extra.json` and `notes.json`, the reference shapes.
- `weeks/<week end>/` — each week's `extra.json` and `notes.json`, kept so the Tuesday inventory update rebuilds the same deck.
