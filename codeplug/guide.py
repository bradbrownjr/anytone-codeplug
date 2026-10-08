#!/usr/bin/env python3
"""Render a printable PDF radio guide (zone list, per-zone channel tables, talkgroups) from a built codeplug folder.

    python3 codeplug/guide.py [codeplug dir] [output.pdf] [radio title]     default: import/d878uv -> out/guides/d878uv.pdf

The footer carries the date and git commit so a printed copy can be traced to a codeplug version.  The programmable
button map and the diagram are NOT in the CSV export (key assignments live in the CPS binary); fill BUTTONS below once the
physical layout is confirmed.
"""
import csv, datetime, subprocess, sys
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import BaseDocTemplate, Flowable, Frame, KeepTogether, NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parent.parent
# Key assignments (CPS Optional Setting -> Key Function; not in the CSV export).  {model: {key: (short press, long press)}}.
# The 578 is still to be filled in from its CPS screen.
BUTTONS = {
    'AT-D878UV': {'PF1': ('Scan', 'Nuisance Delete'), 'PF2': ('Digital Monitor', 'LastCall Reply'), 'PF3': ('Power', 'Roaming'),
                  'P1': ('Main Channel Switch', 'APRS Send'), 'P2': ('V/M', 'FM'), 'UPDN': ('Up: Previous zone', 'Down: Next zone')},
}
BUTTONS['AT-D578UV'] = {'P1': ('Power', 'Repeater'), 'P2': ('Scan', 'Nuisance Delete'), 'P3': ('Digital Monitor', 'Roaming'), 'P4': ('Zone-', 'APRS Send'),
                        'P5': ('Zone+', 'GPS Information'), 'P6': ('VFO/MR', 'Reverse'), 'PA': ('Menu', 'Off'), 'PB': ('Zone+', 'Off'), 'PC': ('Zone-', 'Off'),
                        'PD': ('Exit', 'Off'), 'KNOB': ('Main Channel Switch', 'Sub CH On/Off')}
USE = {   # operating notes; from KC1JMH's DMR page (kc1jmh.us) and the key assignments above
    'AT-D878UV': ['<b>Digital Monitor</b> (PF2 short press): press once for single time slot (the slot of the active channel / talkgroup); press twice for double time slot, which lets you hear any talkgroup the repeater is transmitting; press again for off.',
                  '<b>Scan</b> (PF1 short press): Menu, Scan, then option 3 "Scan List", pick a list and select "Select Cur List". Scan lists hold analog channels only; for DMR, use Digital Monitor instead. <b>Nuisance Delete</b> (PF1 long press) drops a busy channel from the scan temporarily.',
                  '<b>Power</b> (PF3 short press) steps the power level: L low, M medium, H high, T turbo. <b>Roaming</b> (PF3 long press) searches for the strongest DMR repeater nearby.'],
    'AT-D578UV': ['<b>Digital Monitor</b> (P3 short press): press for single time slot, again for double time slot (hear any talkgroup the repeater transmits), again for off.',
                  '<b>Scan</b> (P2 short press) scans the selected scan list; scan lists hold analog channels only, so use Digital Monitor for DMR. <b>Nuisance Delete</b> (P2 long press) drops a busy channel temporarily.',
                  '<b>Power</b> (P1 short press) steps the power level. <b>Roaming</b> (P3 long press) searches for the strongest DMR repeater nearby.'],
}
BEFORE = ('<b>Before first use:</b> this codeplug carries the owner\'s callsign and DMR ID (KC1JMH, 3123446). Replace them in the CPS under Digital, Radio ID List, '
          'and set your callsign and SSID under Public, APRS, and the power-on text under Optional Setting.')
KEYNOTE = {'AT-D878UV': 'Long press = hold 1 second. Key lock: manual.',
           'AT-D578UV': 'Long press = hold 2 seconds. Key lock: manual. Mic keys A-D are set as Menu, Zone+, Zone-, Exit (left to right), not the labels printed on the keys. Knob = push the channel knob.'}

