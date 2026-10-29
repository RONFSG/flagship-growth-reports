#!/usr/bin/env python3
"""The deck's own weekly data, on Monday–Sunday weeks (the dashboards keep their own Sunday–Saturday weeks).

Files live in <deck folder>/wk/ (the folder that holds deck_config.json: _tools/dormeo-us-deck for Dormeo US,
_tools/dormeo-canada-deck for Canada). Run from _tools/dormeo-us-deck, with DECK_BRAND set for brands other than Dormeo US.

  deck_week.py plan [YYYY-MM-DD]       the Sellerise calls for the last complete Mon–Sun week and the one before
                                       (date = run day; default today in America/Los_Angeles)
  deck_week.py save <kind> <monday> <raw.json>
        kind = meta  get_account_metrics groupBy none, the totalsByCurrency[0].metrics object
               week  get_products: [[asin, revenue, units], ...] from salesProfitSummaryByAsin
               camp  get_ppc_efficiency, every page: {"names": {campaignId: name}, "rows": [[campaignId, type, spend, sales, impressions, clicks, orders], ...]}
               kw    get_ads_targeting_insights top_spend SP,SB: {"tot": {...}, "R": [[adProduct, keyword, match, spend, sales, clicks, orders, impressions, units, topOfSearchPct], ...]}
  deck_week.py build <monday>          writes wk/deckweek.json, which compute.py uses for the week's KPIs, product lines,
                                       products, campaigns and keywords
"""
import datetime as dt, json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DK = os.path.abspath(os.environ["DECK_BRAND"]) if os.environ.get("DECK_BRAND") else HERE
WK = os.path.join(DK, "wk"); os.makedirs(WK, exist_ok=True)
sys.path.insert(0, os.path.join(HERE, "..", "dormeo-us-dashboard"))
import update_data as U   # campaign naming rules, product groups and metric mapping (same as the dashboard)

D = dt.date.fromisoformat
f = lambda kind, mon: os.path.join(WK, f"{kind}_{mon}.json")


def last_monday(run_day):
    sun = run_day - dt.timedelta(days=(run_day.weekday() + 1) % 7 or 7)   # most recent complete Sunday before run day
    return sun - dt.timedelta(days=6)


def plan(run_day):
    mon = last_monday(run_day); prev = mon - dt.timedelta(days=7)
    base = {"accountSearch": U.BRAND.get("account", "Dormeo"), "marketplaces": U.BRAND.get("marketplace", "US")}
    am = {**base, "targetCurrency": U.BRAND["currency"]} if U.BRAND.get("currency") else base
    calls = []
    for m in (mon - dt.timedelta(days=21), mon - dt.timedelta(days=14)):   # the 4-week table's older weeks: usually saved already
        e = str(m + dt.timedelta(days=6)); m = str(m)
        if not os.path.exists(f("meta", m)): calls.append({"save_with": f"save meta {m} <raw>", "tool": "get_account_metrics", "args": {**am, "groupBy": "none", "start": m, "end": e}})
    for m in (prev, mon):
        e = str(m + dt.timedelta(days=6)); m = str(m)
        if not os.path.exists(f("meta", m)): calls.append({"save_with": f"save meta {m} <raw>", "tool": "get_account_metrics", "args": {**am, "groupBy": "none", "start": m, "end": e}})
        if not os.path.exists(f("week", m)): calls.append({"save_with": f"save week {m} <raw>", "tool": "get_products", "args": {**base, "start": m, "end": e, "limit": 60, "activeOnly": False, "mode": "top", "metric": "revenue"}})
        if not os.path.exists(f("camp", m)): calls.append({"save_with": f"save camp {m} <raw>", "tool": "get_ppc_efficiency", "args": {**base, "start": m, "end": e, "mode": "top_spend", "minSpend": 0.01, "minClicks": 0, "limit": 100, "note": "page with offset until hasMore is false"}})
    e = str(mon + dt.timedelta(days=6))
    calls.append({"save_with": f"save kw {mon} <raw>", "tool": "get_ads_targeting_insights", "args": {**base, "start": str(mon), "end": e, "mode": "top_spend", "adProducts": "SP,SB", "limit": 25, "note": "keyword targets only; skip ASIN/product targets"}})
    print(json.dumps({"week": f"{mon}..{e}", "prior": f"{prev}..{prev + dt.timedelta(days=6)}", "then": f"build {mon}", "calls": calls}, indent=1))


