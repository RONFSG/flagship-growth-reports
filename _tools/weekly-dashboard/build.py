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


def slack_text(cfg, slug, label, m):
    """Same layout as the old sendBrandSlackNotification table (Markdown for the Slack connector)."""
    def wow(cur, prev):
        if not prev:
            return '  —'
        p = pct_change(cur, prev)
        return ('▲ +' if p >= 0 else '▼ ') + ('%.1f%%' % p if p < 0 else '%.1f%%' % p)
    metrics = [('Total Sales', money(m['sales']), wow(m['sales'], m['prevSales'])),
               ('Units Sold', '{:,}'.format(m['units']), '  —'),
               ('Ad Spend', money(m['spend']), wow(m['spend'], m['prevSpend'])),
               ('ROAS', '%.2fx' % m['roas'], wow(m['roas'], m['prevRoas'])),
               ('TACoS', '%.1f%%' % m['tacos'], wow(m['tacos'], m['prevTacos'])),
               ('Ad Sales', money(m['adSales']), wow(m['adSales'], m['prevAdSales']))]
    daily = []
    for l, v in zip(m['dailyLabels'], m['dailyValues']):
        dname, mon, day = l.split(' ')
        mnum = dt.datetime.strptime(mon, '%b').month
        daily.append('%-13s  %s' % ('%s %d/%s' % (dname, mnum, day), money(v)))
    rows = ['%-15s%-14s%-14s%s' % ('Metric', 'Value', 'WoW', 'Daily Sales'), '─' * 65]
    for i in range(max(len(metrics), len(daily))):
        left = '%-15s%-14s%-14s' % metrics[i] if i < len(metrics) else ' ' * 43
        rows.append(left + (daily[i] if i < len(daily) else ''))
    sym = cfg.get('currencySymbol', '$')
    table = '\n'.join(rows).replace('$', sym)
    links = ['[View Full Dashboard](https://reports.flagshipgrowth.com/%s-weekly)' % slug]
    return ('**%s Weekly Report — %s**\n```\n%s\n```\n%s\n_Flagship Growth · %s Weekly Report · %s · Confidential_' % (
        cfg['brand'], label, table, '  ·  '.join(links), cfg['brand'], label))


