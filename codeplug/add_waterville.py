#!/usr/bin/env python3
"""Add the Waterville ME DMR site (146.925 / 146.325, CC12, TS2 TG 3123) listed on the state ARES EC's emcomm sheet.
NEDECN has no page for it, so the channel set is copied from the Augusta ME site (same Maine standard set, same
slots) with prefix WTVME; also added to the NEDECN (ALL) and Maine roaming zones.  Verify against NEDECN when listed.
Usage: python3 codeplug/add_waterville.py [codeplug dir]"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from cplib import Codeplug

RX, TX, CC = 146.925, 146.325, '12'
d = Path(sys.argv[1] if len(sys.argv) > 1 else 'import/d878uv')
cp = Codeplug(d)
src = cp.members('Augusta ME')
names = []
rows = []
for n in src:
    new = 'WTVME' + n[len('AUGME'):]
    r = list(cp.by[n])
    r[1] = new
    r[cp.c['Receive Frequency']] = '%.5f' % RX
    r[cp.c['Transmit Frequency']] = '%.5f' % TX
    r[cp.c['RX Color Code']] = CC
    r[cp.c['TxCC']] = CC
    rows.append(r); names.append(new)
last = src[-1]
cp.add_channels(rows, after=cp.members('Topsham ME')[-1])
cp.add_zone('Waterville ME', names, before='Bow NH')
assert not cp.validate()
cp.save()
# roaming: channel row + membership in NEDECN (ALL) and Maine (RoamingZone does not round-trip through csv, edit as text)
rc = d / 'RoamingChannel.CSV'
t = rc.read_text(newline='')
n = len([l for l in t.split('\r\n') if l.strip()])
rc.write_text(t.rstrip('\r\n') + '\r\n"%d","%.5f","%.5f","%s","Slot2","Waterville ME"\r\n' % (n, RX, TX, CC), newline='')
rz = d / 'RoamingZone.CSV'
t = rz.read_text(newline='')
t = re.sub(r'(?m)^("\d+","(?:NEDECN \(ALL\)|Maine)","[^"\r\n]*)"', r'\1|Waterville ME"', t)
rz.write_text(t, newline='')
print('added Waterville ME:', len(names), 'channels')
