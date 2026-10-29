# Weekly deck: how it works and how to run it

The weekly business review deck has 17 slides. Each week it's published on the brand's **Weekly deck** tab in Flagship Insights: open it in Google Slides, view the PowerPoint in the browser, download the PDF, or click through the slide images. Each brand has **one** Google Slides file (its id is in `_tools/deck-schedule.json`); every run replaces its slides with one picture per slide, so the link never changes. The old editable Slides sync took 20+ minutes and is retired.

**One design for every brand.** All brands use the same 17-slide build (`_tools/dormeo-us-deck/build_slides.py`); a brand only adds its settings folder `_tools/<slug>-deck/`. Each week only the data and commentary change. `deck.py` runs each step for any brand by slug, so nobody sets `DECK_BRAND` by hand.

## What's needed

**Claude Code connectors:** Sellerise, Google Drive, Google Slides.

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
| Google Slides | one file, same link every week (`googleSlidesId` in deck-schedule.json), Drive folder "Weekly decks" | same |
| Money | USD, $ | CAD, shown as $ (the cover says CAD) |

The scripts live in `_tools/dormeo-us-deck/` and `_tools/dormeo-us-dashboard/`, and one copy serves every brand. To run them for a brand other than Dormeo US, set `DECK_BRAND=../<brand>-deck`. **If `DECK_BRAND` isn't set, they run for Dormeo US.**

## The weekly cycle

| Day | Run | What it does |
|---|---|---|
| Monday | Dormeo US, then Dormeo Canada (the `monday` list in `_tools/deck-schedule.json`) | Pulls Sellerise for every slide except inventory, writes the commentary, builds and publishes (PowerPoint and PDF) |
| Tuesday | Inventory update | Rebuilds slide 12 from the new inventory sheet. No Sellerise calls. Skips any brand whose sheet hasn't been updated yet |
| Sunday | Other brands (`sunday` list, currently empty) | Same steps as Monday, once a brand has a deck |

**The deck's week is Monday–Sunday** (ending the Sunday before the Monday run). `deck_week.py` pulls it and writes
`wk/deckweek.json`; the dashboards keep Sunday–Saturday.

## Monday steps (detail in each runbook)

1. `git pull --rebase origin main`
2. **Data**: Dormeo US needs the daily dashboard run first; Canada runs `update_data.py plan` / save / `finalize`.
   Both: `deck_week.py plan` → make the calls → `save` each → `build <monday>` for the Mon–Sun week.
3. **Extras**: `deck.py extra-plan <slug>` lists the remaining Sellerise calls → write `pulled.json` →
   `deck.py extra-build <slug> pulled.json`. The 4-week table and last week's daily rows come from saved files.
4. **Commentary**: `/tmp/deck/<slug>/notes.json` with every key; only numbers from the data files; rewritten every week.
5. **Build**: `deck.py build <slug>` → look at the one contact-sheet image.
6. **Publish**: `deck.py publish <slug>` (also saves the week's inputs, sets the Slides link, commits only the brand's folders).
7. **Google Slides**: `read_presentation` (slide ids) → `deck.py slides <slug> <ids>` → `update_presentation`.
8. **Report**: a short summary of the week and how long each part took.

**Tuesday**: `deck.py tuesday <slug>` does the whole inventory update (or says why it skipped), then
`deck.py slides <slug> <ids> --only 1,12` replaces just those two slides in Google Slides.

## Speed and cost

Each run is an agent session, so its cost is mostly the Sellerise data and the text the agent reads and writes. To keep it low:
- Weekly totals are saved in `wk/` and reused: the 4-week table needs one new week's pull, not four, and the daily table
  needs 7 new days, not 14.
- `deck.py` does the build/publish/commit steps in one command each and prints one line of JSON, instead of many tool calls.
- One contact-sheet image replaces looking at 17 slide images.
- Tuesday's Google Slides call replaces 2 slides (6 requests) instead of all 17 (51 requests).
- The commentary is the only part written fresh each week.

## Rules

- **Inventory** comes only from the sheet, never from Sellerise.
- **Numbers**: never estimate them, and never reuse last week's numbers or commentary.
- **Sellerise calls**:
  - For Canada, every `get_account_metrics` call needs `targetCurrency: "CAD"`; otherwise Sellerise converts to USD.
  - Page through campaign pulls with `offset` until `hasMore` is false.
- **Commits**: only the brand's own deck folders and its `_tools` folder. Never `fs.html`, and never another brand's report.
- **Google Slides**: the weekly copy is pictures; edits belong in the .pptx build, not in Slides.
- **Insights PRs**: put each change on a branch with a PR, then squash-merge it with a plain title, so no "Merge pull request" line appears.

## Adding a new brand

1. Copy `_tools/dormeo-canada-deck/` to `_tools/<slug>-deck/` (the design is shared; this folder is only the brand's settings and data), then:
   - Edit `brand.json`: account, marketplace, currency, sheet page names, SQP ASIN and short names.
   - Edit `data/groups.json`: the brand's product lines and ASINs.
   - Empty `raw/` and `weeks/`.
   - Point the runbook at the new folder.
2. Pull the data, then build and publish the first week. Expect the first build to take longer than a normal week.
3. Add the brand to `_tools/deck-schedule.json` (`sunday` for brands other than Dormeo).
4. In Insights, add a migration that sets `brands.deck_manifest_url` to `https://reports.flagshipgrowth.com/<slug>/deck/manifest.json`. Use migration `0069_dormeo-canada-deck` as the pattern.
5. The scheduled tasks need the Sellerise, Google Slides and Google Drive connectors.