def email_html(cfg, slug, label, m, insights):
    """Port of the old sendBrandEmail HTML (Google Doc button removed). Returns (subject, html)."""
    cur = cfg.get('currencySymbol', '$')
    G, R, A, MUT, INK = '#16A34A', '#DC2626', '#D97706', '#6B6558', '#0B0D12'

    def cm(v):
        return cur + '{:,}'.format(int(v // 1))

    def wtxt(v, suffix='% WoW'):
        return ('▲ +' if v >= 0 else '▼ ') + '%.1f' % abs(v) + suffix

    def col(v):
        return G if v >= 0 else R
    roas, tacos = m['roas'], m['tacos']
    acos = m['acos']
    roas_c, roas_l = (G, '▲ Strong') if roas >= 4 else ((A, '— Moderate') if roas >= 2 else (R, '▼ Low'))
    s = m['sales']
    org_pct = '%.1f' % (m['organic'] / s * 100) if s else '0'
    paid_pct = '%.1f' % (m['adSales'] / s * 100) if s else '0'
    wn = label.split(' · ')[0].replace('Week ', '')
    date_range = label

    def strip_label(t):
        return re.sub(r'^\*\*.*?\*\*\s*', '', t).strip()
    highlight = strip_label(insights[0]) if insights else ''
    actions = [x.strip().rstrip('.') + '.' for x in re.split(r'\.\s+', strip_label(insights[3])) if len(x.strip()) > 15][:3] if len(insights) > 3 else []

    sec = lambda t: '<div style="font-size:9px;font-weight:700;letter-spacing:1.5px;color:#2447FF;margin-bottom:10px;border-bottom:2px solid #2447FF;padding-bottom:5px;">' + t + '</div>'
    card = lambda big, lbl, sub, subc: ('<td style="text-align:center;padding:12px 6px;background:#F8F8F5;border-radius:6px;">'
                                       '<div style="font-size:17px;font-weight:bold;color:%s;">%s</div>'
                                       '<div style="font-size:10px;color:%s;margin-top:3px;">%s</div>'
                                       '<div style="font-size:11px;color:%s;margin-top:3px;font-weight:600;">%s</div></td>') % (INK, big, MUT, lbl, subc, sub)
    gap = '<td width="6"></td>'

    one_line = ('<div style="background:#EEF2FF;border-left:3px solid #2447FF;border-radius:0 6px 6px 0;padding:14px 16px;margin-bottom:20px;">'
                '<div style="font-size:9px;font-weight:700;letter-spacing:1.5px;color:#2447FF;text-transform:uppercase;margin-bottom:6px;">▶ This week in one line</div>'
                '<div style="font-size:13px;color:%s;line-height:1.6;">%s</div></div>' % (INK, html.escape(highlight))) if highlight else ''

    rev = (sec('REVENUE HIGHLIGHTS') + '<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;"><tr>' +
           card(cm(s), 'Total Sales', wtxt(m['wow']), col(m['wow'])) + gap +
           card('%.2fx' % roas, 'ROAS', roas_l, roas_c) + gap +
           card(cm(m['spend']), 'Ad Spend', '%.1f%% TACoS' % tacos, MUT) + gap +
           card(cm(m['adSales']), 'PPC Revenue', wtxt(m['paidWoW']), col(m['paidWoW'])) + '</tr></table>')

    def ovp(lbl, val, w, share):
        return ('<td style="vertical-align:top;background:#F8F8F5;border-radius:6px;padding:14px 12px;">'
                '<div style="font-size:9px;color:%s;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px;">%s</div>'
                '<div style="font-size:16px;font-weight:bold;color:%s;">%s</div>'
                '<div style="font-size:11px;color:%s;margin-top:3px;font-weight:600;">%s</div>'
                '<div style="font-size:10px;color:%s;margin-top:2px;">%s%% of total</div></td>') % (MUT, lbl, INK, val, col(w), wtxt(w), MUT, share)
    eff_row = lambda k, v: '<tr><td style="font-size:11px;color:%s;padding:3px 0;width:52%%;">%s</td><td style="font-size:11px;font-weight:bold;color:%s;padding:3px 0;white-space:nowrap;">%s</td></tr>' % (MUT, k, INK, v)
    eff = ('<td style="vertical-align:top;background:#F8F8F5;border-radius:6px;padding:14px 12px;">'
           '<div style="font-size:9px;color:%s;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:8px;">Ad Efficiency</div>'
           '<table cellpadding="0" cellspacing="0" width="100%%" style="border-collapse:collapse;">' % MUT +
           eff_row('ACoS', '%.1f%% <span style="color:%s;">%s</span>' % (acos, G if acos <= 20 else R, '▲' if acos <= 20 else '▼')) +
           eff_row('TACoS', '%.1f%% <span style="color:%s;">%s</span>' % (tacos, G if tacos <= 10 else R, '▲' if tacos <= 10 else '▼')) +
           eff_row('Units', '{:,}'.format(m['units'])) +
           eff_row('CVR', '%.2f%%' % m['cvr']) + '</table></td>')
    wow_sec = (sec('WEEK-OVER-WEEK PERFORMANCE') + '<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;"><tr>' +
               ovp('Organic Revenue', cm(m['organic']), m['orgWoW'], org_pct) + gap +
               ovp('PPC Revenue', cm(m['adSales']), m['paidWoW'], paid_pct) + gap + eff + '</tr></table>')

    bars = ''
    mx = m['maxDaily'] or 1
    for l, v in zip(m['dailyLabels'], m['dailyValues']):
        dname, mon, day = l.split(' ')
        dl = '%s %d/%s' % (dname, dt.datetime.strptime(mon, '%b').month, day)
        peak = v == m['maxDaily']
        h = max(4, round(v / mx * 56))
        amt = (cur + str(int(v // 1000)) + 'k') if v >= 1000 else cur + str(int(v))
        bars += ('<td style="text-align:center;vertical-align:bottom;padding:0 3px;width:%d%%;">'
                 '<div style="font-size:9px;color:%s;margin-bottom:3px;">%s</div>'
                 '<div style="background:%s;height:%dpx;border-radius:3px 3px 0 0;"></div>'
                 '<div style="font-size:9px;margin-top:4px;font-weight:%s;color:%s;">%s</div></td>') % (
            100 // len(m['dailyValues']), MUT, amt, '#2447FF' if peak else '#DDE4F5', h, '700' if peak else '400', '#2447FF' if peak else MUT, dl)
    daily = sec('DAILY SALES') + '<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;"><tr style="vertical-align:bottom;">' + bars + '</tr></table>'

    th = lambda t, a: '<th style="padding:7px 8px;font-size:9px;color:%s;font-weight:600;text-align:%s;">%s</th>' % (MUT, a, t)
    prow = ''
    for i, p in enumerate(m['products'][:3]):
        prow += ('<tr style="border-bottom:1px solid #E5E0D6;">'
                 '<td style="padding:9px 8px;font-size:12px;color:%s;width:20px;">%d</td>'
                 '<td style="padding:9px 8px;font-size:12px;color:%s;font-weight:500;">%s</td>'
                 '<td style="padding:9px 8px;font-size:12px;font-weight:700;color:%s;text-align:right;white-space:nowrap;">%s</td>'
                 '<td style="padding:9px 8px;font-size:12px;color:%s;text-align:right;white-space:nowrap;font-weight:600;">%s</td>'
                 '<td style="padding:9px 8px;font-size:11px;color:%s;text-align:right;white-space:nowrap;">%d units</td></tr>') % (
            MUT, i + 1, INK, html.escape(p['name']), INK, cm(p['sales']), col(p['wow']), wtxt(p['wow'], '%'), MUT, p['units'])
    prods = (sec('TOP SELLING PRODUCTS') + '<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-bottom:20px;">'
             '<tr style="background:#F8F8F5;">' + th('#', 'left') + th('Product', 'left') + th('Sales', 'right') + th('WoW', 'right') + th('Units', 'right') + '</tr>' + prow + '</table>') if m['products'] else ''

    acts = (sec("WHAT WE'RE DOING THIS WEEK") + '<ul style="margin:0 0 20px 16px;padding:0;">' +
            ''.join('<li style="font-size:12px;color:%s;line-height:1.6;margin-bottom:8px;padding-left:4px;">%s</li>' % (INK, html.escape(a)) for a in actions) + '</ul>') if actions else ''

    url = 'https://reports.flagshipgrowth.com/%s-weekly' % slug
    body = ('<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;background:#F6F3EC;margin:0;padding:20px;"><div style="max-width:600px;margin:0 auto;">'
            '<div style="background:#ffffff;padding:18px 24px 16px;border-radius:8px 8px 0 0;border:0.5px solid #e2e8f0;border-bottom:2px solid #2447FF;">'
            '<table width="100%" cellpadding="0" cellspacing="0"><tr><td style="vertical-align:middle;width:110px;"><img src="' + LOGO + '" height="36" style="display:block;" alt="Flagship Growth"></td>'
            '<td style="text-align:right;vertical-align:middle;"><div style="font-size:16px;font-weight:bold;color:' + INK + ';line-height:1.3;">Amazon Weekly Sales Report WK' + wn + '</div>'
            '<div style="font-size:12px;color:' + MUT + ';margin-top:3px;">' + cfg['brand'] + ' · ' + date_range + '</div></td></tr></table></div>'
            '<div style="background:#fff;padding:22px 24px;border:0.5px solid #e2e8f0;border-top:none;">' +
            one_line + rev + wow_sec + daily + prods + acts +
            '<div style="text-align:center;margin-bottom:8px;"><a href="' + url + '" style="display:inline-block;background:#2447FF;color:#fff;padding:12px 28px;border-radius:6px;text-decoration:none;font-size:13px;font-weight:600;">View Full Dashboard →</a></div>'
            '</div><div style="background:#F6F3EC;padding:14px 24px;border-radius:0 0 8px 8px;text-align:center;border:0.5px solid #e2e8f0;border-top:none;">'
            '<div style="font-size:10px;color:#9E9689;">Flagship Growth · ' + cfg['brand'] + ' Weekly Report · ' + date_range + ' · Confidential</div>'
            '<div style="font-size:10px;color:#9E9689;margin-top:2px;">Questions? Reply to this email or reach us on Slack.</div></div></div></body></html>')
    subject = 'Weekly Performance Summary / %s / %s' % (cfg['brand'], date_range)
    return subject, body


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
    if '--email' in sys.argv:                      # --email <out.html>: write the client email (not published)
        subject, body = email_html(cfg, slug, label, m, d.get('insights') or [])
        out = sys.argv[sys.argv.index('--email') + 1]
        open(out, 'w').write(body)
        print('SUBJECT:', subject)
        print('wrote', out)
        return
    if '--slack' in sys.argv:
        print(slack_text(cfg, slug, label, m))
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
