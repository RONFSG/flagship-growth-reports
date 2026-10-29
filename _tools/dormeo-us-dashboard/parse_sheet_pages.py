#!/usr/bin/env python3
"""Read the FSG Combined Report pages (built from the Dormeo US sheet's Inventory Tracker and
Reconciliation Update tabs) and write data/inv_sheet.json and data/rec.json.
Usage: parse_sheet_pages.py <repo_dir> <data_dir>"""
import html, json, os, re, sys

REPO, OUT = sys.argv[1], sys.argv[2]
# DECK_BRAND=<folder with brand.json> reads another brand's pages; unset = Dormeo US.
B = json.load(open(os.path.join(os.environ["DECK_BRAND"], "brand.json"))) if os.environ.get("DECK_BRAND") else {}
NAME, INV, REC = B.get("sheetName", "Dormeo US"), B.get("invPage", "dormeo-us-inventory"), B.get("recPage", "dormeo-us-reconciliation")
txt = lambda c: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
num = lambda x: 0.0 if x.strip() in ("—", "", "-") else float(re.sub(r"[^\d.\-]", "", x) or 0)
rows_of = lambda t: [[txt(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S)] for r in re.findall(r"<tr.*?</tr>", t, re.S)]

# ---------- inventory (Inventory Tracker tab) ----------
G = json.load(open(OUT + "/groups.json"))
IS_DORMEO = B.get("account", "Dormeo") == "Dormeo"; OTHER = B.get("otherKey", "pr")
amap = {a: g["key"] for g in G for a in g["asins"]}
# ASINs the sheet carries that are inactive in Sellerise, mapped by product name (brand.json asinGroups; Dormeo's built in)
amap.update(B.get("asinGroups", {"B09JQWSHQR": "ps", "B0DK9Z7CYB": "fm", "B0DK9ZZWGP": "fm", "B0DK7DVX2V": "fm",
             "B0DK7DT4SL": "fm", "B09HQXHNZC": "pl", "B0F74RSY4V": "pr"} if IS_DORMEO else {}))
inv_path = REPO + f"/{INV}/index.html" if INV else ""
s = open(inv_path, encoding="utf8").read() if inv_path and os.path.exists(inv_path) else ""   # no inventory page: empty
if s and "Available FBA" not in s: s = ""
plain = txt(s)
m = re.search(re.escape(NAME) + r" · (\d{1,2}/\d{1,2}/\d{4}) · Week (\d+)", plain)
asof, week = (m.group(1), int(m.group(2))) if m else ("", 0)
inv_tbl = next((t for t in re.findall(r"<table.*?</table>", s, re.S) if "Available FBA" in t), "")
agg = {g["key"]: dict(total=0, avail=0, inbound=0, wkAvg=0, l30=0, n=0, asins=[]) for g in G}
unmapped, skus = [], []
for c in rows_of(inv_tbl)[1:]:
    a_ = re.search(r"ASIN: (\w+)", c[0])
    if not a_: continue
    asin = a_.group(1); k = amap.get(asin)
    sku = (re.search(r"SKU: ([^|]+)$", c[0]) or [None, ""])[1].strip()
    skus.append(dict(asin=asin, sku=sku, name=c[0].split(" ASIN:")[0].strip(), status=c[1], total=num(c[3]),
                     avail=num(c[4]), inbound=num(c[5]), wkAvg=num(c[6]), l30=num(c[7]), wkLeft=num(c[8])))
    if not k: unmapped.append(asin); k = OTHER
    g = agg[k]
    for f, i in (("total", 3), ("avail", 4), ("inbound", 5), ("wkAvg", 6), ("l30", 7)): g[f] += num(c[i])
    g["n"] += 1; g["asins"].append(asin)
po_tbl = next((t for t in re.findall(r"<table.*?</table>", s, re.S) if "Warehouse Status" in t), "")
po = [c for c in rows_of(po_tbl)[1:] if len(c) >= 3]
json.dump({"asOf": asof, "week": week, "groups": agg, "skus": skus, "po": po, "unmapped": unmapped},
          open(OUT + "/inv_sheet.json", "w"), indent=1)

# ---------- reconciliation (Reconciliation Update tab) ----------
rec_path = REPO + f"/{REC}/index.html" if REC else ""
s = open(rec_path, encoding="utf8").read() if rec_path and os.path.exists(rec_path) else ""   # no reconciliation page: zeros
plain = txt(re.sub(r"<script.*?</script>|<style.*?</style>", "", s, flags=re.S))
g1 = lambda pat, d=None: (re.search(pat, plain) or [None, d])[1]
rec = {
    "asOf": g1(r"FBA Operations · ([A-Z][a-z]{2} \d{1,2}, \d{4})", ""),
    "ytd": num(g1(r"\$([\d,\.]+) YTD Reimbursements", "0")),
    "units": int(num(g1(r"([\d,]+) units reimbursed", "0"))),
    "shipments": int(num(g1(r"([\d,]+) Total Shipments", "0"))),
    "receiving": int(num(g1(r"(\d+) receiving", "0"))), "closed": int(num(g1(r"(\d+) closed", "0"))),
    "missing": int(num(g1(r"Missing ([\d,]+)", "0"))),
    "receiveRate": num(g1(r"Shipment Receiving Rate .*? ([\d\.]+)% Target", "0")),
    "recoveryRate": num(g1(r"Recovery Rate .*? ([\d\.]+)% Target", "0")),
    "resolved": int(num(g1(r"Target 100% (\d+) resolved", "0"))),
}
mtd = re.search(r"mtd:([\d\.]+)", s); umtd = re.search(r"uvals=\{ytd:\d+,mtd:(\d+)", s)
rec["mtd"] = round(float(mtd.group(1)), 2) if mtd else None
rec["mtdUnits"] = int(umtd.group(1)) if umtd else None
mon = re.search(r"Value recovered per period \(YTD\) Monthly Weekly (.*?) W1 ", plain)
rec["monthly"] = [[mm, num(v)] for v, mm in re.findall(r"\$([\d,]+) ([A-Z][a-z]{2})", mon.group(1))] if mon else []
ct = re.search(r"Value recovered by type (.*?) Case Resolution Detail", plain)
rec["byType"] = [[t_.strip(), None if v == "—" else num(v)] for t_, v in re.findall(r"([A-Za-z_ ]+?) (\$[\d,\.]+|—)", ct.group(1))] if ct else []
case_tbl = next((t for t in re.findall(r"<table.*?</table>", s, re.S) if "Case ID" in t), "")
rec["cases"] = [dict(id=c[0], date=c[1], type=c[2], note=c[3], status=c[4], units=int(num(c[5])), value=num(c[6]))
                for c in rows_of(case_tbl)[1:] if len(c) >= 7]
json.dump(rec, open(OUT + "/rec.json", "w"), indent=1, ensure_ascii=False)
print("inventory", asof, "wk", week, "skus", len(skus), "unmapped", unmapped, "po rows", len(po))
print("rec", {k: v for k, v in rec.items() if k not in ("cases", "monthly", "byType")}, "cases", len(rec["cases"]),
      "months", len(rec["monthly"]), "types", len(rec["byType"]))
