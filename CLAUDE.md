# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Codeplugs for KC1JMH's **AnyTone AT-D878UV** (DMR/analog HT) and **AT-D578UV** (mobile), as CSV files imported into the AnyTone CPS. Original CPS exports live in `exports/d878uv/` and `exports/d578uv/`. A Python generator that builds both radios' CSVs from one data source is planned. See `TODO.md` for the work plan and status.

Data sources: nedecn.org (DMR repeaters, plus its official AnyTone CSV pack), the state frequency coordinators — nesmc.org (ME/NH/MA/RI), ctspectrum.com (CT), ranv.org/rptr.html for VIRCC (VT) — all public, no login; fetch with `python3 codeplug/fetch_coordinators.py`, nerepeaters.com, RepeaterBook (API token), mygmrs.com (GMRS). NEDECN's per-site web pages are more current and more reliable than its CSV pack (see `TODO.md`); the pack has typos, empty zone frequency lists and duplicate channel names. Credentials go in `.env` (gitignored; see `.env.example`). Raw fetches go in `cache/` (gitignored).

## File format rules (CPS import is strict)

- `at-d878uv.LST` is the import manifest: first line is the file count, then `index,"Filename.CSV"`. The CPS imports by this list, so filenames must not change.
- Every field is double-quoted, lines are CRLF, plain ASCII (no BOM). Preserve the exact header row of each file, including quirks like trailing commas (`AlertTone.CSV`, `RoamingZone.CSV`) and misspellings (`Longtitude`, `Frequencys`, `"Zone Hide "`).
- Every row in a file must have the same column count as its header (`Channel.CSV` = 56 columns).
- `No.` columns are 1-based sequential indices; renumber after inserting/deleting rows.
- Multi-value fields use `|` as the separator, and parallel `|` lists must stay aligned element-for-element.
- Names are limited to 16 characters (channel, zone, scan list, talkgroup names).
- Use Python's `csv` module with `quoting=csv.QUOTE_ALL` and `lineterminator='\r\n'` when rewriting files.

## Cross-file references

Records are linked **by name (plus frequency)**, not by ID, so renaming something requires updating every reference:

- `Channel.CSV` → `Contact` + `Contact TG/DMR ID` must match a row in `TalkGroups.CSV`; `Radio ID` matches a `Name` in `RadioIDList.CSV` (`KC1JMH / Brad Brown`, ID 3123446); `Scan List` matches `ScanList.CSV` names (or `None`); `Receive Group List` matches `ReceiveGroupCallList.CSV` (or `None`).
- `Zone.CSV` and `ScanList.CSV` → `... Channel Member` lists channel names, with parallel `... RX Frequency` / `... TX Frequency` lists that must match those channels' frequencies in `Channel.CSV`. `A Channel`/`B Channel` and priority/revert channels follow the same name+RX+TX pattern.
- `RoamingZone.CSV` → `Roaming Channel Member` lists `Name`s from `RoamingChannel.CSV` (DMR repeater roaming, e.g. the NEDECN network).
- `DigitalContactList.CSV` is the large (~317k row) RadioID.net user database for caller ID display; it is standalone, gitignored, and regenerated rather than hand-edited. Avoid loading it into context.

## Data conventions

- Channels: `Channel Type` is `D-Digital` or `A-Analog`; frequencies are MHz with 5 decimals (`442.20000`); `Slot` is `1`/`2`; DMR channels are named `<SITE> <Talkgroup>` (e.g. `BRDCT CT SW`) and grouped one zone per repeater site.
- Coverage is New England DMR repeaters (CT/MA/ME/NH/VT), plus analog channels and a NOAA Weather scan list.
