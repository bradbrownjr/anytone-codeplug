#!/usr/bin/env python3
"""Fetch NEDECN's per-site repeater pages and compare them with the DMR zones in import/d878uv.

NEDECN's site pages are the authority for DMR sites (the CSV pack on the downloads page is sloppy).  The state
repeater index pages list every site; each site page gives frequency, offset, color code and talkgroups with slots.

    python3 codeplug/nedecn.py fetch     download the index + every site page into cache/nedecn/ (gitignored)
    python3 codeplug/nedecn.py report    compare the cached pages with import/d878uv and print what differs

The report lists: pages whose zone is missing or differs (frequency, color code, talkgroups, slots), pages with no zone
(a new site), zones with no page (retired, moved or never listed), and talkgroups in TalkGroups.CSV that no NEDECN page
carries any more (candidates for removal).  Talkgroups present in a zone but absent from its page are NOT errors: the
original codeplug carries a standard extra set (WW English, UA English 1/2, Region North ...) at every site.
Run `fetch` first; pages change when repeaters are added, moved or retired, so re-run it before each refresh.
"""
import csv, html, json, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / 'cache' / 'nedecn'
STATES = {'connecticut': 'CT', 'maine': 'ME', 'massachusetts': 'MA', 'new-hampshire': 'NH', 'new-york': 'NY', 'rhode-island': 'RI', 'vermont': 'VT'}
BASE = 'https://nedecn.org/home/repeaters/'
EVENT_TGS = {'31231', '31232'}          # ME Event 1/2 are added by us, not listed per site
# zone name -> text in the NEDECN page key, where several zones share a frequency or the names differ (Fort/Ft, Dukes County = W Tisbury ...)
ALIASES = {'Fort Kent ME': 'ft-kent', 'W Tisbury MA': 'dukes', 'Gofftstown NH': 'uncanoonuc', 'Sommersworth NH': 'somersworth', 'Southboro VHF MA': 'southboro', 'Southboro UHF MA': 'southboro'}


def get(url):
    return subprocess.run(['curl', '-s', '-m', '30', '-A', 'Mozilla/5.0', url], capture_output=True, text=True).stdout


def fetch():
    CACHE.mkdir(parents=True, exist_ok=True)
    links = []
    for st in STATES:
        page = get(f'{BASE}{st}-repeaters/')
        links += sorted(set(re.findall(rf'{re.escape(BASE)}{st}-repeaters/[a-z0-9-]+/', page)))
    for f in CACHE.glob('*.html'):
        f.unlink()
    for u in links:
        (CACHE / (u[len(BASE):].strip('/').replace('/', '_') + '.html')).write_text(get(u), encoding='utf8')
        time.sleep(0.3)
    print(f'fetched {len(links)} pages into {CACHE}')


def num(x):
    m = re.search(r'[\d.]+', x or '')
    return float(m.group()) if m else None


def lines_of(path):
    s = path.read_text(encoding='utf8', errors='ignore')
    m = re.search(r'<article.*?</article>', s, re.S)
    t = m.group(0) if m else s
    t = re.sub(r'<script.*?</script>|<style.*?</style>', '', t, flags=re.S)
    t = re.sub(r'</(tr|p|h\d|li|div|td|th)>|<br ?/?>', '\n', t)
    t = html.unescape(re.sub(r'<[^>]+>', '', t))
    return [re.sub(r'\s+', ' ', l).strip() for l in t.split('\n') if l.strip()]


def parse(path):
    L = lines_of(path)
    txt = '\n'.join(L)
    d = {'title': L[0]}
    grab = lambda label: (m.group(1).strip() if (m := re.search(label + r'[: ]*\n?\s*([^\n]+)', txt)) else None)
    d['freq'], d['off'], d['cc'] = grab('Frequency'), grab('(?:Offset|Input)'), grab('Color ?Code')
    tgs, slot = {}, None
    for i, l in enumerate(L):
        if m := re.match(r'Time ?[Ss]lot #?(\d)\s*[–-]\s*Group Call (\d+) = (.+)', l):
            tgs[m.group(2)] = m.group(1); continue
        if m := re.match(r'Timeslot (\d) Talkgroups', l):
            slot = m.group(1); continue
        if (m := re.match(r'^(\d+)\s*(Full-?[Tt]ime|PTT)\s*(.+)$', l)) and slot:
            tgs[m.group(1)] = slot
        if re.fullmatch(r'\d+', l) and i + 1 < len(L) and re.fullmatch(r'Full-?[Tt]ime|PTT', L[i + 1], re.I):
            for j in range(i, -1, -1):
                if mm := re.match(r'Time ?slot (\d)', L[j], re.I):
                    tgs[l] = mm.group(1); break
    d['tgs'] = tgs
    d['offline'] = bool(re.search(r'Offline|Off the Air|Off-Air', txt[:600], re.I))
    fr = num(d['freq']); o = num((d['off'] or '').replace('-', '').replace('+', ''))
    d['rx'] = '%.5f' % fr if fr else None
    d['tx'] = '%.5f' % (fr + (-1 if '-' in (d['off'] or '') else 1) * o) if fr and o is not None else None
    d['ccn'] = str(int(num(d['cc']))) if num(d['cc']) is not None else None
    return d


