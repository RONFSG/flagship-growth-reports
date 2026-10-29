# Dormeo Canada weekly deck — Monday runbook (and the Tuesday inventory update)

Same 17-slide Weekly Business Review as Dormeo US, for the Canada marketplace (Sellerise account "Dormeo",
marketplace CA, all money in CAD, shown as $; the cover says the amounts are CAD). Published to `dormeo-canada/deck/` in this repo
(https://reports.flagshipgrowth.com/dormeo-canada/deck/manifest.json), which the Flagship Insights "Weekly deck" tab
reads. Only ever commit `dormeo-canada/deck/` and this folder.

It reuses the Dormeo US scripts. Every script is told which brand to run for with `DECK_BRAND=../dormeo-canada-deck`
(run from `_tools/dormeo-us-dashboard` or `_tools/dormeo-us-deck`). Without `DECK_BRAND` they run for Dormeo US, so
never forget it (`deck.py` sets it for you). Canada has no daily dashboard, so the Monday run pulls its own data (step 2).

**Week = Monday–Sunday** (Ron, 2026-10-27). "This week" = the last complete Mon–Sun week; "prior week" = the one
before it. Step 2's data stays on Sunday–Saturday weeks (month, P&L, history); the deck's own week comes from step 2b.

## Steps

1. **Get the repo.** `git pull --rebase origin main`. Set `export DECK_BRAND=../dormeo-canada-deck` for every command below.
2. **Data (Sellerise).** `cd _tools/dormeo-us-dashboard && python3 update_data.py plan` prints the calls (account "Dormeo",
   marketplace CA; `get_account_metrics` calls carry `targetCurrency: "CAD"`, keep it). Make every call except the
   `month` ones (the deck doesn't use them), save each as the US dashboard RUNBOOK describes (same file shapes), run its
   `save_with` command, then `python3 update_data.py finalize`. Campaign pulls (`camp`) must be paged with `offset` until
   `hasMore` is false. If the plan doesn't list `week <last week's Sunday>` because it exists already, fine; the deck needs
   `raw/week_<this week's Sunday>.json` and `raw/week_<prior week's Sunday>.json`.
   An empty SQP result (Amazon's report not loaded yet) is fine: skip that save.
2b. **The deck's Mon–Sun week.** `cd ../dormeo-us-deck && python3 deck_week.py plan` (with `DECK_BRAND` set; the
   calls carry `marketplaces: CA` and `targetCurrency: "CAD"`), make the calls, `deck_week.py save <kind> <monday> <file>`
   each (page `camp` until `hasMore` is false), then `deck_week.py build <this week's monday>`. Writes
   `../dormeo-canada-deck/wk/deckweek.json`, replacing last week's.
3. **Inventory and reconciliation (sheet only, no Sellerise):**
   `python3 parse_sheet_pages.py ../.. ../dormeo-canada-deck/data` (reads `dormeo-canada-inventory/` and
   `dormeo-canada-reconciliation/`).
4. **Deck extras:** `cd ../dormeo-us-deck && python3 deck.py extra-plan dormeo-canada` lists only the calls still needed
   (CA, `targetCurrency: "CAD"` already set). Make them, write `/tmp/deck/dormeo-canada/pulled.json` (one key per call, each
   in the shape of last week's `weeks/<week end>/extra.json`; `daily` = this week's 7 rows; same rules as the US RUNBOOK
   step 2), then `python3 deck.py extra-build dormeo-canada /tmp/deck/dormeo-canada/pulled.json`. The 4-week table and last
   week's daily rows come from saved files. Copy numbers exactly; never estimate.
5. **Numbers** (for the commentary): `DECK_BRAND=../dormeo-canada-deck python3 compute.py ../dormeo-canada-deck /tmp/deck/dormeo-canada/deck_data.json ../dormeo-canada-deck/deck_config.json`
6. **Commentary:** `/tmp/deck/dormeo-canada/notes.json` with every key of last week's `notes.json` (rewrite all of it), same rules as
   the US RUNBOOK step 5. Write money as $ (e.g. "$1,605"); the cover already says it is CAD. Canada retail dates: Black Friday / Cyber Monday, Boxing Day (Dec 26).
7. **Build and look:** `python3 deck.py build dormeo-canada`, then look at the one contact-sheet image it prints; fix overflow
   by shortening notes and build again.
8. **Publish:** `python3 deck.py publish dormeo-canada` (publishes, saves the week's inputs, sets the Slides link, commits
   only Canada's folders, pushes).
9. **Google Slides: nothing to do.** The brand's editable Google Slides file (googleSlidesId in
   `_tools/deck-schedule.json`, the link Insights opens) is rebuilt from this publish by the Apps Script in
   `_tools/apps-script/` within about 30 minutes. **Never call Google Slides `update_presentation` on it and never
   send slide pictures into it**: that would replace the editable slides. Put the link in the report.
10. **Report:** two lines on the week.
   Also report the time each part took (run `date` at the start, after the data pulls and at the end): data pulls,
   build and publish.

## Tuesday: inventory update (slide 12 only)

Same as the US RUNBOOK's Tuesday section, with `dormeo-canada`:
1. `python3 _tools/dormeo-us-deck/deck.py tuesday dormeo-canada`. `"skipped"` = "Dormeo Canada inventory sheet not updated
   yet"; `"stopped"` = the reason (e.g. Monday didn't publish). Otherwise it rebuilds, publishes, commits and pushes.
2. Look at the `check` image (slide 12).
3. Google Slides: nothing to do (the Apps Script rebuilds the editable file within ~30 minutes). Never call
   `update_presentation` on it.
4. One-line report: sheet date, out-of-stock / low-stock counts (or the skip reason).

## Files
- `brand.json`: account, marketplace, currency, sheet page names, SQP ASIN, size-aware short names for products whose sheet names leave the size out.
- `deck_config.json`: event days.
- `data/`, `raw/`: Canada's own copy of the dashboard data (the US scripts write here when `DECK_BRAND` is set).
- `gslides_state.json`: what the Canada presentation holds. `weeks/<week end>/`: each week's extra.json and notes.json.