NAV = {
    'AT-D578UV': ['Change zone: P5 or mic B = next zone (Zone+); P4 or mic C = previous zone (Zone-).',
                  'Change channel: turn the channel knob (right of the display). Push the knob to switch the main channel between A and B.',
                  'P6 switches between VFO and memory (channel) mode. P1 sets power level (Power).',
                  'Receive-only channels (marked RX only) have PTT Prohibit on and will not transmit.',
                  'Key assignments below are from the CPS (Optional Setting -> Key Function).'],
    'AT-D878UV': ['Change zone: press Down on the front pad for the next zone, Up for the previous zone.',
                  'Change channel: turn the channel knob (top of the radio) within the current zone.',
                  'Switch the main channel between A and B: short press P1 (Main Channel Switch).',
                  'Receive-only channels (marked RX only) have PTT Prohibit on and will not transmit.',
                  'Key assignments below are from the CPS (Optional Setting -> Key Function).'],
}


class KeyDiagram(Flowable):
    """Blank radio outline with write-in boxes, to be filled by hand (key assignments are not in the CSV export)."""
    W, H = 7.5 * inch, 3.6 * inch

    def __init__(self, mobile, keys=None):
        super().__init__(); self.mobile = mobile; self.keys = keys or {}; self.width, self.height = self.W, self.H

    def wrap(self, aw, ah):
        return self.W, self.H

    def box(self, c, x, y, label, w=1.45 * inch, vals=None):
        c.setLineWidth(0.6); c.rect(x, y, w, 0.58 * inch)
        c.setFont('Helvetica', 6.5); c.drawString(x + 3, y + 0.58 * inch - 8, label)
        c.setLineWidth(0.25); c.line(x + 3, y + 8, x + w - 3, y + 8); c.line(x + 3, y + 20, x + w - 3, y + 20)
        if vals:     # typed assignments sit on the two write-in lines: long press on the lower one
            c.setFont('Helvetica-Bold', 7.5)
            c.drawString(x + 4, y + 21.5, vals[0] if vals[0][:3] in ('Up:', 'Dow') else 'S: ' + vals[0]); c.drawString(x + 4, y + 9.5, vals[1] if vals[1][:3] in ('Up:', 'Dow') else 'L: ' + vals[1])

    def draw(self):
        c = self.canv; c.saveState(); c.setStrokeColor(colors.black)
        cx = self.W / 2
        c.setLineWidth(1.2)
        if not self.mobile:     # AT-D878UV(II): layout from the user manual, "4. Radio overview" (front view and left side view)
            fx = 2.6 * inch                                        # front view centre x
            c.setFont('Helvetica', 6.5)
            c.roundRect(fx - 0.7 * inch, 0.15 * inch, 1.4 * inch, 2.55 * inch, 8)
            c.line(fx - 0.45 * inch, 2.7 * inch, fx - 0.5 * inch, 3.3 * inch)           # antenna
            c.rect(fx - 0.15 * inch, 2.7 * inch, 0.2 * inch, 0.15 * inch)                 # channel switch
            c.rect(fx + 0.15 * inch, 2.7 * inch, 0.25 * inch, 0.2 * inch)                 # power/vol
            c.rect(fx - 0.55 * inch, 2.7 * inch, 0.18 * inch, 0.15 * inch)                # PF3
            c.rect(fx - 0.5 * inch, 1.7 * inch, 1.0 * inch, 0.8 * inch); c.drawCentredString(fx, 2.05 * inch, 'LCD')
            c.drawString(fx - 0.62 * inch, 1.55 * inch, 'Menu'); c.circle(fx, 1.45 * inch, 0.17 * inch); c.drawString(fx + 0.38 * inch, 1.55 * inch, 'Exit')
            c.drawString(fx - 0.62 * inch, 1.2 * inch, 'P1'); c.drawString(fx + 0.45 * inch, 1.2 * inch, 'P2')
            c.rect(fx - 0.5 * inch, 0.3 * inch, 1.0 * inch, 0.75 * inch); c.drawCentredString(fx, 0.62 * inch, 'keypad')
            sx = 5.6 * inch                                        # left side view: PTT with PF1 above PF2 below
            c.roundRect(sx - 0.3 * inch, 0.15 * inch, 0.6 * inch, 2.55 * inch, 6)
            c.rect(sx - 0.2 * inch, 1.65 * inch, 0.4 * inch, 0.7 * inch); c.drawCentredString(sx, 1.98 * inch, 'PTT')
            c.rect(sx - 0.15 * inch, 1.1 * inch, 0.3 * inch, 0.2 * inch); c.drawRightString(sx - 0.2 * inch, 1.15 * inch, 'PF1')
            c.rect(sx - 0.15 * inch, 0.75 * inch, 0.3 * inch, 0.2 * inch); c.drawRightString(sx - 0.2 * inch, 0.8 * inch, 'PF2')
            c.drawString(fx + 0.3 * inch, 3.3 * inch, 'FRONT VIEW'); c.drawString(sx - 0.3 * inch, 2.85 * inch, 'LEFT SIDE VIEW')
            # write-in boxes for the keys that can be programmed; leaders point at the key
            k = self.keys
            targets = [('PF3 - emergency key (top)', 0.1, 2.95, fx - 0.5 * inch, 2.78 * inch, k.get('PF3')),
                       ('Up / Down (front pad): zone', 0.1, 1.8, fx - 0.17 * inch, 1.5 * inch, k.get('UPDN')),
                       ('P1 key', 0.1, 0.75, fx - 0.55 * inch, 1.23 * inch, k.get('P1')),
                       ('P2 key', 3.9, 0.75, fx + 0.55 * inch, 1.23 * inch, k.get('P2')),
                       ('PF1 - upper side key', 6.15, 1.45, sx + 0.15 * inch, 1.2 * inch, k.get('PF1')),
                       ('PF2 - lower side key', 6.15, 0.6, sx + 0.15 * inch, 0.85 * inch, k.get('PF2'))]
            for t, x, y, tx, ty, v in targets:
                x, y = x * inch, y * inch
                self.box(c, x, y, t, w=1.35 * inch if not v else 1.55 * inch, vals=v)
                c.setLineWidth(0.4)
                c.line(x + ((1.55 * inch if v else 1.35 * inch) if x < tx else 0), y + 0.25 * inch, tx, ty)
            c.setFont('Helvetica', 6.5)
            c.drawString(0.1 * inch, 0.05 * inch, 'Not programmable here: channel switch and POWER/VOL knobs (top), Menu, Exit, speaker, PTT.')
        else:                   # AT-D578UV: layout from the user manual, "3. Getting acquainted" (front panel and hand mic)
            c.setFont('Helvetica', 6.5)
            hx, hy, hw, hh = 0.2 * inch, 1.4 * inch, 4.0 * inch, 1.5 * inch
            c.roundRect(hx, hy, hw, hh, 6)
            c.circle(hx + 0.35 * inch, hy + 1.0 * inch, 0.22 * inch); c.circle(hx + 0.35 * inch, hy + 0.45 * inch, 0.18 * inch)   # A/B volume knob, power
            c.rect(hx + 1.35 * inch, hy + 0.45 * inch, 1.5 * inch, 0.95 * inch); c.drawCentredString(hx + 2.1 * inch, hy + 0.9 * inch, 'display')
            for i in range(3):
                c.rect(hx + 0.85 * inch, hy + (1.05 - i * 0.3) * inch, 0.35 * inch, 0.22 * inch); c.drawString(hx + 0.9 * inch, hy + (1.11 - i * 0.3) * inch, 'P%d' % (i + 1))
                c.rect(hx + 3.0 * inch, hy + (1.05 - i * 0.3) * inch, 0.3 * inch, 0.22 * inch); c.drawString(hx + 3.05 * inch, hy + (1.11 - i * 0.3) * inch, 'P%d' % (i + 4))
            c.rect(hx + 1.0 * inch, hy + 0.08 * inch, 0.6 * inch, 0.22 * inch); c.drawString(hx + 1.1 * inch, hy + 0.14 * inch, 'MENU')
            c.rect(hx + 2.6 * inch, hy + 0.08 * inch, 0.6 * inch, 0.22 * inch); c.drawString(hx + 2.7 * inch, hy + 0.14 * inch, 'EXIT')
            c.circle(hx + 3.65 * inch, hy + 0.95 * inch, 0.25 * inch); c.drawCentredString(hx + 3.65 * inch, hy + 0.5 * inch, 'channel knob')
            c.drawString(hx, hy + hh + 6, 'FRONT PANEL')
            mx, my = 5.0 * inch, 0.35 * inch                       # hand microphone
            c.roundRect(mx, my, 1.4 * inch, 2.7 * inch, 10)
            c.rect(mx + 0.15 * inch, my + 2.2 * inch, 1.1 * inch, 0.35 * inch); c.drawCentredString(mx + 0.7 * inch, my + 2.35 * inch, 'Up / Down')
            c.rect(mx + 0.15 * inch, my + 0.95 * inch, 1.1 * inch, 1.15 * inch); c.drawCentredString(mx + 0.7 * inch, my + 1.5 * inch, 'keypad 0-9 * #')
            for i, t in enumerate('ABCD'):
                c.rect(mx + (0.15 + i * 0.28) * inch, my + 0.6 * inch, 0.25 * inch, 0.25 * inch); c.drawCentredString(mx + (0.275 + i * 0.28) * inch, my + 0.7 * inch, t)
            c.drawString(mx - 0.05 * inch, my + 2.8 * inch, 'HAND MIC')
            c.rect(mx - 0.12 * inch, my + 1.5 * inch, 0.12 * inch, 0.55 * inch)                  # PTT on the left edge
            c.drawRightString(mx - 0.15 * inch, my + 1.7 * inch, 'PTT')
            k = self.keys
            def lines(*ids): return [f'{i}  S: {k[i][0]}  L: {k[i][1]}' for i in ids] if k else None
            groups = [('P1 P2 P3 (left of display)', 0.2, 0.05, hx + 0.85 * inch, hy + 0.45 * inch, ('P1', 'P2', 'P3')),
                      ('P4 P5 P6 (right of display)', 2.35, 0.05, hx + 3.15 * inch, hy + 0.45 * inch, ('P4', 'P5', 'P6')),
                      ('Mic keys (short)', 6.45, 0.75, 'mic', None, ('PA', 'PB', 'PC', 'PD')),
                      ]
            for t, x, y, tx, ty, ids in groups:
                x, y = x * inch, y * inch
                w = 2.0 * inch if tx != 'mic' else 1.0 * inch
                h = 0.2 * inch + 0.13 * inch * len(ids) + 0.1 * inch
                c.setLineWidth(0.6); c.rect(x, y, w, h); c.setFont('Helvetica', 6.5); c.drawString(x + 3, y + h - 8, t)
                c.setFont('Helvetica-Bold', 7)
                for j, i in enumerate(ids):
                    if k:
                        sh, lg = k[i]
                        c.drawString(x + 4, y + h - 8 - 11 * (j + 1), f'{i}:  S: {sh}  /  L: {lg}' if tx != 'mic' else f'{ "ABCD"[j]}: {sh}')
                if tx == 'mic':
                    c.setLineWidth(0.4); c.line(x, y + h - 6, 5.0 * inch + 1.1 * inch, 1.0 * inch)
                elif tx:
                    c.setLineWidth(0.4); c.line(x + w / 2, y + h, tx, ty)
            kb = k['KNOB'] if k else ('', '')
            c.setFont('Helvetica', 6.5)
            c.drawString(hx + 0.9 * inch, hy + hh + 6, 'Channel knob push:  S: %s  /  L: %s' % kb)
        c.restoreState()


