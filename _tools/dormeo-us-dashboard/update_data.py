#!/usr/bin/env python3
"""Dormeo US dashboard data updater. State lives in data/*.json; every Sellerise pull is archived in raw/.
Commands (run from this folder):
  plan [YYYY-MM-DD]          print today's pull list (date = run day in America/Los_Angeles; default today PT)
  ads    <raw.json>          daily account rows   [[yyyymmdd, revenue, ppcSpend, ppcSales, ppcOrders], ...]
  month  <MM> <raw.json>     products for a month [[asin, revenue, units, sessions, ppcSpend, ppcSales], ...]
  pl     <MM> <raw.json>     account totals for a completed month (the totalsByCurrency[0].metrics object)
  week   <YYYY-MM-DD> <raw>  products for a Sun–Sat week starting that Sunday [[asin, revenue, units], ...]
  meta   <YYYY-MM-DD> <raw>  account totals for that week (totalsByCurrency[0].metrics object)
  camp   <YYYY-MM-DD> <raw>  {"names":{id:name}, "rows":[[id, type, spend, sales, impressions, clicks, orders], ...]}
  kw     <YYYY-MM-DD> <raw>  {"tot":{spend,sales,orders,clicks,impressions}, "R":[[adProduct, keyword, match, spend, sales, clicks, orders, impressions, units, topOfSearchPct], ...]}
  sqp    <YYYY-MM-DD> <raw>  week ENDING that Saturday: [[query, queryVolume, totalImpr, asinImpr, totalPurchases, asinPurchases], ...]
  ly     <raw.json>          last year's revenue by month: [[month 1-12, revenue], ...] (get_account_metrics groupBy month)
  finalize                   rebuild campaigns, keywords, SQP, meta and inventory weeks from raw/
"""
import datetime as dt, json, os, re, shutil, sys

# Brand: DECK_BRAND=<folder with brand.json> runs this for another brand (data/ and raw/ live in that folder).
# Unset = Dormeo US (this folder), exactly as before.
_BD = os.environ.get("DECK_BRAND")
BRAND = json.load(open(os.path.join(_BD, "brand.json"))) if _BD else {}

