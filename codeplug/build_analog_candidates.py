#!/usr/bin/env python3
"""Build data/sources/analog_candidates.csv: coordinator repeater records (cache/*.csv from fetch_coordinators.py) joined with
NERepeaters' last-updated dates and notes (https://nerepeaters.com/NERepeaters.php).

Columns: state,freq,call,city,updated,recent,net_or_link,pl,notes,sponsor,source.  `recent` = updated within two years;
`net_or_link` = the NERepeaters notes name a net.  Rows are 2 m / 70 cm FM only (NERepeaters mode blank), plus K8MOT Bridgton.  add_analog_states.py applies the
FM-only / activity rule to this file.   Usage: python3 codeplug/build_analog_candidates.py [--offline]
"""
import csv, datetime, glob, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'cache' / 'nerepeaters.html'


def main():
    if '--offline' not in sys.argv or not RAW.exists():
        RAW.parent.mkdir(exist_ok=True)
        RAW.write_text(subprocess.run(['curl', '-s', '-m', '60', '-A', 'Mozilla/5.0', 'https://nerepeaters.com/NERepeaters.php'], capture_output=True, text=True).stdout, encoding='utf8')
    ner = {}
    for r in csv.reader(l for l in RAW.read_text(encoding='utf8').splitlines() if l.startswith('"') and l[1].isdigit()):
        if len(r) >= 14 and r[13]:
            ner[(r[2], r[0], r[5], r[3])] = (r[13], r[12], r[4].strip())
    coord = {}
    for f in sorted(glob.glob(str(ROOT / 'cache' / '*.csv'))):
        for r in csv.DictReader(open(f, newline='')):
            coord[(r['state'], r['freq'], r['call'], r['city'])] = r
    cutoff = datetime.date.today() - datetime.timedelta(days=730)
    out = []
    for key, (date, nnotes, mode) in ner.items():
        r = coord.get(key)
        f = float(key[1])
        if not r or key[0] not in ('CT', 'MA', 'ME', 'NH', 'RI', 'VT') or not (144 <= f < 148 or 420 <= f < 450):
            continue
        if mode and not (key[2] == 'K8MOT' and key[3] == 'Bridgton'):     # FM only; the Bridgton P25/FM repeater is the one exception
            continue
        d = datetime.datetime.strptime(date, '%Y/%m/%d').date()
        link = 'net' in nnotes.lower()
        out.append(dict(state=key[0], freq=key[1], call=key[2], city=key[3], updated=d.isoformat(), recent=int(d >= cutoff), net_or_link=int(link),
                        pl=r['pl'], notes=r['notes'], sponsor=r['sponsor'], source=r['source']))
    out.sort(key=lambda r: (float(r['freq']), r['state'], r['call']))
    with open(ROOT / 'data' / 'sources' / 'analog_candidates.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, list(out[0]), lineterminator='\n'); w.writeheader(); w.writerows(out)
    print(len(out), 'candidate records,', sum(r['recent'] or r['net_or_link'] for r in out), 'pass the activity rule')


if __name__ == '__main__':
    main()
