#!/usr/bin/env python3
"""Publish a built deck to the Dormeo US dashboard's "Weekly deck" tab.
Usage: publish_deck.py <deck.pptx> <deck_data.json> <site_dir>   (site_dir = repo's dormeo-us/ folder)
Writes <site_dir>/deck/<week-end>/{deck.pptx,deck.pdf,slide-NN.jpg} and updates <site_dir>/deck/manifest.json."""
import json, os, shutil, subprocess, sys, glob, datetime as dt, tempfile

PPTX, DATA, SITE = sys.argv[1:4]
D = json.load(open(DATA)); W = D["week"]
end = W["end"]; folder = f"deck/{end}"; out = os.path.join(SITE, folder)
os.makedirs(out, exist_ok=True)
base = f"{D.get('brand', 'Dormeo US').replace(' ', '-')}-Weekly-Business-Review-Week-{W['num']}-{end}"
shutil.copy(PPTX, os.path.join(out, base + ".pptx"))

with tempfile.TemporaryDirectory() as tmp:
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", tmp, os.path.join(out, base + ".pptx")],
                   check=True, capture_output=True, timeout=240)
    pdf = glob.glob(os.path.join(tmp, "*.pdf"))[0]
    shutil.copy(pdf, os.path.join(out, base + ".pdf"))
    for f in glob.glob(os.path.join(out, "slide-*.jpg")): os.remove(f)
    subprocess.run(["pdftoppm", "-jpeg", "-jpegopt", "quality=82", "-scale-to-x", "1280", "-scale-to-y", "-1",
                    pdf, os.path.join(out, "slide")], check=True, timeout=240)
slides = sorted(glob.glob(os.path.join(out, "slide-*.jpg")))
assert len(slides) >= 10, f"only {len(slides)} slides rendered"

# Paths are relative to manifest.json's own folder (deck/), so they resolve the same from any page that reads it.
entry = {"week": W["num"], "label": W["label"], "end": end,
         "built": dt.datetime.now(dt.timezone.utc).strftime("%b %-d, %Y"),
         "pptx": f"{end}/{base}.pptx", "pdf": f"{end}/{base}.pdf",
         "slides": [f"{end}/{os.path.basename(s)}" for s in slides]}
mpath = os.path.join(SITE, "deck", "manifest.json")
M = json.load(open(mpath)) if os.path.exists(mpath) else {"history": []}
hist = [h for h in M.get("history", []) if h["end"] != end]
hist.insert(0, {k: entry[k] for k in ("week", "label", "end", "pptx", "pdf")})
M = {"current": entry, "history": hist[:26]}
# the editable Google Slides deck (same link every week), shown as "Open in Google Slides" in Insights
cfg_path = os.path.join(os.environ.get("DECK_BRAND") or os.path.dirname(os.path.abspath(__file__)), "deck_config.json")
cfg = json.load(open(cfg_path)) if os.path.exists(cfg_path) else {}
if cfg.get("googleSlidesUrl"):
    M["googleSlides"] = cfg["googleSlidesUrl"]
json.dump(M, open(mpath, "w"), indent=1)
print("DECK_PUBLISHED", entry["pptx"], len(slides), "slides")
