"""Channel naming for FM repeaters: '<CALL> <City>', always including the location, max 16 chars.

Rules (see CLAUDE.md):
  1. Callsign first, then the city. The state is implied by the per-state zone, so it is only
     appended (2 letters) when the same city name exists in more than one state in our list.
  2. Over 16 chars: abbreviate North/East/South/West/Mount/Saint/Fort, then truncate the city.
  3. The same callsign+city on two bands/frequencies gets ' 2m' / ' 70cm' appended, and the city
     is truncated to make room.
"""
import re

LIMIT = 16
ABBREV = {'north': 'N', 'east': 'E', 'south': 'S', 'west': 'W', 'mount': 'Mt', 'mt.': 'Mt', 'saint': 'St', 'st.': 'St', 'fort': 'Ft'}
BAND = [(144, 148, '2m'), (222, 225, '1.25m'), (420, 450, '70cm')]


def band_tag(freq_mhz):
    return next((t for lo, hi, t in BAND if lo <= float(freq_mhz) < hi), '')


def repeater_name(call, city, state=None, multi_state=False, band=None):
    """>>> repeater_name('W1QUI', 'Falmouth')
    'W1QUI Falmouth'
    >>> repeater_name('N1BS', 'North Providence')
    'N1BS N Providenc'
    >>> repeater_name('KC1US', 'North Reading')
    'KC1US N Reading'
    >>> repeater_name('WJ1L', 'Alfred', band='2m')
    'WJ1L Alfred 2m'
    >>> repeater_name('W1NPP', 'Auburn')
    'W1NPP Auburn'
    >>> repeater_name('W1SYE', 'Portsmouth', 'RI', multi_state=True)
    'W1SYE Portsmo RI'
    >>> repeater_name('N1IMO', 'Greenville', 'RI', multi_state=True)
    'N1IMO Greenvi RI'
    """
    suffix = (f' {state}' if multi_state and state else '') + (f' {band}' if band else '')
    base = f'{call} '
    city = re.sub(r'\s+', ' ', city.strip())
    if len(base + city + suffix) > LIMIT:
        city = ' '.join(ABBREV.get(w.lower(), w) for w in city.split())
    room = LIMIT - len(base) - len(suffix)
    return (base + city[:room].rstrip() + suffix)


if __name__ == '__main__':
    import doctest
    print(doctest.testmod())
