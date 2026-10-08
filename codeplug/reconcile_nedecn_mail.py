#!/usr/bin/env python3
"""Apply the 2026-10 NEDECN group-mail findings (label ham/NEDECN):
 - TG 8808 NH Lakes (TS2, PTT) on Gunstock UHF/VHF, Franklin, West Ossipee, Wakefield (Rick Zach, 2026-09-23)
 - WW English (13) dropped from the network ("No more WWE", NE1B, 2026-06-19); unused WW Spanish (14) / WW German (10) dropped too
 - Mt Snow VT is now Northfield VT (W1MTW, 2026-12-13 thread), so the Mt Snow site is removed
Usage: python3 codeplug/reconcile_nedecn_mail.py [codeplug dir]   (not idempotent)"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from cplib import Codeplug

d = Path(sys.argv[1] if len(sys.argv) > 1 else 'import/d878uv')
cp = Codeplug(d)

# Mt Snow VT: remove zone and its channels
snow = cp.members('Mt Snow VT')
cp.zones = [z for z in cp.zones if z[1] != 'Mt Snow VT']
cp.ch = [r for r in cp.ch if r[1] not in snow]
cp.reindex()

# WW English: drop channels from every zone, then the channels
ww = {r[1] for r in cp.ch if cp.col(r, 'Contact TG/DMR ID') == '13'}
for z in cp.zones:
    drop = ww & set(z[cp.zc['Zone Channel Member']].split('|'))
    if drop:
        cp.remove_from_zone(z[1], drop)
cp.ch = [r for r in cp.ch if r[1] not in ww]
cp.reindex()
cp.tgs = [r for r in cp.tgs if r[1] not in ('13', '14', '10')]

# NH Lakes on the five Lakes Region sites
for zn in ('Gunstock NH UHF', 'Gunstock NH VHF', 'Franklin NH', 'West Ossipee NH', 'Wakefield NH'):
    m = cp.members(zn)
    src = next(n for n in m if n.endswith(' NH SW'))
    pre = src[:-len(' NH SW')]
    r = list(cp.by[src]); r[1] = pre + ' NH Lakes'
    r[cp.c['Contact']] = 'NH Lakes'; r[cp.c['Contact TG/DMR ID']] = '8808'
    cp.add_channels([r], after=src)
    cp.extend_zone(zn, [r[1]])
assert not cp.validate()
cp.save()

# roaming: drop Mt Snow (text edit; RoamingZone does not round-trip through csv)
rc = d / 'RoamingChannel.CSV'
lines = [l for l in rc.read_text(newline='').split('\r\n') if l.strip()]
out = [lines[0]]
for l in lines[1:]:
    if not l.endswith('"Mt Snow VT"'):
        out.append(re.sub(r'^"\d+"', '"%d"' % len(out), l))
rc.write_text('\r\n'.join(out) + '\r\n', newline='')
rz = d / 'RoamingZone.CSV'
t = rz.read_text(newline='')
t = re.sub(r'\|?Mt Snow VT(?=[|"])', '', t).replace('"|', '"')
rz.write_text(t, newline='')
print('removed', len(snow), 'Mt Snow +', len(ww), 'WW English channels; added 5 NH Lakes')
