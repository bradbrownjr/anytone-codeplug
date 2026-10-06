# TODO

Goal: one source of truth that generates CPS-importable CSVs for both the **AT-D878UV** (HT) and **AT-D578UV** (mobile), kept current from NEDECN, NESMC, NERepeaters, RepeaterBook and myGMRS.

## 0. Repo setup
- [x] `git init`, `.gitignore`, `.env.example`
- [x] Move the original 878 CPS export to `exports/d878uv/`
- [ ] Create public GitHub repo (`gh repo create bradbrownjr/anytone-codeplug --public --source . --push`)
- [ ] README: what this is, how to build, how to import into the CPS

## 1. Inputs from Brad
- [ ] Export all CSVs from the **578 CPS** into `exports/d578uv/` (Tools → Export, all tables, with the `.LST`)
- [ ] Record CPS + firmware versions for both radios (in README)
- [ ] Fill in `.env`: RepeaterBook API token, NESMC login, myGMRS login
- [ ] Decide what "active" means for analog repeaters: NESMC coordination status, NERepeaters last-updated age, or both

## 2. Generator tool (`codeplug/`, Python)
- [ ] Data model + YAML source files in `data/` (channels, talkgroups, zones, scan lists, roaming, radio IDs, static settings)
- [ ] Importer: convert the current 878 export into `data/` (one-time bootstrap)
- [ ] Writers for `out/d878uv/` and `out/d578uv/` (per-model column maps, `.LST` manifest, QUOTE_ALL, CRLF)
- [ ] Round-trip test: bootstrap → generate 878 → byte-identical to `exports/d878uv/`
- [ ] Validator: dangling zone/scan/roaming members, RX/TX lists match channels, contact/TG ID pairs, 16-char names, ≤250 channels/zone, ≤4000 channels, ≤250 zones, duplicate names
- [ ] Dry-run diff report: what changed in channels/zones vs the last build

## 3. Fetchers (snapshots go to `cache/`, gitignored; normalized output to `data/sources/`)
- [ ] **NEDECN** — repeater pages + official AnyTone CSV pack (nedecn.org/downloads/codeplugs/); also check their D578UV codeplug for column layout
- [ ] **NERepeaters** — parse the embedded data in `NERepeaters.php` (freq, offset, state, city, call, tones, last-updated)
- [ ] **NESMC** — logged-in fetch of coordination data; treat as authoritative for coordinated/active status
- [ ] **RepeaterBook** — token API export for CT/MA/ME/NH/RI/VT, 2m + 70cm FM (cross-check)
- [ ] **myGMRS** — find the JSON endpoint behind mygmrs.com/repeaters; pull New England GMRS repeaters
- [ ] **RadioID** — regenerate `DigitalContactList.CSV` (N.A. only, or full DB, depending on radio memory)
- [ ] Reconcile: merge sources keyed on freq + location + call, flag conflicts for manual review

## 4. Codeplug content
- [ ] DMR: refresh NEDECN sites/talkgroups/zones; drop decommissioned sites; refresh `RoamingChannel`/`RoamingZone`
- [ ] Analog: replace "ME Analog"/"NH Analog" with one zone per state — CT, MA, ME, NH, RI, VT (split 2m/440 if over 250)
- [ ] Per-state analog scan lists
- [ ] GMRS: rebuild repeater list from myGMRS (keep simplex GMRS 1–22)
- [ ] Keep as-is: Simplex, MURS, Marine, Weather, CCEMA/public safety, Packet, satellites
- [x] 2026-10-06: ME Event 1/2 talkgroups (31231/31232) added to TalkGroups + every Maine zone (slots from Shapleigh announcement: Event 1 TS1, Event 2 TS2; verify per site)
- [x] 2026-10-06: added zones Bridgton ME, Peru ME, Wilmington MA, Henniker NH, Portsmouth NH; Holden ME zone rebuilt from orphaned HLDME channels; K8MOT Bridgton FM (145.21 -, 118.8) added to ME Analog + All Analog scan list
- [ ] Skipped TGs with no contact (Audio Watch 9999, TAC312, TAC316) — add contacts/channels if wanted
- [ ] Reconcile existing zones that disagree with NEDECN pages (freq/CC): Augusta ME (codeplug 145.17 vs NEDECN 145.24), Dexter ME and Dresden ME (CC 0 vs 12), Smyrna ME (147.09 vs 145.19), plus Bow NH, Chester NH, Boston MA, Sagamore MA, Southboro MA, Northford CT, Hudson NH, Gofftstown NH, Gunstock NH VHF, VT sites — several NEDECN pages are image/table-only and didn't parse; check by hand
- [ ] Orphan channels not in any zone (MTWNH COOS, MTWNH VT SW, GMRS 1.. etc.) — decide keep/remove
- [ ] GMRS zone B channel (WJ1L Alfred 2m) isn't a zone member — pre-existing quirk
- [ ] Naming convention for analog repeaters within 16 chars (e.g. `W1QUI Falmouth`)
- [ ] 578-only: 220 MHz (1.25 m) repeaters? Cross-band / mobile-specific settings?

## 5. Workflow
- [ ] `make`/script entry points: `fetch`, `build`, `validate`, `diff`
- [ ] Update CLAUDE.md with the tool's commands and layout once it exists
- [ ] Optional: scheduled GitHub Action to fetch + open a PR when sources change
