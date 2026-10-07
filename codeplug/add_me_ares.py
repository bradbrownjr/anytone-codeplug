#!/usr/bin/env python3
"""Add the `ME ARES` zone from the 2020 Maine ARES frequency list (ka1aar.org/download/MaineARESFreqs.pdf).

Simplex: every county primary/secondary/tertiary frequency, one channel per unique frequency (reused when an
analog transmit-capable simplex channel already exists). Repeaters: reused when an analog channel already has the
same RX frequency and tone; otherwise created, named `<CALL> <City>` from the NESMC record matching frequency + PL.
Not on the D878UV (52.525, 223.500) or not matched to a coordinated repeater (Penobscot 145.450/67.0,
Piscataquis 147.150/71.9) are skipped. Existing channels are never modified.

Usage: python3 codeplug/add_me_ares.py [codeplug dir]
"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from cplib import Codeplug
from naming import repeater_name

SIMPLEX = [146.400, 146.415, 146.430, 146.445, 146.460, 146.475, 146.490, 146.505, 146.520, 146.535, 146.550,
           146.565, 146.580, 146.595, 147.420, 147.435, 147.450, 147.465, 147.480, 147.495, 147.510, 147.525,
           147.540, 147.555, 147.565, 147.570, 147.585, 446.050, 446.150, 446.250, 446.500]
# (RX MHz, PL, call, city) -- RX is the repeater output; None call = must already exist in the codeplug
REPEATERS = [(146.610, '88.5', 'W1NPP', 'Auburn'), (147.315, '103.5', 'W1NPP', 'Poland'), (146.730, '62.5', 'W1KVI', 'Falmouth'),
             (146.730, '91.5', 'KA1C', 'Madison'), (146.730, '123.0', 'K1FS', 'Caribou'), (147.180, '123.0', 'W1BHR', 'Farmington'),
             (146.910, '151.4', 'KB1NEB', 'Ellsworth'), (145.390, '100.0', 'W1FDC', 'Farmington'), (147.060, '91.5', 'W1PBR', 'Hope'),
             (145.490, '91.5', 'KC1CG', 'Washington'), (146.985, '136.5', 'K1LX', 'Newcastle'), (146.880, '100.0', 'KQ1L', 'Buckfield'),
             (147.105, '103.5', 'N1BUG', 'Brownville'), (147.210, '100.0', 'KS1R', 'Phippsburg'), (147.270, '136.5', 'W1EMA', 'Knox'),
             (147.330, '118.8', 'W1LH', 'Cooper'), (145.410, '103.5', 'WJ1L', 'Alfred'), (147.345, '123.0', 'W1BHR', 'Alfred'),
             (147.090, '100.0', 'W1QUI', 'Falmouth')]


def analog(cp, rx, tx=None, tone=None):
    for r in cp.by_rx(rx):
        if cp.col(r, 'Channel Type') != 'A-Analog' or cp.col(r, 'PTT Prohibit') == 'On':
            continue
        if tx is not None and cp.col(r, 'Transmit Frequency') != '%.5f' % tx:
            continue
        if tone is not None and cp.col(r, 'CTCSS/DCS Encode') != tone:
            continue
        return r[1]


if __name__ == '__main__':
    cp = Codeplug(sys.argv[1] if len(sys.argv) > 1 else 'exports/d878uv')
    members, new, last = [], [], 'ECT3'
    def use(name):
        if name not in members:
            members.append(name)
    for f in SIMPLEX:
        n = analog(cp, f, tx=f)
        if not n:
            n = 'ME %.3f' % f
            cp.add_channels([cp.new_channel('ECT1', n, f, f)], after=last)
            last = n; new.append(n)
        use(n)
    for f, pl, call, city in REPEATERS:
        n = analog(cp, f, tone=pl)
        if not n:
            n = repeater_name(call, city)
            tx = f - 0.6 if f < 147.0 else f + 0.6
            cp.add_channels([cp.new_channel('W1QUI Falmouth', n, f, round(tx, 4), decode=pl, encode=pl)], after=last)
            last = n; new.append(n)
        use(n)
    cp.add_zone('ME ARES', members, before='Packet')
    errs = cp.validate()
    assert not errs, errs[:10]
    cp.save()
    print(f'ME ARES: {len(members)} members, {len(new)} new: {new}')