class Lazy(Flowable):
    """Builds its table at layout time, so page numbers learned in the first pass of multiBuild show up in the second."""
    def __init__(self, fn):
        super().__init__(); self.fn = fn

    def wrap(self, aw, ah):
        self.t = self.fn(); self.width, self.height = self.t.wrap(aw, ah); return self.width, self.height

    def draw(self):
        self.t.drawOn(self.canv, 0, 0)


def rows(path):
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def commit():
    try:
        return subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', '--short', 'HEAD'], text=True).strip()
    except Exception:
        return 'unknown'


def channel_types(chs, zones):
    """(category, zones, channels, description) rows for the channel-types summary, derived from the built codeplug."""
    def members(z): return z['Zone Channel Member'].split('|') if z['Zone Channel Member'] else []
    cat = {}
    for z in zones:
        n = z['Zone Name']; m = members(z)
        digital = bool(m) and chs[m[0]]['Channel Type'] == 'D-Digital'
        if n == 'Simplex': k = 'Simplex'
        elif digital: k = 'DMR repeater sites (NEDECN)'
        elif n.endswith(' GMRS') or n == 'GMRS': k = 'GMRS'
        elif n.endswith(' Analog'): k = 'Analog repeaters by state'
        elif n.startswith('EMA '): k = 'County EMA (Maine)'
        elif n.startswith('SAT-'): k = 'Satellites'
        elif n.startswith('CCEMA') or n in ('ME ARES', 'ME State Net', 'ME Interop'): k = 'ARES / EmComm (Maine)'
        elif n == 'US Interop': k = 'Federal / national interoperability'
        else: k = n
        c = cat.setdefault(k, [0, set()]); c[0] += 1; c[1].update(m)
    desc = {
        'DMR repeater sites (NEDECN)': 'One zone per repeater site across New England, NY and RI. Each channel is a talkgroup on that repeater (CC and time slot set per site); network talkgroups include state-wide, regional, TAC, SKYWARN and Parrot.',
        'Analog repeaters by state': 'FM repeaters (2 m, 70 cm and 1.25 m on the 578), filed by state and named CALL City. Tones are programmed.',
        'ARES / EmComm (Maine)': 'Maine ARES and Cumberland County EMA channels, state net and interoperability lists.',
        'County EMA (Maine)': 'County emergency management frequencies, from the Maine FOG. Receive only.',
        'Federal / national interoperability': 'NIFOG national interoperability channels (VHF, UHF, 700/800 MHz). Government channels are receive only.',
        'GMRS': 'GMRS simplex and repeater channels, shared and by state. A trailing * means the repeater tone is not publicly listed.',
        'Satellites': 'Amateur satellite downlink/uplink pairs (SO-50, ISS, AO-91, AO-123 and others), one zone each.',
        'Simplex': 'Amateur simplex calling and common simplex frequencies.',
        'MURS': 'MURS channels 1-5.', 'Marine': 'Marine VHF channels.', 'Weather': 'NOAA weather radio, receive only.',
        'Packet': 'Packet radio (APRS and node frequencies).'}
    return [(k, v[0], len(v[1]), desc.get(k, '')) for k, v in sorted(cat.items(), key=lambda kv: -kv[1][1] if False else 0)]


