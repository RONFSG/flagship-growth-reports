#!/usr/bin/env python3
"""The Google Slides API requests that rebuild a built deck as real, editable slides, for the Apps Script
(_tools/apps-script/WeeklyDeckSlides.gs) to send. Same design as the PowerPoint: this reads the .pptx and turns
every shape, text box, table and logo into Slides requests (gslides_sync.py's element model), so nothing is
re-coded in Apps Script and the two can't drift apart.

Usage: slides_requests.py <deck.pptx> <out.json.gz>   (gzipped: ~25 KB instead of ~450 KB per week)
Writes {"version": 1, "slides": N, "batches": [[request, ...], ...]}. Every object id carries a run tag, so the
script can add the new slides next to last week's and delete the old ones afterwards (never a half-built file).
Run by publish_deck.py, which publishes the file as <week end>/slides-requests.json.gz next to the deck."""
import gzip, json, sys, time
from pptx import Presentation
import gslides_sync as G

MAX_BATCH_CHARS = 400_000   # one Slides batchUpdate per batch; Apps Script sends them itself, so they can be big


def write(pptx, path):
    out = build(pptx)
    with gzip.open(path, "wt", compresslevel=9) as f: f.write(G.J(out))
    return out


def build(pptx):
    run = format(int(time.time()), "x")
    batches, cur = [], []
    slides = Presentation(pptx).slides
    for i, sl in enumerate(slides):
        reqs = G.build_slide(f"w{run}s{i + 1:02d}", i, G.model_slide(sl))
        if cur and len(G.J(cur)) + len(G.J(reqs)) > MAX_BATCH_CHARS:
            batches.append(cur); cur = []
        cur += reqs
    batches.append(cur)
    return {"version": 1, "run": run, "slides": len(slides), "batches": batches}


if __name__ == "__main__":
    out = write(sys.argv[1], sys.argv[2])
    print("slides-requests", out["slides"], "slides,", sum(len(b) for b in out["batches"]), "requests in", len(out["batches"]), "batch(es)")