def save(kind, mon, path):
    D(mon)
    if kind == "meta":
        o = json.load(open(path)); m = U.map_metrics(o) if "revenue" in o and "ppc" in o else o
        if "refundAmount" in o: m["refundUnits"] = int(o["refundAmount"] or 0)   # Sellerise's refundAmount = refunded units
        json.dump(m, open(f(kind, mon), "w"), indent=1)
    else:
        if os.path.abspath(path) != f(kind, mon): shutil.copy(path, f(kind, mon))
    print(kind, mon, "saved")


def camp(mon):
    o = json.load(open(f("camp", mon))); out = {}
    for cid, typ, s, r, im, c, od in o["rows"]:
        d = out.setdefault(str(cid), {"t": U.TYPE.get(str(typ).lower(), str(typ).upper()), "s": 0, "r": 0, "i": 0, "c": 0, "o": 0})
        d["s"] += s or 0; d["r"] += r or 0; d["i"] += im or 0; d["c"] += c or 0; d["o"] += od or 0
    return out, {str(k): v for k, v in o["names"].items()}


def build(mon):
    prev = str(D(mon) - dt.timedelta(days=7)); r2 = U.r2
    cur, n1 = camp(mon); prv, n2 = camp(prev); N = {**n2, **n1}; CAMP = []
    for cid in set(cur) | set(prv):
        n = N.get(cid, cid); c = cur.get(cid, {}); p = prv.get(cid, {}); typ = (c or p)["t"]
        st, pr = U.strat(n), U.prodname(n)
        CAMP.append(dict(id=cid, name=n.strip(), label=f"{pr.replace('Octaspring ', '')} · {st} · {U.match(n, typ)}", type=typ, strat=st, prod=pr,
                         s=r2(c.get("s")), r=r2(c.get("r")), i=int(c.get("i", 0)), c=int(c.get("c", 0)), o=int(c.get("o", 0)),
                         ps=r2(p.get("s")), pr=r2(p.get("r")), pc=int(p.get("c", 0)), pi=int(p.get("i", 0))))
    x = json.load(open(f("kw", mon))); g = {}
    for ap, kw, mt, sp, sa, cl, o, im, u, tos in x["R"]:
        d = g.setdefault((kw, mt.title()), dict(t=set(), n=0, sp=0, sa=0, cl=0, o=0, u=0, im=0, tw=0))
        d["t"].add(ap); d["n"] += 1; d["sp"] += sp; d["sa"] += sa; d["cl"] += cl; d["o"] += o; d["u"] += u; d["im"] += im; d["tw"] += (tos or 0) * im
    rows = [[kw, mt, "/".join(sorted(d["t"], reverse=True)), d["n"], 1 if U.isB(kw) else 0, r2(d["sp"]), r2(d["sa"]), d["cl"], d["o"], d["u"], d["im"],
             round(d["tw"] / d["im"], 1) if d["im"] else None, None] for (kw, mt), d in g.items()]
    out = {"weekStart": mon, "cur": json.load(open(f("meta", mon))), "prev": json.load(open(f("meta", prev))),
           "CAMP": sorted(CAMP, key=lambda r: -r["s"]), "STRAT_LABEL": U.STRAT_LABEL, "TYPE_LABEL": U.TYPE_LABEL,
           "KW": {"s": mon, "e": str(D(mon) + dt.timedelta(days=6)), "tot": x["tot"], "rows": rows},
           "weekCur": json.load(open(f("week", mon))), "weekPrev": json.load(open(f("week", prev))),
           "groupOf": {a: U.gk(a) for a in {r[0] for r in json.load(open(f("week", mon))) + json.load(open(f("week", prev)))}}}
    json.dump(out, open(os.path.join(WK, "deckweek.json"), "w"), indent=1, ensure_ascii=False)
    print("deckweek", mon, "| campaigns", len(CAMP), "| keywords", len(rows), "| revenue", out["cur"]["revenue"], "vs", out["prev"]["revenue"])


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(1)
    if a[0] == "plan":
        if len(a) > 1: day = D(a[1])
        else:
            import zoneinfo; day = dt.datetime.now(zoneinfo.ZoneInfo("America/Los_Angeles")).date()
        plan(day)
    elif a[0] == "save": save(a[1], a[2], a[3])
    elif a[0] == "build": build(a[1])
    else: print(__doc__); sys.exit(1)
