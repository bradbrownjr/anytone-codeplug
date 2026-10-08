# TODO

Goal: one source of truth that generates CPS-importable CSVs for both the **AT-D878UV** (HT) and **AT-D578UV** (mobile), kept current from NEDECN, NESMC, NERepeaters, RepeaterBook and myGMRS.

## 0. Repo setup
- [x] `git init`, `.gitignore`, `.env.example`
- [x] Move the original 878 CPS export to `exports/d878uv/`
- [ ] Create public GitHub repo (`gh repo create bradbrownjr/anytone-codeplug --public --source . --push`)
- [x] README: what this is, how to build, how to import into the CPS

## 1. Inputs from Brad
- [x] 2026-10-08: 578 CPS export (firmware 1.14) is in `exports/d578uv/`. Differences from the 878: 50 channel columns (`Color Code`, `TDMA`, `TDMA Adaptive`, `Simplex`; no APRS-mute/TxCC/ARC4 etc.), Zone.CSV has no `Zone Hide`, talkgroups are in `ContactTalkGroups.CSV`, radio ID name is 16 chars (`KC1JMH / Brad Br`), and the 1.14 export has no OptionalSetting, AlertTone, AES/ARC4 or GPSRoaming tables (the CPS froze mid-export, but Brad confirmed it finished: the complete set is 21 tables, listed in its `.LST`). The 578 build uses the 878's RoamingChannel/RoamingZone (same layout, newer NEDECN data). Still to do: re-export once the firmware is updated if the newer layout matters
- [ ] Record CPS + firmware versions for both radios (in README)
- [ ] Fill in `.env`: RepeaterBook API token, myGMRS login (NESMC needs none)
- [ ] Decide what "active" means for analog repeaters: NESMC coordination status, NERepeaters last-updated age, or both

## 2. Generator tool (`codeplug/`, Python)
- [ ] Data model + YAML source files in `data/` (channels, talkgroups, zones, scan lists, roaming, radio IDs, static settings)
- [x] 2026-10-07: Importer: `codeplug/model.py bootstrap` converts the 878 export into `data/` with stable channel/zone/scan list IDs
- [x] 2026-10-07: writer `model.py build` (QUOTE_ALL, CRLF, frequency lists derived, band filter per radio profile). Remaining: 578 column map once its export arrives; retarget the add_* scripts to edit `data/` instead of `exports/`
- [x] Round-trip test: `model.py check d878uv` is byte-identical to `exports/d878uv/`
- [ ] Validator: dangling zone/scan/roaming members, RX/TX lists match channels, contact/TG ID pairs, 16-char names, ≤250 channels/zone, ≤4000 channels, ≤250 zones, duplicate names
- [ ] Dry-run diff report: what changed in channels/zones vs the last build

## 3. Fetchers (snapshots go to `cache/`, gitignored; normalized output to `data/sources/`)
- [ ] **NEDECN** — repeater pages + official AnyTone CSV pack (nedecn.org/downloads/codeplugs/); also check their D578UV codeplug for column layout
- [ ] **NERepeaters** — parse the embedded data in `NERepeaters.php` (freq, offset, state, city, call, tones, last-updated)
- [x] **Coordinators** (`codeplug/fetch_coordinators.py`, writes `cache/`): no logins needed. NESMC (ME/NH/MA/RI) and CSMA (CT) share one search backend at rptr.amateur-radio.net (radius queries, max 120 mi, swept from several centers; 144 and 440 only); VIRCC (VT) is a static table at ranv.org/rptr.html that needs a browser-style User-Agent and also lists some NY/NH/QC repeaters. Owners can hide records, so absence != uncoordinated. Notes carry DMR/P25/Fusion/D-STAR modes
- [ ] Coordinator lists have no offsets (except VIRCC) — derive from band plan (2m ±0.6, 70cm ±5) or cross-check RepeaterBook
- [ ] VIRCC has no "last updated" date; sanity-check against NERepeaters
- [x] **RepeaterBook** — dropped: API access not available (2026-10-07)
- [ ] **myGMRS** — find the JSON endpoint behind mygmrs.com/repeaters; pull New England GMRS repeaters
- [ ] **RadioID** — regenerate `DigitalContactList.CSV` (N.A. only, or full DB, depending on radio memory)
- [ ] Reconcile: merge sources keyed on freq + location + call, flag conflicts for manual review

