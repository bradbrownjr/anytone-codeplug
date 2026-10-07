#!/usr/bin/env python3
"""Parse the Maine Statewide Interoperability Field Operations Guide (ICS-217A worksheets, v. 2017-03-22)
into data/sources/maine_fog.csv.

Source PDF: http://www.ws1sm.com/Images/2017%20Statewide%20Interoperability%20FOG.pdf
Usage: python3 codeplug/parse_maine_fog.py path/to/fog.pdf
The frequencies are the radio's view (RX = what a radio receives). DCS tones are kept as text
(e.g. 'D612'); CSQ means carrier squelch.
"""
import csv, re, subprocess, sys

F4 = re.compile(r'^\d{2,3}\.\d{3,4}$')
CTCSS = {'67.0','69.3','71.9','74.4','77.0','79.7','82.5','85.4','88.5','91.5','94.8','97.4','100.0','103.5','107.2','110.9','114.8','118.8','123.0','127.3','131.8','136.5','141.3','146.2','151.4','156.7','162.2','167.9','173.8','179.9','186.2','192.8','203.5','210.7','218.1','225.7','229.1','233.6','241.8','250.3','254.1'}
CONFIG = {'simplex', 'duplex', 'repeater', 'tactical'}


def tone(tok):
    t = tok.strip()
    if t.upper() == 'CSQ':
        return 'CSQ'
    m = re.fullmatch(r'(?:pl\s*)?(\d{2,3})(?:\.(\d))?', t, re.I)
    if m:
        v = f"{m.group(1)}.{m.group(2) or '0'}"
        return v if v in CTCSS else None
    m = re.fullmatch(r'(?:dcs|dpl|d)\s*(\d{3})([NI]?)', t, re.I)
    if m:
        return 'D' + m.group(1) + (m.group(2).upper() or 'N')
    return None


def parse_row(parts):
    i = next((k for k, p in enumerate(parts) if F4.match(p)), None)
    if i is None:
        return None
    pre = [re.sub(r'^\d+\s+', '', parts[0])] + parts[1:i]
    config = pre[0]
    name = pre[1] if len(pre) > 1 else pre[0]
    users = pre[2] if len(pre) > 2 else ''
    f, tones, rest = [], {}, []
    for p in parts[i:]:
        if F4.match(p):
            f.append(p)
        elif (t := tone(p)) is not None and f:
            tones.setdefault(len(f) - 1, t)
        elif p not in ('A', 'M', 'D'):
            rest.append(p)
    rx = f[0]
    tx = f[1] if len(f) > 1 else f[0]
    rt, tt = tones.get(0), tones.get(1)
    if rt is None and tt is not None and len(f) > 1:
        rt = tt                                   # one tone after both frequencies applies to both
    if tt is None and rt is not None:
        tt = rt
    return dict(config=config, name=name, users=users, rx=rx, rx_tone=rt or '', tx=tx, tx_tone=tt or '', remarks=' / '.join(rest))


def main(pdf, out='data/sources/maine_fog.csv'):
    text = subprocess.run(['pdftotext', '-layout', pdf, '-'], capture_output=True, text=True, check=True).stdout
    rows = []
    for pageno, page in enumerate(text.split('\f'), 1):
        hdr = next((l for l in page.split('\n')[:8] if 'COMMUNICATIONS RESOURCE AVAILABILITY WORKSHEET' in l), None)
        if not hdr:
            continue
        bits = re.split(r'\s{2,}', hdr.split('WORKSHEET', 1)[1].strip())
        section = re.sub(r'\s*page \d+\s*$', '', ' '.join(bits[1:])).strip()
        for line in page.split('\n'):
            if line.strip().startswith(('The convention', 'ICS 217A')):
                continue
            parts = re.split(r'\s{2,}', line.strip())
            r = parse_row(parts) if any(F4.match(p) for p in parts) else None
            if r:
                r.update(page=pageno, section=section)
                rows.append(r)
    cols = ['page', 'section', 'config', 'name', 'users', 'rx', 'rx_tone', 'tx', 'tx_tone', 'remarks']
    with open(out, 'w', newline='') as f:
        w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(rows)
    print(f'wrote {out}: {len(rows)} rows')


if __name__ == '__main__':
    main(sys.argv[1])
