# Weekly deck → editable Google Slides (Apps Script, trial)

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
3. On the left, **Services +** → **Google Slides API** → Add.
4. Choose `setup` in the function menu at the top → **Run**. Allow access when Google asks (your own account).
5. Open **Executions** (left menu): the log shows each brand's new file link, e.g.
   `Dormeo US: created https://docs.google.com/presentation/d/.../edit`. The files go into your "Weekly decks"
   folder if you have one.

`setup` loads this week's decks right away and then checks every 30 minutes on its own.

## The trial

- Each brand gets a **new** file, "<brand> - Weekly deck (editable)". The picture copy the deck run updates
  (and the Insights link) is left alone, so you can compare the two for a week or two.
- Each new deck replaces the file's slides (new slides are added first, then the old ones removed, so the file
  never shows a half-built deck). Edits made in the file are replaced the next week; version history keeps them.
- To switch over after the trial: put the editable file's id in `fileId` for that brand, then tell Claude to set it
  as the brand's `googleSlidesId` in `_tools/deck-schedule.json` and drop the picture-copy step from the runbooks.
- `reloadAll` rebuilds every brand's file now (e.g. after someone edited it by hand).
- To add a brand: add a line to `BRANDS` with its manifest address.
