#!/usr/bin/env python3
"""Fetch financial news headlines from Marketaux for Portfolio Builder (adviser, 10 Nov 2026).

Keeps headlines, the provider's short description, source, link, time and the companies/markets
mentioned. Never the article text. The API key comes from the MARKETAUX_KEY repository secret.
Usage: python3 news_fetch.py news.json
"""
import json, os, sys, datetime, urllib.request, urllib.parse

KEY = os.environ.get('MARKETAUX_KEY', '').strip()
OUT = sys.argv[1] if len(sys.argv) > 1 else 'news.json'
API = 'https://api.marketaux.com/v1/news/all'
KEEP_DAYS, CAP = 7, 90
# one request per topic; the free plan gives 100 requests a day and 3 articles per request
TOPICS = [
    ('Markets', {'countries': 'us,gb,de,fr,jp', 'must_have_entities': 'true'}),
    ('Europe & Ireland', {'countries': 'ie,de,fr,nl,it,es,ch', 'must_have_entities': 'true'}),
    ('Technology', {'industries': 'Technology', 'countries': 'us', 'must_have_entities': 'true'}),
    ('Emerging markets & Asia', {'countries': 'cn,tw,kr,in,hk,au,sg,br', 'must_have_entities': 'true'}),
    ('Energy & commodities', {'search': 'oil | gold | copper | OPEC | commodities'}),
    ('Central banks & rates', {'search': '"ECB" | "Federal Reserve" | "interest rates" | "bond yields" | inflation'}),
    ('Ireland', {'countries': 'ie', 'must_have_entities': 'true'}),
]

def get(params):
    q = {'api_token': KEY, 'language': 'en', 'group_similar': 'true', 'limit': '3', **params}
    req = urllib.request.Request(API + '?' + urllib.parse.urlencode(q), headers={'User-Agent': 'portfolio-builder-news/1'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def main():
    if not KEY:
        print('No MARKETAUX_KEY secret yet: nothing to do.')
        return 0
    now = datetime.datetime.now(datetime.timezone.utc)
    since = (now - datetime.timedelta(days=2)).strftime('%Y-%m-%dT%H:%M')
    fresh, ok = [], 0
    for group, params in TOPICS:
        try:
            d = get({**params, 'published_after': since})
            ok += 1
        except Exception as e:  # one topic failing must not stop the rest
            print(f'{group}: {e}')
            continue
        for a in d.get('data', []):
            ents = sorted(a.get('entities') or [], key=lambda e: -(e.get('match_score') or 0))[:6]
            fresh.append({
                'id': a.get('uuid') or a.get('url'), 'group': group,
                'title': (a.get('title') or '').strip(), 'description': (a.get('description') or '').strip()[:400],
                'source': a.get('source') or '', 'url': a.get('url') or '', 'published': a.get('published_at') or '',
                'entities': [{'symbol': e.get('symbol'), 'name': e.get('name'), 'country': (e.get('country') or '').lower(),
                              'industry': e.get('industry'), 'type': e.get('type'), 'sentiment': e.get('sentiment_score')} for e in ents],
            })
    if ok == 0:
        print('Every request failed: keeping the previous file.')
        return 1
    old = []
    if os.path.exists(OUT):
        try:
            old = json.load(open(OUT)).get('items', [])
        except Exception:
            old = []
    cut = (now - datetime.timedelta(days=KEEP_DAYS)).isoformat()
    seen, items = set(), []
    for it in sorted(fresh + old, key=lambda x: x.get('published', ''), reverse=True):
        k = it.get('url') or it.get('id')
        if not it.get('title') or k in seen or it.get('published', '') < cut[:19]:
            continue
        seen.add(k); items.append(it)
    out = {'type': 'market-news', 'version': 1, 'made': now.isoformat(timespec='seconds'), 'source': 'Marketaux', 'items': items[:CAP]}
    json.dump(out, open(OUT, 'w'), indent=1, ensure_ascii=False)
    print(f'{len(fresh)} new, {len(out["items"])} kept')
    return 0

if __name__ == '__main__':
    sys.exit(main())
