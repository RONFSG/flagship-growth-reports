# Weekly deck — shared runbook for every brand except Dormeo

One 17-slide Weekly Business Review per brand, same design as Dormeo's (`_tools/dormeo-us-deck/build_slides.py`).
Each brand only has a settings folder `_tools/<SLUG>-deck/` (`brand.json`, `deck_config.json`, its data). Every command
below names the brand by `SLUG`; never set `DECK_BRAND` by hand except where a step shows it.
Published to `<SLUG>/deck/` (https://reports.flagshipgrowth.com/<SLUG>/deck/manifest.json). Only ever commit
`<SLUG>/deck/` and `_tools/<SLUG>-deck/`.

**Week = Monday–Sunday**: the last complete week, ending yesterday when the run is on Monday; the prior week is the one
before it. Sellerise account, marketplace and currency come from `_tools/<SLUG>-deck/brand.json`: every
`get_account_metrics` call carries `targetCurrency` = its `currency` (the plans add it; keep it).

Paths: run from the repo root unless a step says otherwise. `T=/tmp/deck/<SLUG>` (deck.py creates it).

## Monday steps

0. **First run only** (no `_tools/<SLUG>-deck/data/groups.json` yet). Pull the brand's products for the last 30 days:
   Sellerise `get_products` (accountSearch/marketplaces from brand.json, start = end = "last 30 days", mode "top",
   metric "revenue", limit 100, activeOnly false), every page (`offset` until `hasMore` is false). Write
   `$T/products.json` = `[[asin, parentAsin or null, product title, revenue], ...]` (revenue from
   `salesProfitSummaryByAsin`, titles/parents from `entities.products`), then
   `python3 _tools/dormeo-us-deck/deck.py init <SLUG> $T/products.json`. It makes the starting data files, picks the
   product lines (7 biggest products by parent ASIN + "Other products") and the search-query ASIN. A brand with no
   sales in 30 days: stop and report "no sales in the last 30 days".
1. **Get the repo.** `git pull --rebase origin main`.
2. **Data.** `cd _tools/dormeo-us-dashboard && DECK_BRAND=../<SLUG>-deck python3 update_data.py plan` prints the calls.
   Make every call except the `month` ones, save each in the shape the table in `_tools/dormeo-us-dashboard/RUNBOOK.md`
   step 3 gives (the `sqp` ASIN is the one in the plan, not Dormeo's), run its `save_with` command with the same
   `DECK_BRAND=../<SLUG>-deck`, then `DECK_BRAND=../<SLUG>-deck python3 update_data.py finalize`. The first run also
   lists the year's finished months (`pl`) and last year's months (`ly`: `[[month 1-12, revenue], ...]`).
   Page `camp` with `offset` until `hasMore` is false. An empty SQP result is fine: skip that save.
3. **The deck's Mon–Sun week.** `cd ../dormeo-us-deck && DECK_BRAND=../<SLUG>-deck python3 deck_week.py plan`, make the
   calls, `DECK_BRAND=../<SLUG>-deck python3 deck_week.py save <kind> <monday> <file>` each (page `camp` until
   `hasMore` is false), then `DECK_BRAND=../<SLUG>-deck python3 deck_week.py build <this week's monday>`.
4. **Inventory and reconciliation (sheet pages only, no Sellerise):**
   `cd ../dormeo-us-dashboard && DECK_BRAND=../<SLUG>-deck python3 parse_sheet_pages.py ../.. ../<SLUG>-deck/data`.
   A brand with no sheet page gets empty inventory (slide 12 says so); that's expected.
5. **Deck extras.** `cd ../dormeo-us-deck && python3 deck.py extra-plan <SLUG>` lists the remaining calls; write
   `$T/pulled.json` with one key per call in the shape of `_tools/dormeo-us-deck/example/extra.json` (`daily` = the
   rows the plan asks for; same rules as `_tools/dormeo-us-deck/RUNBOOK.md` step 2, except branded search terms are the
   ones containing any of brand.json's `brandTerms`), then `python3 deck.py extra-build <SLUG> $T/pulled.json`.
   Copy numbers exactly; never estimate.
6. **Numbers** (to write the commentary from): `DECK_BRAND=../<SLUG>-deck python3 compute.py ../<SLUG>-deck $T/deck_data.json ../<SLUG>-deck/deck_config.json`.
7. **Commentary:** `$T/notes.json` with every key of `_tools/dormeo-us-deck/example/notes.json`, written fresh for this
   brand and week, same rules as `_tools/dormeo-us-deck/RUNBOOK.md` step 5 (plain English, only numbers from
   `deck_data.json` and `extra.json`, name what actually moved, 5–8 recommendations). Money in the brand's symbol
   (brand.json `money`); a non-USD brand's cover already says the currency.
8. **Build and look:** `python3 deck.py build <SLUG>`, look at the contact-sheet image it prints, fix overflow by
   shortening notes and build again.
9. **Publish:** `python3 deck.py publish <SLUG>` (publishes, saves the week's inputs, sets the Google Slides link,
   commits only this brand's folders, pushes).
10. **Google Slides: nothing to do.** The editable file in `googleSlidesId` is rebuilt by the Apps Script within ~30
    minutes. Never call `update_presentation` on it or send slide pictures into it.
11. **Report:** two lines on the week, the Google Slides link, and how long the data pulls, build and publish took.

If a Sellerise call fails: leave that block empty as the file shapes allow and say on the slide which data is missing.
If the build or publish fails: publish nothing for this brand, report why, and go on to the next brand.

## Tuesday: inventory update

`python3 _tools/dormeo-us-deck/deck.py tuesday <SLUG>`. It refreshes the brand's sheet data, skips when the sheet isn't
newer than the published slide 12 (or the brand has no inventory sheet), otherwise rebuilds with this week's saved
inputs, publishes and pushes. Google Slides: nothing to do. Report its one line.
