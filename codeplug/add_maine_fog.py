#!/usr/bin/env python3
"""Add channels and zones from data/sources/maine_fog.csv (parsed Maine Statewide Interoperability FOG).

All government channels are added receive-only (PTT Prohibit on, TX = RX, carrier squelch) and are reused
when a channel with the same RX frequency already exists. Existing channels are never modified.

Usage: python3 codeplug/add_maine_fog.py <stage> [codeplug dir]    stage: state-net | interop | counties
"""
import csv, re, sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from cplib import Codeplug, short

TEMPLATE = 'CHF 265'          # existing analog 12.5K carrier-squelch channel
RXONLY = {'Transmit Power': 'Low', 'PTT Prohibit': 'On', 'Band Width': '12.5K', 'Squelch Mode': 'Carrier', 'Scan List': 'None'}


def ctcss(t):
    return t if re.fullmatch(r'\d{2,3}\.\d', t or '') else 'Off'


def rx_only(cp, name, row, made):
    """Return the channel name to use for this FOG row, creating a receive-only channel if needed."""
    key = '%.5f' % float(row['rx'])
    if key in made:
        return made[key]
    existing = cp.by_rx(row['rx'])
    if existing:
        made[key] = existing[0][1]
        return made[key]
    tone = ctcss(row['rx_tone'])
    r = cp.new_channel(TEMPLATE, name, row['rx'], row['rx'], decode='Off', encode=tone, **RXONLY)
    cp.add_channels([r], after=cp.pending_after)
    cp.pending_after = name
    made[key] = name
    return name


def load(section):
    return [r for r in csv.DictReader(open('data/sources/maine_fog.csv', newline='')) if r['section'] in section]


def national_name(n):
    m = re.fullmatch(r'(V|U)(CALL?|TAC|FIRE|MED|LAW)(\d+)D?', n.replace(' ', ''))
    return f"{m.group(1)}{'CALL' if m.group(2).startswith('CAL') else m.group(2)} {m.group(3)}" if m else n


def stage_state_net(cp):
    made, members = {}, []
    cp.pending_after = cp.ch[-1][1] if False else 'CCFIRE'
    for r in load({'MSCOMMNET Region Net'}):
        name = 'RN ' + short(r['name'], 12)
        n = rx_only(cp, name, r, made)
        if n not in members:
            members.append(n)
    cp.add_zone('ME State Net', members, before='Packet')


def stage_interop(cp):
    made, members = {}, []
    cp.pending_after = 'CCFIRE'
    rows = load({'State of Maine CONOP', 'FCC Interoperable Channels'})
    rows += [r for r in load({'Cumberland County EMA'}) if r['name'] == 'T-PIKE']
    for r in rows:
        if r['name'] == 'T-PIKE':
            name = 'ME T-PIKE'
        elif r['section'] == 'State of Maine CONOP':
            name = f"{r['name'][:7]} {float(r['rx']):.3f}"      # e.g. 'SWSP 154.710'; frequency in the name avoids clashing with existing C1..C6 names
        else:
            name = national_name(r['name'])
        n = rx_only(cp, name, r, made)
        if n not in members:
            members.append(n)
    cp.add_zone('ME Interop', members, before='Packet')


if __name__ == '__main__':
    cp = Codeplug(sys.argv[2] if len(sys.argv) > 2 else 'exports/d878uv')
    before = len(cp.ch)
    {'state-net': stage_state_net, 'interop': stage_interop}[sys.argv[1]](cp)
    errs = cp.validate()
    print(f'added {len(cp.ch) - before} channels;', 'errors:' if errs else 'validation ok', errs[:10])
    if not errs:
        cp.save()
