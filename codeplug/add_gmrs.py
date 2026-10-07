#!/usr/bin/env python3
"""Build per-state GMRS repeater zones from data/sources/gmrs_snapshots.csv (myGMRS screenshots, 2026-10-07).

Rule: Open System repeaters only (others need the owner's permission or membership); skip DPL (DCS) tones until the CSV
DCS format is confirmed.  Repeater output = listed frequency, input = +5 MHz.  TX CTCSS = the listed "Tone In"; receive
tone squelch is left Off (matches the existing GMRS repeater channels).  Names `<City>-<ch>` (ch = last three digits).
Existing channels are reused when RX/TX/tone match and never modified; the original `GMRS` zone is untouched.
Usage: python3 codeplug/add_gmrs.py [codeplug dir]
"""
import csv, sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from cplib import Codeplug, short
from add_me_ares import analog

ZONES = {s: f'{s} GMRS' for s in ('CT', 'MA', 'ME', 'NH', 'RI', 'VT', 'NY')}
# existing repeater channels (original GMRS zone) that belong in a state zone
EXISTING = {'ME': ['Brunswick-700', 'Falmouth-650', 'Gray-575', 'Hiram-575', 'Portland-725', 'Shapleigh-Fam', 'Shapleigh-Pub', 'Waterboro-625', 'Woodstock-675'],
            'NH': ['Milton--700', 'Ossipee-550']}

if __name__ == '__main__':
    cp = Codeplug(sys.argv[1] if len(sys.argv) > 1 else 'exports/d878uv')
    per, new, skipped = {s: [] for s in ZONES}, [], []
    for r in csv.DictReader(open('data/sources/gmrs_snapshots.csv', newline='')):
        if r['type'] != 'Open System':
            continue
        if 'DPL' in r['tone_in'] or 'DPL' in r['tone_out']:
            skipped.append(f"{r['state']} {r['city']} {r['rx']} {r['tone_in']}"); continue
        rx = float(r['rx']); tx = round(rx + 5, 4); tone = r['tone_in'] or 'Off'
        n = analog(cp, rx, tx=tx, tone=None if tone == 'Off' else tone)
        if not n:
            n = short(r['city'], 16 - 4) + '-' + r['rx'][-3:]
            assert n not in cp.by, n
            cp.add_channels([cp.new_channel('Gray-575', n, rx, tx, decode='Off', encode=tone)]); new.append(n)
        if n not in per[r['state']]:
            per[r['state']].append(n)
    for st, names in per.items():
        names += [m for m in EXISTING.get(st, []) if m not in names]
        if names:
            cp.add_zone(ZONES[st], sorted(names, key=lambda m: (float(cp.col(cp.by[m], 'Receive Frequency')), m)), before='Packet')
    errs = cp.validate(); assert not errs, errs[:10]
    cp.save(); print(len(new), 'new;', {s: len(v) for s, v in per.items()}, 'skipped', skipped)
