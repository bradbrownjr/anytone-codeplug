#!/usr/bin/env python3
"""Build per-state GMRS repeater zones from data/sources/gmrs_snapshots.csv (myGMRS screenshots, 2026-10-07).

Rule: every listed repeater, including Permission Required / Members Only ones (Brad has the owners' permission);
repeaters with an unlisted tone get no tone; skip DPL (DCS) tones until the CSV DCS format is confirmed.  Repeater output = listed frequency, input = +5 MHz.  TX CTCSS = the listed "Tone In"; receive
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
        if 'DPL' in r['tone_in'] or 'DPL' in r['tone_out']:
            skipped.append(f"{r['state']} {r['city']} {r['rx']} {r['tone_in']}"); continue
        rx = float(r['rx']); tx = round(rx + 5, 4); tone = r['tone_in'] or 'Off'
        n = next((c[1] for c in cp.by_rx(rx) if cp.col(c, 'Transmit Frequency') == '%.5f' % tx and cp.col(c, 'CTCSS/DCS Encode') == tone
                  and cp.col(c, 'Channel Type') == 'A-Analog' and cp.col(c, 'PTT Prohibit') != 'On'), None)
        if not n:
            n = short(r['city'], 16 - 4) + '-' + r['rx'][-3:]
            if n in cp.by:
                n = short(r['city'], 16 - 7) + ' ' + r['state'] + '-' + r['rx'][-3:]
            assert n not in cp.by, n
            cp.add_channels([cp.new_channel('Gray-575', n, rx, tx, decode='Off', encode=tone)]); new.append(n)
        if n not in per[r['state']]:
            per[r['state']].append(n)
    for st, names in per.items():
        names += [m for m in EXISTING.get(st, []) if m not in names]
        if names and cp.zone(ZONES[st]):
            cp.extend_zone(ZONES[st], names)
        elif names:
            cp.add_zone(ZONES[st], sorted(names, key=lambda m: (float(cp.col(cp.by[m], 'Receive Frequency')), m)), before='Packet')
    errs = cp.validate(); assert not errs, errs[:10]
    cp.save(); print(len(new), 'new;', {s: len(v) for s, v in per.items()}, 'skipped', skipped)
