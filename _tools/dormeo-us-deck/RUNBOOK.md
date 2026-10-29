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
2. **Pull the deck extras** with `python3 deck.py extra-plan dormeo-us` (after step 1b). It lists only the Sellerise calls still
   needed (month to date, the same dates last year, this week's 7 daily rows, search terms, targets, reviews, alerts) with
   their arguments and what to keep from each; make them in parallel and write `/tmp/deck/dormeo-us/pulled.json` with one key
   per call, each in the shape `example/extra.json` uses for that key (`daily` = this week's 7 rows). Copy numbers exactly;
   never estimate. Then `python3 deck.py extra-build dormeo-us /tmp/deck/dormeo-us/pulled.json` writes
   `/tmp/deck/dormeo-us/extra.json`. The 4-week table, weekly clicks/impressions and last week's daily rows come from files
   already saved (step 1b's weekly totals and last week's `weeks/` folder), so they are not pulled again.
   - `searchTerms`: `total` = summary.matchedSearchTerms; `winners`, `harvest` (= harvest_exact_candidate), `negative`
     (= negative_candidate), `noPurchase` (= clicks_no_purchase) from summary.reasonCounts. `rows` = top 8 queries containing
     "dormeo"; `category` = top 5 without it. Row = `[query, adProduct, impressions, clicks, orders, spend, sales]`.
   - `targets`: `total` = matchedTargets, `winners`/`highAcos`/`noSales` (waste_no_sales)/`lowCtr` from reasonCounts,
     `needsAttention` = modeMatchedTargets. `rows` = top 5: `[target, Match, "Brand"|"Category", spend, sales, acos or null, clicks, orders]`.
   - `reviews`: `{"available": false}` if no rows, else the rating/review counts. `alerts`: total, actionable
     (actionableTotal), critical, warning, and `byType` with plain labels.
   - Inventory is **not** pulled from Sellerise. Slide 12 uses only the inventory sheet (Inventory Tracker tab, via the
     `dormeo-us-inventory/` page the dashboard refresh reads). On Monday it shows the latest sheet update there is; the
     Tuesday run below refreshes it once the new weekly sheet update is in.
3. **Event days.** If this month has a sales event (Prime Day, Prime Big Deal Days, BF/CM), list its dates in `deck_config.json`
   `eventDays`; month pacing then counts those days once. Leave last year's dates in; only this month's are used.
4. **Numbers:** `python3 compute.py ../dormeo-us-dashboard /tmp/deck/dormeo-us/deck_data.json deck_config.json` (read it for the commentary; step 6 recomputes it)
5. **Commentary:** write `/tmp/deck/dormeo-us/notes.json` with every key of `example/notes.json` (that file is Week 43's: rewrite all of it).
   Read `/tmp/deck/dormeo-us/deck_data.json` and `extra.json` first. Rules: plain English, short sentences, one idea per line; only numbers that are in
   those two files (or simple sums/ratios of them); name the product lines and targets that actually moved this week; never copy
   last week's story. `recommendations` = 5–8 rows `[area, action, owner team, timing]`, specific to this week's numbers.
   `reviews_*`: if reviews are unavailable say so plainly, as Week 43 does. Slides 9, 12 and 14 have no written read-out (charts and tables only).
6. **Build:** `python3 deck.py build dormeo-us` (checks notes.json has every key, builds, renders). Look at the one
   contact-sheet image it prints (all 17 slides); open a single `/tmp/deck/dormeo-us/s-NN.jpg` only if something looks off.
   Fix overflowing or overlapping text by shortening notes, then build again.
7. **Publish:** `python3 deck.py publish dormeo-us`: publishes, saves this week's inputs to `weeks/<week end>/` for the
   Tuesday run, writes the Google Slides link into the manifest, commits only this brand's folders and pushes.
8. **Google Slides (same file and link every week, one call).** One picture per slide, from the images just published.
   **Dormeo US's file: `1yhYL8dq-pEwjApvrKG2uapZKmmzc6BPF66746nUlr_k`** (Drive folder "Weekly decks"). Never create a new
   file. About a minute after the push: Google_Slides `read_presentation` with `fields: ["slides.objectId"]`, then
   `python3 deck.py slides dormeo-us <those ids, comma-separated>` and pass its output, unchanged, as `requests` to
   `update_presentation`. If an image can't be fetched, the site hasn't updated yet: wait a minute and send it again.
9. **Report:** send `/tmp/deck/dormeo-us/deck.pptx` to the user (SendUserFile) with a two-line summary of the week.
   Also report the time each part took (run `date` at the start, after the data pulls and at the end): data pulls,
   build and publish.

## Tuesday: inventory update (slide 12 only)

Run by the Tuesday task after the weekly inventory sheet update. No Sellerise calls and no new commentary.
1. `python3 _tools/dormeo-us-deck/deck.py tuesday dormeo-us` (from the repo). It pulls, refreshes the sheet data, and stops
   with `"status": "skipped"` if the sheet isn't newer than the published slide 12 ("inventory sheet not updated yet"), or
   `"stopped"` with the reason (e.g. Monday's deck didn't publish). Otherwise it rebuilds with this week's saved inputs,
   publishes, commits only this brand's files and pushes, and prints the sheet date and out-of-stock / low-stock counts.
2. Look at the `check` image it prints (slide 12).
3. About a minute later, refresh just slides 1 and 12 of the same Google Slides file: `read_presentation` with
   `fields: ["slides.objectId"]`, then `python3 _tools/dormeo-us-deck/deck.py slides dormeo-us <those ids> --only 1,12`
   and pass its output, unchanged, to `update_presentation`.
4. Report: one line with the new sheet date and the out-of-stock / low-stock counts (or the skip reason).

## If something fails
- A Sellerise call fails: leave that block as `example/extra.json` shapes it but with this week's values you do have, and say in
  the notes which slide is missing data. Never reuse last week's numbers.
- The build or publish fails: publish nothing, report why. The Insights tab keeps showing last week's deck.

## Files
- `compute.py` — every deck number from the dashboard data (`_tools/dormeo-us-dashboard/data`, `raw/`).
- `build_slides.py` — the 17 slides (python-pptx; charts drawn as shapes so the file stays small and converts cleanly to Google Slides).
- `deck.py` — one command per step for any brand (`brands`, `tuesday`, `extra-plan`, `extra-build`, `build`, `publish`,
  `slides`); no `DECK_BRAND` needed. The other scripts below are what it runs.
- `publish_deck.py` — PowerPoint + PDF + one JPG per slide into `dormeo-us/deck/<week end>/`, updates `manifest.json` (keeps 26 weeks).
- `gslides_images.py` — refreshes the brand's one Google Slides file with the slide pictures (step 8; `--only` for a few slides). `fix_pptx.py` — keeps the .pptx openable in PowerPoint (run by build_slides.py).
- `gslides_sync.py` + `gslides_state.json` — old editable Google Slides sync, not used (too slow). The state file records
  what the presentation holds; commit it after every sync.
- `upload_slides.py` — not used (needs a service account): replaces one Google Slides file's content via the Drive API (needs a service account and Google API access).
- `example/` — Week 43's `extra.json` and `notes.json`, the reference shapes.
- `weeks/<week end>/` — each week's `extra.json` and `notes.json`, kept so the Tuesday inventory update rebuilds the same deck.