HERE = os.path.abspath(_BD) if _BD else os.path.dirname(os.path.abspath(__file__)); DD = os.path.join(HERE, "data"); RAW = os.path.join(HERE, "raw")
os.makedirs(RAW, exist_ok=True)
ld = lambda n: json.load(open(os.path.join(DD, n + ".json"), encoding="utf8"))
def sv(n, o): json.dump(o, open(os.path.join(DD, n + ".json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
# Brand rules. Dormeo (US and Canada) keeps its original hard-coded rules; every other brand gives its own in
# brand.json: brandTerms (words that make a search "branded"), competitors, asinGroups / asinShort (extra ASIN
# mappings), otherKey (the group unknown ASINs fall into, default "pr").
IS_DORMEO = BRAND.get("account", "Dormeo") == "Dormeo"
OTHER = BRAND.get("otherKey", "pr")
G = ld("groups"); KEYS = [g["key"] for g in G]
A2K = {a: g["key"] for g in G for a in g["asins"]}
A2K.update(BRAND.get("asinGroups", {"B09JQWSHQR": "ps", "B0DK9Z7CYB": "fm", "B0DK9ZZWGP": "fm", "B0DK7DVX2V": "fm", "B0DK7DT4SL": "fm",
            "B09HQXHNZC": "pl", "B0F74RSY4V": "pr"} if IS_DORMEO else {}))
gk = lambda asin: A2K.get(asin, OTHER)
A2SHORT = {a: next(g["short"] for g in G if g["key"] == k) for a, k in A2K.items() if any(g["key"] == k for g in G)}
A2SHORT.update(BRAND.get("asinShort", {"B0GHSZ6WJY": "SnowTek & Essentials", "B0DKSLHMV8": "SnowTek & Essentials", "B0DP9W8MVT": "Protectors & Sheets", "B0F7Y8F7QP": "Protectors & Sheets"} if IS_DORMEO else {}))
WK0 = dt.date(2025, 12, 28)                        # week index 0 = Jan 1–3 2026 (week starting Dec 28)
D = lambda s: dt.date.fromisoformat(s)
widx = lambda sun: (sun - WK0).days // 7
MS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
r2 = lambda x: round(float(x or 0), 2)

def archive(kind, key, path):
    dst = os.path.join(RAW, f"{kind}_{key}.json")
    if os.path.abspath(path) != dst: shutil.copy(path, dst)
    return json.load(open(dst, encoding="utf8"))

def map_metrics(m):
    p = m.get("ppc", {})
    return dict(revenue=r2(m["revenue"]), orders=int(m.get("orders", 0)), units=int(m.get("units", 0)), net=r2(m.get("net")),
                margin=r2(m.get("margin")), refunds=r2(m.get("refunds")), refundRate=r2(m.get("refundRate")), promos=r2(m.get("promos")),
                coupons=int(m.get("couponsAmount", 0)), promo=int(m.get("promoAmount", 0)), sns=int(m.get("subAmount", 0)),
                spend=r2(p.get("spend")), adSales=r2(p.get("sales")), acos=r2(p.get("acos")), tacos=r2(p.get("tacos")),
                clicks=int(p.get("clicks", 0)), impr=int(p.get("impressions", 0)), adOrders=int(p.get("orders", 0)), cpc=r2(p.get("cpc")))

def wk_label(sun):
    sat = sun + dt.timedelta(days=6)
    return f"{MS[sun.month-1]} {sun.day}–{sat.day if sat.month == sun.month else MS[sat.month-1] + ' ' + str(sat.day)}"

def last_sat(y): return y - dt.timedelta(days=(y.weekday() - 5) % 7)

# ---------------------------------------------------------------- plan
def plan(run_day):
    y = run_day - dt.timedelta(days=1)                        # last complete day
    P = ld("pnl_ads"); S = ld("sales")
    out = {"run_day": str(run_day), "data_through": str(y), "calls": []}
    add = lambda cmd, tool, args: out["calls"].append({"save_with": cmd, "tool": tool, "args": args})
    base = {"accountSearch": BRAND.get("account", "Dormeo"), "marketplaces": BRAND.get("marketplace", "US")}
    # get_account_metrics converts to USD unless told otherwise; other brands keep their own currency (e.g. CAD)
    am = {**base, "targetCurrency": BRAND["currency"]} if BRAND.get("currency") else base
    add("ads <raw>", "get_account_metrics", {**am, "groupBy": "day", "start": str(y - dt.timedelta(days=59)), "end": str(y)})
    months = {y.month} | ({y.month - 1} if y.day <= 7 and y.month > 1 else set())   # previous month only while it may still settle
    for mo in sorted(months):
        ms = dt.date(2026, mo, 1); me = min(y, (ms + dt.timedelta(days=32)).replace(day=1) - dt.timedelta(days=1))
        add(f"month {mo:02d} <raw>", "get_products", {**base, "start": str(ms), "end": str(me), "limit": 60, "activeOnly": False, "mode": "top", "metric": "revenue"})
    have = len(P["PL"]["gross"])
    need = list(range(have + 1, y.month))                     # completed months missing from the P&L (1-based)
    if y.day <= 7 and y.month > 1 and (y.month - 1) not in need: need.append(y.month - 1)   # late adjustments
    for mo in need:
        ms = dt.date(2026, mo, 1); me = (ms + dt.timedelta(days=32)).replace(day=1) - dt.timedelta(days=1)
        add(f"pl {mo:02d} <raw>", "get_account_metrics", {**am, "groupBy": "none", "start": str(ms), "end": str(me)})
    cur_sun = y - dt.timedelta(days=(y.weekday() + 1) % 7)
    for sun in (cur_sun - dt.timedelta(days=7), cur_sun):
        add(f"week {sun} <raw>", "get_products", {**base, "start": str(sun), "end": str(min(y, sun + dt.timedelta(days=6))), "limit": 60, "activeOnly": False, "mode": "top", "metric": "revenue"})
    sat = last_sat(y); L = sat - dt.timedelta(days=6)
    if P["CAMP_META"].get("weekStart") != str(L):
        out["weekly_refresh"] = f"new complete week {L}..{sat}"
        for sun in (L - dt.timedelta(days=7), L):
            e = sun + dt.timedelta(days=6)
            if not os.path.exists(os.path.join(RAW, f"camp_{sun}.json")):
                add(f"camp {sun} <raw>", "get_ppc_efficiency", {**base, "start": str(sun), "end": str(e), "mode": "top_spend", "minSpend": 0.01, "minClicks": 0, "limit": 100, "note": "page with offset until hasMore is false"})
            if not os.path.exists(os.path.join(RAW, f"meta_{sun}.json")):
                add(f"meta {sun} <raw>", "get_account_metrics", {**am, "groupBy": "none", "start": str(sun), "end": str(e)})
        add(f"kw {L} <raw>", "get_ads_targeting_insights", {**base, "start": str(L), "end": str(sat), "mode": "top_spend", "adProducts": "SP,SB", "limit": 25, "note": "keyword targets only; skip ASIN/product targets"})
        add(f"sqp {sat} <raw>", "get_sqp_report", {**base, "asin": BRAND.get("sqpAsin", "B07WFHMD2V"), "start": str(L), "end": str(sat), "sortBy": "im", "sortOrder": "desc", "limit": 40})
    if not any(S.get("a25") or []):                          # last year's months, once (pacing slide's "last year" bar)
        ly = y.year - 1
        add("ly <raw>", "get_account_metrics", {**am, "groupBy": "month", "start": f"{ly}-01-01", "end": f"{ly}-12-31",
                                                "note": "save as [[month 1-12, revenue], ...]; a month with no sales is 0"})
    print(json.dumps(out, indent=1))

# ---------------------------------------------------------------- updaters
def cmd_ads(path):
    rows = archive("ads", "latest", path); P = ld("pnl_ads")
    P["ADS"] = [[f"{int(str(d)[4:6])}/{int(str(d)[6:8])}", r2(sp), r2(sa), None, None, int(o), r2(rev)] for d, rev, sp, sa, o in sorted(rows)]
    P["year"] = int(str(sorted(rows)[-1][0])[:4]); sv("pnl_ads", P); print("ads", len(P["ADS"]), "days through", P["ADS"][-1][0])

def cmd_month(mo, path):
    rows = archive("month", f"{int(mo):02d}", path); S = ld("sales"); i = int(mo) - 1
    agg = {k: [0, 0, 0, 0, 0] for k in KEYS}; anyad = False
    for asin, rev, u, se, sp, sa in rows:
        a = agg[gk(asin)]; a[0] += rev or 0; a[1] += u or 0; a[2] += se or 0
        if sp is not None: a[3] += sp; a[4] += sa or 0; anyad = True
    for p in S["PRODUCTS"]:
        for f in ("sales", "units", "sessions", "adSpend", "adSales"):
            while len(p[f]) <= i: p[f].append(None if f.startswith("ad") else 0)
        a = agg[p["key"]]
        p["sales"][i], p["units"][i], p["sessions"][i] = r2(a[0]), int(a[1]), int(a[2])
        p["adSpend"][i], p["adSales"][i] = (r2(a[3]), r2(a[4])) if anyad else (None, None)
    sv("sales", S); print("month", MS[i], round(sum(a[0] for a in agg.values())))

def cmd_pl(mo, path):
    m = archive("pl", f"{int(mo):02d}", path); P = ld("pnl_ads"); S = ld("sales"); i = int(mo) - 1; p = m.get("ppc", {})
    v = dict(gross=m["revenue"], returns=m.get("refunds", 0), cogs=m.get("cog", 0), referral=m.get("fees", 0), fba=m.get("fba", 0),
             storage=m.get("storageFee", 0), ads=p.get("spend", 0), promo=m.get("promos", 0), net=m.get("net", 0), adrev=p.get("sales", 0))
    v = {k: round(float(x or 0)) for k, x in v.items()}
    v["addl"] = v["gross"] - v["net"] - sum(v[k] for k in ("returns", "cogs", "referral", "fba", "storage", "ads", "promo"))
    for k in P["PL"]:
        while len(P["PL"][k]) <= i: P["PL"][k].append(0)
        P["PL"][k][i] = v[k]
    S["act26"] = P["PL"]["gross"][:]; sv("pnl_ads", P); sv("sales", S); print("pl", MS[i], v["gross"], v["net"])

def cmd_week(sun, path):
    rows = archive("week", sun, path); I = ld("inv_weekly"); i = widx(D(sun))
    agg = {k: [0, 0] for k in KEYS}
    for asin, rev, u in rows: a = agg[gk(asin)]; a[0] += rev or 0; a[1] += u or 0
    for f, j in (("sales", 0), ("units", 1)):
        for gi, k in enumerate(KEYS):
            arr = I["WEEKLY"][f][gi]
            while len(arr) <= i: arr.append(0)
            arr[i] = r2(agg[k][0]) if j == 0 else int(agg[k][1])
    sv("inv_weekly", I); print("week", sun, round(sum(a[0] for a in agg.values())))

def cmd_ly(path):
    rows = archive("ly", "months", path); S = ld("sales"); a = [0] * 12
    for mo, rev in rows: a[int(mo) - 1] = r2(rev)
    S["a25"] = a; sv("sales", S); print("last year by month", a)

def cmd_simple(kind, key, path):
    o = archive(kind, key, path)
    if kind == "meta" and "revenue" in o and "ppc" in o: json.dump(map_metrics(o), open(os.path.join(RAW, f"meta_{key}.json"), "w"), indent=1)
    print(kind, key, "saved")

# ---------------------------------------------------------------- finalize
STRAT_LABEL = {"Branded": "Branded keywords", "Category": "Category keywords", "Competitor": "Competitor targeting", "Defense": "Brand defense (product targets)",
               "Auto": "Auto targeting", "Audience": "Audience / category display", "Remarketing": "Remarketing", "Other": "Other"}
TYPE_LABEL = {"SP": "Sponsored Products", "SB": "Sponsored Brands", "SBV": "Sponsored Brands Video", "SD": "Sponsored Display", "ST": "Streaming TV"}
TYPE = {"sp": "SP", "hsa": "SB", "sb": "SB", "hsavideo": "SBV", "sbv": "SBV", "sd": "SD", "stv": "ST", "st": "ST"}
COMP = BRAND.get("competitors", ["saatva", "tempur", "purple", "onuia", "helix", "nolah", "linenspa", "sleep innovations", "tuft", "cloudlift"] if IS_DORMEO else [])
BTERMS = [t.lower() for t in BRAND.get("brandTerms", ["dormeo", "domeo"])]
isB = lambda k: any(t in k.lower() for t in BTERMS)
def strat(n):
    l = n.lower(); t = [x.strip().lower() for x in n.split("/")]
    if "competitor" in l: return "Competitor"
    if "defense" in l: return "Defense"
    if "remarketing" in l: return "Remarketing"
    if "aud" in t or "audience" in t: return "Audience"
    if "auto" in t: return "Auto"
    if "brand" in t: return "Branded"
    if "category" in t or "cat" in t: return "Category"
    return "Other"
def match(n, typ):
    t = [x.strip().lower() for x in n.split("/")]; l = n.lower()
    if typ in ("SD", "ST"): return "Audience"
    if "auto" in t: return "Auto"
    if "pt" in t or "pt- cat" in l or "/ pt" in l: return "Product targets"
    m = []
    if re.search(r"\bex(act|cat)?\b", l): m.append("Exact")
    if re.search(r"\bph(rase)?\b|phrase-exact", l): m.append("Phrase")
    if re.search(r"\b(broad|br|bm|bmm)\b", l): m.append("Broad")
    return " + ".join(m) if m else "Keywords"
def prodname(n):
    for a in re.findall(r"B0[A-Z0-9]{8}", n):
        if a in A2SHORT: return A2SHORT[a]
    if IS_DORMEO and "pillow" in n.lower(): return "Pillows"
    if IS_DORMEO and ("snowtek" in n.lower() or "essential" in n.lower()): return "SnowTek & Essentials"
    return "Brand / multi"
def camp_week(sun):
    f = os.path.join(RAW, f"camp_{sun}.json")
    if not os.path.exists(f): return {}, {}
    o = json.load(open(f)); out = {}
    for cid, typ, s, r, im, c, od in o["rows"]:
        d = out.setdefault(str(cid), {"t": TYPE.get(str(typ).lower(), str(typ).upper()), "s": 0, "r": 0, "i": 0, "c": 0, "o": 0})
        d["s"] += s or 0; d["r"] += r or 0; d["i"] += im or 0; d["c"] += c or 0; d["o"] += od or 0
    return out, {str(k): v for k, v in o["names"].items()}

def finalize():
    P = ld("pnl_ads"); C = ld("camp_kw"); I = ld("inv_weekly")
    camps = sorted(f[5:15] for f in os.listdir(RAW) if f.startswith("camp_"))
    if camps:
        L = D(camps[-1]); prev = L - dt.timedelta(days=7)
        cur, n1 = camp_week(str(L)); prv, n2 = camp_week(str(prev)); N = {**n2, **n1}
        CAMP = []
        for cid in set(cur) | set(prv):
            n = N.get(cid, cid); c = cur.get(cid, {}); p = prv.get(cid, {}); typ = (c or p)["t"]
            st, pr = strat(n), prodname(n)
            CAMP.append(dict(id=cid, name=n.strip(), label=f"{pr.replace('Octaspring ', '')} · {st} · {match(n, typ)}", type=typ, strat=st, prod=pr,
                             s=r2(c.get("s")), r=r2(c.get("r")), i=int(c.get("i", 0)), c=int(c.get("c", 0)), o=int(c.get("o", 0)),
                             ps=r2(p.get("s")), pr=r2(p.get("r")), pc=int(p.get("c", 0)), pi=int(p.get("i", 0))))
        C["CAMP"] = sorted(CAMP, key=lambda r: -r["s"]); C["STRAT_LABEL"] = STRAT_LABEL; C["TYPE_LABEL"] = TYPE_LABEL
        mc, mp = os.path.join(RAW, f"meta_{L}.json"), os.path.join(RAW, f"meta_{prev}.json")
        if os.path.exists(mc) and os.path.exists(mp):
            P["CAMP_META"] = {"week": f"{wk_label(L)}, {L.year}", "prior": wk_label(prev), "weekStart": str(L),
                              "cur": json.load(open(mc)), "prev": json.load(open(mp))}
    # SQP: last 4 weeks, newest first
    sq = sorted((f[4:14] for f in os.listdir(RAW) if f.startswith("sqp_")), reverse=True)[:4]
    if sq:
        SQ = [(s, json.load(open(os.path.join(RAW, f"sqp_{s}.json")))) for s in sq]
        wl = lambda s: f"{D(s).month}/{D(s).day}/{D(s).year}"
        q = {}
        for wi, (s, R) in enumerate(SQ):
            for kw, qv, imt, im, cvt, cv in R: q.setdefault(kw, [[0, 0, 0, 0] for _ in SQ])[wi] = [imt, im, cvt, cv]
        top = sorted(q, key=lambda k: -sum(v[1] for v in q[k]))[:60]
        C["SQP"] = dict(weeks=[wl(s) for s, _ in SQ], totals=[[sum(r[2] for r in R), sum(r[3] for r in R), sum(r[4] for r in R), sum(r[5] for r in R)] for _, R in SQ],
                        top=[[k, "B" if isB(k) else "C", q[k]] for k in top])
        QV = {s: {r[0]: r[1] for r in R} for s, R in SQ}
    else: QV = {}
    # keywords: last 4 weeks, oldest first
    kws = sorted(f[3:13] for f in os.listdir(RAW) if f.startswith("kw_"))[-4:]
    if kws:
        KW, FLAG = [], {}
        for sun in kws:
            x = json.load(open(os.path.join(RAW, f"kw_{sun}.json"))); e = str(D(sun) + dt.timedelta(days=6)); g = {}
            for ap, kw, mt, sp, sa, cl, o, im, u, tos in x["R"]:
                d = g.setdefault((kw, mt.title()), dict(t=set(), n=0, sp=0, sa=0, cl=0, o=0, u=0, im=0, tw=0))
                d["t"].add(ap); d["n"] += 1; d["sp"] += sp; d["sa"] += sa; d["cl"] += cl; d["o"] += o; d["u"] += u; d["im"] += im; d["tw"] += (tos or 0) * im
            qv = QV.get(e, {}); rows = []
            for (kw, mt), d in g.items():
                rows.append([kw, mt, "/".join(sorted(d["t"], reverse=True)), d["n"], 1 if isB(kw) else 0, r2(d["sp"]), r2(d["sa"]), d["cl"], d["o"], d["u"], d["im"],
                             round(d["tw"] / d["im"], 1) if d["im"] else None, qv.get(kw.replace("+", "").strip())])
                for c in COMP:
                    if c in kw: FLAG[kw] = f"Another brand’s product ({c.title()})"
            cw, _ = camp_week(sun)
            sd = [r2(sum(v["s"] for v in cw.values() if v["t"] == "SD")), r2(sum(v["r"] for v in cw.values() if v["t"] == "SD"))] if cw else \
                 next((k["sd"] for k in C.get("KW", []) if k["s"] == sun), [0, 0])
            KW.append(dict(s=sun, e=e, tot=x["tot"], sd=sd, rows=rows))
        C["KW"] = KW; C["KW_FLAG"] = FLAG
    # inventory: units for the last 4 complete weeks, from the weekly series
    y = dt.date(P.get("year", 2026), *map(int, P["ADS"][-1][0].split("/")))
    sat = last_sat(y); li = widx(sat - dt.timedelta(days=6))
    for r, gi in zip(I["INV"]["rows"], range(len(KEYS))):
        u = I["WEEKLY"]["units"][gi]; r["wk"] = [int(u[j]) if j < len(u) else 0 for j in range(li - 3, li + 1)]
    I["INV"]["lastWeek"] = li + 1
    sv("pnl_ads", P); sv("camp_kw", C); sv("inv_weekly", I)
    print("finalize: campaigns", len(C["CAMP"]), "| kw weeks", [k["s"] for k in C["KW"]], "| sqp", C.get("SQP", {}).get("weeks"), "| inv weeks", I["INV"]["lastWeek"] - 3, "-", I["INV"]["lastWeek"])

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(1)
    c = a[0]
    if c == "plan":
        if len(a) > 1: day = D(a[1])
        else:
            import zoneinfo; day = dt.datetime.now(zoneinfo.ZoneInfo("America/Los_Angeles")).date()
        plan(day)
    elif c == "ads": cmd_ads(a[1])
    elif c == "month": cmd_month(a[1], a[2])
    elif c == "pl": cmd_pl(a[1], a[2])
    elif c == "week": cmd_week(a[1], a[2])
    elif c in ("meta", "camp", "kw", "sqp"): cmd_simple(c, a[1], a[2])
    elif c == "ly": cmd_ly(a[1])
    elif c == "finalize": finalize()
    else: print(__doc__); sys.exit(1)
