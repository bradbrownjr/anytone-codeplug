#!/usr/bin/env python3
"""GMRS zone cleanup: put the orphaned simplex channels GMRS 1-8 (462.5625-462.7125 interstitials, 467.5625 channel 8) in front of GMRS 9
in the zone and the 'GMRS' scan list, and drop the repeaters that already sit in their state's GMRS zone (the zone is simplex only).
Usage: python3 codeplug/fix_gmrs_zone.py [codeplug dir]   (not idempotent)"""
import csv, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from cplib import Codeplug

d = Path(sys.argv[1] if len(sys.argv) > 1 else 'import/d878uv')
cp = Codeplug(d)
names = [f'GMRS {n}' for n in range(1, 9)]          # these channels already exist in the codeplug but sit in no zone or scan list
assert all(n in cp.by for n in names)

state_gmrs = {m for z in cp.zones if z[1].endswith(' GMRS') and z[1] != 'GMRS' for m in cp.members(z[1])}
repeaters = [n for n in cp.members('GMRS') if not n.startswith('GMRS ')]
drop = [n for n in repeaters if n in set(cp.members('ME GMRS'))]
cp.remove_from_zone('GMRS', set(drop))
z = cp.zone('GMRS')
members = names + cp.members('GMRS')
for k, f in (('Zone Channel Member', lambda m: m), ('Zone Channel Member RX Frequency', lambda m: cp.col(cp.by[m], 'Receive Frequency')),
             ('Zone Channel Member TX Frequency', lambda m: cp.col(cp.by[m], 'Transmit Frequency'))):
    z[cp.zc[k]] = '|'.join(f(m) for m in members)
for k, n in (('A Channel', members[0]), ('B Channel', members[0])):
    z[cp.zc[k]] = n
    z[cp.zc[k + ' RX Frequency']] = cp.col(cp.by[n], 'Receive Frequency')
    z[cp.zc[k + ' TX Frequency']] = cp.col(cp.by[n], 'Transmit Frequency')
assert not cp.validate()
cp.save()

# scan list 'GMRS': new channels first
path = d / 'ScanList.CSV'
t = list(csv.reader(open(path, newline='')))
h = {n: i for i, n in enumerate(t[0])}
for r in t[1:]:
    if r[h['Scan List Name']] == 'GMRS':
        m = names + r[h['Scan Channel Member']].split('|')
        r[h['Scan Channel Member']] = '|'.join(m)
        r[h['Scan Channel Member RX Frequency']] = '|'.join(cp.col(cp.by[x], 'Receive Frequency') for x in m)
        r[h['Scan Channel Member TX Frequency']] = '|'.join(cp.col(cp.by[x], 'Transmit Frequency') for x in m)
with open(path, 'w', newline='') as f:
    csv.writer(f, quoting=csv.QUOTE_ALL, lineterminator='\r\n').writerows(t)
print('added', names, '| dropped from GMRS zone:', drop, '| still there (repeaters not in ME GMRS):', [n for n in repeaters if n not in drop])
