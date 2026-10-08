#!/usr/bin/env python3
"""Add the `US Interop` zone from NIFOG 2.02 (VHF/UHF national, federal IR/LE and UHF medical channels).

Everything is receive-only (PTT Prohibit on, TX = RX, carrier squelch) and reuses an existing channel with the
same RX frequency. Skipped: 700/800 MHz, low band, VTAC17 (inland counties only). VTAC33-38 receive on the
VTAC11-14 frequencies, so they need no channels of their own. Hex NAC/tones ($68F) are left Off.

Usage: python3 codeplug/add_nifog.py [codeplug dir]
"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from cplib import Codeplug
from add_maine_fog import TEMPLATE, RXONLY

# (name, RX MHz, tone) -- tone is the channel's CTCSS (156.7 national/medical, 167.9 federal, 'Off' for CSQ/hex)
VHF = [('VCALL 10', 155.7525, '156.7'), ('VTAC 11', 151.1375, '156.7'), ('VTAC 12', 154.4525, '156.7'),
       ('VTAC 13', 158.7375, '156.7'), ('VTAC 14', 159.4725, '156.7'), ('VSAR 16', 155.1600, '127.3'),
       ('VFIRE 21', 154.2800, 'Off'), ('VFIRE 22', 154.2650, 'Off'), ('VFIRE 23', 154.2950, 'Off'),
       ('VFIRE 24', 154.2725, 'Off'), ('VFIRE 25', 154.2875, 'Off'), ('VFIRE 26', 154.3025, 'Off'),
       ('VMED 28', 155.3400, '156.7'), ('VMED 29', 155.3475, 'Off'), ('VLAW 31', 155.4750, 'Off'), ('VLAW 32', 155.4825, 'Off')]
FED_VHF = [('FED NC1', 169.5375, '167.9'), ('FED IR1', 170.0125, '167.9'), ('FED IR2', 170.4125, '167.9'),
           ('FED IR3', 170.6875, '167.9'), ('FED IR4', 173.0375, '167.9'), ('FED LE A', 167.0875, '167.9'),
           ('FED LE2', 167.2500, 'Off'), ('FED LE3', 167.7500, 'Off'), ('FED LE4', 168.1125, 'Off'), ('FED LE5', 168.4625, 'Off')]
UHF = [('UCALL 40', 453.2125, '156.7'), ('UTAC 41', 453.4625, '156.7'), ('UTAC 42', 453.7125, '156.7'), ('UTAC 43', 453.8625, '156.7')]
FED_UHF = [('FED NC2', 410.2375, '167.9'), ('FED IR10', 410.4375, '167.9'), ('FED IR11', 410.6375, '167.9'),
           ('FED IR12', 410.8375, '167.9'), ('FED IR13', 413.1875, '167.9'), ('FED IR14', 413.2125, '167.9'),
           ('FED LE B', 414.0375, '167.9'), ('FED LE10', 409.9875, '167.9'), ('FED LE11', 410.1875, 'Off'),
           ('FED LE12', 410.6125, 'Off'), ('FED LE13', 414.0625, 'Off'), ('FED LE14', 414.3125, 'Off'), ('FED LE15', 414.3375, 'Off')]
MED = [('MED %s' % n, f, '156.7') for n, f in zip(
    '9 92 10 102 1 12 2 22 3 32 4 42 5 52 6 62 7 72 8 82'.split(),
    [462.95 + 0.0125 * i for i in range(20)])]
MED = [(n, round(f, 4), t) for n, f, t in MED]

if __name__ == '__main__':
    cp = Codeplug(sys.argv[1] if len(sys.argv) > 1 else 'import/d878uv')
    members, new = [], 0
    last = 'CCFIRE'
    for name, rx, tone in VHF + FED_VHF + UHF + FED_UHF + MED:
        ex = cp.by_rx(rx)
        if ex:
            n = ex[0][1]
        else:
            n = name
            cp.add_channels([cp.new_channel(TEMPLATE, name, rx, rx, decode='Off', encode=tone, **RXONLY)], after=last)
            last = name
            new += 1
        if n not in members:
            members.append(n)
    cp.add_zone('US Interop', members, before='Packet')
    errs = cp.validate()
    assert not errs, errs[:10]
    cp.save()
    print(f'US Interop: {len(members)} members, {new} new channels')