## 4. Codeplug content
- [ ] DMR: refresh NEDECN sites/talkgroups/zones; drop decommissioned sites; refresh `RoamingChannel`/`RoamingZone`
- [x] 2026-10-07: Analog: CT/MA/RI/VT Analog zones created and ME/NH Analog extended with the approved activity rule (`codeplug/add_analog_states.py`, data in `data/sources/analog_candidates.csv`); existing channels untouched. Review: outputs skipped for unknown offset (147.505, 445.025, 446.325, 446.675); repeaters with no PL get carrier squelch
- [ ] Per-state analog scan lists
- [x] 2026-10-07: GMRS: per-state `<ST> GMRS` zones (CT MA ME NH RI VT NY) from Brad's myGMRS screenshots (`data/sources/gmrs_snapshots.csv`, `codeplug/add_gmrs.py`), all listed repeaters incl. Permission Required (Brad has the owners' permission; unlisted tones = none, so identical frequency+tone entries share one channel); original GMRS zone kept. Pages were captured in full (no second pages). The 4 DPL repeaters (Pembroke-575, Pittsfield-600, Dennis-725, Gardner-575) use `D<code>N` DCS tones — UNVERIFIED, test-import before relying on them. Channels ending in `*` are private/permission-only repeaters with no tone listed
- [ ] Keep as-is: Simplex, MURS, Marine, Weather, CCEMA/public safety, Packet, satellites
- [x] 2026-10-06: ME Event 1/2 talkgroups (31231/31232) added to TalkGroups + every Maine zone (slots from Shapleigh announcement: Event 1 TS1, Event 2 TS2; verify per site)
- [x] 2026-10-06: added zones Bridgton ME, Peru ME, Wilmington MA, Henniker NH, Portsmouth NH; Holden ME zone rebuilt from orphaned HLDME channels; K8MOT Bridgton FM (145.21 -, 118.8) added to ME Analog + All Analog scan list
- [x] 2026-10-06: cross-referenced all 89 NEDECN repeater pages and NEDECN's CSV pack (AnyTone-878-CSV-Files.zip, dated 2026-09-24). Added TGs 9999 Audio Watch, 312, 316, 8808 NH Lakes, 31361 Upstate NY, 31235 FCEMA; added 383 missing TG channels and fixed 34 slots so every site matches its NEDECN page; fixed Dexter/Dresden CC (0->12), Augusta (145.24), Smyrna (145.19/CC12); added Mattituck, Riverhead, Selden NY and Bristol RI from the pack
- NEDECN pages are the primary source (newer: Bridgton, Peru, Henniker, Portsmouth are not in the pack). The pack is sloppy: empty zone frequency lists, ambiguous duplicate channel names, typos (Southboro UHF 447.375 vs the page's 448.375), CC 0 entries. Use it only as a cross-check
- [ ] Verify pack-only sites that have no NEDECN page: Bristol RI (K1CW 145.33 CC2 — NERepeaters lists K1CW 145.33 as FM only), Riverhead NY, Selden NY, Mattituck NY
- [ ] Verify Lyndeborough NH: changed 433.9375/438.9375 -> 443.9375/448.9375 on the pack's word alone (no NEDECN page)
- [x] 2026-10-07: duplicate Augusta/Sydney repeater resolved: kept `Augusta ME`, removed `Sydney ME` and its 25 SIDME channels (Brad's call)
- [ ] No NEDECN page to check against: Northford CT, Boothbay ME, Topsham ME, Goffstown UHF NH, Gunstock NH UHF, Hudson NE1B/UHF NH, Lyndon VT, Mt Snow VT. Northfield VT and Somersworth NH are marked off the air on NEDECN
- [ ] Sort order: new channels were appended to the end of each zone, not alphabetized
- [ ] Orphan channels not in any zone (MTWNH COOS, MTWNH VT SW, GMRS 1.. etc.) — decide keep/remove
- [ ] GMRS zone B channel (WJ1L Alfred 2m) isn't a zone member — pre-existing quirk
- [x] 2026-10-07: Mt Washington W1NH tone 62.5 -> 100.0; added ECT1/ECT2 SKYWARN/ECT3, X-Band V/U and a `CCEMA PACE` zone built from the two WSSM-ECT ICS-217A sheets (FM + DV); fixed DMR simplex typo 146.790 -> 145.790 (renamed `DMRS 145.790`)
- [x] 2026-10-07: Maine statewide interoperability FOG added receive-only (`ME State Net`, `ME Interop`, 15 `EMA <County>` zones; `codeplug/add_maine_fog.py`) and NIFOG 2.02 VHF/UHF national, federal IR/LE and UHF medical channels (`US Interop`, `codeplug/add_nifog.py`; 700/800 MHz, low band and VTAC17 skipped)
- [x] 2026-10-07: `ME ARES` zone from the 2020 Maine ARES frequency list (`codeplug/add_me_ares.py`): 31 unique simplex frequencies and 19 repeaters. Skipped: 52.525 and 223.500 (not on the 878), Penobscot 145.450/67.0 and Piscataquis 147.150/71.9 (no matching coordinated repeater; verify). Check: Aroostook's 146.730 PL (list says 100.0, NESMC K1FS Caribou is 123.0) and Cumberland's 146.730 (list 100.0; existing W1KVI Falmouth channel uses 62.5, left unchanged per the CCEMA MOU)
- [x] 2026-10-07: YCECT 217A/205 (k1yem.com) extras added to `ME ARES` (`codeplug/add_york_ect.py`): KB1PRG Alfred 444.850, KC1ETT Wells 448.025, 446.075/446.175, packet 145.730; GMRS Fort Ridge 462.600/162.2 and GMRS 15/16 left for the GMRS refresh. Do not modify the existing RN/CCFIRE channels (covered by the CCEMA MOU)
- [x] Naming convention for analog repeaters: `<CALL> <City>`, location always in the name (`codeplug/naming.py`, documented in CLAUDE.md)
- [ ] 578-only: the 578 does 220 MHz (1.25 m), so the generator must add 223.500 (Maine state coordination simplex, skipped on the 878) to its ME ARES zone, plus 220 MHz repeaters from the coordinators. Also check cross-band / mobile-specific settings

## 5. Workflow
- [ ] `make`/script entry points: `fetch`, `build`, `validate`, `diff`
- [ ] Update CLAUDE.md with the tool's commands and layout once it exists
- [ ] Optional: scheduled GitHub Action to fetch + open a PR when sources change

## 6. Radio guides (printable PDF)
Goal: program a colleague's radio and hand them a manual for it. One guide per radio model (D878UV, D578UV), generated from the same data as the CSVs so it never drifts from the codeplug.
- [ ] Programmable button map: every side/top/front/long-press key function, with a labeled diagram of the radio showing where each button is
- [ ] How to move between zones and channels (and A/B VFO) on that model, step by step, plus scan, priority, talk-around, power, TX-prohibit and emergency functions
- [x] 2026-10-07: `codeplug/guide.py` renders a PDF (zone list, per-zone tables, talkgroups, date + commit footer; 77 pages for the 878) to `out/guides/`. Still missing: button map and diagram (key assignments aren't in the CSV export) and verified navigation steps; CCEMA PACE first-ordering and a one-page quick card
- [ ] (original item) Zone list with channel counts, then per-zone channel tables (name, RX/TX, tone or color code/slot/talkgroup, notes), with the CCEMA PACE zone first
- [ ] Talkgroup list with slots and what each is for, DMR radio ID and contact setup, and a quick-reference card (one page, laminate-friendly)
- [ ] Mark receive-only channels (government/interop) and any usage restrictions (e.g. amateur-only, CCEMA MOU channels)
- [ ] Build step: generate Markdown/HTML from `data/`, then render to PDF (print-ready, page numbers, date + git commit in the footer so a printed copy can be traced to a codeplug version)
- [ ] Need from Brad: photos or confirmation of the physical button layout for each radio, and how the D578UV's keys are assigned today (from the 578 CPS export)

- [x] 2026-10-07: ME ARES: added W1PSQ Milo 147.150 (123.0) and W1YA Orono 145.470 (71.9); verify against RepeaterBook when a token is available
- [x] 2026-10-07: newer *Maine Amateur Radio Emcomm Frequencies* sheet (from the state ARES EC) applied over the 2020 list (`codeplug/add_emcomm2026.py`): W1NPP Auburn/Poland dropped from ME ARES (off air), added Fort Kent 146.640, Houlton 146.790, Hulls Cove 147.030, Norway 147.120, Marshfield 146.775 (192.8), Knox 443.500, WS1EC 449.225 reuse, ME 145.450 (Penobscot, still listed, callsign unknown), simplex 147.595 and 446.000. Confirmed Milo 147.150 is 123.0
- [ ] From that sheet, still open: DMR Waterville 146.925 CC12 TS2 TG 3123 (no NEDECN page, no zone yet); GMRS repeaters 462.575-462.725 (77.0 PL: Lincoln-Bagley Mtn, Charleston-Bull Hill, Cooper Hill, Eddington-Blackcap, Frankfort-Mt Waldo, Camden-Ragged Mtn) and York 462.600/162.2 for the GMRS refresh; 220 MHz (578 only): 223.500 and Oxford 224.620 (103.5, KE1M); 52.525 6 m; UFB New England Fusion repeaters (digital, not added); sheet says the DMR statewide repeaters are no longer linked
- [ ] Androscoggin W1NPP Auburn 146.610/88.5 and Poland 147.315/103.5 are off air per the state EC sheet but expected to return, possibly on new frequencies: kept in ME ARES; update frequencies when the EC publishes them
- [x] 2026-10-07: YCECT GMRS (Shapleigh-Pub 462.600/162.2 = Fort Ridge, GMRS 15/16) added to ME ARES
- [ ] DCS CSV format: RepeaterBook's AnyTone wiki says only that 'if DCS, the letter N is appended' to the CTCSS/DCS Encode/Decode value; the `D` prefix and `I` (inverted) suffix are not documented there, so `D023N` is a best inference. Verify by exporting one DCS channel from the CPS (or test-importing the 4 DPL GMRS channels), then use DCS for the FOG channels (left Off so far)
- [x] RepeaterBook: dropped (Brad: API access not going to happen); coordinators + NERepeaters remain the cross-check
- [x] 2026-10-08: `model.py` 578 profile (column map, fixed Radio ID, ContactTalkGroups, no Zone Hide) builds `out/d578uv` (2881 channels, 154 zones) from the same data; `model.py sync` re-adopts the 578-only 220 MHz channels into a `220` zone (12 channels incl. 223.500 and 224.620). Adopted KA1EKS Millinocket, KQ1L Lincoln, K1PQ Brownville from the old 578 codeplug into ME Analog
- [ ] 578: untested import. The generated `out/d578uv/Channel.CSV` has not been imported into the CPS; the 578's old scan lists (Southern ME, Northern ME, NH Analog, CCEMA, MURS...) are not carried over (only the 878's five), 578 OptionalSetting/hotkeys/startup zone untouched, and the old 578 zones Sydney ME/Southern ME/Northern ME are gone (Sydney removed; the ME 220 channels now live in `220`). The 878 and 578 codeplugs still reference scan lists that do not exist (ISS, AO-91, Packet, ...) — pre-existing
- [ ] 578 `Simplex` column: the 878 `Through Mode` has no confirmed 578 equivalent; the generator writes `Simplex` = Off for every channel
- [x] 2026-10-08: 578 export confirmed complete by Brad (what we have is what we get): 21 tables per its `.LST`; the goal is to standardize the 578's channel list on this project and replace its programming
- [x] 2026-10-08: 578's 220 MHz channels also placed in ME Analog / NH Analog (repeaters), Simplex (1.25m Calling), the All Analog and Simplex scan lists, besides the `220` zone and ME ARES; the 878 build drops them, `model.py parity` passes
