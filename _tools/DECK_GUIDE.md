# Weekly deck: how it works and how to run it

The weekly business review deck has 17 slides. Each week it's published on the brand's **Weekly deck** tab in Flagship Insights: view the PowerPoint in the browser, download the PDF, or click through the slide images. (The Google Slides copy is paused since 2026-10-27: updating it took minutes per brand.)

## What's needed

**Claude Code connectors:** Sellerise.

**Repos:**
- `RONFSG/flagship-growth-reports` holds the scripts, the data, and the published deck.
- `FlagshipGrowth/flagship-insights-ai` holds the Insights tab.

**On the machine:** Python 3 with `python-pptx` and `Pillow`, plus LibreOffice (`soffice`) and `pdftoppm` (poppler) for turning the deck into a PDF and images.

**Per brand:**

| | Dormeo US | Dormeo Canada |
|---|---|---|
| Runbook | `_tools/dormeo-us-deck/RUNBOOK.md` | `_tools/dormeo-canada-deck/RUNBOOK.md` |
| Data | `_tools/dormeo-us-dashboard/data` (refreshed daily by the dashboard run) | `_tools/dormeo-canada-deck/data` (pulled during the Monday run) |
| Inventory sheet page | `dormeo-us-inventory/` | `dormeo-canada-inventory/` |
| Published to | `dormeo-us/deck/` | `dormeo-canada/deck/` |
| Google Slides | presentation `1czOrE5asUOUB-aRAiKWyxjtaCg3rEuicfRBxpVHXYQQ` | presentation `1OmJTSCZYU8SyI5Ky8IicQb6k2fjhdBePyZ8jfx30Djs` |
| Money | USD, $ | CAD, shown as $ (the cover says CAD) |

The scripts live in `_tools/dormeo-us-deck/` and `_tools/dormeo-us-dashboard/`, and one copy serves every brand. To run them for a brand other than Dormeo US, set `DECK_BRAND=../<brand>-deck`. **If `DECK_BRAND` isn't set, they run for Dormeo US.**

## The weekly cycle

| Day | Run | What it does |
|---|---|---|
| Monday | Dormeo US, then Dormeo Canada (the `monday` list in `_tools/deck-schedule.json`) | Pulls Sellerise for every slide except inventory, writes the commentary, builds, publishes, and updates Google Slides |
| Tuesday | Inventory update | Rebuilds slide 12 from the new inventory sheet. No Sellerise calls. Skips any brand whose sheet hasn't been updated yet |
| Sunday | Other brands (`sunday` list, currently empty) | Same steps as Monday, once a brand has a deck |

## Monday steps (detail in each runbook)

1. `git pull --rebase origin main`
2. **Data**:
   - Dormeo US: the daily dashboard run must already have run.
   - Canada: run `update_data.py plan`, make the Sellerise calls it lists, save each result, then run `finalize`.
3. **Extras**: Sellerise pulls saved to `/tmp/deck/extra.json`, in the same shape as `weeks/<last week>/extra.json`. These cover the 4-week table, month to date, last year's month to date, daily rows, search terms, targets, reviews and alerts.
4. **Numbers**: `python3 compute.py <data folder> /tmp/deck/deck_data.json <deck_config.json>`
5. **Commentary**: `/tmp/deck/notes.json` must contain every key. Use only numbers from the two data files, write in plain English, and rewrite it every week.
6. **Build and check**:
   - Run `python3 build_slides.py …`.
   - Render it with `soffice` and `pdftoppm`, then look at every slide.
7. **Publish**:
   - Run `python3 publish_deck.py deck.pptx deck_data.json ../../<brand folder>`.
   - Save the week's `extra.json` and `notes.json` to `weeks/<week end>/`.
   - Commit and push.
8. **Google Slides**: paused, skip.
9. **Report**: a short summary of the week and how long each part took.

## Rules

- **Inventory** comes only from the sheet, never from Sellerise.
- **Numbers**: never estimate them, and never reuse last week's numbers or commentary.
- **Sellerise calls**:
  - For Canada, every `get_account_metrics` call needs `targetCurrency: "CAD"`; otherwise Sellerise converts to USD.
  - Page through campaign pulls with `offset` until `hasMore` is false.
- **Commits**: only the brand's own deck folders and its `_tools` folder. Never `fs.html`, and never another brand's report.
- **Google Slides**: never edit the presentation by hand outside `gslides_sync.py`, or the state file falls out of step.
- **Insights PRs**: put each change on a branch with a PR, then squash-merge it with a plain title, so no "Merge pull request" line appears.

## Adding a new brand

1. Copy `_tools/dormeo-canada-deck/` to `_tools/<slug>-deck/`, then:
   - Edit `brand.json`: account, marketplace, currency, sheet page names, SQP ASIN and short names.
   - Edit `data/groups.json`: the brand's product lines and ASINs.
   - Empty `raw/`, `weeks/` and `gslides_state.json`.
   - Point the runbook at the new folder.
2. Pull the data, then build and publish the first week. Expect the first build to take longer than a normal week.
3. Create a blank Google Slides file. Run plan with `--existing p`, send all batches, commit, and put the link in `deck_config.json`.
4. Add the brand to `_tools/deck-schedule.json` (`sunday` for brands other than Dormeo).
5. In Insights, add a migration that sets `brands.deck_manifest_url` to `https://reports.flagshipgrowth.com/<slug>/deck/manifest.json`. Use migration `0069_dormeo-canada-deck` as the pattern.
6. The scheduled tasks need the Sellerise, Google Slides and Google Drive connectors.
