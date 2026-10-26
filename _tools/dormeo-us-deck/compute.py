#!/usr/bin/env python3
"""Work out every number for the Dormeo US weekly deck from the dashboard's data (Sellerise + sheet pages).
Usage: compute.py <dashboard tools dir> <out deck_data.json> [deck_config.json]
deck_config.json may list "eventDays" (YYYY-MM-DD) such as Prime Day; month pacing counts those days once
and paces the rest of the month on the average of the other days."""
import json, datetime as dt, sys, calendar
R = sys.argv[1].rstrip("/") + "/"
OUTP = sys.argv[2]
CFG = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}
L = lambda p: json.load(open(R + p))
G = L("data/groups.json"); S = L("data/sales.json"); P = L("data/pnl_ads.json"); C = L("data/camp_kw.json")
I = L("data/inv_weekly.json"); IS = L("data/inv_sheet.json"); REC = L("data/rec.json")
META = P["CAMP_META"]; ws = dt.date.fromisoformat(META["weekStart"]); we = ws + dt.timedelta(days=6)
prev_ws = ws - dt.timedelta(days=7)
cur, prv = META["cur"], META["prev"]
D = lambda s, y=2026: dt.date(y, *map(int, s.split("/")))
ads = [dict(d=D(r[0]), spend=r[1], adSales=r[2], orders=r[5], rev=r[6]) for r in P["ADS"]]
chg = lambda a, b: (a / b - 1) if b else None
MS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
fmtd = lambda d: f"{MS[d.month-1]} {d.day}"
WK0 = dt.date(2025, 12, 28); widx = lambda d: (d - WK0).days // 7
wnum = widx(ws) + 1

out = {"brand": "Dormeo US", "week": {"num": wnum, "start": str(ws), "end": str(we), "label": f"{fmtd(ws)}–{we.day if ws.month==we.month else fmtd(we)}, {we.year}",
       "prior": f"{fmtd(prev_ws)}–{(prev_ws+dt.timedelta(days=6)).day}"}, "dataThrough": str(ads[-1]["d"])}

# 1. week at a glance (Sellerise account totals for the two weeks)
roas = lambda m: m["adSales"] / m["spend"] if m["spend"] else None
conv = lambda m: m["adOrders"] / m["clicks"] if m["clicks"] else None
k = []
for key, label, kind, better in [("revenue","Revenue","usd","up"),("units","Units","num","up"),("orders","Orders","num","up"),("net","Net payout (before COGS)","usd","up"),
                                  ("spend","Ad spend","usd","down"),("adSales","Ad sales","usd","up"),("acos","ACoS","pct","down"),("tacos","TACoS","pct","down")]:
    a, b = cur[key], prv[key]
    k.append(dict(key=key, label=label, kind=kind, value=a, prev=b, change=(a - b) if kind == "pct" else chg(a, b), better=better))
out["kpis"] = k
out["kpiExtra"] = dict(roas=roas(cur), roasPrev=roas(prv), refunds=cur["refunds"], refundsPrev=prv["refunds"], refundRate=cur["refundRate"],
                       adShare=cur["adSales"] / cur["revenue"] if cur["revenue"] else None, margin=cur["margin"], marginPrev=prv["margin"])

# 2. the week by day
days = [a for a in ads if ws <= a["d"] <= we]
out["daily"] = [dict(day=a["d"].strftime("%a"), date=fmtd(a["d"]), rev=a["rev"], spend=a["spend"], adSales=a["adSales"], orders=a["orders"],
                     acos=a["spend"] / a["adSales"] if a["adSales"] else None) for a in days]

# 3. 8-week trend from the daily account series (complete Sun–Sat weeks only)
trend = []
s = ws - dt.timedelta(days=49)
while s <= ws:
    e = s + dt.timedelta(days=6); xs = [a for a in ads if s <= a["d"] <= e]
    if len(xs) == 7:
        rv, sp = sum(a["rev"] for a in xs), sum(a["spend"] for a in xs)
        trend.append(dict(label=f"Wk {widx(s)+1}", start=fmtd(s), rev=rv, spend=sp, tacos=sp / rv if rv else None))
    s += dt.timedelta(days=7)