def report():
    pages = {}
    for f in sorted(CACHE.glob('*.html')):
        k = f.stem
        d = parse(f)
        if d['title'].startswith('Page not found'):
            continue
        d['state'] = STATES[k.split('-repeaters')[0]]
        pages[k] = d
    # a few NEDECN pages describe two repeaters (Southboro VHF+UHF); they are matched by hand below
    imp = ROOT / 'import' / 'd878uv'
    ch = {r['Channel Name']: r for r in csv.DictReader(open(imp / 'Channel.CSV', newline=''))}
    zones = {z['Zone Name']: z['Zone Channel Member'].split('|') for z in csv.DictReader(open(imp / 'Zone.CSV', newline=''))}
    tgnames = {r['Radio ID']: r['Name'] for r in csv.DictReader(open(imp / 'TalkGroups.CSV', newline=''))}
    dz = {}
    for zn, m in zones.items():
        c = ch[m[0]]
        if c['Channel Type'] == 'D-Digital' and not c['Channel Name'].startswith('DMRS'):
            dz.setdefault((c['Receive Frequency'], c['Transmit Frequency']), []).append(zn)
    tok = lambda s: re.sub(r'[^a-z]', '', s.lower())
    used, good, notes = set(), 0, []
    page_tgs = set()
    for k, p in pages.items():
        if not p['rx'] or not p['tx'] or not p['ccn']:
            notes.append(f"INCOMPLETE page {k} ({p['freq']} {p['off']} CC {p['cc']}{', offline' if p['offline'] else ''})"); continue
        page_tgs |= set(p['tgs'])
        zl = dz.get((p['rx'], p['tx']), [])
        by_alias = [z for z in zones if ALIASES.get(z) and ALIASES[z] in k and z in sum(dz.values(), [])]
        if by_alias and not any(ALIASES.get(z, '\0') in k for z in zl):
            zl = by_alias
        if len(zl) > 1:
            zl = [z for z in zl if ALIASES.get(z, '\0') in k or tok(z)[:4] in tok(k)] or zl
        if not zl or (len(zl) == 1 and False):
            zl = []
        if not zl:
            notes.append(f"NEW or MOVED: page {k} {p['rx']}/{p['tx']} CC{p['ccn']} has no zone at that frequency"); continue
        used.add(zl[0])
        cs = [ch[n] for n in zones[zl[0]]]
        have = {}
        for c in cs:
            have.setdefault(c['Contact TG/DMR ID'], c['Slot'])
        prob = []
        if {c['RX Color Code'] for c in cs} != {p['ccn']}:
            prob.append(f"color code zone {sorted({c['RX Color Code'] for c in cs})} page {p['ccn']}")
        if miss := [t for t in p['tgs'] if t not in have]:
            prob.append('TGs on the page but not in the zone: ' + ', '.join(f"{t} ({tgnames.get(t, '?')}, TS{p['tgs'][t]})" for t in miss))
        if slot := [t for t in p['tgs'] if t in have and have[t] != p['tgs'][t]]:
            prob.append('slot differs: ' + ', '.join(f"{t} page TS{p['tgs'][t]} zone TS{have[t]}" for t in slot))
        if prob:
            notes.append(f"DIFF {zl[0]} <- {k}: " + '; '.join(prob))
        else:
            good += 1
    print(f'{len(pages)} pages, {good} match their zone exactly')
    for n in notes:
        print(n)
    print('ZONES WITH NO PAGE (retired, moved, or never listed):', ', '.join(sorted({z for v in dz.values() for z in v} - used)))
    gone = [f'{t} {n}' for t, n in tgnames.items() if t not in page_tgs and t not in EVENT_TGS and int(t) < 10000]   # group TGs only (long IDs are private-call contacts)
    print('TALKGROUPS IN TalkGroups.CSV THAT NO PAGE CARRIES (check whether they were removed):', ', '.join(gone) or 'none')


if __name__ == '__main__':
    {'fetch': fetch, 'report': report}[sys.argv[1] if len(sys.argv) > 1 else 'report']()
