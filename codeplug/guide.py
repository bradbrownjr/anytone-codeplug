#!/usr/bin/env python3
"""Render a printable PDF radio guide (zone list, per-zone channel tables, talkgroups) from a built codeplug folder.

    python3 codeplug/guide.py [codeplug dir] [output.pdf] [radio title]     default: exports/d878uv -> out/guides/d878uv.pdf

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
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent.parent
BUTTONS = []   # [(key, short press, long press)] -- needs Brad's confirmation / the 578 export

NAV = {
    'AT-D878UV': ['Change zone: press the Zone/menu function (long press of the P-key mapped to it, or Menu -> Zone) and pick the zone with the knob or Up/Down, then confirm.',
                  'Change channel: turn the channel knob (or Up/Down) within the current zone; the A/B line shows the active VFO.',
                  'Switch A/B: use the A/B key (top of keypad); each line holds its own zone and channel.',
                  'Receive-only channels (marked RX only) have PTT Prohibit on and will not transmit.',
                  'Confirm these steps against your radio; button assignments are in the CPS under Optional Setting -> Key Function.'],
}


def rows(path):
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def commit():
    try:
        return subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', '--short', 'HEAD'], text=True).strip()
    except Exception:
        return 'unknown'


def build(folder, out, title):
    chs = {r['Channel Name']: r for r in rows(folder / 'Channel.CSV')}
    zones = rows(folder / 'Zone.CSV')
    tgs = rows(folder / 'TalkGroups.CSV')
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
    S += [Paragraph('Programmable buttons', ss['Heading2'])]
    S += [tbl([['Key', 'Short press', 'Long press']] + BUTTONS, [1.5 * inch, 2.5 * inch, 2.5 * inch])] if BUTTONS else \
         [Paragraph('Not yet filled in: key assignments are not part of the CPS CSV export and the button diagram needs the physical layout confirmed.', ss['BodyText'])]
    S += [Paragraph('Zones', ss['Heading2'])]
    S += [tbl([['#', 'Zone', 'Channels']] + [[z['No.'], escape(z['Zone Name']), str(len(z['Zone Channel Member'].split('|')) if z['Zone Channel Member'] else 0)] for z in zones],
              [0.5 * inch, 3 * inch, 1 * inch])]
    S += [PageBreak()]
    for z in zones:
        S += [Paragraph(f"{z['No.']}. {escape(z['Zone Name'])}", ss['Heading3'])]
        data = [['Channel', 'RX MHz', 'TX MHz', 'Type', 'Tone / CC / TG', 'Notes']]
        for n in (z['Zone Channel Member'].split('|') if z['Zone Channel Member'] else []):
            r = chs[n]
            if r['Channel Type'] == 'D-Digital':
                info = f"CC{r['RX Color Code']} TS{r['Slot']} {r['Contact']}"
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
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'exports' / 'd878uv')
    out = Path(sys.argv[2] if len(sys.argv) > 2 else ROOT / 'out' / 'guides' / (folder.name + '.pdf'))
    build(folder, out, sys.argv[3] if len(sys.argv) > 3 else 'AT-D878UV')
    print('wrote', out)
