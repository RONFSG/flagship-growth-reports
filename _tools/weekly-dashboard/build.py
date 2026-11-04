#!/usr/bin/env python3
"""Build a brand's weekly dashboard (<slug>-weekly/index.html) from Sellerise data.

Python port of Weekly_buildBrandHTML / Weekly_buildOrgVsPaidSection / buildTopProductsSection /
Weekly_getChartScript from the old FSG_Weekly_Report Apps Script, so the page looks the same.

Usage (from repo root):
  python3 _tools/weekly-dashboard/build.py <slug> <weekStart YYYY-MM-DD> --summary   # print metrics for writing insights
  python3 _tools/weekly-dashboard/build.py <slug> <weekStart YYYY-MM-DD>             # write <slug>-weekly/index.html
Input: _tools/weekly-dashboard/data/<slug>/<weekStart>.json  (see data/opopop/2026-10-25.json)
Brand settings: _tools/weekly-dashboard/brands.json
"""
import datetime as dt
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
LOGO = 'https://ronfsg.github.io/flagship-growth-reports/assets/fsg-logo.png'
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
          'September', 'October', 'November', 'December']


def money(v):            # '$' + Math.floor(v).toLocaleString()
    return '${:,}'.format(int(v // 1))


def rmoney(v):           # was Math.round in the old script; floor everywhere so cards, highlights and insights agree
    return money(v)


def pct_change(cur, prev):
    return (cur - prev) / prev * 100 if prev else 0.0


def week_label(start):
    s = dt.date.fromisoformat(start)
    e = s + dt.timedelta(days=6)
    wn = (s + dt.timedelta(days=1)).isocalendar()[1]          # ISO week of the Monday, as the script did
    return 'Week %d · %s %d – %s %d, %d' % (wn, MONTHS[s.month - 1], s.day,
                                                      MONTHS[e.month - 1], e.day, e.year)


def net_sales(x):
    """Sales shown on the dashboard = Sellerise revenue minus sales tax (matches Amazon Ordered Product Sales)."""
    return x['revenue'] - x.get('salesTaxes', 0)


def compute(d):
    c, p = d['current'], d['prev']
    c = dict(c, revenue=net_sales(c))
    p = dict(p, revenue=net_sales(p))
    m = {}
    m['sales'] = c['revenue']
    m['units'] = c['units']
    m['spend'] = c['ppcSpend']
    m['adSales'] = c['ppcSales']
    m['impressions'] = c['ppcImpressions']
    m['clicks'] = c['ppcClicks']
    m['orders'] = c['ppcOrders']
    m['roas'] = c['ppcSales'] / c['ppcSpend'] if c['ppcSpend'] else 0
    m['acos'] = c['ppcSpend'] / c['ppcSales'] * 100 if c['ppcSales'] else 0
    m['tacos'] = c['ppcSpend'] / c['revenue'] * 100 if c['revenue'] else 0
    m['ctr'] = c['ppcClicks'] / c['ppcImpressions'] * 100 if c['ppcImpressions'] else 0
    m['cvr'] = c['ppcOrders'] / c['ppcClicks'] * 100 if c['ppcClicks'] else 0
    m['prevSales'] = p['revenue']
    m['prevAdSales'] = p['ppcSales']
    m['prevSpend'] = p['ppcSpend']
    m['prevRoas'] = p['ppcSales'] / p['ppcSpend'] if p['ppcSpend'] else 0
    m['prevTacos'] = p['ppcSpend'] / p['revenue'] * 100 if p['revenue'] else 0
    m['wow'] = pct_change(m['sales'], m['prevSales'])
    m['organic'] = m['sales'] - m['adSales']
    m['prevOrganic'] = m['prevSales'] - m['prevAdSales']
    m['orgWoW'] = pct_change(m['organic'], m['prevOrganic'])
    m['paidWoW'] = pct_change(m['adSales'], m['prevAdSales'])
    labels, values = [], []
    for row in d['daily']:
        dd = dt.date.fromisoformat(row['date'])
        labels.append(dd.strftime('%a %b ') + str(dd.day))       # 'EEE MMM d'
        values.append(int(net_sales(row) // 1))
    m['dailyLabels'], m['dailyValues'] = labels, values
    m['maxDaily'] = max(values) if values else 0
    m['peakLabel'] = labels[values.index(m['maxDaily'])] if values else ''
    prods = []
    for pr in d['products']:
        cu = dict(pr['cur'], revenue=net_sales(pr['cur']))
        pv = dict(pr['prev'], revenue=net_sales(pr['prev']))
        cvr = cu['units'] / cu['sessions'] * 100 if cu['sessions'] else 0
        pcvr = pv['units'] / pv['sessions'] * 100 if pv['sessions'] else 0
        prods.append(dict(name=pr['title'], asin=pr['asin'], sales=cu['revenue'], units=cu['units'],
                          sessions=cu['sessions'], cvr=cvr,
                          wow=pct_change(cu['revenue'], pv['revenue']),
                          wowUnits=pct_change(cu['units'], pv['units']),
                          wowSessions=pct_change(cu['sessions'], pv['sessions']),
                          wowCvr=pct_change(cvr, pcvr)))
    m['products'] = sorted(prods, key=lambda x: -x['sales'])[:5]
    return m


def summary_text(brand, label, m):
    lines = ['%s Weekly Sales (%s):' % (brand, label), '',
             'Total Sales: %s (prior week %s, %+.1f%% WoW)' % (rmoney(m['sales']), rmoney(m['prevSales']), m['wow']),
             'Units Sold: %d' % m['units'],
             'Ad Spend: %s (prior %s)' % (rmoney(m['spend']), rmoney(m['prevSpend'])),
             'PPC Revenue: %s (prior %s, %+.1f%%)' % (rmoney(m['adSales']), rmoney(m['prevAdSales']), m['paidWoW']),
             'ROAS: %.2fx (prior %.2fx)' % (m['roas'], m['prevRoas']),
             'TACoS: %.1f%% (prior %.2f%%)' % (m['tacos'], m['prevTacos']),
             'ACOS: %.1f%%' % m['acos'],
             'CTR (ads): %.2f%%  CVR (ad orders/clicks): %.2f%%' % (m['ctr'], m['cvr']),
             'Organic: %s (%+.1f%% WoW)' % (rmoney(m['organic']), m['orgWoW']),
             'Peak Day: %s %s' % (m['peakLabel'], money(m['maxDaily'])),
             'Daily: ' + ', '.join('%s %s' % (l, money(v)) for l, v in zip(m['dailyLabels'], m['dailyValues'])),
             'Top products:']
    for p in m['products']:
        lines.append('  %s (%s): %s %+.1f%%, units %d %+.1f%%, sessions %d %+.1f%%, CVR %.1f%% %+.1f%%' % (
            p['name'], p['asin'], money(p['sales']), p['wow'], p['units'], p['wowUnits'],
            p['sessions'], p['wowSessions'], p['cvr'], p['wowCvr']))
    return '\n'.join(lines)


def recs_html(insights):
    """insights: list of 4 strings like '**Weekly Highlights —** text'."""
    out = []
    for line in insights:
        line = html.escape(line.strip(), quote=False)
        line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
        out.append('<div class="rec-item"><div class="rec-arrow">►</div><div class="rec-text">' + line + '</div></div>')
    return ''.join(out)


def org_vs_paid(m):
    def badge(v):
        if v == 0:
            return '<span class="neutral">—</span>'
        return ('<span class="wow-up">▲ +%.1f%% WoW</span>' % v) if v > 0 else ('<span class="wow-down">▼ %.1f%% WoW</span>' % v)
    s = m['sales']
    op = m['organic'] / s * 100 if s else 0
    pp = m['adSales'] / s * 100 if s else 0
    return ('<div class="section-header"><div class="bar-accent"></div><div class="section-title">Organic vs Paid Revenue</div></div>'
            '<div class="ovp-grid">'
            '<div class="ovp-card"><div class="ovp-label">Organic Revenue</div><div class="ovp-value">' + money(m['organic']) + '</div><div class="ovp-wow">' + badge(m['orgWoW']) + '</div><div class="ovp-share">%.1f%% of total sales</div></div>' % op +
            '<div class="ovp-divider"></div>'
            '<div class="ovp-card"><div class="ovp-label">PPC Revenue</div><div class="ovp-value">' + money(m['adSales']) + '</div><div class="ovp-wow">' + badge(m['paidWoW']) + '</div><div class="ovp-share">%.1f%% of total sales</div></div>' % pp +
            '</div>')


def top_products(m):
    if not m['products']:
        return ''

    def b(v):
        cls = 'wow-up' if v >= 0 else 'wow-down'
        return '<br><span class="%s" style="font-size:9px;">%s%.1f%%</span>' % (cls, '▲ +' if v >= 0 else '▼ ', abs(v))
    td = 'text-align:right;padding:8px 6px;border-bottom:1px solid var(--border);font-size:11px;'
    rows = ''
    for i, p in enumerate(m['products']):
        rows += ('<tr><td style="text-align:left;padding:8px 6px;border-bottom:1px solid var(--border);font-size:11px;font-weight:600;color:var(--navy);">'
                 '%d. %s<br><span style="font-size:9px;color:var(--muted);font-weight:400;">ASIN: %s</span></td>' % (i + 1, html.escape(p['name']), p['asin']) +
                 '<td style="%sfont-weight:700;">%s%s</td>' % (td, money(p['sales']), b(p['wow'])) +
                 '<td style="%s">{:,}%s</td>'.format(p['units']) % (td, b(p['wowUnits'])) +
                 '<td style="%s">{:,}%s</td>'.format(p['sessions']) % (td, b(p['wowSessions'])) +
                 '<td style="%s">%.1f%%%s</td>' % (td, p['cvr'], b(p['wowCvr'])) + '</tr>')
    return ('<div class="section-header"><div class="bar-accent"></div><div class="section-title">Top Selling Products</div></div>'
            '<div class="table-scroll"><table><thead><tr><th style="text-align:left;">Product</th><th>Sales</th><th>Units</th><th>Sessions</th><th>CVR</th></tr></thead>'
            '<tbody>' + rows + '</tbody></table></div>')


def chart_script(m):
    data = [{'day': l, 'val': v, 'peak': v == m['maxDaily']} for l, v in zip(m['dailyLabels'], m['dailyValues'])]
    return ('<script>(function(){var data=' + json.dumps(data, separators=(',', ':')) + ';\n'
            'var maxV=Math.max.apply(null,data.map(function(d){return d.val;}));\n'
            'var el=document.getElementById("chart");\n'
            'data.forEach(function(d){var h=maxV>0?Math.round((d.val/maxV)*220):0;var g=document.createElement("div");g.className="bar-group";\n'
            'g.innerHTML=\'<div class="bar-col" style="height:\'+h+\'px;background:\'+(d.peak?"#2447FF":"#DDE4F5")+\'">\'+\'<span class="bar-top-label">$\'+Math.floor(d.val).toLocaleString()+\'</span></div>\'+\'<div class="bar-day"><span class="d1">\'+d.day+\'</span></div>\';\n'
            'el.appendChild(g);});'
            'var io=new IntersectionObserver(function(entries){entries.forEach(function(e){if(e.isIntersecting){e.target.classList.add("visible");}});},{threshold:0.08,rootMargin:"0px 0px -20px 0px"});'
            'document.querySelectorAll(".animate").forEach(function(el){io.observe(el);});'
            '})();</script>')


def build_html(brand, label, m, insights, note=''):
    css = open(os.path.join(HERE, 'style.html')).read()
    wow = m['wow']
    wow_cls = 'up' if wow >= 0 else 'down'
    wow_str = ('▲ +' if wow >= 0 else '▼ ') + '%.1f%% WoW' % abs(wow)

    def small(cur, prev):
        if not prev:
            return '<div class="kpi-change neutral">No prev data</div>'
        p = pct_change(cur, prev)
        return '<div class="kpi-change %s">%s%.1f%% vs %s</div>' % ('up' if p >= 0 else 'down', '▲ +' if p >= 0 else '▼ ', abs(p), money(prev))

    def small_x(cur, prev, suf):
        if not prev:
            return '<div class="kpi-change neutral">No prev data</div>'
        p = pct_change(cur, prev)
        return '<div class="kpi-change %s">%s%.1f%% vs %.2f%s</div>' % ('up' if p >= 0 else 'down', '▲ +' if p >= 0 else '▼ ', abs(p), prev, suf)

    def card(i, value, lbl, change):
        return '<div class="kpi-card animate" style="transition-delay:%dms"><div class="kpi-value">%s</div><div class="kpi-label">%s</div>%s</div>' % (i * 60, value, lbl, change)

    roas_change = small_x(m['roas'], m['prevRoas'], 'x') if m['prevRoas'] > 0 else '<div class="kpi-change %s">%s</div>' % ('up' if m['roas'] >= 4 else 'neutral', '▲ Strong' if m['roas'] >= 4 else '')
    kpis = (card(0, money(m['sales']), 'Total Sales', '<div class="kpi-change %s">%s</div>' % (wow_cls, wow_str)) +
            card(1, '{:,}'.format(m['units']) if m['units'] > 0 else '—', 'Units Sold', '<div class="kpi-change neutral">This week</div>') +
            card(2, money(m['spend']), 'Ad Spend', small(m['spend'], m['prevSpend']) if m['prevSpend'] > 0 else '<div class="kpi-change neutral">This week</div>') +
            card(3, money(m['adSales']), 'PPC Revenue', small(m['adSales'], m['prevAdSales']) if m['prevAdSales'] > 0 else '<div class="kpi-change neutral">Ad Attributed</div>') +
            card(4, '%.2fx' % m['roas'], 'ROAS', roas_change) +
            card(5, '%.1f%%' % m['tacos'], 'TACoS', small_x(m['tacos'], m['prevTacos'], '%') if m['prevTacos'] > 0 else '<div class="kpi-change neutral">Brand blend</div>') +
            card(6, '%.2f%%' % m['ctr'], 'CTR', '<div class="kpi-change neutral">Clicks/Impr</div>') +
            card(7, '%.2f%%' % m['cvr'], 'CVR', '<div class="kpi-change neutral">Orders/Clicks</div>'))

    def hl(tag, strong, p):
        return '<div class="highlight-row"><div class="highlight-tag">%s</div><div class="highlight-text"><strong>%s</strong><p>%s</p></div></div>' % (tag, strong, p)
    highlights = (hl('Total Sales', rmoney(m['sales']), 'Week of ' + label) +
                  hl('vs Prior Week', ('▲ +' if wow >= 0 else '▼ ') + '%.1f%% WoW' % abs(wow), 'Prior week: ' + rmoney(m['prevSales'])) +
                  hl('Ad Performance', '%.2fx ROAS · %.1f%% ACOS' % (m['roas'], m['acos']), '%.1f%% TACoS · %s PPC Revenue' % (m['tacos'], rmoney(m['adSales']))) +
                  hl('Engagement', '{:,} clicks · {:.2f}% CVR'.format(m['clicks'], m['cvr']), '%d orders' % m['orders']) +
                  hl('Peak Day', m['peakLabel'], ('{:,}'.format(m['maxDaily']) if m['maxDaily'] > 0 else 'N/A').join(['$', ' revenue'])))
    note_html = ('<div style="background:#FFF7ED;border-bottom:1px solid #FED7AA;padding:6px 32px;font-size:10px;font-weight:600;color:#C2410C;">⚠️  ' + html.escape(note) + '</div>') if note else ''
    return ('<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>' + brand + ' Weekly Report</title>' + css + '</head><body>'
            '<div class="page">'
            '<div class="header"><div style="display:flex;flex-direction:column;align-items:flex-start;gap:6px;"><img src="' + LOGO + '" alt="Flagship Growth" class="header-logo"/><div class="header-sub" style="margin:0;">' + brand + ' Weekly Report</div></div>'
            '<div><div class="header-title">Weekly <span>Sales</span> Report</div><div class="header-period">' + brand + ' &nbsp;·&nbsp; ' + label + '</div></div></div>' +
            note_html +
            '<div class="container">'
            '<div class="kpi-grid-wide">' + kpis + '</div>'
            '<div class="two-col">'
            '<div><div class="section-header"><div class="bar-accent"></div><div class="section-title">Daily Sales — ' + brand + '</div></div><div class="chart-wrapper" id="chart"></div></div>'
            '<div><div class="section-header"><div class="bar-accent"></div><div class="section-title">Highlights</div></div>' + highlights + '</div></div>' +
            org_vs_paid(m) + top_products(m) +
            '<div class="recs-box"><div class="section-header"><div class="bar-accent"></div><div class="section-title" style="color:#F6F3EC;letter-spacing:0.12em;">Weekly Insights &amp; Actions</div></div><div class="rec-list">' + recs_html(insights) + '</div></div>'
            '</div>'
            '<div class="footer"><div class="footer-left">' + brand + ' Weekly Report · ' + label + ' · Confidential · Flagship Growth</div><div class="footer-right">flagshipgrowth.com</div></div>'
            '</div>' + chart_script(m) + '</body></html>')


def main():
    slug, start = sys.argv[1], sys.argv[2]
    brands = json.load(open(os.path.join(HERE, 'brands.json')))
    cfg = brands[slug]
    d = json.load(open(os.path.join(HERE, 'data', slug, start + '.json')))
    if d['week']['start'] != start:
        sys.exit('data file week.start does not match ' + start)
    if len(d['daily']) != 7:
        sys.exit('need 7 daily rows, got %d — week incomplete, not publishing' % len(d['daily']))
    m = compute(d)
    label = week_label(start)
    if '--summary' in sys.argv:
        print(summary_text(cfg['brand'], label, m))
        return
    ins = d.get('insights') or []
    if len(ins) != 4:
        sys.exit('data file needs 4 insights before publishing')
    page = build_html(cfg['brand'], label, m, ins, d.get('note', ''))
    if cfg.get('currencySymbol', '$') != '$':
        page = page.replace('$', cfg['currencySymbol'])
    out = os.path.join(ROOT, slug + '-weekly', 'index.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w').write(page)
    print('wrote', out, len(page), 'bytes')


if __name__ == '__main__':
    main()
