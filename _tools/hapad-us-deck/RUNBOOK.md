# Hapad US weekly deck

This brand uses the shared weekly-deck runbook: **follow `_tools/BRAND_DECK_RUNBOOK.md` with `SLUG=hapad-us`**
(Monday steps, and its "Tuesday: inventory update" section on Tuesdays). Same 17-slide design as every brand.

- Sellerise: account "Hapad", marketplace US, amounts in USD.
- Inventory sheet page: `hapad-us-inventory/`. Reconciliation page: `hapad-us-reconciliation/`.
- Settings: `brand.json` (account, pages, branded-search words). Event days for month pacing: `deck_config.json`.
- Google Slides: the editable file in `googleSlidesId` (`_tools/deck-schedule.json`) is filled by the Apps Script. Never send
  `update_presentation` calls or pictures into it.

## Tuesday: inventory update

`python3 _tools/dormeo-us-deck/deck.py tuesday hapad-us`, then report its one line (see the shared runbook).
