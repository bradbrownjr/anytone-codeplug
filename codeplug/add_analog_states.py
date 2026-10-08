#!/usr/bin/env python3
"""Add per-state FM repeater zones from data/sources/analog_candidates.csv (coordinator records joined with
NERepeaters last-updated dates).

Rule: FM-only (no DMR/P25/Fusion/D-STAR in the notes), listed by the coordinator (not '#' flagged), and either updated
within two years or noted as a net/link repeater.  Offsets come from the New England band plan (2m: 145.1-145.5 and
146.6-147.0 are -0.6, 147.0-147.4 and 146.0-146.4 are +0.6; 70cm: output 440-445 is +5, 447-450 is -5).  Outputs that fit
neither (147.4+, 445-447) are skipped and listed.  Existing channels are reused when RX, TX and tone match and
are never modified.  New zones: CT/MA/RI/VT Analog; ME Analog and NH Analog are extended.
Usage: python3 codeplug/add_analog_states.py [codeplug dir]
"""
import csv, sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from cplib import Codeplug
from naming import repeater_name, band_tag
from add_me_ares import analog

DIGITAL = ('DMR', 'P25', 'FUSION', 'D-STAR', 'DSTAR', 'YSF')
ZONES = {'CT': 'CT Analog', 'MA': 'MA Analog', 'ME': 'ME Analog', 'NH': 'NH Analog', 'RI': 'RI Analog', 'VT': 'VT Analog'}


def offset(f):
    if 145.1 <= f < 145.5 or 146.6 <= f < 147.0:
        return -0.6
    if 147.0 <= f < 147.4:
        return 0.6
    if 440 <= f < 445:
        return 5.0
    if 447 <= f < 450:
        return -5.0
    return None


def select(path='data/sources/analog_candidates.csv'):
    for r in csv.DictReader(open(path, newline='')):
        if r['state'] not in ZONES or r['notes'].startswith('#') or any(d in r['notes'].upper() for d in DIGITAL):
            continue
        if r['recent'] == '1' or r['net_or_link'] == '1':
            yield r


if __name__ == '__main__':
    cp = Codeplug(sys.argv[1] if len(sys.argv) > 1 else 'import/d878uv')
    per, skipped, seen, new = {}, [], set(), 0
    for r in select():
        f = float(r['freq'])
        key = (r['state'], r['freq'], r['call'], r['city'])
        if key in seen:
            continue
        seen.add(key)
        off = offset(f)
        if off is None:
            skipped.append(f"{r['state']} {r['call']} {r['city']} {r['freq']}")
            continue
        tx = round(f + off, 4)
        tone = r['pl'] if r['pl'] else 'Off'
        n = analog(cp, f, tx=tx, tone=None if tone == 'Off' else tone)
        if not n:
            n = repeater_name(r['call'], r['city'])
            if n in cp.by:
                n = repeater_name(r['call'], r['city'], band_tag(f))
            cp.add_channels([cp.new_channel('W1QUI Falmouth', n, f, tx, decode=tone, encode=tone,
                                            **({} if tone != 'Off' else {'Squelch Mode': 'Carrier'}))])
            new += 1
        per.setdefault(r['state'], [])
        if n not in per[r['state']]:
            per[r['state']].append(n)
    for st, names in per.items():
        zn = ZONES[st]
        if cp.zone(zn):
            cp.extend_zone(zn, names)
        else:
            cp.add_zone(zn, sorted(names, key=lambda m: float(cp.col(cp.by[m], 'Receive Frequency'))), before='Packet')
    errs = cp.validate(); assert not errs, errs[:10]
    cp.save()
    print('new channels', new, {s: len(v) for s, v in per.items()}, 'skipped', skipped)