def build(folder, out, title):
    chs = {r['Channel Name']: r for r in rows(folder / 'Channel.CSV')}
    zones = rows(folder / 'Zone.CSV')
    tgs = rows(folder / ('TalkGroups.CSV' if (folder / 'TalkGroups.CSV').exists() else 'ContactTalkGroups.CSV'))
    ss = getSampleStyleSheet()
    small = ss['BodyText'].clone('small', fontSize=7, leading=8.5)
    head = f'{title} guide'
    stamp = f'{head} - {datetime.date.today()} - codeplug commit {commit()}'

    def footer(c, d):
        c.saveState(); c.setFont('Helvetica', 7); c.drawString(0.5 * inch, 0.35 * inch, stamp); c.drawRightString(8 * inch, 0.35 * inch, f'Page {d.page}'); c.restoreState()

    h1 = ss['Heading1'].clone('Section', fontSize=15, leading=18, spaceBefore=6, spaceAfter=4)
    zhead = ss['Heading3'].clone('ZoneHead', fontSize=8.5, leading=10, spaceBefore=4, spaceAfter=1)
    ztext = ss['BodyText'].clone('ztext', fontSize=6.5, leading=7.5)
    zpage = {}                                                  # zone number -> page, filled during the first pass

    def tbl(data, widths, fs=7, pad=1):
        t = Table(data, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([('FONTSIZE', (0, 0), (-1, -1), fs), ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                               ('GRID', (0, 0), (-1, -1), 0.25, colors.grey), ('TOPPADDING', (0, 0), (-1, -1), pad), ('BOTTOMPADDING', (0, 0), (-1, -1), pad), ('LEADING', (0, 0), (-1, -1), fs + 1)]))
        return t

    class Doc(BaseDocTemplate):
        def afterFlowable(self, f):
            if isinstance(f, KeepTogether):
                f = f._content[0]
            st = getattr(f, 'style', None)
            if st is not None and st.name == 'Section':
                self.notify('TOCEntry', (0, f.getPlainText(), self.page))
            elif st is not None and st.name == 'ZoneHead':
                zpage[f.getPlainText().split('.')[0]] = self.page

    m, W, H, col = 0.5 * inch, letter[0], letter[1], (letter[0] - 1.0 * inch - 0.2 * inch) / 2
    doc = Doc(str(out), pagesize=letter, title=head, leftMargin=m, rightMargin=m, topMargin=m, bottomMargin=0.6 * inch)
    fy, fh = 0.6 * inch, H - 1.1 * inch
    doc.addPageTemplates([
        PageTemplate('one', [Frame(m, fy, W - 2 * m, fh, id='f', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=footer),
        PageTemplate('two', [Frame(m, fy, col, fh, id='l', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
                             Frame(m + col + 0.2 * inch, fy, col, fh, id='r', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=footer)])

    mobile = 'D578' in title
    S = [Paragraph(head, ss['Title']), Paragraph(f'Generated {datetime.date.today()} from codeplug commit {commit()}. KC1JMH.', ss['BodyText']), Spacer(1, 8),
         Paragraph('Moving between zones and channels', ss['Heading2'])]
    S += [Paragraph(escape(t), ss['BodyText']) for t in NAV.get(title, ['(navigation steps for this model still to be written)'])]
    S += [Paragraph('Programmable buttons' if BUTTONS.get(title) else 'Programmable buttons (write in the assignments)', ss['Heading2']), KeyDiagram(mobile, BUTTONS.get(title)), Spacer(1, 6)]
    bk = BUTTONS.get(title)
    if bk:
        keys = [[n, *bk[k]] for n, k in ((('PF1 (side, upper)', 'PF1'), ('PF2 (side, lower)', 'PF2'), ('PF3 (top, emergency)', 'PF3'), ('P1', 'P1'), ('P2', 'P2')) if not mobile else
                                         tuple((f'P{i}', f'P{i}') for i in range(1, 7)) + (('Mic A', 'PA'), ('Mic B', 'PB'), ('Mic C', 'PC'), ('Mic D', 'PD'), ('Channel knob push', 'KNOB')))]
        if not mobile:
            keys += [['Up (front pad)', 'Previous zone', ''], ['Down (front pad)', 'Next zone', '']]
    else:
        keys = [['P1-P6 (head)', '', ''], ['A / B / C / D (mic)', '', ''], ['Mic Up / Down', '', '']] if mobile else []
    blank = [['Key', 'Short press', 'Long press']] + keys + [['', '', ''] for _ in range(0 if bk else 8 - len(keys))]
    bt = tbl(blank, [1.8 * inch, 2.35 * inch, 2.35 * inch], fs=8 if bk else 7, pad=3 if bk else 1)
    if not bk:
        bt._argH[1:] = [0.3 * inch] * (len(blank) - 1)
    if KEYNOTE.get(title):
        S += [Spacer(1, 2)]
    S += [bt] + ([Spacer(1, 4), Paragraph(KEYNOTE[title], small)] if KEYNOTE.get(title) else []) + [PageBreak()]

    toc = TableOfContents(); toc.levelStyles = [ss['BodyText'].clone('toc0', fontSize=10, leading=14)]
    S += [Paragraph('Contents', ss['Heading2']), toc, Spacer(1, 10)]
    ro = sum(1 for r in chs.values() if r['PTT Prohibit'] == 'On')
    S += [Paragraph('What is programmed on this radio', h1)]
    S += [Paragraph(f"{len(chs)} channels in {len(zones)} zones; {ro} are receive only. Zones fall into these groups:", ss['BodyText']), Spacer(1, 4)]
    S += [tbl([['Group', 'Zones', 'Channels', 'What it is']] + [[Paragraph(escape(k), small), str(zn), str(cn), Paragraph(escape(d), small)] for k, zn, cn, d in channel_types(chs, zones)],
              [1.6 * inch, 0.5 * inch, 0.7 * inch, 4.7 * inch])]
    S += [Spacer(1, 6), Paragraph('Channel names: DMR channels are SITE then talkgroup (e.g. BRDCT CT SW); FM repeaters are CALL City. A zone holds up to 250 channels; a scan list is selected per channel.', ss['BodyText'])]
    S += [Spacer(1, 8), Paragraph('Using the radio', ss['Heading2'])] + [Paragraph(t, ss['BodyText']) for t in USE.get(title, [])] + [Spacer(1, 4), Paragraph(BEFORE, ss['BodyText'])]
    S += [PageBreak()]

    cnt = lambda z: len(z['Zone Channel Member'].split('|')) if z['Zone Channel Member'] else 0
    def zone_table():
        zr = [[z['No.'], z['Zone Name'], str(cnt(z)), str(zpage.get(z['No.'], ''))] for z in zones]
        half = (len(zr) + 1) // 2
        pair = [['#', 'Zone', 'Ch', 'Page', '#', 'Zone', 'Ch', 'Page']]
        for i in range(half):
            pair.append(zr[i] + (zr[i + half] if i + half < len(zr) else ['', '', '', '']))
        w = [0.3 * inch, 1.9 * inch, 0.35 * inch, 0.45 * inch]
        zt = tbl(pair, w + w, fs=6.5, pad=0.5)
        zt.setStyle(TableStyle([('LINEAFTER', (3, 0), (3, -1), 1.5, colors.black)]))
        return zt
    zt = Lazy(zone_table)
    S += [Paragraph('Zone list', h1), zt, NextPageTemplate('two'), PageBreak()]

    S += [Paragraph('Zone channels', h1)]
    for z in zones:
        data = [['Channel', 'RX MHz', 'TX MHz', 'Tone / CC TS TG']]
        for n in (z['Zone Channel Member'].split('|') if z['Zone Channel Member'] else []):
            r = chs[n]
            if r['Channel Type'] == 'D-Digital':
                info = f"CC{r.get('RX Color Code', r.get('Color Code'))} TS{r['Slot']} {r['Contact']}"
            else:
                info = r['CTCSS/DCS Encode'] if r['CTCSS/DCS Encode'] != 'Off' else ''
            if r['PTT Prohibit'] == 'On':
                info = (info + ' RX only').strip()
            data.append([Paragraph(escape(n), ztext), r['Receive Frequency'], r['Transmit Frequency'], Paragraph(escape(info), ztext)])
        S += [KeepTogether([Paragraph(f"{z['No.']}. {escape(z['Zone Name'])}", zhead), tbl(data, [1.05 * inch, 0.62 * inch, 0.62 * inch, col - 2.29 * inch], fs=6.5, pad=0.5)]), Spacer(1, 4)]
    S += [Paragraph('Talkgroups', h1),
          tbl([['#', 'ID', 'Name', 'Call type']] + [[t['No.'], t['Radio ID'], escape(t['Name']), t['Call Type']] for t in tgs], [0.4 * inch, 0.7 * inch, 1.6 * inch, col - 2.7 * inch], fs=6.5, pad=0.5)]
    def grid(names, n=3):
        cells = [[Paragraph(escape(x), ztext) for x in names[k:k + n]] + [Paragraph('', ztext)] * (n - len(names[k:k + n])) for k in range(0, len(names), n)]
        t = Table(cells, colWidths=[col / n] * n)
        t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.25, colors.grey), ('TOPPADDING', (0, 0), (-1, -1), 0.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5)]))
        return t

    def named_lists(title_, items):
        out_ = [Paragraph(title_, h1)]
        for name, members in items:
            out_ += [KeepTogether([Paragraph(f'{escape(name)} ({len(members)})', zhead), grid(members)]), Spacer(1, 4)]
        return out_

    S += named_lists('Scan lists', [(r['Scan List Name'], r['Scan Channel Member'].split('|')) for r in rows(folder / 'ScanList.CSV') if r['Scan Channel Member']])
    rz = [r for r in csv.reader(open(folder / 'RoamingZone.CSV', newline='')) if len(r) > 2 and r[0] != 'No.']
    S += named_lists('Roaming zones (DMR sites)', [(r[1], r[2].split('|')) for r in rz])
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    doc.multiBuild(S)


if __name__ == '__main__':
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'import' / 'd878uv')
    out = Path(sys.argv[2] if len(sys.argv) > 2 else ROOT / 'out' / 'guides' / (folder.name + '.pdf'))
    build(folder, out, sys.argv[3] if len(sys.argv) > 3 else 'AT-D878UV')
    print('wrote', out)
