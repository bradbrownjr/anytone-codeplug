#!/usr/bin/env python3
"""Fetch the public repeater lists of New England's frequency coordinators into cache/ (gitignored).

  nesmc  NESMC  (ME NH MA RI)  search form at nesmc.org/rptr.html
  csma   CSMA   (CT)           search form at ctspectrum.com (same backend as NESMC, different template)
  vircc  VIRCC  (VT)           static HTML table at ranv.org/rptr.html

The search backend only does radius queries (max 120 mi) around a place, so we sweep a few centers
per state and de-duplicate. Owners can hide records, so absence from a list is not proof a repeater
is uncoordinated.

Usage: python3 codeplug/fetch_coordinators.py [nesmc csma vircc]   (default: all)
Writes cache/<source>_<band>.csv for nesmc/csma and cache/vircc.csv.
"""
import csv, html, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

UA = 'Mozilla/5.0 (X11; Linux x86_64) anytone-codeplug/KC1JMH'
DB_URL = 'https://rptr.amateur-radio.net/cgi-bin/exec.cgi'
DB = {
    'nesmc': ['Portland, ME', 'Bangor, ME', 'Presque Isle, ME', 'Calais, ME', 'Rangeley, ME', 'Augusta, ME',
              'Concord, NH', 'Berlin, NH', 'Keene, NH', 'Worcester, MA', 'Boston, MA', 'Springfield, MA',
              'Pittsfield, MA', 'Barnstable, MA', 'Providence, RI'],
    'csma': ['Hartford, CT', 'Norwich, CT', 'Danbury, CT'],
}
BANDS = ['144', '440']
COLS = ['source', 'state', 'city', 'freq', 'offset', 'pl', 'call', 'sponsor', 'notes']


def fetch(url, data=None):
    req = urllib.request.Request(url, data, {'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9'})
    return urllib.request.urlopen(req, timeout=60).read().decode('latin-1')


def cells(row):
    return [html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', c.replace('&nbsp;', ' ')))).strip()
            for c in re.findall(r'<TD[^>]*>(.*?)</TD>', row, re.S | re.I)]


def fetch_db(source, band):
    seen = {}
    for center in DB[source]:
        data = urllib.parse.urlencode({'task': 'rsearch', 'template': source, 'dbfilter': source, 'band': f'{band},',
                                       'sortby': 'freq', 'meth': 'RPList', 'radi': 120, 'loca': center, 'final': 'Go!'}).encode()
        page = fetch(DB_URL, data)
        for row in re.findall(r'<TR[^>]*CLASS=line\d[^>]*>(.*?)</TR>', page, re.S | re.I):
            c = cells(row)
            if len(c) != 7:
                continue
            city, freq, pl, call, _dist, sponsor, notes = c
            city, _, state = city.rpartition(', ')
            seen[(freq, call, city, state)] = dict(source=source, state=state, city=city, freq=freq, offset='',
                                                   pl=pl, call=call, sponsor=sponsor, notes=notes)
        print(f'{source} {band} {center}: {len(seen)} unique', file=sys.stderr)
        time.sleep(2)
    return sorted(seen.values(), key=lambda r: (r['freq'], r['state'], r['city']))


def fetch_vircc():
    page = re.sub(r'<!--.*?-->', '', fetch('https://www.ranv.org/rptr.html'), flags=re.S)   # drop commented-out rows
    out = []
    for row in re.findall(r'<tr>(.*?)</tr>', page, re.S | re.I):
        c = [html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', x.replace('&nbsp;', ' ')))).strip()
             for x in re.findall(r'<td[^>]*>(.*?)</td>', row, re.S | re.I)]
        if len(c) != 11 or not re.match(r'^[\d.]+$', c[0]):
            continue
        freq, off, mode, acc, call, loc, region, sponsor, coord, flag, links = c
        m = re.match(r'^(.*?),?\s+(NY|NH|MA|QC|ME|CT)$', loc)
        city, state = (m.group(1), m.group(2)) if m else (loc, 'VT')
        notes = ' '.join(x for x in (mode, acc, f'region:{region}', f'coord:{coord}', f'flag:{flag}' if flag else '', links) if x)
        out.append(dict(source='vircc', state=state, city=city, freq=freq, offset=off, pl=acc if mode == 'FM' else '',
                        call=call, sponsor=sponsor, notes=notes))
    return out


def write(path, rows):
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, COLS); w.writeheader(); w.writerows(rows)
    print(f'wrote {path}: {len(rows)} rows', file=sys.stderr)


def main(sources):
    Path('cache').mkdir(exist_ok=True)
    for s in sources:
        if s == 'vircc':
            write('cache/vircc.csv', fetch_vircc())
        else:
            for band in BANDS:
                write(f'cache/{s}_{band}.csv', fetch_db(s, band))


if __name__ == '__main__':
    main(sys.argv[1:] or ['nesmc', 'csma', 'vircc'])
