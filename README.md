# AnyTone codeplugs (KC1JMH)

CSV codeplugs for the **AnyTone AT-D878UV** (HT) and **AT-D578UV** (mobile), for import into the AnyTone CPS. New England DMR (NEDECN),
FM repeaters from the state coordinators, Maine ARES / Cumberland County ECT channels, and receive-only government interoperability
channels (Maine FOG, NIFOG).

- `exports/d878uv/` — the live 878 codeplug (CPS export, edited by the scripts in `codeplug/`). `exports/d578uv/` is the 578's CPS export (firmware 1.14), used as the column/format template for its build.
- `data/` — the single-source tables with stable IDs (`codeplug/model.py`); `out/` is generated from it.
- `codeplug/` — fetchers, parsers and the zone builders (`add_*.py`). `data/sources/` holds parsed source data.
- `TODO.md` — status and open items.

## Importing into the CPS
Back up your current codeplug first. In the CPS: Tools -> Import -> select `at-d878uv.LST` from the folder (the CPS imports by that list; do not rename the files).
Check Zone and Channel counts afterwards. Receive-only channels have PTT Prohibit on and cannot transmit.

## Building
    python3 codeplug/model.py bootstrap      # exports/d878uv -> data/ (adopts stable channel IDs; done once)
    python3 codeplug/model.py build d878uv   # data/ -> out/d878uv
    python3 codeplug/model.py check d878uv   # byte-for-byte comparison with exports/d878uv
    python3 codeplug/model.py sync           # bootstrap + adopt the 578-only (220 MHz) channels
    python3 codeplug/model.py build d578uv   # data/ -> out/d578uv (578 column layout; untested import)
Radio profiles in `model.py` list each radio's bands, so 220 MHz channels reach the 578 only. Until the add_* scripts are retargeted to
`data/`, they edit `exports/d878uv` and `model.py bootstrap` re-adopts the result (IDs for existing channels would be reassigned by position, so
treat the data/ tables as regenerated, not hand-edited, until then).

## Sources
nedecn.org, nesmc.org / CSMA / VIRCC (via `codeplug/fetch_coordinators.py`, no logins), nerepeaters.com, the Maine Statewide Interoperability FOG, NIFOG 2.02,
the 2020 Maine ARES frequency list, YCECT (k1yem.com) ICS 217A. Credentials for RepeaterBook and myGMRS go in `.env` (see `.env.example`; gitignored).
Receive-only government channels are for monitoring; transmit only on frequencies you are licensed for.
