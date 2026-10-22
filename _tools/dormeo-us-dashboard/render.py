#!/usr/bin/env python3
"""Fill the Dormeo US dashboard template with the latest data.
Usage: render.py <template.html> <data_dir> <out.html>
Data files (see RUNBOOK.md): groups, sales, pnl_ads, camp_kw, inv_weekly, inv_sheet, rec, tasks (.json)."""
import datetime as dt, json, re, sys

TPL, D, OUT = sys.argv[1], sys.argv[2].rstrip("/") + "/", sys.argv[3]
L = lambda n: json.load(open(D + n + ".json", encoding="utf8"))
G, S, P, C, I, IS, REC, T = (L(n) for n in ("groups", "sales", "pnl_ads", "camp_kw", "inv_weekly", "inv_sheet", "rec", "tasks"))
J = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))
MS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ML = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
YEAR = int(P.get("year", 2026))

# ---- as-of date = last day in the daily series ----
m, d = map(int, P["ADS"][-1][0].split("/"))
asof = dt.date(YEAR, m, d)
fmt = lambda x: f"{MS[x.month-1]} {x.day}, {x.year}"
m0, d0 = map(int, P["ADS"][0][0].split("/"))
first = dt.date(YEAR if m0 <= m else YEAR - 1, m0, d0)

# ---- products (8 lines) ----
gmap = {g["key"]: g for g in G}
prods = []
for p in S["PRODUCTS"]:
    g = gmap[p["key"]]; n = len(g["asins"])
    prods.append({"asin": g["asins"][0], "name": g["name"], "short": g["short"], "col": g["col"],
                  "sales": p["sales"], "units": p["units"], "sessions": p["sessions"],
                  "adSpend": p["adSpend"], "adSales": p["adSales"], **({"sub": f"{n} ASINs in this line"} if n > 1 else {})})
NMS = len(prods[0]["sales"]); cur = NMS - 1

# ---- inventory: sheet position + Sellerise weekly units ----
po_by_group = {}
for row in IS.get("po", []):
    a_ = re.search(r"ASIN: (\w+)", row[0] or "")
    k = next((g["key"] for g in G if a_ and a_.group(1) in g["asins"]), None)
    try: q = int(float(re.sub(r"[^\d.]", "", row[-1]) or 0))
    except ValueError: q = 0
    if k: po_by_group[k] = po_by_group.get(k, 0) + q
