#!/usr/bin/env python3
"""Extend `ME ARES` with the York County ECT (YCECT, k1yem.com) ICS-217A frequencies not already in the codeplug:
KB1PRG Alfred 444.850 and KC1ETT Wells 448.025 repeaters, 70cm simplex 446.075/446.175, packet 145.730.
(The GMRS Fort Ridge repeater and GMRS 15/16 belong to the GMRS refresh.)  Usage: python3 codeplug/add_york_ect.py [dir]
"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from cplib import Codeplug
from add_me_ares import analog

if __name__ == '__main__':
    cp = Codeplug(sys.argv[1] if len(sys.argv) > 1 else 'exports/d878uv')
    last = cp.members('ME ARES')[-1]
    members, new = [], []
    for name, rx, tx, tone, tmpl in [('KB1PRG Alfred', 444.85, 449.85, '103.5', 'W1QUI Falmouth'), ('KC1ETT Wells', 448.025, 443.025, '103.5', 'W1QUI Falmouth'),
                                     ('ME 446.075', 446.075, 446.075, 'Off', 'ECT1'), ('ME 446.175', 446.175, 446.175, 'Off', 'ECT1'),
                                     ('PKT 145.730', 145.73, 145.73, 'Off', 'ECT1')]:
        n = analog(cp, rx, tx=tx, tone=None if tone == 'Off' else tone)
        if not n:
            n = name
            cp.add_channels([cp.new_channel(tmpl, n, rx, tx, decode=tone, encode=tone)], after=last)
            new.append(n)
        members.append(n)
    cp.extend_zone('ME ARES', members)
    errs = cp.validate(); assert not errs, errs[:10]
    cp.save()
    print('added', new)
