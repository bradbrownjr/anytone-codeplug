#!/usr/bin/env python3
"""Single-source data model and generator.

data/ holds one set of tables with stable IDs; zones and scan lists reference channels by ID, so renaming a
channel or inserting one never breaks a list. `build` renders the CPS CSVs (frequency lists, numbering and
name references are derived) for a radio profile.

    python3 codeplug/model.py bootstrap [export dir]     exports/d878uv -> data/   (one-time; adopts IDs)
    python3 codeplug/model.py build d878uv                data/ -> out/d878uv
    python3 codeplug/model.py check d878uv                build, then compare with exports/d878uv byte for byte

Tables (UTF-8 CSV, header = CPS column names where applicable):
    data/channels.csv        id + every Channel.CSV column except `No.`
    data/talkgroups.csv      id + TalkGroups.CSV columns except `No.`
    data/zones.csv           id, name, a_id, b_id, hide      data/zone_members.csv     zone_id, seq, channel_id
    data/scanlists.csv       id, name + non-member scan list columns   data/scanlist_members.csv  scanlist_id, seq, channel_id
Radio profiles (RADIOS) say which bands a radio can do; channels outside them are left out of that radio's build.
"""
import csv, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
GENERATED = ('Channel.CSV', 'Zone.CSV', 'ScanList.CSV', 'TalkGroups.CSV')
RADIOS = {  # MHz ranges the radio can transmit/receive
    'd878uv': {'folder': 'd878uv', 'bands': [(136, 174), (400, 480)]},
    'd578uv': {'folder': 'd578uv', 'bands': [(136, 174), (200, 260), (400, 480)]},
}


def read(path):
    with open(path, newline='') as f:
        return list(csv.reader(f))


def write(path, rows, quote_all=True, eol='\r\n'):
    with open(path, 'w', newline='') as f:
        csv.writer(f, quoting=csv.QUOTE_ALL if quote_all else csv.QUOTE_MINIMAL, lineterminator=eol).writerows(rows)


def table(name):
    t = read(DATA / name)
    return t[0], t[1:]


def bootstrap(src):
    src = Path(src)
    DATA.mkdir(exist_ok=True)
    ch = read(src / 'Channel.CSV'); head, rows = ch[0], ch[1:]
    ids = {r[1]: 'ch%05d' % i for i, r in enumerate(rows, 1)}
    assert len(ids) == len(rows), 'duplicate channel names'
    write(DATA / 'channels.csv', [['id'] + head[1:]] + [[ids[r[1]]] + r[1:] for r in rows], quote_all=False, eol='\n')
    tg = read(src / 'TalkGroups.CSV')
    write(DATA / 'talkgroups.csv', [['id'] + tg[0][1:]] + [['tg%04d' % i] + r[1:] for i, r in enumerate(tg[1:], 1)], quote_all=False, eol='\n')
    z = read(src / 'Zone.CSV'); zh = z[0]; zc = {n: i for i, n in enumerate(zh)}
    zones, members = [['id', 'name', 'a_id', 'b_id', 'hide']], [['zone_id', 'seq', 'channel_id']]
    for i, r in enumerate(z[1:], 1):
        zid = 'z%03d' % i
        zones.append([zid, r[zc['Zone Name']], ids.get(r[zc['A Channel']], ''), ids.get(r[zc['B Channel']], ''), r[zc['Zone Hide ']]])
        for s, m in enumerate(r[zc['Zone Channel Member']].split('|') if r[zc['Zone Channel Member']] else [], 1):
            members.append([zid, s, ids[m]])
    write(DATA / 'zones.csv', zones, quote_all=False, eol='\n'); write(DATA / 'zone_members.csv', members, quote_all=False, eol='\n')
    s = read(src / 'ScanList.CSV'); sh = s[0]; sc = {n: i for i, n in enumerate(sh)}
    keep = [i for i, n in enumerate(sh) if n in ('Scan Mode', 'Priority Channel Select', 'Priority Channel 1', 'Priority Channel 2', 'Revert Channel', 'Look Back Time A[s]', 'Look Back Time B[s]', 'Dropout Delay Time[s]', 'Dwell Time[s]')]
    scans, smem = [['id', 'name'] + [sh[i] for i in keep]], [['scanlist_id', 'seq', 'channel_id']]
    for i, r in enumerate(s[1:], 1):
        sid = 's%03d' % i
        scans.append([sid, r[sc['Scan List Name']]] + [r[i2] for i2 in keep])
        for n, m in enumerate(r[sc['Scan Channel Member']].split('|') if r[sc['Scan Channel Member']] else [], 1):
            smem.append([sid, n, ids[m]])
    write(DATA / 'scanlists.csv', scans, quote_all=False, eol='\n'); write(DATA / 'scanlist_members.csv', smem, quote_all=False, eol='\n')
    print(f'bootstrapped {len(rows)} channels, {len(z) - 1} zones, {len(s) - 1} scan lists, {len(tg) - 1} talkgroups')


