# AnyTone codeplugs (KC1JMH)

CSV codeplugs for the **AnyTone AT-D878UV** (HT) and **AT-D578UV** (mobile), for import into the AnyTone CPS. New England DMR (NEDECN),
FM repeaters from the state coordinators, Maine ARES / Cumberland County ECT channels, and receive-only government interoperability
channels (Maine FOG, NIFOG).

- `import/d878uv/` and `import/d578uv/` — **the CSVs to import into each radio's CPS** (generated from `data/`, committed). Both radios are built from the same data and match, except that the 578 also carries the 220 MHz band.
- `data/` — the single source of truth (channels, zones, scan lists, talkgroups with stable IDs; `data/static/` holds the other tables such as hotkeys and roaming). `data/sources/` holds parsed source data.
- `exports/d878uv/`, `exports/d578uv/` — raw CPS exports, kept only as templates (column headers; the 578's own per-channel values). Not edited.
- `codeplug/` — the generator (`model.py`), fetchers, parsers and the one-shot zone builders (`add_*.py`, which edit `import/d878uv`). `TODO.md` — status and open items.

**Maintaining this (agents and humans): see [docs/MAINTAINING.md](docs/MAINTAINING.md)** — the model, the refresh procedure, standing rules and the verification checklist.

## Importing into the CPS
Back up your current codeplug first. In the CPS: Tools -> Import -> select `at-d878uv.LST` from the folder (the CPS imports by that list; do not rename the files).
Check Zone and Channel counts afterwards. Receive-only channels have PTT Prohibit on and cannot transmit.

## Building
    python3 codeplug/model.py build d878uv   # data/ -> import/d878uv   (also: build d578uv)
    python3 codeplug/model.py check d878uv   # round trip: data/ -> build -> byte-identical to import/d878uv
    python3 codeplug/model.py parity         # the radios must match except the 578's 220 MHz content
    python3 codeplug/guide.py import/d578uv guides/d578uv.pdf AT-D578UV   # printable PDF guide
To change the codeplug: edit `import/d878uv` (with `codeplug/cplib.py` or a script like `add_*.py`), then run `python3 codeplug/model.py sync` to fold the change into `data/` (IDs are kept by name) and `build` both radios. `DigitalContactList.CSV` is large and gitignored: it is kept in `data/static/` locally and regenerated from RadioID.net.

## Sources
nedecn.org, nesmc.org / CSMA / VIRCC (via `codeplug/fetch_coordinators.py`, no logins), nerepeaters.com, the Maine Statewide Interoperability FOG, NIFOG 2.02,
the 2020 Maine ARES frequency list, YCECT (k1yem.com) ICS 217A. Credentials for RepeaterBook and myGMRS go in `.env` (see `.env.example`; gitignored).
Receive-only government channels are for monitoring; transmit only on frequencies you are licensed for.
