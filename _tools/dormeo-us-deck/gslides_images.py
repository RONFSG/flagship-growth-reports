#!/usr/bin/env python3
"""Requests that put the published slide pictures into the brand's one Google Slides file (same link every week).

Each slide becomes one full-page picture of the published slide image (fetched by Google from
reports.flagshipgrowth.com, so the deck must be pushed and live first). The new slides are added and the old ones
deleted in the same call, so the file is never left half-done. The text is not editable in Google Slides; edit the .pptx.

Usage:
  gslides_images.py <brand deck folder, e.g. ../../dormeo-us/deck> <the file's current slide ids, comma-separated>
      prints the JSON list to pass as `requests` to Google_Slides update_presentation
  gslides_images.py link <brand deck folder> <presentation id>
      writes the Google Slides link into manifest.json (top level and this week). Earlier weeks keep only their PDF,
      since the same file now shows the newest week."""
import json, os, sys, time

if sys.argv[1] == "link":
    deck, pid = sys.argv[2], sys.argv[3]
    path = os.path.join(deck, "manifest.json")
    man = json.load(open(path))
    url = f"https://docs.google.com/presentation/d/{pid}/edit"
    man["googleSlides"] = url  # what Insights reads
    man["current"]["googleSlides"] = url
    for h in man.get("history", []):
        if h.get("end") == man["current"]["end"]:
            h["googleSlides"] = url
        else:
            h.pop("googleSlides", None)
    json.dump(man, open(path, "w"), indent=1)
    print("linked", url)
    sys.exit()

deck, old = sys.argv[1], [s for s in sys.argv[2].split(",") if s.strip()]
man = json.load(open(os.path.join(deck, "manifest.json")))
brand = os.path.basename(os.path.dirname(os.path.abspath(deck)))
base = f"https://reports.flagshipgrowth.com/{brand}/deck/"
run = str(int(time.time()))  # new ids every run, so they never clash with the slides being replaced
W, H = 9144000, 5143500  # 16:9, same shape as the deck
reqs = []
for i, img in enumerate(man["current"]["slides"], 1):
    sid = f"wbr{run}_s{i:02d}"
    reqs.append({"createSlide": {"objectId": sid, "insertionIndex": i - 1,
                                 "slideLayoutReference": {"predefinedLayout": "BLANK"}}})
    reqs.append({"createImage": {"objectId": f"wbr{run}_i{i:02d}", "url": base + img,
                                 "elementProperties": {"pageObjectId": sid,
                                                       "size": {"width": {"magnitude": W, "unit": "EMU"},
                                                                "height": {"magnitude": H, "unit": "EMU"}},
                                                       "transform": {"scaleX": 1, "scaleY": 1, "translateX": 0,
                                                                     "translateY": 0, "unit": "EMU"}}}})
for s in old:
    reqs.append({"deleteObject": {"objectId": s.strip()}})
print(json.dumps(reqs, separators=(",", ":")))
