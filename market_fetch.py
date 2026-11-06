#!/usr/bin/env python3
"""Daily market data for Portfolio Builder's Markets tab (adviser, Nov 2026).

Fetches about three years of daily closes from Yahoo Finance, converts every price series to euro with the
same day's exchange rate, and writes one JSON file the tool loads with "Load market data".
Levels (the US 10-year yield, the VIX) are kept as they are. Uses only the standard library and curl.

    python3 tools/market_fetch.py [output.json]
"""
import json, subprocess, sys, time, urllib.parse, datetime as dt

# key, label, group, Yahoo symbol, currency of the quote, kind ('price' = convert to EUR and use returns; 'level' = keep, use changes)
SERIES = [
    ('world',  'MSCI World',                 'Shares',      'IWDA.AS',   'EUR', 'price', 'iShares Core MSCI World ETF (Amsterdam, EUR)'),
    ('sp500',  'S&P 500',                    'Shares',      '^GSPC',     'USD', 'price', 'S&P 500 index'),
    ('ndx',    'Nasdaq 100',                 'Shares',      '^NDX',      'USD', 'price', 'Nasdaq-100 index'),
    ('sx5e',   'Euro Stoxx 50',              'Shares',      '^STOXX50E', 'EUR', 'price', 'Euro Stoxx 50 index'),
    ('ftse',   'FTSE 100',                   'Shares',      '^FTSE',     'GBP', 'price', 'FTSE 100 index'),
    ('n225',   'Nikkei 225',                 'Shares',      '^N225',     'JPY', 'price', 'Nikkei 225 index'),
    ('em',     'Emerging markets',           'Shares',      'IEMA.AS',   'EUR', 'price', 'iShares MSCI EM ETF (Amsterdam, EUR)'),
    ('eugov',  'Euro government bonds',      'Bonds',       'IEGA.AS',   'EUR', 'price', 'iShares Core € Govt Bond ETF (Amsterdam)'),
    ('ust',    'US Treasuries 20+ years',    'Bonds',       'TLT',       'USD', 'price', 'iShares 20+ Year Treasury Bond ETF'),
    ('us10y',  'US 10-year yield',           'Rates',       '^TNX',      '%',   'level', 'CBOE 10-year Treasury yield'),
    ('prop',   'Global property',            'Property',    'IWDP.AS',   'EUR', 'price', 'iShares Developed Markets Property Yield ETF (Amsterdam, EUR)'),
    ('gold',   'Gold',                       'Commodities', 'GC=F',      'USD', 'price', 'Gold futures (front month)'),
    ('brent',  'Brent oil',                  'Commodities', 'BZ=F',      'USD', 'price', 'Brent crude futures (front month)'),
    ('vix',    'VIX',                        'Volatility',  '^VIX',      'pts', 'level', 'CBOE Volatility Index'),
]
FX = {'USD': 'EURUSD=X', 'GBP': 'EURGBP=X', 'JPY': 'EURJPY=X'}   # units of currency per 1 euro

def fetch(sym, rng='3y'):
    u = 'https://query1.finance.yahoo.com/v8/finance/chart/' + urllib.parse.quote(sym) + f'?range={rng}&interval=1d'
    for attempt in range(3):
        r = subprocess.run(['curl', '-sS', '-A', 'Mozilla/5.0', '--max-time', '40', u], capture_output=True, text=True)
        try:
            d = json.loads(r.stdout)['chart']['result'][0]
            q = d['indicators']['quote'][0]['close']
            out = {}
            for t, c in zip(d['timestamp'], q):
                if c is not None:
                    out[dt.datetime.fromtimestamp(t + d['meta'].get('gmtoffset', 0), dt.timezone.utc).strftime('%Y-%m-%d')] = float(c)
            if out: return out
        except Exception:
            pass
        time.sleep(2 + 3*attempt)
    raise RuntimeError(f'{sym}: no data ({r.stdout[:120]!r})')

def main(path):
    fx = {c: fetch(s) for c, s in FX.items()}
    raw = {k: fetch(sym) for k, _, _, sym, _, _, _ in SERIES}
    dates = sorted({d for v in raw.values() for d in v if dt.date.fromisoformat(d).weekday() < 5})
    # forward-fill each series (and FX) onto one weekday calendar, at most 5 days, so markets closed on a holiday show no move
    def ffill(m):
        out, last, gap = [], None, 0
        for d in dates:
            if d in m: last, gap = m[d], 0
            else: gap += 1
            out.append(last if (last is not None and gap <= 5) else None)
        return out
    fxa = {c: ffill(m) for c, m in fx.items()}
    series = []
    for k, label, group, sym, ccy, kind, src in SERIES:
        v = ffill(raw[k])
        if kind == 'price' and ccy in fxa:
            v = [None if (a is None or f is None or f == 0) else a / f for a, f in zip(v, fxa[ccy])]
        sig = lambda x: None if x is None else float(f'{x:.6g}')
        series.append({'k': k, 'label': label, 'group': group, 'symbol': sym, 'quote': ccy, 'kind': kind, 'source': src, 'v': [sig(x) for x in v]})
    # trim leading days where the first price is missing for most series
    start = next(i for i in range(len(dates)) if sum(s['v'][i] is not None for s in series) >= len(series) - 1)
    for s in series: s['v'] = s['v'][start:]
    out = {'type': 'market-data', 'version': 1, 'asOf': dates[-1], 'made': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'),
           'currency': 'EUR', 'source': 'Yahoo Finance daily closes; prices converted to euro at the same day\'s exchange rate',
           'dates': dates[start:], 'series': series}
    with open(path, 'w') as f: json.dump(out, f, separators=(',', ':'))
    print(f'{path}: {len(out["dates"])} days to {out["asOf"]}, {len(series)} series')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'market-data.json')