def in_bands(freq, bands):
    return any(lo <= float(freq) < hi for lo, hi in bands)


def build(radio, out=None, static=None):
    prof = RADIOS[radio]
    out = Path(out or ROOT / 'out' / prof['folder'])
    static = Path(static or ROOT / 'exports' / prof['folder'])
    out.mkdir(parents=True, exist_ok=True)
    for f in static.iterdir():
        if f.name not in GENERATED and f.is_file():
            shutil.copyfile(f, out / f.name)
    ch_head, chs = table('channels.csv')
    c = {n: i for i, n in enumerate(ch_head)}
    keep = [r for r in chs if in_bands(r[c['Receive Frequency']], prof['bands']) and in_bands(r[c['Transmit Frequency']], prof['bands'])]
    by_id = {r[0]: r for r in keep}
    header = read(static / 'Channel.CSV')[0]
    write(out / 'Channel.CSV', [header] + [[str(i)] + r[1:] for i, r in enumerate(keep, 1)])
    name = lambda cid: by_id[cid][c['Channel Name']]
    rx = lambda cid: by_id[cid][c['Receive Frequency']]
    tx = lambda cid: by_id[cid][c['Transmit Frequency']]
    zh = read(static / 'Zone.CSV')[0]
    zmem = {}
    for zid, seq, cid in table('zone_members.csv')[1]:
        if cid in by_id:
            zmem.setdefault(zid, []).append(cid)
    rows = []
    for i, (zid, zname, a, b, hide) in enumerate(table('zones.csv')[1], 1):
        m = zmem.get(zid, [])
        if not m:
            continue
        a, b = (a if a in by_id else m[0]), (b if b in by_id else m[0])
        rows.append([str(len(rows) + 1), zname, '|'.join(map(name, m)), '|'.join(map(rx, m)), '|'.join(map(tx, m)),
                     name(a), rx(a), tx(a), name(b), rx(b), tx(b), hide])
    write(out / 'Zone.CSV', [zh] + rows)
    sh = read(static / 'ScanList.CSV')[0]
    sh_h, sh_rows = table('scanlists.csv')
    smem = {}
    for sid, seq, cid in table('scanlist_members.csv')[1]:
        if cid in by_id:
            smem.setdefault(sid, []).append(cid)
    byname = {r[c['Channel Name']]: r for r in keep}
    rows = []
    for r in sh_rows:
        sid, sname, mode, psel, p1, p2, rev, lbA, lbB, drop, dwell = r
        m = smem.get(sid, [])
        f = lambda n: (byname[n][c['Receive Frequency']], byname[n][c['Transmit Frequency']]) if n in byname else ('', '')
        rows.append([str(len(rows) + 1), sname, '|'.join(map(name, m)), '|'.join(map(rx, m)), '|'.join(map(tx, m)), mode, psel,
                     p1, *f(p1), p2, *f(p2), rev, lbA, lbB, drop, dwell])
    write(out / 'ScanList.CSV', [sh] + rows)
    th = read(static / 'TalkGroups.CSV')[0]
    write(out / 'TalkGroups.CSV', [th] + [[str(i)] + r[1:] for i, r in enumerate(table('talkgroups.csv')[1], 1)])
    # OptionalSetting.CSV stores 0-based zone numbers: re-point by zone name if zones moved.
    return out, len(keep)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'bootstrap':
        bootstrap(sys.argv[2] if len(sys.argv) > 2 else ROOT / 'exports' / 'd878uv')
    elif cmd in ('build', 'check'):
        out, n = build(sys.argv[2])
        print('built', out, n, 'channels')
        if cmd == 'check':
            bad = [f.name for f in (ROOT / 'exports' / RADIOS[sys.argv[2]]['folder']).iterdir()
                   if f.is_file() and f.name != 'DigitalContactList.CSV' and f.read_bytes() != (out / f.name).read_bytes()]
            print('MISMATCH: ' + ', '.join(bad) if bad else 'byte-identical to exports/')
            sys.exit(bool(bad))