out["trend"] = trend

# 4. product lines (weekly Sellerise sales by line)
i = widx(ws); lines = []
for gi, g in enumerate(G):
    a, b = I["WEEKLY"]["sales"][gi][i], I["WEEKLY"]["sales"][gi][i - 1]
    lines.append(dict(name=g["short"], rev=a, prev=b, change=chg(a, b), units=I["WEEKLY"]["units"][gi][i], unitsPrev=I["WEEKLY"]["units"][gi][i - 1]))
tot = sum(x["rev"] for x in lines)
for x in lines: x["share"] = x["rev"] / tot if tot else 0
out["lines"] = sorted(lines, key=lambda x: -x["rev"])

# 5. top products (ASIN level, Sellerise weekly pulls)
names = {k_["asin"]: k_["name"] for k_ in IS["skus"]}
wc = {r[0]: r for r in L(f"raw/week_{ws}.json")}; wp = {r[0]: r for r in L(f"raw/week_{prev_ws}.json")}
def short(n):
    n = n.replace("Ⓡ", "").replace("Dormeo ", "")
    for cut in (" - 3-Zone", " – ", " - ", " | ", ","): n = n.split(cut)[0]
    return n.replace("Cooling Mattress Topper", "Topper").replace("Mattress Topper", "Topper").strip()
prods = []
for asin, (_, rv, u) in wc.items():
    if rv <= 0: continue
    pr = wp.get(asin, [asin, 0, 0])[1]
    prods.append(dict(asin=asin, name=short(names.get(asin, asin)), rev=rv, units=u, prev=pr, change=chg(rv, pr)))
out["products"] = sorted(prods, key=lambda x: -x["rev"])[:8]

# 6. advertising by type and strategy, and campaign actions (same rules as the dashboard)
def grp(key):
    g_ = {}
    for c in C["CAMP"]:
        o = g_.setdefault(c[key], dict(s=0, r=0, o=0, ps=0, pr=0))
        o["s"] += c["s"]; o["r"] += c["r"]; o["o"] += c["o"]; o["ps"] += c["ps"]; o["pr"] += c["pr"]
    rows = [dict(name=(C["TYPE_LABEL"] if key == "type" else C["STRAT_LABEL"]).get(k_, k_), spend=v["s"], sales=v["r"], orders=v["o"],
                 acos=v["s"] / v["r"] if v["r"] else None, prevSpend=v["ps"], change=chg(v["s"], v["ps"])) for k_, v in g_.items() if v["s"] > 0]
    return sorted(rows, key=lambda x: -x["spend"])
out["adsByType"], out["adsByStrat"] = grp("type"), grp("strat")
live = [c for c in C["CAMP"] if c["s"] > 0]
li = lambda c: dict(name=c["label"], spend=c["s"], sales=c["r"], acos=c["s"] / c["r"] if c["r"] else None, orders=c["o"])
out["actions"] = dict(
    scale=[li(c) for c in sorted([c for c in live if c["r"] > 0 and c["s"] / c["r"] <= .25 and c["o"] >= 2], key=lambda c: -c["r"])][:5],
    fix=[li(c) for c in sorted([c for c in live if c["r"] > 0 and c["s"] / c["r"] > .40], key=lambda c: -c["s"])][:5],
    cut=[li(c) for c in sorted([c for c in live if c["r"] <= 0], key=lambda c: -c["s"])][:5])
out["actionsTotals"] = dict(scaleN=len([c for c in live if c["r"] > 0 and c["s"] / c["r"] <= .25 and c["o"] >= 2]),
                            fixN=len([c for c in live if c["r"] > 0 and c["s"] / c["r"] > .40]),
                            cutN=len([c for c in live if c["r"] <= 0]), cutSpend=sum(c["s"] for c in live if c["r"] <= 0), campaigns=len(live))

