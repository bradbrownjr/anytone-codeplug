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
- [ ] Fill in `.env`: RepeaterBook API token, myGMRS login (NESMC needs none)
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
- [x] **Coordinators** (`codeplug/fetch_coordinators.py`, writes `cache/`): no logins needed. NESMC (ME/NH/MA/RI) and CSMA (CT) share one search backend at rptr.amateur-radio.net (radius queries, max 120 mi, swept from several centers; 144 and 440 only); VIRCC (VT) is a static table at ranv.org/rptr.html that needs a browser-style User-Agent and also lists some NY/NH/QC repeaters. Owners can hide records, so absence != uncoordinated. Notes carry DMR/P25/Fusion/D-STAR modes
- [ ] Coordinator lists have no offsets (except VIRCC) — derive from band plan (2m ±0.6, 70cm ±5) or cross-check RepeaterBook
- [ ] VIRCC has no "last updated" date; sanity-check against NERepeaters
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
- [x] 2026-10-06: cross-referenced all 89 NEDECN repeater pages and NEDECN's CSV pack (AnyTone-878-CSV-Files.zip, dated 2026-09-24). Added TGs 9999 Audio Watch, 312, 316, 8808 NH Lakes, 31361 Upstate NY, 31235 FCEMA; added 383 missing TG channels and fixed 34 slots so every site matches its NEDECN page; fixed Dexter/Dresden CC (0->12), Augusta (145.24), Smyrna (145.19/CC12); added Mattituck, Riverhead, Selden NY and Bristol RI from the pack
- NEDECN pages are the primary source (newer: Bridgton, Peru, Henniker, Portsmouth are not in the pack). The pack is sloppy: empty zone frequency lists, ambiguous duplicate channel names, typos (Southboro UHF 447.375 vs the page's 448.375), CC 0 entries. Use it only as a cross-check
- [ ] Verify pack-only sites that have no NEDECN page: Bristol RI (K1CW 145.33 CC2 — NERepeaters lists K1CW 145.33 as FM only), Riverhead NY, Selden NY, Mattituck NY
- [ ] Verify Lyndeborough NH: changed 433.9375/438.9375 -> 443.9375/448.9375 on the pack's word alone (no NEDECN page)
- [ ] Duplicate repeater: NEDECN's Sidney page is the Augusta KC1FRJ repeater, so `Augusta ME` and `Sydney ME` zones are the same site now. Drop one
- [ ] No NEDECN page to check against: Northford CT, Boothbay ME, Topsham ME, Goffstown UHF NH, Gunstock NH UHF, Hudson NE1B/UHF NH, Lyndon VT, Mt Snow VT. Northfield VT and Somersworth NH are marked off the air on NEDECN
- [ ] Sort order: new channels were appended to the end of each zone, not alphabetized
- [ ] Orphan channels not in any zone (MTWNH COOS, MTWNH VT SW, GMRS 1.. etc.) — decide keep/remove
- [ ] GMRS zone B channel (WJ1L Alfred 2m) isn't a zone member — pre-existing quirk
- [x] 2026-10-07: Mt Washington W1NH tone 62.5 -> 100.0; added ECT1/ECT2 SKYWARN/ECT3, X-Band V/U and a `CCEMA PACE` zone built from the two WSSM-ECT ICS-217A sheets (FM + DV); fixed DMR simplex typo 146.790 -> 145.790 (renamed `DMRS 145.790`)
- [ ] Incorporate Maine statewide interoperability FOG (2017, mostly government channels: add receive-only), current NIFOG, Maine ARES county frequencies (ka1aar.org/download/MaineARESFreqs.pdf, 2020), and YCECT's 217A/205 (k1yem.com). Do not modify the existing RN/CCFIRE channels (covered by the CCEMA MOU)
- [x] Naming convention for analog repeaters: `<CALL> <City>`, location always in the name (`codeplug/naming.py`, documented in CLAUDE.md)
- [ ] 578-only: 220 MHz (1.25 m) repeaters? Cross-band / mobile-specific settings?

## 5. Workflow
- [ ] `make`/script entry points: `fetch`, `build`, `validate`, `diff`
- [ ] Update CLAUDE.md with the tool's commands and layout once it exists
- [ ] Optional: scheduled GitHub Action to fetch + open a PR when sources change
