"""Read, edit and validate an AnyTone CPS CSV export (D878UV layout).

Zones, scan lists and roaming lists reference channels by name, so every edit goes through this
module, which keeps the frequency lists, numbering and startup-zone settings consistent.
"""
import csv
import re
from pathlib import Path


def _read(path):
    with open(path, newline='') as f:
        return list(csv.reader(f))


def _write(path, rows):
    with open(path, 'w', newline='') as f:
        csv.writer(f, quoting=csv.QUOTE_ALL, lineterminator='\r\n').writerows(rows)


class Codeplug:
    def __init__(self, folder):
        self.dir = Path(folder)
        t = _read(self.dir / 'Channel.CSV'); self.ch_head, self.ch = t[0], t[1:]
        t = _read(self.dir / 'Zone.CSV'); self.z_head, self.zones = t[0], t[1:]
        t = _read(self.dir / 'TalkGroups.CSV'); self.tg_head, self.tgs = t[0], t[1:]
        self.c = {n: i for i, n in enumerate(self.ch_head)}
        self.zc = {n: i for i, n in enumerate(self.z_head)}
        self.old_zone_names = [z[1] for z in self.zones]
        self.reindex()

    # ---- lookups ----
    def reindex(self):
        self.by = {r[1]: r for r in self.ch}

    def col(self, row, name):
        return row[self.c[name]]

    def zone(self, name):
        return next((z for z in self.zones if z[1] == name), None)

    def members(self, zone_name):
        return self.zone(zone_name)[self.zc['Zone Channel Member']].split('|')

    def by_rx(self, rx):
        """Existing channels whose receive frequency equals rx (MHz string or float)."""
        key = '%.5f' % float(rx)
        return [r for r in self.ch if self.col(r, 'Receive Frequency') == key]

    # ---- editing ----
    def new_channel(self, template, name, rx, tx, decode='Off', encode='Off', **fields):
        assert len(name) <= 16, name
        assert name not in self.by, f'duplicate channel name {name!r}'
        r = list(self.by[template])
        for k, v in dict({'Channel Name': name, 'Receive Frequency': '%.5f' % float(rx), 'Transmit Frequency': '%.5f' % float(tx),
                          'CTCSS/DCS Decode': decode, 'CTCSS/DCS Encode': encode}, **fields).items():
            r[self.c[k]] = v
        return r

    def add_channels(self, rows, after=None):
        """Insert channel rows after the named channel (or at the end)."""
        i = len(self.ch) if after is None else next(i for i, r in enumerate(self.ch) if r[1] == after) + 1
        self.ch[i:i] = rows
        self.reindex()

    def add_zone(self, name, members, a=None, b=None, before=None):
        assert len(name) <= 16 and self.zone(name) is None and len(members) <= 250
        assert all(m in self.by for m in members) and len(set(members)) == len(members)
        a, b = a or members[0], b or members[0]
        z = [''] * len(self.z_head)
        z[1] = name
        z[self.zc['Zone Channel Member']] = '|'.join(members)
        z[self.zc['Zone Channel Member RX Frequency']] = '|'.join(self.col(self.by[m], 'Receive Frequency') for m in members)
        z[self.zc['Zone Channel Member TX Frequency']] = '|'.join(self.col(self.by[m], 'Transmit Frequency') for m in members)
        for k, n in (('A Channel', a), ('B Channel', b)):
            z[self.zc[k]] = n
            z[self.zc[k + ' RX Frequency']] = self.col(self.by[n], 'Receive Frequency')
            z[self.zc[k + ' TX Frequency']] = self.col(self.by[n], 'Transmit Frequency')
        z[self.zc['Zone Hide ']] = '0'
        i = len(self.zones) if before is None else next(i for i, q in enumerate(self.zones) if q[1] == before)
        self.zones.insert(i, z)

    def extend_zone(self, name, new_members):
        """Append channels to an existing zone (keeps A/B channels)."""
        z = self.zone(name)
        members = self.members(name) + [m for m in new_members if m not in self.members(name)]
        assert len(members) <= 250 and all(m in self.by for m in members)
        z[self.zc['Zone Channel Member']] = '|'.join(members)
        z[self.zc['Zone Channel Member RX Frequency']] = '|'.join(self.col(self.by[m], 'Receive Frequency') for m in members)
        z[self.zc['Zone Channel Member TX Frequency']] = '|'.join(self.col(self.by[m], 'Transmit Frequency') for m in members)

    def rename_channel(self, old, new):
        """Rename a channel and every zone reference to it (zones list members and A/B channels by name)."""
        assert len(new) <= 16 and new not in self.by and old in self.by
        self.by[old][1] = new
        for z in self.zones:
            for k in ('Zone Channel Member', 'A Channel', 'B Channel'):
                i = self.zc[k]
                z[i] = '|'.join(new if m == old else m for m in z[i].split('|'))
        self.reindex()

    def remove_from_zone(self, name, drop):
        """Drop members from a zone (the channels themselves stay)."""
        z = self.zone(name)
        members = [m for m in self.members(name) if m not in drop]
        z[self.zc['Zone Channel Member']] = '|'.join(members)
        z[self.zc['Zone Channel Member RX Frequency']] = '|'.join(self.col(self.by[m], 'Receive Frequency') for m in members)
        z[self.zc['Zone Channel Member TX Frequency']] = '|'.join(self.col(self.by[m], 'Transmit Frequency') for m in members)
        for k in ('A Channel', 'B Channel'):
            if z[self.zc[k]] in drop:
                z[self.zc[k]] = members[0]
                z[self.zc[k + ' RX Frequency']] = self.col(self.by[members[0]], 'Receive Frequency')
                z[self.zc[k + ' TX Frequency']] = self.col(self.by[members[0]], 'Transmit Frequency')

    def add_talkgroup(self, tid, name, call_type='Group Call'):
        if not any(r[1] == tid for r in self.tgs):
            last = max((i for i, r in enumerate(self.tgs) if r[3] == 'Group Call'), default=len(self.tgs) - 1)
            self.tgs.insert(last + 1, ['', tid, name, call_type, 'None'])

    # ---- output ----
    def save(self):
        for n, r in enumerate(self.ch, 1):
            r[0] = str(n)
        for n, z in enumerate(self.zones, 1):
            z[0] = str(n)
        for n, r in enumerate(self.tgs, 1):
            r[0] = str(n)
        _write(self.dir / 'Channel.CSV', [self.ch_head] + self.ch)
        _write(self.dir / 'Zone.CSV', [self.z_head] + self.zones)
        _write(self.dir / 'TalkGroups.CSV', [self.tg_head] + self.tgs)
        self._remap_zone_settings()

    def _remap_zone_settings(self):
        """OptionalSetting.CSV stores zone numbers (0-based); re-point them by zone name after inserts."""
        path = self.dir / 'OptionalSetting.CSV'
        lines = path.read_text(newline='').split('\r\n')
        hdr = [t.strip('"') for t in lines[0].split(',')]
        vals = lines[1].split(',')
        new_idx = {z[1]: i for i, z in enumerate(self.zones)}
        for k in ('Work_Zone1', 'Work_Zone2', 'PriZoneA', 'PriZoneB', 'StartZone1', 'StartZone2'):
            i = hdr.index(k)
            v = int(vals[i].strip('"'))
            if v < len(self.old_zone_names):
                vals[i] = '"%d"' % new_idx[self.old_zone_names[v]]
        lines[1] = ','.join(vals)
        path.write_text('\r\n'.join(lines), newline='')
        self.old_zone_names = [z[1] for z in self.zones]

    # ---- checks ----
    def validate(self):
        errs = []
        names = [r[1] for r in self.ch]
        if len(set(names)) != len(names):
            errs.append('duplicate channel names')
        if len(self.ch) > 4000 or len(self.zones) > 250:
            errs.append('over radio limits')
        tgs = {(r[2], r[1]) for r in self.tgs}
        for r in self.ch:
            if len(r[1]) > 16:
                errs.append(f'name too long: {r[1]}')
            if self.col(r, 'Channel Type') == 'D-Digital' and (self.col(r, 'Contact'), self.col(r, 'Contact TG/DMR ID')) not in tgs:
                errs.append(f'no contact for {r[1]}')
        for z in self.zones:
            m = z[self.zc['Zone Channel Member']].split('|')
            rx = z[self.zc['Zone Channel Member RX Frequency']].split('|')
            tx = z[self.zc['Zone Channel Member TX Frequency']].split('|')
            if not (len(m) == len(rx) == len(tx)) or len(set(m)) != len(m) or len(m) > 250:
                errs.append(f'zone shape: {z[1]}')
            for n, a, b in zip(m, rx, tx):
                if n not in self.by or (self.col(self.by[n], 'Receive Frequency'), self.col(self.by[n], 'Transmit Frequency')) != (a, b):
                    errs.append(f'zone {z[1]}: bad member {n}')
        return errs


def short(name, limit):
    """Abbreviate common words, then truncate, to fit limit characters."""
    ab = {'north': 'N', 'east': 'E', 'south': 'S', 'west': 'W', 'mountain': 'Mt', 'mount': 'Mt', 'saint': 'St', 'fort': 'Ft', 'county': 'Cty', 'tower': 'Twr', 'ground': 'Gnd', 'primary': 'Pri', 'secondary': 'Sec', 'tactical': 'Tac'}
    if len(name) > limit:
        name = ' '.join(ab.get(w.lower(), w) for w in name.split())
    return re.sub(r'\s+', ' ', name)[:limit].rstrip()
