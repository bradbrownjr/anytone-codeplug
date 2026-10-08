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
from reportlab.platypus import Flowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent.parent
BUTTONS = []   # [(key, short press, long press)] -- needs Brad's confirmation / the 578 export

NAV = {
    'AT-D878UV': ['Change zone: press the Zone/menu function (long press of the P-key mapped to it, or Menu -> Zone) and pick the zone with the knob or Up/Down, then confirm.',
                  'Change channel: turn the channel knob (or Up/Down) within the current zone; the A/B line shows the active VFO.',
                  'Switch A/B: use the A/B key (top of keypad); each line holds its own zone and channel.',
                  'Receive-only channels (marked RX only) have PTT Prohibit on and will not transmit.',
                  'Confirm these steps against your radio; button assignments are in the CPS under Optional Setting -> Key Function.'],
}


class KeyDiagram(Flowable):
    """Blank radio outline with write-in boxes, to be filled by hand (key assignments are not in the CSV export)."""
    W, H = 7.5 * inch, 3.6 * inch

    def __init__(self, mobile):
        super().__init__(); self.mobile = mobile; self.width, self.height = self.W, self.H

    def wrap(self, aw, ah):
        return self.W, self.H

    def box(self, c, x, y, label, w=1.45 * inch):
        c.setLineWidth(0.6); c.rect(x, y, w, 0.5 * inch)
        c.setFont('Helvetica', 6.5); c.drawString(x + 3, y + 0.5 * inch - 8, label)
        c.setLineWidth(0.25); c.line(x + 3, y + 8, x + w - 3, y + 8); c.line(x + 3, y + 20, x + w - 3, y + 20)

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
            targets = [('PF3 - emergency key (top)', 0.1, 2.95, fx - 0.5 * inch, 2.78 * inch),
                       ('P1 key', 0.1, 0.75, fx - 0.55 * inch, 1.23 * inch),
                       ('P2 key', 3.9, 0.75, fx + 0.55 * inch, 1.23 * inch),
                       ('PF1 - upper side key', 6.15, 1.45, sx + 0.15 * inch, 1.2 * inch),
                       ('PF2 - lower side key', 6.15, 0.6, sx + 0.15 * inch, 0.85 * inch)]
            for t, x, y, tx, ty in targets:
                x, y = x * inch, y * inch
                self.box(c, x, y, t, w=1.35 * inch)
                c.setLineWidth(0.4)
                c.line(x + (1.35 * inch if x < tx else 0), y + 0.25 * inch, tx, ty)
            c.setFont('Helvetica', 6.5)
            c.drawString(0.1 * inch, 0.05 * inch, 'Not programmable here: channel switch and POWER/VOL knobs (top), Menu, Exit, speaker, PTT.')
        else:                   # mobile: control head and hand microphone
            c.roundRect(0.2 * inch, 1.9 * inch, 4.2 * inch, 1.4 * inch, 6); c.setFont('Helvetica', 7); c.drawCentredString(2.3 * inch, 2.6 * inch, 'control head / display')
            c.roundRect(5.3 * inch, 0.3 * inch, 1.1 * inch, 2.6 * inch, 8); c.drawCentredString(5.85 * inch, 1.6 * inch, 'hand mic')
            c.rect(5.45 * inch, 0.5 * inch, 0.8 * inch, 1.0 * inch); c.drawCentredString(5.85 * inch, 0.95 * inch, 'keypad')
            for x, t in enumerate(('head key 1', 'head key 2', 'head key 3')):
                self.box(c, (0.2 + x * 1.5) * inch, 1.1 * inch, t, w=1.4 * inch)
            for x, t in enumerate(('mic P1', 'mic P2', 'mic P3', 'mic P4')):
                self.box(c, (6.5 + 0 * x) * inch if False else 6.5 * inch, (2.85 - x * 0.65) * inch, t, w=0.95 * inch)
            self.box(c, 0.2 * inch, 0.3 * inch, 'knobs / other', w=1.4 * inch); self.box(c, 1.75 * inch, 0.3 * inch, 'other', w=1.4 * inch)
        c.restoreState()


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

    def tbl(data, widths):
        t = Table(data, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([('FONTSIZE', (0, 0), (-1, -1), 7), ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                               ('GRID', (0, 0), (-1, -1), 0.25, colors.grey), ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1)]))
        return t

    S = [Paragraph(head, ss['Title']), Paragraph(f'Generated {datetime.date.today()} from codeplug commit {commit()}. KC1JMH.', ss['BodyText']), Spacer(1, 12),
         Paragraph('Moving between zones and channels', ss['Heading2'])]
    S += [Paragraph(escape(t), ss['BodyText']) for t in NAV.get(title, ['(navigation steps for this model still to be written)'])]
    mobile = 'D578' in title
    S += [Paragraph('Programmable buttons (write in the assignments)', ss['Heading2']), KeyDiagram(mobile), Spacer(1, 6)]
    keys = [['PF1 (side, upper)', '', ''], ['PF2 (side, lower)', '', ''], ['PF3 (top, emergency)', '', ''], ['P1', '', ''], ['P2', '', '']] if not mobile else []
    blank = [['Key', 'Short press', 'Long press']] + keys + [['', '', ''] for _ in range(8 - len(keys))]
    bt = tbl(blank, [1.5 * inch, 2.5 * inch, 2.5 * inch]); bt._argH[1:] = [0.3 * inch] * 8
    S += [bt]
    S += [PageBreak(), Paragraph('What is programmed on this radio', ss['Heading2'])]
    ro = sum(1 for r in chs.values() if r['PTT Prohibit'] == 'On')
    S += [Paragraph(f"{len(chs)} channels in {len(zones)} zones; {ro} are receive only. Zones fall into these groups:", ss['BodyText']), Spacer(1, 4)]
    S += [tbl([['Group', 'Zones', 'Channels', 'What it is']] + [[Paragraph(escape(k), small), str(zn), str(cn), Paragraph(escape(d), small)] for k, zn, cn, d in channel_types(chs, zones)],
              [1.6 * inch, 0.5 * inch, 0.7 * inch, 4.7 * inch])]
    S += [Spacer(1, 6), Paragraph('Channel names: DMR channels are SITE then talkgroup (e.g. BRDCT CT SW); FM repeaters are CALL City. A zone holds up to 250 channels; a scan list is selected per channel.', ss['BodyText'])]
    S += [PageBreak(), Paragraph('Zones', ss['Heading2'])]
    S += [tbl([['#', 'Zone', 'Channels']] + [[z['No.'], escape(z['Zone Name']), str(len(z['Zone Channel Member'].split('|')) if z['Zone Channel Member'] else 0)] for z in zones],
              [0.5 * inch, 3 * inch, 1 * inch])]
    S += [PageBreak()]
    for z in zones:
        S += [Paragraph(f"{z['No.']}. {escape(z['Zone Name'])}", ss['Heading3'])]
        data = [['Channel', 'RX MHz', 'TX MHz', 'Type', 'Tone / CC / TG', 'Notes']]
        for n in (z['Zone Channel Member'].split('|') if z['Zone Channel Member'] else []):
            r = chs[n]
            if r['Channel Type'] == 'D-Digital':
                info = f"CC{r.get('RX Color Code', r.get('Color Code'))} TS{r['Slot']} {r['Contact']}"
            else:
                info = (r['CTCSS/DCS Encode'] if r['CTCSS/DCS Encode'] != 'Off' else '')
            data.append([Paragraph(escape(n), small), r['Receive Frequency'], r['Transmit Frequency'], r['Channel Type'][2:], Paragraph(escape(info), small),
                         'RX only' if r['PTT Prohibit'] == 'On' else ''])
        S += [tbl(data, [1.5 * inch, 0.9 * inch, 0.9 * inch, 0.6 * inch, 2.2 * inch, 0.8 * inch]), Spacer(1, 10)]
    S += [PageBreak(), Paragraph('Talkgroups', ss['Heading2']),
          tbl([['#', 'ID', 'Name', 'Call type']] + [[t['No.'], t['Radio ID'], escape(t['Name']), t['Call Type']] for t in tgs], [0.5 * inch, 1 * inch, 2.5 * inch, 1.2 * inch])]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(out), pagesize=letter, leftMargin=0.5 * inch, rightMargin=0.5 * inch, topMargin=0.5 * inch, bottomMargin=0.6 * inch,
                      title=head).build(S, onFirstPage=footer, onLaterPages=footer)


if __name__ == '__main__':
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'import' / 'd878uv')
    out = Path(sys.argv[2] if len(sys.argv) > 2 else ROOT / 'out' / 'guides' / (folder.name + '.pdf'))
    build(folder, out, sys.argv[3] if len(sys.argv) > 3 else 'AT-D878UV')
    print('wrote', out)
