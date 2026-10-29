# Reshoevn8r Canada weekly deck

This brand uses the shared weekly-deck runbook: **follow `_tools/BRAND_DECK_RUNBOOK.md` with `SLUG=reshoevn8r-canada`**
(Monday steps, and its "Tuesday: inventory update" section on Tuesdays). Same 17-slide design as every brand.

- Sellerise: account "Reshoevn8r", marketplace CA, amounts in CAD (shown as $).
- Inventory sheet page: `reshoevn8r-canada-inventory/`. Reconciliation page: `reshoevn8r-canada-reconciliation/`.
- Settings: `brand.json` (account, pages, branded-search words). Event days for month pacing: `deck_config.json`.
- Google Slides: the editable file in `googleSlidesId` (`_tools/deck-schedule.json`) is filled by the Apps Script. Never send
  `update_presentation` calls or pictures into it.

## Tuesday: inventory update

`python3 _tools/dormeo-us-deck/deck.py tuesday reshoevn8r-canada`, then report its one line (see the shared runbook).