# 7. keywords for the week
kw = next(x for x in C["KW"] if x["s"] == str(ws))
rows = sorted(kw["rows"], key=lambda r: -r[5])[:10]
out["keywords"] = [dict(kw=r[0], match=r[1], type=r[2], spend=r[5], sales=r[6], roas=r[6] / r[5] if r[5] else None, orders=r[8], sv=r[12], branded=bool(r[4])) for r in rows]
out["kwTotals"] = kw["tot"]

# 8. month pacing (event days such as Prime Day counted once, the rest paced on the normal-day average)
last = ads[-1]["d"]; m0 = last.replace(day=1)
ev = {dt.date.fromisoformat(x) for x in CFG.get("eventDays", [])}
md = [a for a in ads if a["d"] >= m0]; prime = [a for a in md if a["d"] in ev]; norm = [a for a in md if a["d"] not in ev]
dim = calendar.monthrange(last.year, last.month)[1]; avg = sum(a["rev"] for a in norm) / len(norm) if norm else 0
fc = sum(a["rev"] for a in md) + avg * (dim - last.day)
LONG = ["January","February","March","April","May","June","July","August","September","October","November","December"]
out["pacing"] = dict(monthLong=LONG[last.month - 1], month=MS[last.month - 1], through=fmtd(last), day=last.day, dim=dim, mtd=sum(a["rev"] for a in md), primeRev=sum(a["rev"] for a in prime),
                     avg=avg, forecast=fc, prevMonth=P["PL"]["gross"][-1], prevMonthName=MS[len(P["PL"]["gross"]) - 1], lastYear=S["a25"][last.month - 1],
                     spendMtd=sum(a["spend"] for a in md), eventDays=[str(a["d"]) for a in prime])

# 9. inventory (sheet: FSG Weekly Inventory Update)
inv = []
for g in G:
    a = IS["groups"][g["key"]]; wa = a["wkAvg"]
    inv.append(dict(name=g["short"], total=a["total"], avail=a["avail"], inbound=a["inbound"], wkAvg=wa,
                    weeksAvail=a["avail"] / wa if wa else None, weeksTotal=a["total"] / wa if wa else None))
out["inventory"] = dict(asOf=IS["asOf"], week=IS["week"], rows=inv, total=sum(x["total"] for x in inv), avail=sum(x["avail"] for x in inv), inbound=sum(x["inbound"] for x in inv))
out["restock"] = [dict(name=short(k_["name"]), asin=k_["asin"], avail=k_["avail"], inbound=k_["inbound"], l30=k_["l30"], wkLeft=k_["wkLeft"])
                  for k_ in IS["skus"] if k_["l30"] >= 5 and (k_["avail"] <= 0 or k_["wkLeft"] <= 2)]

# 10. reconciliation (sheet: Reconciliation Update)
out["rec"] = {k_: REC[k_] for k_ in ("asOf", "ytd", "units", "mtd", "mtdUnits", "shipments", "receiving", "closed", "missing", "receiveRate", "recoveryRate", "resolved")}
out["rec"]["monthly"] = REC["monthly"]; out["rec"]["topTypes"] = [t for t in REC["byType"] if t[1]][:4]
out["rec"]["openCases"] = sum(1 for c in REC["cases"] if c["status"] not in ("Reimbursed", "Reconciled"))

json.dump(out, open(OUTP, "w"), indent=1, ensure_ascii=False, default=str)
print(json.dumps({k_: out[k_] for k_ in ("week", "dataThrough")}), "| products", len(out["products"]), "| restock", len(out["restock"]), "| trend", len(out["trend"]))
for x in out["kpis"]: print(f"  {x['label']:<26} {x['value']:>12} prev {x['prev']:>12} chg {x['change']}")
print("pacing", {k_: round(v) if isinstance(v, float) else v for k_, v in out["pacing"].items()})
