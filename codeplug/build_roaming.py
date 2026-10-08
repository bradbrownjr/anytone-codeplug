#!/usr/bin/env python3
"""Regenerate the DMR roaming channels and roaming zones from the DMR repeater zones in a built codeplug.
One roaming channel per DMR site (named like its zone, RX/TX/CC from the site's first channel, Slot 2), one roaming zone per
state, plus the curated 'i95 Corridor'.  A roaming zone holds at most 60 members here (the CPS rejected 64).
Writes data/static/d878uv/RoamingChannel.CSV and RoamingZone.CSV (the 578 shares them), then run model.py build for both radios.
Usage: python3 codeplug/build_roaming.py [codeplug dir]"""
import csv, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
d = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'import' / 'd878uv'
out = ROOT / 'data' / 'static' / 'd878uv'
STATES = [('Maine', 'ME'), ('New Hampshire', 'NH'), ('Vermont', 'VT'), ('Massachusetts', 'MA'), ('Connecticut', 'CT'), ('Rhode Island', 'RI'), ('New York', 'NY')]
I95 = ['Augusta ME', 'Holden ME', 'Buckfield ME', 'Litchfield ME', 'Portland ME', 'Shapleigh ME', 'Portsmouth NH', 'Sommersworth NH', 'Bridgeport CT']
LIMIT = 60

head, *chs = list(csv.reader(open(d / 'Channel.CSV', newline='')))
i = {n: k for k, n in enumerate(head)}
by = {r[i['Channel Name']]: r for r in chs}
zones = list(csv.reader(open(d / 'Zone.CSV', newline='')))[1:]
sites = {}
for z in zones:
    first = by[z[2].split('|')[0]]
    if first[i['Channel Type']] == 'D-Digital' and z[1] != 'Simplex':
        sites[z[1]] = first
rows = [['No.', 'Receive Frequency', 'Transmit Frequency', 'Color Code', 'Slot', 'Name']]
state_members = {code: [] for _, code in STATES}
for name, r in sites.items():
    code = name.split()[-1] if name.split()[-1] in state_members else name.split()[-2]
    rows.append([str(len(rows)), r[i['Receive Frequency']], r[i['Transmit Frequency']], r[i['RX Color Code']], 'Slot2', name])
    state_members[code].append(name)
assert len(rows) - 1 <= 250
zrows = [['No.', 'Name', 'Roaming Channel Member', '']]
for zname, members in [('i95 Corridor', [m for m in I95 if m in sites])] + [(n, state_members[c]) for n, c in STATES]:
    assert 0 < len(members) <= LIMIT, (zname, len(members))
    zrows.append([str(len(zrows)), zname, '|'.join(members)])
w = lambda p, t, tail='': open(p, 'w', newline='').write(''.join('"' + '","'.join(r[:len(r) - (1 if len(r) == 4 else 0)]) + '"' + (',' if len(r) == 4 else '') + '\r\n' for r in t))
w(out / 'RoamingChannel.CSV', rows)
w(out / 'RoamingZone.CSV', zrows)
print(len(rows) - 1, 'roaming channels;', ', '.join(f'{r[1]} {len(r[2].split(chr(124)))}' for r in zrows[1:]))
