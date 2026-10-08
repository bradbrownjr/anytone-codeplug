#!/usr/bin/env python3
"""Create the scan lists that channels already reference by name but that ScanList.CSV never defined
(Packet and the satellites ISS, SO-50, AO-91 ...): one list per name, holding the channels that name it.
Usage: python3 codeplug/add_scanlists.py [codeplug dir]"""
import csv, sys
from pathlib import Path

d = Path(sys.argv[1] if len(sys.argv) > 1 else 'exports/d878uv')
rd = lambda f: list(csv.reader(open(d / f, newline='')))
chs = rd('Channel.CSV'); ch, rows = chs[0], chs[1:]
sc = rd('ScanList.CSV'); head, lists = sc[0], sc[1:]
have = {r[1] for r in lists}
groups = {}
for r in rows:
    n = r[ch.index('Scan List')]
    if n != 'None' and n not in have:
        groups.setdefault(n, []).append(r)
template = next(r for r in lists if r[1] == 'Weather')
for n, members in sorted(groups.items(), key=lambda kv: [r[0] for r in rows].index(kv[1][0][0])):
    f = lambda col: '|'.join(r[ch.index(col)] for r in members)
    lists.append([str(len(lists) + 1), n, f('Channel Name'), f('Receive Frequency'), f('Transmit Frequency')] + template[5:])
with open(d / 'ScanList.CSV', 'w', newline='') as fh:
    csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator='\r\n').writerows([head] + lists)
print('added scan lists:', {k: len(v) for k, v in groups.items()})
