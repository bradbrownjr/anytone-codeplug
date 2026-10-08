#!/usr/bin/env python3
"""Build per-state GMRS repeater zones from data/sources/gmrs_snapshots.csv (myGMRS screenshots, 2026-10-07).

Rule: every listed repeater, including Permission Required / Members Only ones (Brad has the owners' permission);
repeaters with an unlisted tone get no tone; DPL (DCS) tones are written as D<code>N (normal polarity).  Repeater output = listed frequency, input = +5 MHz.  TX CTCSS = the listed "Tone In"; receive
tone squelch is left Off (matches the existing GMRS repeater channels).  Names `<City>-<ch>` (ch = last three digits).
Repeaters listed with no tone (private/permission-only, 'Unlisted' on myGMRS) get a trailing `*` in the name to flag missing info.
Channels are shared only within a state (same frequency and tone), plus the original channels listed in EXISTING; existing channels are never modified; the original `GMRS` zone is untouched.
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
    cp = Codeplug(sys.argv[1] if len(sys.argv) > 1 else 'import/d878uv')
    per, new, skipped, made = {s: [] for s in ZONES}, [], [], {}
    for r in csv.DictReader(open('data/sources/gmrs_snapshots.csv', newline='')):
        st, rx = r['state'], float(r['rx'])
        tx = round(rx + 5, 4); tone = r['tone_in'] or 'Off'
        if 'DPL' in tone:
            tone = 'D%sN' % tone.split()[0]     # AnyTone CSV DCS: 'D' + 3-digit code + N (normal polarity); see TODO.md, test one import first
        star = '*' if not r['tone_in'] and r['type'] != 'Open System' else ''
        # reuse only within the same state: a channel created earlier in this run, or an original channel for this state
        n = made.get((st, rx, tone))
        if not n:
            n = next((m for m in EXISTING.get(st, []) if cp.col(cp.by[m], 'Receive Frequency') == '%.5f' % rx
                      and cp.col(cp.by[m], 'Transmit Frequency') == '%.5f' % tx and cp.col(cp.by[m], 'CTCSS/DCS Encode') == tone), None)
        if not n:
            n = short(r['city'], 16 - 4 - len(star)) + '-' + r['rx'][-3:] + star
            if n in cp.by:
                n = short(r['city'], 16 - 7 - len(star)) + ' ' + st + '-' + r['rx'][-3:] + star
            assert n not in cp.by, n
            cp.add_channels([cp.new_channel('Gray-575', n, rx, tx, decode='Off', encode=tone)]); new.append(n)
        made[(st, rx, tone)] = n
        if n not in per[st]:
            per[st].append(n)
    for st, names in per.items():
        names += [m for m in EXISTING.get(st, []) if m not in names]
        if names:
            cp.add_zone(ZONES[st], sorted(names, key=lambda m: (float(cp.col(cp.by[m], 'Receive Frequency')), m)), before='Packet')
    errs = cp.validate(); assert not errs, errs[:10]
    cp.save(); print(len(new), 'new;', {s: len(v) for s, v in per.items()}, 'skipped', skipped)
