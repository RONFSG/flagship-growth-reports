# Weekly deck → editable Google Slides (Apps Script)

Every weekly deck publish (Monday build and the Tuesday inventory update) now also writes
`<brand>/deck/<week end>/slides-requests.json.gz`: the Google Slides instructions that rebuild the same deck as real,
editable slides (text boxes, tables, shapes, logos). It's made from the PowerPoint itself
(`_tools/dormeo-us-deck/slides_requests.py`), so there is still only one design.

`WeeklyDeckSlides.gs` runs in your Google account, fetches those instructions every 30 minutes, and rebuilds one
Google Slides file per brand when a new deck appears. Nothing is sent from the Claude run to Google; no service
account, no file sharing, no Cloud project.

## Set up (about 5 minutes, once)

1. Go to script.google.com → **New project**. Name it "Weekly deck Slides".
2. Replace the contents of `Code.gs` with `WeeklyDeckSlides.gs` from this folder. Save.
3. Add the Google Slides service: **Services +** (in the Files panel next to the side menu; click **Editor** to
   show it) → **Google Slides API** → Add. If that panel won't show: **Project Settings** → tick "Show
   appsscript.json", open `appsscript.json` and add
   `"dependencies": {"enabledAdvancedServices": [{"userSymbol": "Slides", "serviceId": "slides", "version": "v1"}]}`.
   Without it the log says "Slides is not defined" and no file is created.
4. Choose `setup` in the function menu at the top → **Run**. Allow access when Google asks (your own account).
5. Open **Executions** (left menu): the log shows each brand's new file link, e.g.
   `Dormeo US: created https://docs.google.com/presentation/d/.../edit`. The files go into your "Weekly decks"
   folder if you have one.

`setup` loads this week's decks right away and then checks every 30 minutes on its own.

## How it runs

- Brands come from `decks.json` on the reports site (`deck.py index`). Each brand's file is its manifest's
  `googleSlides` link (googleSlidesId in `_tools/deck-schedule.json`), the same link Insights opens.
  A brand with no link gets a new file; the log prints the id to put in `googleSlidesId`.
- Each new deck (Monday build or Tuesday inventory rebuild) replaces the file's slides: new slides are added first,
  then the old ones removed, so the file never shows a half-built deck. Edits made in the file are replaced the
  next week; version history keeps them.
- The deck runs never write to Google Slides any more (the old picture step would overwrite the editable slides).
- `reloadAll` rebuilds every brand's file now (e.g. after someone edited it by hand).
- Share each brand's file with whoever needs it (the old picture files were shared with valvare6@gmail.com as editor).