for r in I["INV"]["rows"]:
    a = IS["groups"][r["key"]]
    tot, av, inb, wa = int(a["total"]), int(a["avail"]), int(a["inbound"]), int(round(a["wkAvg"]))
    pw = max(1, round(wa * 1.2)); ts = po_by_group.get(r["key"], 0)
    r.update(toShip=ts, atFba=tot, avail=av, inbound=inb, fc=0, reserve=max(0, tot - av - inb), wkAvg=wa, l30=int(a["l30"]),
             projWk=pw, need30=round(pw * 30 / 7), minReq=pw * 3, wkLeftFba=av // pw, wkLeftAll=(tot + ts) // pw)
I["INV"]["asOf"] = IS["asOf"]
lw = I["INV"]["lastWeek"]

# ---- tasks: static list + restock tasks rebuilt from the latest inventory sheet ----
short = lambda nm: re.split(r" - | – |, ", nm)[0].replace("Ⓡ", "").strip()
tasks = [t for t in T["TASKS"] if not (t["cat"] == "Inventory" and (t["task"].startswith("Restock") or "low FBA stock" in t["task"]))]
for k in IS["skus"]:
    if k["l30"] >= 5 and k["avail"] <= 0:
        tasks.append({"src": "Inventory Tracker", "cat": "Inventory", "task": f"Restock {short(k['name'])} ({k['asin']})",
                      "desc": f"0 units available at FBA, {int(k['inbound'])} inbound, {int(k['l30'])} sold in the last 30 days (Week {IS['week']} inventory update).",
                      "status": "Not Started", "owners": []})
    elif k["l30"] >= 5 and k["wkLeft"] <= 2:
        tasks.append({"src": "Inventory Tracker", "cat": "Inventory", "task": f"{short(k['name'])} ({k['asin']}): low FBA stock",
                      "desc": f"{int(k['avail'])} available, about {int(k['wkLeft'])} week(s) left at {int(k['wkAvg'])}/week; {int(k['inbound'])} inbound.",
                      "status": "Not Started", "owners": []})
owners = [o for o in T["OWNERS"] if any(o in t["owners"] for t in tasks)]

# ---- conversion notes ----
U = [sum(p["units"][i] for p in prods) for i in range(NMS)]; SE = [sum(p["sessions"][i] for p in prods) for i in range(NMS)]
cv = [U[i] / SE[i] if SE[i] else 0 for i in range(NMS)]
best = max(range(NMS), key=lambda i: cv[i])
pq = prods[0]; pqc = pq["units"][cur] / pq["sessions"][cur] if pq["sessions"][cur] else 0
qa = IS["groups"]["pq"]
avail_clause = f", with 0 units available at FBA and {int(qa['inbound'])} inbound, so its sessions are converting on limited availability" if qa["avail"] <= 0 else ""
notes = (f"• {ML[cur]} month to date converts at {cv[cur]*100:.1f}% across all products, against {cv[cur-1]*100:.1f}% in {ML[cur-1]}. "
         f"The best month this year is {MS[best]} at {cv[best]*100:.1f}%.\n"
         f"• Octaspring Queen, the biggest line, is converting at {pqc*100:.1f}% this month{avail_clause}.\n"
         f"• Pillows and Protectors & Sheets run on small session counts; read their rates with care.")
if asof < dt.date(YEAR, 11, 27):
    notes += "\n• Next: BF/CM runs Nov 27–30; keep the top lines in stock so holiday traffic converts."

# ---- inventory notes ----
ig = sorted(IS["groups"].items(), key=lambda kv: -kv[1]["inbound"])
lead = [f"{gmap[k]['short']} ({int(a['inbound'])} inbound, {int(a['avail'])} available)" for k, a in ig[:3] if a["inbound"] > 0]
tot_in = int(sum(a["inbound"] for a in IS["groups"].values()))
if IS.get("po"):
    po_note = f"To ship comes from the Week {IS['week']} PO replenishment table."
    po_panel = f"The Week {IS['week']} PO replenishment table lists {sum(po_by_group.values())} units ready to ship. Inbound to FBA right now: {tot_in} units" + (f", led by {', '.join(lead)}." if lead else ".")
else:
    po_note = f"The Week {IS['week']} PO replenishment table lists no warehouse units, so To ship is 0."
    po_panel = f"The Week {IS['week']} inventory update ({IS['asOf']}) has an empty PO replenishment table, and the Master Spec Sheet doesn’t list a PO number or ETA. Inbound to FBA right now: {tot_in} units" + (f", led by {', '.join(lead)}." if lead else ".")

# ---- weekly label ----
nW = len(I["WEEKLY"]["sales"][0])
ws = dt.date(2025, 12, 28) + dt.timedelta(days=7 * (nW - 1)); we = min(ws + dt.timedelta(days=6), asof)
wk_last = f"{MS[ws.month-1]} {ws.day}–{we.day if ws.month == we.month else MS[we.month-1] + ' ' + str(we.day)}" + (" (partial)" if we < ws + dt.timedelta(days=6) else "")

tok = {
    "TASKS": J(tasks), "OWNERS": J(owners), "CAMPAIGNS": J(T["CAMPAIGNS"]), "PL": J(P["PL"]), "PRODUCTS": J(prods),
    "S25": J(S["S25"]), "SQP": J(C["SQP"]), "ADS": J(P["ADS"]), "CAMP_META": J(P["CAMP_META"]), "CAMP": J(C["CAMP"]),
    "TYPE_LABEL": J(C["TYPE_LABEL"]), "STRAT_LABEL": J(C["STRAT_LABEL"]), "INV": J(I["INV"]),
    "FC": J({"a25": S["a25"], "plan26": S["a25"], "act26": S["act26"], "sku25": S["sku25"]}),
    "KW": J(C["KW"]), "KW_FLAG": J(C["KW_FLAG"]), "WEEKLY": J(I["WEEKLY"]), "CVR_NOTES": J(notes), "REC": J(REC),
    "ASOF": fmt(asof), "SNAPSHOT_TS": f"Date.UTC({asof.year},{asof.month-1},{asof.day},20,0)", "TEAM": T["TEAM"],
    "PL_RANGE": f"January–{ML[len(P['PL']['gross'])-1]} {YEAR}; the current month is paced above",
    "MTD_NOTE": f"{ML[cur]} is month to date ({MS[cur]} 1–{asof.day}).", "MTD_MONTH": ML[cur],
    "MTD_NOTE_SHORT": f"is month to date ({MS[cur]} 1–{asof.day}).", "YTD_RANGE": f"Jan–{MS[cur]}",
    "WK_LAST": wk_last, "ADS_RANGE": f"{MS[first.month-1]} {first.day} – {fmt(asof)}",
    "CAMP_WEEK": P["CAMP_META"]["week"], "CAMP_PRIOR": P["CAMP_META"]["prior"], "CAMP_N": str(len(C["CAMP"])),
    "INV_WEEK": str(IS["week"]), "INV_DATE": IS["asOf"], "INV_SKUS": str(len(IS["skus"])), "INV_WKS": f"{lw-3}–{lw}",
    "PO_NOTE": po_note, "PO_PANEL": po_panel,
}
html = open(TPL, encoding="utf8").read()
for k, v in tok.items(): html = html.replace("{{" + k + "}}", v)
left = re.findall(r"\{\{[A-Z_0-9]+\}\}", html)
if left: raise SystemExit("unfilled placeholders: " + ", ".join(sorted(set(left))))
open(OUT, "w", encoding="utf8").write(html)
print("rendered", OUT, "as of", fmt(asof), "| inventory wk", IS["week"], IS["asOf"], "| rec", REC["asOf"], "| tasks", len(tasks))
