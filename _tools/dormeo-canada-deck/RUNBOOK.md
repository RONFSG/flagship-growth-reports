# Dormeo Canada weekly deck — Monday runbook (and the Tuesday inventory update)

Same 17-slide Weekly Business Review as Dormeo US, for the Canada marketplace (Sellerise account "Dormeo",
marketplace CA, all money in CAD, shown as $; the cover says the amounts are CAD). Published to `dormeo-canada/deck/` in this repo
(https://reports.flagshipgrowth.com/dormeo-canada/deck/manifest.json), which the Flagship Insights "Weekly deck" tab
reads. Only ever commit `dormeo-canada/deck/` and this folder.

It reuses the Dormeo US scripts. Every script is told which brand to run for with `DECK_BRAND=../dormeo-canada-deck`
(run from `_tools/dormeo-us-dashboard` or `_tools/dormeo-us-deck`). Without `DECK_BRAND` they run for Dormeo US, so
never forget it. Canada has no daily dashboard, so the Monday run pulls its own data (step 2).

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
4. **Deck extras** (`/tmp/deck/extra.json`, shape of `weeks/2026-10-24/extra.json`), all CA and `targetCurrency: "CAD"` for
   account metrics. Same list as the US RUNBOOK step 2, plus: weekly rows need impressions and clicks, so pull each of the
   4 Mon–Sun weeks with `groupBy: none`; `daily` = `get_account_metrics` groupBy `day` for the two Mon–Sun weeks;
   `septRevenue`-style keys: last full month's revenue (`data/pnl_ads.json` PL gross) and last year's same month
   (`data/sales.json` a25); `primeDays` = event days in `deck_config.json`. Copy numbers exactly; never estimate.
5. **Numbers:** `cd ../dormeo-us-deck && python3 compute.py ../dormeo-canada-deck /tmp/deck/deck_data.json ../dormeo-canada-deck/deck_config.json`
6. **Commentary:** `/tmp/deck/notes.json` with every key of `weeks/2026-10-24/notes.json` (rewrite all of it), same rules as
   the US RUNBOOK step 5. Write money as $ (e.g. "$1,605"); the cover already says it is CAD. Canada retail dates: Black Friday / Cyber Monday, Boxing Day (Dec 26).
7. **Build and look:** `python3 build_slides.py /tmp/deck/deck_data.json /tmp/deck/extra.json /tmp/deck/notes.json /tmp/deck/deck.pptx`,
   render (`soffice` + `pdftoppm -r 40`) and look at every slide; fix overflow by shortening notes.
8. **Publish:** `python3 publish_deck.py /tmp/deck/deck.pptx /tmp/deck/deck_data.json ../../dormeo-canada` (with `DECK_BRAND` set,
   so it uses this folder's `deck_config.json`), then
   `mkdir -p ../dormeo-canada-deck/weeks/<week end> && cp /tmp/deck/extra.json /tmp/deck/notes.json ../dormeo-canada-deck/weeks/<week end>/`,
   `git add ../../dormeo-canada/deck ../dormeo-canada-deck && git commit -m "Dormeo Canada weekly deck: week <N> (<label>)" && git push origin main`.
9. **Google Slides copy (one call, about a minute).** The deck goes to Google Slides as one picture per slide, from the
   images just published (not editable there; the .pptx is the editable file). After the push, wait about a minute for
   reports.flagshipgrowth.com to update, then:
   - Google_Drive `create_file`: title `Dormeo Canada - Weekly Business Review - Week <N> (<label>)`,
     `contentMimeType` `application/vnd.google-apps.presentation`, `parentId` `1AObylhEtAg2iJCLOAd8a-f7SCgawUGg2` (Drive folder "Weekly decks").
   - Google_Slides `read_presentation` with `fields: ["slides.objectId"]` → the one blank slide's id (usually `p`).
   - (from `_tools/dormeo-us-deck`) `python3 gslides_images.py ../../dormeo-canada/deck <that slide id>` and pass its output, unchanged, as `requests` to
     Google_Slides `update_presentation` for the new file. If it says an image can't be fetched, the site hasn't updated
     yet: wait a minute and send it again.
   - (from `_tools/dormeo-us-deck`) `python3 gslides_images.py link ../../dormeo-canada/deck <presentation id>`, then commit and push `../../dormeo-canada/deck/manifest.json`.
     Insights then shows "Open in Google Slides" next to View PowerPoint.
10. **Report:** two lines on the week.
   Also report the time each part took (run `date` at the start, after the data pulls and at the end): data pulls,
   build and publish.

## Tuesday: inventory update (slide 12 only)

As the US RUNBOOK's Tuesday section, with `DECK_BRAND=../dormeo-canada-deck`:
1. `git pull --rebase origin main`; newest `../dormeo-canada-deck/weeks/<week end>/` (missing = Monday didn't publish: stop and report).
2. `cd _tools/dormeo-us-dashboard && python3 parse_sheet_pages.py ../.. ../dormeo-canada-deck/data`. If the sheet date is not
   newer than the one on the published slide 12, stop: "Dormeo Canada inventory sheet not updated yet".
3. `cd ../dormeo-us-deck && python3 compute.py ../dormeo-canada-deck /tmp/deck/deck_data.json ../dormeo-canada-deck/deck_config.json`, then
   `python3 build_slides.py /tmp/deck/deck_data.json ../dormeo-canada-deck/weeks/<week end>/extra.json ../dormeo-canada-deck/weeks/<week end>/notes.json /tmp/deck/deck.pptx`.
4. Publish as step 8 (same week end); commit `../../dormeo-canada/deck ../dormeo-canada-deck` and push.
   Then make a new Google Slides copy as step 9 (title ends "… inventory update").
5. One-line report.

## Files
- `brand.json`: account, marketplace, currency, sheet page names, SQP ASIN, size-aware short names for products whose sheet names leave the size out.
- `deck_config.json`: event days.
- `data/`, `raw/`: Canada's own copy of the dashboard data (the US scripts write here when `DECK_BRAND` is set).
- `gslides_state.json`: what the Canada presentation holds. `weeks/<week end>/`: each week's extra.json and notes.json.
