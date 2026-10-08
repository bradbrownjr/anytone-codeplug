# Maintaining the codeplugs (runbook for people and agents)

Goal: keep KC1JMH's AT-D878UV and AT-D578UV codeplugs current and identical (the 578 also carries 220 MHz), starting from public
sources. Everything here can be re-run; read "Standing rules" before changing anything.

## The model in one minute
- `import/d878uv/`, `import/d578uv/` — CSVs to import into the CPS (generated, committed). `import/d878uv` is also the working copy the editing scripts change.
- `data/` — source of truth with stable IDs (`channels.csv`, `zones.csv`, `zone_members.csv`, `scanlists.csv`, `scanlist_members.csv`, `talkgroups.csv`); `data/static/<radio>/` holds the tables that are copied through (hotkeys, FM, roaming, OptionalSetting ...); `data/sources/` holds parsed source data.
- `exports/<radio>/` — raw CPS exports, templates only (column headers; the 578's own per-channel `Simplex` values). Never edit.
- Loop: edit `import/d878uv` → `python3 codeplug/model.py sync` → `build d878uv` → `build d578uv` → `check d878uv` → `check d578uv` → `parity` → commit and push.

## Commands that are safe to re-run
| Command | What it does |
|---|---|
| `model.py sync / build <radio> / check <radio> / parity` | data model (see the module docstring); `check` proves data -> build equals the working copy byte for byte; `parity` proves the radios match except 220 MHz |
| `fetch_coordinators.py` | NESMC/CSMA/VIRCC repeater lists into `cache/` (no logins) |
| `nedecn.py fetch` then `nedecn.py report` | re-download NEDECN's site pages and diff them with the DMR zones: new/moved/retired sites, color codes, talkgroup/slot differences, talkgroups no page carries any more |
| `build_analog_candidates.py` | join the coordinator cache with NERepeaters dates -> `data/sources/analog_candidates.csv` (the committed file is a 2026-10-07 snapshot) |
| `guide.py <folder> <pdf> <title>` | printable PDF guide |

## One-shot builders (NOT idempotent: they create zones and fail or duplicate if rerun on a codeplug that has them)
`add_maine_fog.py` (ME State Net, ME Interop, EMA county zones; data from `parse_maine_fog.py` -> `data/sources/maine_fog.csv`), `add_nifog.py` (US Interop), `add_me_ares.py` +
`add_york_ect.py` + `add_emcomm2026.py` (ME ARES), `add_analog_states.py` (per-state analog zones), `add_gmrs.py` (per-state GMRS zones from `data/sources/gmrs_snapshots.csv`),
`add_scanlists.py`, `add_waterville.py`. To refresh one of these areas, write a small script on `cplib.Codeplug` (`new_channel`, `add_channels`, `add_zone`, `extend_zone`,
`remove_from_zone`, `rename_channel`, `validate`, `save`) that reconciles what is there with the new data, rather than rerunning the original.

## Refresh procedure (do this periodically, e.g. every few months, and after NEDECN/ARES announcements)
1. `git pull`; make sure `python3 codeplug/model.py check d878uv` and `parity` pass.
2. **DMR (NEDECN):** `nedecn.py fetch && nedecn.py report`. For each NEW or MOVED page add/adjust the zone (copy an existing site's channel set; channel names `<SITE5> <Talkgroup>`, one zone per site; slots as on the page; color code from the page; add to RoamingChannel/RoamingZone). For a retired site remove the zone and its channels (check nothing else references them). For talkgroups removed from the network (the NEDECN Google Group is members-only; its mail is in Brad's Gmail under the label `ham/NEDECN`, readable through the claude.ai Gmail connector once Brad authorizes it with /mcp, otherwise ask him to paste relevant posts), remove those channels and the TalkGroups.CSV row. Event talkgroups 31231 (TS1) / 31232 (TS2) are added by us to every Maine site.
3. **FM repeaters:** `fetch_coordinators.py`, `build_analog_candidates.py`, then reconcile `*Analog` zones with `add_analog_states.py` logic (FM only, updated within two years or net noted; the Bridgton K8MOT P25/FM repeater is the one digital exception).
4. **ARES / interop:** Maine ARES frequency sheet (the current one comes from the state ARES EC, newer than the 2020 PDF at ka1aar.org), NIFOG (version 2.02 used), Maine statewide FOG (2017), YCECT 217A (k1yem.com), CCEMA 217s (ws1sm.com/ECT.html).
5. **GMRS:** myGMRS repeater screenshots/text from Brad (their site has no pagination; one search per state); update `data/sources/gmrs_snapshots.csv` and reconcile `<ST> GMRS` zones.
6. Run the verification checklist below, update `TODO.md`, commit and push every logical change separately (restore points).

## Standing rules (decisions Brad made; do not undo without asking)
- **Never modify the existing RN/CCFIRE/CCEMA/ECT channels** (memorandum of understanding with Cumberland County EMA). Add, don't change. The `CCEMA PACE` zone is built from the WSSM-ECT ICS-217A sheets.
- **Government/federal/interop channels are receive-only**: PTT Prohibit On, TX = RX, Transmit Power Low, carrier squelch; reuse an existing channel with the same RX frequency; hex NAC tones left Off.
- **FM repeater names**: `<CALL> <City>` (no state), 16-char limit with direction/word abbreviations (`naming.py`); same call+city on two bands gets ` 2m`/` 70cm`. GMRS repeaters: `<City>-<ch>`, a trailing `*` means "no tone listed, private/permission-only".
- **One channel per unique frequency+tone** where reuse is sensible; share channels within a state, never across states for named repeaters.
- **Both radios must match**; only band-limited channels (220 MHz) may differ. Names ≤16 chars, ≤250 channels per zone, ≤250 zones, ≤4000 channels.
- Commit and push after every change. CPS format rules are in `CLAUDE.md` (QUOTE_ALL, CRLF, ASCII, exact headers, `No.` renumbering, `|` lists in step).
- Sources of truth: NEDECN site pages for DMR (the downloads pack is sloppy); NESMC/CSMA/VIRCC for coordination; ARES EC sheet for ARES; do not scrape RepeaterBook (API token not available).

## Verification checklist
`model.py check d878uv`, `check d578uv`, `parity`; `nedecn.py report` shows every page matching; no channel names >16; every zone/scan-list member exists with matching frequencies (`Codeplug.validate`); both radios have no dangling scan lists; open `TODO.md` for unverified items.
Test a CPS import on a small piece first (Channel.CSV + Zone.CSV) and keep a backup of the radio's current codeplug.

## Known gaps (also in TODO.md)
DCS tones are written as `D<code>N` (unverified, four GMRS channels use them; FOG channels still Off); 578 `OptionalSetting`/AES/AlertTone/GPSRoaming tables are not in the firmware-1.14 export; button map and diagrams for the guide need Brad's input; sites with no NEDECN page cannot be verified (see TODO.md).
