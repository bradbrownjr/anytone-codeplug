#!/usr/bin/env python3
"""Apply the newer Maine Amateur Radio Emcomm Frequencies sheet (state ARES EC) on top of the 2020 list.

Changes vs the 2020 PDF: Androscoggin repeaters W1NPP Auburn/Poland are off the air (dropped from ME ARES; their
channels stay), new repeaters Aroostook Fort Kent 146.640 and Houlton 146.790, Hancock 147.030, Oxford 147.120,
Washington 146.775 (192.8), Waldo 443.500, Cumberland 449.225 (local ops), Washington primary simplex 147.595,
statewide UHF 446.000.  Penobscot 145.450 (67.0) is still listed but has no callsign anywhere (named ME 145.450).
Callsigns/cities from NESMC.  Usage: python3 codeplug/add_emcomm2026.py [dir]
"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from cplib import Codeplug
from add_me_ares import analog

REPEATERS = [('N1SJV Fort Kent', 146.640, 146.040, '100.0'), ('W1BC Houlton', 146.790, 146.190, '100.0'),
             ('W1TU Hulls Cove', 147.030, 147.630, '100.0'), ('W1OCA Norway', 147.120, 147.720, '136.5'),
             ('K1HF Marshfield', 146.775, 146.175, '192.8'), ('W1EMA Knox 70cm', 443.500, 448.500, '103.5'),
             ('WS1EC', 449.225, 444.225, '103.5'), ('ME 145.450', 145.450, 144.850, '67.0')]

if __name__ == '__main__':
    cp = Codeplug(sys.argv[1] if len(sys.argv) > 1 else 'exports/d878uv')
    # W1NPP Auburn/Poland (off air, expected back) were first dropped here, then restored by Brad's request; they stay in ME ARES.
    members, new = [], []
    for name, rx, tx, pl in REPEATERS:
        n = analog(cp, rx, tx=tx, tone=pl)
        if not n:
            n = name
            cp.add_channels([cp.new_channel('W1QUI Falmouth', n, rx, tx, decode=pl, encode=pl)]); new.append(n)
        members.append(n)
    for f in (147.595, 446.000):
        n = analog(cp, f, tx=f)
        if not n:
            n = 'ME %.3f' % f
            cp.add_channels([cp.new_channel('ECT1', n, f, f)]); new.append(n)
        members.append(n)
    cp.extend_zone('ME ARES', members)
    errs = cp.validate(); assert not errs, errs[:10]
    cp.save(); print('new', new)
