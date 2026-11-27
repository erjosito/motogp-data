# MotoGP Race Results Downloader

Downloads comprehensive MotoGP weekend data — **all sessions, lap-by-lap times, and sector splits** — from the official public API and timing PDFs, and exports everything to a formatted Excel workbook.

## New-engine dashboard preview

[Classic dashboard](https://motogp-data.com/) ·
[Paddock — new engine](https://motogp-data.com/paddock/) ·
[Preview revision](https://motogp-data---preview.bluehill-35b09ccb.swedencentral.azurecontainerapps.io/)

The React/TypeScript + FastAPI preview runs alongside the classic Streamlit app,
using the same read-only, managed-identity Azure SQL connection. Paddock now opens
on **Marc Marquez's rider profile**, with a searchable page for every rider in
the recorded championship/race archive. Each profile features official final
titles, recorded GP wins and podiums, separately counted Sprint wins, signature
venues and at least two charts. Marc also has a dedicated verified comeback
chapter. Career counts describe the stored archive, not certified complete
career totals; final titles never include standings to date. Profiles lead with
race achievements instead of a numeric title hero when official rank coverage
does not span their recorded seasons. Modern race counts
exclude non-scoring restarts; historical classification evidence may lack points.
Standings-only riders receive official-rank charts instead of invented race counts.
Share a profile with `?view=riders&rider=<rider_id>`; theme parameters persist.
The Classic domain root is unchanged.
Classic's sidebar includes an **Open Paddock App** link with an external-link
icon; it opens the new app in a separate tab without replacing the current analysis.
Paddock's always-visible **Data analysis** shortcut opens Classic in a new tab.

Career profiles use a reusable visual identity card: individually reviewed
biography facts where collected, a licensed, season-labeled portrait where
approved, and initials/plain numbers otherwise. Portrait credits, license links
and adaptation notices stay next to the image. Unapproved official image
references and the full local biography catalog are not shipped.

The other views cover category-scoped championships, session results, rider lap
comparisons, and sector analysis. Explicit season/event/session deep links retain
their destination rather than being redirected to the new entry page.
Session pages also show a compact circuit outline when the sourced catalog
recognizes the venue. These are explicitly **2026 reference layouts**, not
reconstructions of historical tracks or sector maps; facts and OpenStreetMap
attribution remain linked. Uncollected venues retain normal analysis without
invented geometry.
Race and Sprint results lead with recorded podium positions and a directly
labeled **elapsed-time difference to P1 (s)** graphic. The comparison uses
validated positive elapsed durations for same-lap classified finishers with a
unique P1, never parsed lap/penalty gap text or a recalculated race order.
Conflicting source gap labels, non-finishers and missing timings remain
explicitly unscaled. These are elapsed-time differences, not official adjusted
winning margins; original times, gaps, statuses and source labels stay accessible.
Practice and qualifying use session-classification language without race podiums.

On mobile, championship headlines stay with the main graphic and recovery
bridges precede standings. Long classifications, standings, career records and
comparison controls have explicit Show/Hide disclosures (open initially on
desktop). Collapsing them does not unmount searches or filter selections.
Source/timing qualifications outside advanced controls stay visible. Narrow
charts reduce axis-label density without removing data; hover/tap retains full
labels.

Every season has an evidence-backed story: dominance,
consistency, narrow margins or a turnaround, with the actual supporting metric.
The 2026 championship highlights Marc Marquez's recovery from the verified
102-point deficit, including every imported Sprint and Grand Prix. His 2025
story combines the recorded dominance with a clearly attributed MotoGP article
for the injury-recovery context; injury history is not inferred from race data.
Stories are generated deterministically from stored results, with no AI API calls.

Every available season/category overview includes two evidence-backed charts.
Layouts adapt to the story rather than using a separate bespoke template for
each season: comeback curves and floating-bar recovery bridges, decisive-session
bars, wins-versus-points scatter plots and stacked podiums, victory doughnuts,
or close-finish rank comparisons and gap lollipops. Snapshot-only seasons use
official-score bars and classified-point shares without inventing a timeline.
Missing standings instead show actual stored-record and session coverage counts.
Win shares use recorded wins as their denominator; point shares describe the
classified standings table, not all points awarded in races. All profiles retain
the underlying standings, source caveats and responsive light/dark styling.

The preview supports dark/light themes and shareable season/event/session URLs.
It is English-only; Classic retains the full analysis suite and EN/ES/IT support.
Coverage is reported from imported results, not assumed complete. Scoring
weekends and GP race results are counted separately: a cancelled GP can still
have a completed Sprint. Restarted race classifications remain on the timeline,
but sessions awarding no points do not add a phantom GP win or countback finish.
Lap-only sessions remain available even when the
official classification is empty. Historical comparisons are not called
"all-time" until the database genuinely covers the earlier premier-class era.
For 1949–1989, official final `championship_standings` preserve stored ranks and
decimal points, including dropped-score and half-point rules. Partial historical
race classifications are not used to reconstruct title progression, GP-win totals
or podium totals. A tied points total does not override the official rank.
Missing usable standings produce an honest incomplete-story state, not invented
zero-point leaders. Newer seasons are explicitly described as imported results;
the app does not certify their completeness or any unrecorded points adjustments.

The database does not currently preserve PDF lap/sector cancellation annotations
or new-versus-used tyre flags. Raw timing comparisons may include cancelled
times; they do not certify official valid-lap rankings or infer tyre age.
These limitations require a separate importer/schema enhancement.

### Run the preview locally

Requires Node.js 22.12+ and the existing ODBC Driver 18 / Azure CLI SQL setup
described below. SQL credentials are never included in the frontend.

```powershell
python -m pip install -r requirements-dev.txt
az login
Set-Location .\preview-web
npm ci
npm run build
Set-Location ..
python -m uvicorn preview_api:app --host 127.0.0.1 --port 8502
```

Open `http://127.0.0.1:8502/paddock/` (the revision-root URL also works). For
frontend hot reload, run `npm run dev` from `preview-web` in another terminal;
Vite proxies both `/api` and `/paddock/api` to port 8502.

```powershell
python -m unittest test_preview_api test_sql_connection test_motogp_results
Set-Location .\preview-web
npm test
npm run lint
npm run build
```

### Deploy side by side in the same Container App

Run `.\scripts\deploy-preview.ps1` from the repository root. It builds
`Dockerfile.preview` in the existing ACR, enables multiple revisions, pins 100%
of main-domain traffic to the existing classic revision **before** creating the
preview revision, and assigns the stable `classic` and `preview` labels. It
refuses an ambiguous production traffic split. Both engines use ingress port
8501; the revision label chooses the engine, not a query parameter or header.
No new app, database, registry, or environment is created.

### Route the custom domain by URL

`infra/paddock-route.json` uses the existing environment's native HTTP routing:
the path-segment prefix `/paddock` targets the `preview` label, and all other
paths target `classic`. `/paddock-other` does not match Paddock. No path rewrite
is required: React assets, navigation and API requests work under `/paddock/`,
and `/paddock` redirects there while preserving the query string.

After deploying and verifying the prefixed preview, run:

```powershell
.\scripts\deploy-paddock-routing.ps1
# Inspect the printed route-host URL before the hostname cutover:
.\scripts\deploy-paddock-routing.ps1 -BindDomains
```

The first command validates the route host without changing custom-domain
bindings. The second snapshots the two existing app hostname/certificate
bindings in ignored `.azure\paddock-domain-bindings.json`, removes those bindings
from the app, and binds the same certificates to the route. It checks Classic,
React and a SQL-backed story on both domains, and restores the original app
bindings if cutover fails. Certificates are never deleted or reissued.
Keep the snapshot for rollback; the script refuses to overwrite it.

TLS bindings select a hostname, not a URL path. These are environment-scoped
certificates, so the route can reuse them. The existing default Consumption
ingress is used: no Front Door, Application Gateway or premium ingress is added.
Build/storage usage and traffic-driven compute, requests, bandwidth and logs
can still affect the bill; this is not a guarantee of zero incremental cost.

`infra/main.bicep` validates the same route rules. Its `customDomains` parameter
is deliberately required: supply `[]` only before hostname migration, or the
actual existing bindings afterward. Never apply an empty domain list to an
already-bound route. The deployment script preserves the live bindings.

The script prints the label URL after checking revision health and the unchanged
production traffic allocation. A prebuilt image can be deployed with
`.\scripts\deploy-preview.ps1 -Tag <existing-tag> -SkipBuild`.
The existing `redeploy-app.ps1` now moves the `classic` label and named production
traffic together when releasing future Streamlit updates, preserving preview
isolation. Do not reset ingress to `latest=100` or switch back to single revision
mode while both engines are in use. Multiple active revisions can incur
additional compute charges.

For a preview-image rollback, move the `preview` label back to a known-good
**passwordless, `/paddock`-compatible** revision; main-domain traffic does not
need to change. Before removing Paddock entirely, remove its route rule and
restore root routing/custom-domain bindings as appropriate, then remove its label
and deactivate its revision without touching Classic. Never roll back to an old
password-based image or leave a live route targeting a removed label.

## Data Sources

| Source | URL | Purpose |
|--------|-----|---------|
| **MotoGP PulseLive API** | `api.motogp.pulselive.com` | Session metadata, classifications |
| **MotoGP Resources** | `resources.motogp.com` | Official timing PDFs (lap & sector analysis) |

Both are free and **require no API key or authentication**.

## What You Get

A multi-sheet Excel workbook with **two sheets per session** (e.g., FP1 Results + FP1 Laps):

**Results sheets** — classification summary:
- Position, rider, team, bike, total laps, time, gap, best lap, top speed, points

**Laps sheets** — full lap-by-lap timing data:
- Every lap for every rider: lap time, T1, T2, T3, T4 sector splits, speed
- Tyre compounds (front/rear), pit stops, run/stint number
- Best lap per rider highlighted in bold purple

Rider timing blocks are preserved across PDF columns and pages. Pit and out
laps are included; speed cells are left blank when the source does not record it.

Sessions covered: **FP1, Practice, FP2, Q1, Q2, Sprint Race, Warm Up, Race**

## Setup on Windows

### Prerequisites

- **Python 3.10+** — Download from [python.org](https://www.python.org/downloads/) or install via `winget`:
  ```powershell
  winget install Python.Python.3.12
  ```
  > During installation, make sure to check **"Add Python to PATH"**.

### Install Dependencies

```powershell
pip install requests openpyxl pdfplumber
```

| Package | Purpose |
|---------|---------|
| `requests` | HTTP client for API calls and PDF downloads |
| `openpyxl` | Excel (.xlsx) file generation |
| `pdfplumber` | Parsing official timing PDFs for lap/sector data |

### Verify Installation

```powershell
python --version          # Should show 3.10 or higher
pip show requests openpyxl pdfplumber
```

## Usage

### Basic — Get the Full Latest MotoGP Weekend

```powershell
python Get-MotoGPResults.py
```

This downloads data for **all sessions** (FP1 through Race) of the most recent finished MotoGP Grand Prix.
The downloader verifies that the selected category's main race is finished;
events marked finished by the API without a completed race are skipped.

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `--year YYYY` | Season year | Current season |
| `--category NAME` | `MotoGP`, `Moto2`, or `Moto3` | `MotoGP` |
| `--output FILE` / `-o FILE` | Custom output file path | Auto-generated |

### Examples

```powershell
# Full weekend data for the latest MotoGP race (default)
python Get-MotoGPResults.py

# Latest Moto2 weekend
python Get-MotoGPResults.py --category Moto2

# A specific past season
python Get-MotoGPResults.py --year 2025

# Custom output file name
python Get-MotoGPResults.py --output "C:\Users\me\Desktop\austin_full.xlsx"
```

### Output

The script shows progress as it processes each session:

```
MotoGP Full Weekend Data Downloader
Sources: api.motogp.pulselive.com + resources.motogp.com (free, no API key)

Finding season (current)...
   Season 2026
Finding latest race event...
   Red Bull Grand Prix of The United States (2026-03-29)
   Circuit Of The Americas, Austin
   Category: MotoGP™
Fetching all sessions...
   8 finished sessions found
        FP1  Free Practice 1           2026-03-27T10:45
         PR  Practice                  2026-03-27T15:00
        FP2  Free Practice 2           2026-03-28T10:10
         Q1  Qualifying 1              2026-03-28T10:50
         Q2  Qualifying 2              2026-03-28T11:15
        SPR  Sprint Race               2026-03-28T15:00
        WUP  Warm Up                   2026-03-29T10:40
        RAC  Race                      2026-03-29T15:00

--- Race (RAC) ---
   Downloading classification...
   21 riders classified
   Downloading analysis PDF...
   Parsing lap-by-lap data (233,433 bytes)...
   20 riders, 322 lap entries extracted

Saved to: MotoGP_2026_USA_motogp_full.xlsx
   16 sheets | 1266 total lap entries
```

The auto-generated file name follows the pattern: `MotoGP_{year}_{event}_{category}_full.xlsx`

### Excel Sheets Structure

| Sheet | Contents |
|-------|----------|
| `FP1 Results` | Free Practice 1 classification |
| `FP1 Laps` | FP1 lap-by-lap times + T1/T2/T3/T4 sectors |
| `PR Results` | Practice classification |
| `PR Laps` | Practice lap-by-lap times + sectors |
| `FP2 Results` | Free Practice 2 classification |
| `FP2 Laps` | FP2 lap-by-lap times + sectors |
| `Q1 Results` | Qualifying 1 classification |
| `Q1 Laps` | Q1 lap-by-lap times + sectors |
| `Q2 Results` | Qualifying 2 classification |
| `Q2 Laps` | Q2 lap-by-lap times + sectors |
| `SPR Results` | Sprint Race classification (with points) |
| `SPR Laps` | Sprint Race lap-by-lap times + sectors |
| `WUP Results` | Warm Up classification |
| `WUP Laps` | Warm Up lap-by-lap times + sectors |
| `RAC Results` | Main Race classification (with points) |
| `RAC Laps` | Main Race lap-by-lap times + sectors |

## Web Dashboard

The Streamlit dashboard reads imported results from Azure SQL; it does not read
the generated Excel workbooks. Use `load_to_sql.py` to update the database.
If a session's API classification is empty, the loader resolves PDF lap riders
from classifications in other sessions of the same GP and category. It reports
this source gap and does not fabricate classification results.
Events without any finished sessions in the requested category are not inserted,
even if the API incorrectly labels the event finished. A GP can have a completed
Sprint but a cancelled main race, so GP coverage and main-race counts can differ.

```powershell
pip install -r requirements.txt
az login
# The signed-in Entra account must have database access; see authentication below.
streamlit run dashboard.py
```

Navigation groups all existing analyses into **Overview**, **Race Centre**,
**Riders**, **Season**, and **History**. Overview opens with the latest loaded
season's MotoGP World Championship: leading riders, points gaps, standings,
and title-race progression, with a link to the detailed championship analysis.
The GP and date of the latest imported result are shown explicitly; missing GPs
can affect standings. **Data coverage** retains the historical
database statistics and coverage charts. Navigation and filters are preserved
when switching between English, Spanish, and Italian.

The default light theme is configured in `.streamlit/config.toml` and included
in the Docker image. Switch light/dark appearance through Streamlit's top-right
**menu > Light / Dark**; localized sidebar guidance points to this control.
The native control themes widgets, tables, charts, and custom cards without a
server restart, preserving filters and language. The preference is browser-local,
not a process-global setting. Custom light/dark variants require Streamlit 1.51
or newer, as specified in `requirements.txt`. Streamlit has no supported Python theme setter,
so the dashboard uses its native control rather than a simulated sidebar toggle.
Plotly uses Streamlit's theme-aware template, including animation axes and labels;
explicit podium and in-bar label color pairs retain their readable contrast.
The visual refresh retains the database schema and existing
analytical views. Both championship views share the same Race + Sprint points
calculation. Both views show tied points as shared positions, without
claiming to apply official championship countback rules.
For imported seasons before 1990, both championship views instead use the
official final positions and decimal points, preserving the period's counting
rules. They do not reconstruct a cumulative progression from missing race points.

Dashboard interaction tests use sample data and never connect to Azure SQL:

The first two coverage charts include localized explanations below each chart.
GP counts describe imported weekends, not a complete historical calendar.
Lap/sector counts describe imported timing records and source availability,
not laps actually raced; the sector indicator records T1 availability, not
necessarily a complete four-sector lap.

Sector Heatmap requires all four sectors before showing an ideal lap or its
gap to the best lap. Missing sectors leave those values unavailable.

Race/Sprint cumulative gaps use unfiltered lap timing, including slow and pit
laps. Missing or invalid timing invalidates subsequent elapsed totals; gaps
are shown only where every selected rider has complete timing. Position Battle
is a reconstruction, not official live timing: each lap requires complete times
for every rider whose classification reports reaching that lap. Missing data is
not replaced with final finishing positions, and Q2 is not treated as a grid.

Category selection uses the shared allowlist in `category_scope.py`: premier
(MotoGP/500cc), intermediate (Moto2/250cc), lightweight (Moto3/125cc), and separate
350cc, 50cc and 80cc championships. Source labels are
preserved; predicates ignore the trademark suffix, surrounding spaces and case.
These were independent world championships, not a universal feeder ladder.
Points and standings must never be summed across categories.

Classic filters belong to the active task and are remembered independently:
race analysis selects season, GP, available category, then session; championship
views require a season and a single category, defaulting to premier class.
**Riders > Pilot Profile** starts with every imported category and season for
the selected rider, regardless of the category used on another page. Narrow the
career using its category multiselect and **Season > All** or a particular year.
Points and season statistics remain separated by actual class, including riders
who contested several classes during the same year. Head-to-head comparisons
match the same session, not unrelated classes at the same GP.
Coverage, circuit history and cross-year views allow several category families
for a labeled comparison of imported race/session coverage. The detailed
analytics underneath are for the selected **Detailed analysis category**;
they never silently pool championships or point totals. Empty selections show
an explicit prompt. Navigation and language changes retain each task's filters.

**History > Circuits** matches physical circuit names and verified aliases,
not reused GP short codes. Track facts do not change with the racing class;
the winner, timing and points analyses below remain class-scoped. The bundled
`circuit_catalog.json` contains sourced modern-layout length and corner counts
for Jerez, Le Mans (Bugatti), Assen, Mugello, Phillip Island and Valencia,
verified on 2026-11-27 against the active track entries in the
[official MotoGP event API](https://api.pulselive.motogp.com/motogp/v1/events?seasonYear=2026).
Official circuit/track IDs preserve the factual snapshot's provenance.
Modern diagrams and distances must not be interpreted as the layout used
in every historical season.

Attendance means an explicitly reported MotoGP record, with year, weekend or
race-day scope and source. The initial verified record is Le Mans:
[311,797 over the 2025 GP weekend](https://www.motorsport.com/motogp/news/french-gp-breaks-moto-gp-attendance-record-in-2025/10721868/).
Capacity, ordinary attendance and unverified or disputed historical estimates
are not substituted. Missing facts, records and reusable geometry are shown
explicitly; this is a curated snapshot, not a live all-time ranking.

Diagrams are original Plotly renderings of mapped raceway coordinates, with
local longitude/latitude projection and equal axis scales. Geometry is
[OpenStreetMap contributors' data](https://www.openstreetmap.org/copyright),
not copied MotoGP artwork. The bundled circuit database is available under
[ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/); each outline records
its OSM source identifiers and retrieval date. Attribution and source links
appear beneath the diagram. No runtime map API or external artwork request
is required.

Pilot Rhythm and Sector Heatmap compare absolute times within one selected
session, not across unrelated circuits or conditions. Pace cleaning excludes
pit laps, non-finite/non-positive times, and laps at least 15% slower than their
own session's median. Lap loaders preserve stable session/event IDs and context;
combining sessions no longer changes their outlier baselines. Speed Trap keeps
its all-session/event/season aggregation.

```powershell
python -m unittest test_dashboard test_motogp_results
```

## Official Grand Prix Archive

### Archive analytics contracts

The expanded-history views are available in Classic:

- **Riders → Pilot Profile** starts with a class-lane career timeline. Circles
  combine recorded race participation with independently stored official final
  standings; stars indicate official world titles. Standings-only seasons are
  retained, and linked sources remain available. Race-result detail selects one
  season rather than overlaying every career season.
- **History → Cross-Year → Champions by year and class** shows official final
  rank-one records only, with an adjustable era, actual classes, joint winners,
  source links and a years-as-rows option for narrow screens.
  Empty cells mean no stored official champion, not that no
  championship took place; provisional standings never establish titles.
- **History → Cross-Year → Constructor eras** shows imported race-winner shares
  by actual class and decade. Unknown constructors remain in the denominator,
  and grouping smaller constructors preserves every recorded victory. These
  shares are not official constructor titles or guaranteed full-calendar totals.
- **Overview → Data coverage → Data Quality & Coverage** contains the archive
  availability heatmap only. Select standings, race classifications, laps or
  complete four-sector rows. Independent source aggregates prevent join
  multiplication; finished imported sessions seed otherwise empty cells and
  missing calendar years stay visible. Standings include final/current rows;
  timing counts cover all finished session types. Availability is not completeness.

Historical constructors come from the classification when available, falling
back to the team record, never the other way round. Unknown teams do not remove
known historical constructors from the charts.

Points efficiency is a **nominal recorded-entry metric**, not championship
efficiency over the scheduled calendar. It uses 25 per recorded race entry
from 1993 and 12 per recorded Sprint entry from 2023, including recorded DNS
entries. Earlier scoring systems, missing scores and totals outside these
bounds remain unavailable rather than becoming zero. Shortened-race maxima
are not inferred. Official full-season points are never divided by partial
imported start counts. Only official final rank-one standings establish titles.
See the [scoring-system history](https://www.boxrepsol.com/en/motogp-en/motogp-scoring-system-history-and-evolution/).

Grid analytics use an explicitly labeled **qualifying-order proxy**, not an
official starting grid: Q2 followed by non-promoted Q1 riders. Supported
two-stage formats are MotoGP from 2013 (12 in Q2, two promoted) and Moto2/Moto3
from 2019 (18 in Q2, four promoted). Both complete stages and a matching order
for every recorded starter are required. DNS entries are excluded; DNF and
unclassified starters remain in finish-conversion denominators. Position gains
use classified finishes only. Grid penalties, older formats and incomplete
orders are not guessed. See the [2013 format](https://www.crash.net/motogp/news/189421/1/motogps-2013-qualifying-format-explained)
and [official 2019 qualifying archive](https://www.motogp.com/en/videopass/archive/season-2019/malaysia).
Pole statistics count recorded Q2 winners only within these supported formats;
missing qualifying records are unavailable, not zero historical career poles.

Circuit pace uses the race winner's recorded non-pit laps and classification
best lap, keyed to physical circuit names/curated aliases rather than GP short
codes. Separate observations do not imply unchanged layouts or conditions.
Cancellation flags are not yet stored, so these are recorded times, not
certified valid-lap rankings. This diagnostic is presented only on the data
quality dashboard; analytical charts retain ordinary methodology captions.

### Importing the archive

`import_historical.py` imports official race classifications and independent
standings in bounded season/class transactions, separately from full-weekend
practice/qualifying ingestion. It supports 500cc (1949–2001), MotoGP (2002–),
250cc (1949–2009), Moto2 (2010–), 125cc (1949–2011), Moto3 (2012–), 350cc
(1949–1982), 50cc (1962–1983) and 80cc (1984–1989).
Install `requirements.txt` and sign
in with an Entra account authorized to write to the database.

```powershell
# Phase 1: fetch and validate the pilot, without writing to SQL
python import_historical.py --years 1966,1975

# Explicit additive migration, followed by atomic per-season imports
python import_historical.py --years 1966,1975 --apply --migrate

# Expand only after verifying the pilot
python import_historical.py --years 1976-1989 --apply
python import_historical.py --years 1960-1974 --apply
python import_historical.py --years 1949-1959 --apply

# Lower-class pilots and modern race/PDF imports
python import_historical.py --years 1969 --category 50cc --apply
python import_historical.py --years 1969 --category 350cc --apply
python import_historical.py --years 1984 --category 80cc --apply
python import_historical.py --years 2026 --category Moto2 --apply --include-laps
python import_historical.py --years 2026 --category Moto3 --apply --include-laps
```

Apply the checked-in migration before running the updated normal SQL loader
or dashboard against an existing database; migrations add classification
constructors, session-specific rider numbers, archive/provenance tables and the
effective classification view. They do
not rewrite existing timings, classifications, or laps. Azure SQL authentication
remains passwordless; the deployed app needs only its existing read permissions.

The importer preserves:

- Available race classifications and constructors even when no team is recorded.
- **Official final championship standings** in `championship_standings`,
  including fractional points and source-provided ranking, rather than applying
  today's scoring rules to historical results.
- Current-season standings remain explicitly non-final. Where the official API
  supplies race results but no standings, a source-gap marker is retained and
  no official final ranking is invented.
- A JSON source snapshot, SHA-256 fingerprint and verified row counts in
  `historical_imports`. Original existing rider profiles are not overwritten.
- Existing shared weekend metadata is reused unchanged when adding another
  class. Reusing an event ID for a different season stops the transaction.

**Coverage is not completeness.** The API sometimes labels a historical race
`FINISHED` but returns an empty classification. Those sessions remain empty:
no winner, zero score, or lap timing is invented. Some weekends do not list
the selected class at all; the snapshot records that source limitation without
asserting that its race never took place. Zero placeholders for unavailable historical
race points, lap counts and top speeds become SQL `NULL`. Official final
standings are stored separately and must not be derived by summing those gaps.
Later 125cc/250cc race tables that contain a winner but no nonzero score also
have unavailable points, not zero-point wins. Their raw snapshots stay unchanged;
cached reruns upgrade only zero placeholders within the verified transaction.
Scored race tables retain genuine zero scores, including unawarded modern
Moto2/Moto3 race parts.
The pilots, for example, provide Agostini's official 36 points in 1966 and
84 in 1975, but only part of each season's race classifications.

Source fidelity does not guarantee that every supplied point total is reliable.
Data-quality warnings appear only in Classic **Home > Data coverage**, under
**Data Quality & Coverage**, not on analytical pages in either app.
This section lists unsupported source categories and category-scoped official
final score anomalies, including the affected seasons, raw ranks/scores and sources.
Analytical views have no diagnostic banners or verification-required labels.
Historical counted/gross scoring or source discrepancies may explain a mismatch;
the original ranks and raw scores are preserved for verification, while derived
gaps, title margins and point-progression claims are withheld. For example, the
1970 350cc API supplies 9/28/46 points for its first three ranked riders. These
values are not silently corrected or replaced with reconstructed race totals.
Paddock retains its safe source-score/rank chart pair; inconsistency flags remain
in the API for diagnostics. Missing-data prompts, operational errors, source
attribution and ordinary chart methodology remain visible.

Source snapshots are cached in ignored `historical_cache\`. Cached reruns verify
the stored rows without duplicating them; `--refresh` refetches official data.
Each season commits only after comparison with its source. If verification fails,
that season rolls back and the command stops; earlier committed seasons remain.
Unexpected existing rows are not silently deleted to force a match.
Successful HTTP responses are also cached for interrupted fetches. Uncached
requests are spaced two seconds apart. HTTP 429 stops the import without caching
an error as empty data; honor `Retry-After` when supplied and allow a cooldown
before resuming. Do not bypass source access restrictions or run parallel
uncached archive fetches.

### Audited external supplementation

`import_external.py` pins the public Kaggle dataset to a reviewed SHA-256 and
records its publisher-declared CC0 license, URL, raw candidate facts and decision
reasons. Numeric dataset rider IDs are **not** official UUIDs. Matching requires a
unique official season/class/name and race identity; ambiguous identities,
negative status markers and conflicting positions/points remain held.

Accepted facts live in `external_classifications`, not the official base table.
`vw_effective_classifications` prefers official positions, timing and non-NULL
points. A corroborated external score can fill an official NULL score; provenance
is exposed as `official-api+external` or `external`. Official final championship
rankings remain independent and authoritative. Historical scoring tables are
used to corroborate candidate race scores, **not** to reconstruct final totals.
1949's fastest-lap bonus needs additional evidence.

The premier pilot stages 4,656 candidates: 3,072 accepted, 30 corroborated without
augmentation, and 1,554 held. Accepted facts include **two** independently
cross-checked 1966 Senior TT finishes (Hailwood/Agostini); that is a partial
recovery, not a complete TT classification or recovery of all 106 candidate races.
No external elapsed times, speed, tyre data, negative statuses or `0 Lap`
placeholders are imported as timing. Reference-only archives with unestablished
bulk reuse permissions are not scraped wholesale.

```powershell
python import_external.py                         # Audit only; no writes
python import_external.py --apply --rollback      # Real SQL rollback verification
python import_external.py --apply                 # Verified, repeat-safe facts
python import_external.py --categories 500cc,250cc,125cc,350cc,50cc,80cc --apply
```

After the official expansion, the six-class external audit stages **16,941
candidates: 11,258 accepted, 71 corroborated without augmentation and 5,612 held**.
All 5,892 previously accepted facts remain unchanged; 5,366 additional facts
passed the same identity, position and scoring checks. Repeated imports preserve
the accepted facts and candidate decisions. Most augmentation fills unavailable
race scores, not missing race classifications.

Following the 51-archive pilot, **218 lower-class season/class archives** have
been imported and compared with their official source snapshots. Together with
the 41 historical premier seasons, this is 259 verified archive snapshots.
Lower-class coverage comprises 2,493 race sessions, 42,486 official classification
rows and 6,268 championship-standing rows; 2026 standings remain non-final.

| Class | Seasons | Archives | Race sessions | Classification rows | Standing rows |
|-------|---------|----------|---------------|---------------------|---------------|
| 250cc | 1949–2009 | 61 | 683 | 10,406 | 1,722 |
| Moto2 | 2010–2026 | 17 | 321 | 9,957 | 668 |
| 125cc | 1949–2011 | 63 | 708 | 10,198 | 1,608 |
| Moto3 | 2012–2026 | 15 | 282 | 8,402 | 590 |
| 350cc | 1949–1982 | 34 | 281 | 1,587 | 937 |
| 50cc | 1962–1983 | 22 | 171 | 1,147 | 581 |
| 80cc | 1984–1989 | 6 | 47 | 789 | 162 |

All advertised 2026 race PDFs were
field-verified: **9,097 Moto2 laps across 22 race parts** and **8,053 Moto3 laps
across 21 race parts**. Eight laps have unavailable sector cells; elapsed times
are preserved but ambiguous collapsed sector values are not guessed.
Practice/qualifying timing backfill is a separate stage.

Successful responses were cached and uncached requests paced after respecting
the official API cooldown. Original premier classifications, sessions, laps,
profiles, final standings and shared event metadata remain preserved.
There are still **450 finished historical sessions without official
classifications**, **19 season/class tables without official final standings**
and **18 non-monotonic official point tables** requiring the source warning.
These are source gaps, not evidence that the races or titles never happened.
All seven Agostini 350cc title rankings are now
represented alongside his eight 500cc titles, but this does not validate every
supplied point total. Nieto's six 50cc and four 125cc title rankings are available;
the official API has no final standings for his 1979, 1983 and 1984 125cc titles.
Those gaps are not filled by summing incomplete race results. Lower-class
coverage is not yet a claim of complete careers or an independently complete
championship archive.

```powershell
python -m unittest test_import_historical test_load_to_sql test_dashboard
```

## Portable data snapshot

### Standings-only premier backfill

`championship_standings` also includes independent official premier season tables
for **1990–2026**: 1,064 additional rows across 37 seasons. These were imported
without changing any original events, sessions, race classifications, laps,
teams, external facts or earlier standings/profiles. Two previously absent
official riders were added insert-only. Full-row preservation fingerprints and
an exact repeat-run comparison verified those invariants.

```powershell
# Fetch/cache and validate official season/category/calendar/document evidence only.
python import_standings.py --years 1990-2026
# Add the provenance table, then persist only independent standings and new riders.
python import_standings.py --years 1990-2026 --apply --migrate
# Explicit refresh; historical requests normally reuse the paced HTTP cache.
python import_standings.py --years 2026 --apply --refresh
python -m unittest test_import_standings test_export_data
```

`standings_imports` stores the complete payload, source URL/hash, calendar,
category identity, supplied PDF/XML links, row count and finality separately from
`historical_imports` (race archives). Original source labels/ranks/points remain
unchanged. Empty source tables are recorded as gaps, never reconstructed from
race totals. Unowned conflicting existing standings or unexpected stored riders
stop the transaction instead of being silently overwritten/deleted.

The importer verifies the document round against elapsed official calendar
events. PDF and XML references can disagree: for example, the 2000 API links an
earlier Valencia PDF and an Australian XML; several modern XML links lag their
PDF. Both are retained, and the latest verified round (race over sprint) is used
for as-of evidence, not as permission to alter the API's actual scores. A narrow
2001 XML `BRA` to API `RIO` event-code mapping is supported: the official XML
header explicitly names the Cinzano Rio GP.

**2026 is provisional.** The current calendar lists Valencia on November 29,
after Portugal on November 22. Past, non-current seasons with last-round
evidence are final; the current season remains conservatively non-final.
Marc's stored rank-one rows now include nine completed title-winning final
tables (2010/125cc, 2012/Moto2 and seven MotoGP seasons through 2025) plus
provisional 2026/MotoGP rank one. His separately confirmed tenth title must not
be denied or inferred merely by counting final tables. Follow-up work is tracked
for independent confirmed-title evidence and for remaining source gaps,
anomalous scores and lower-class timing coverage.

### Compressed snapshots

`python export_data.py --output exports\motogp-data-2026-11-27-standings.tar.xz` creates a
maximum-compression, consistent CSV snapshot of all application tables, including
source provenance, live schema/keys, a convenient flat results file, quality
metadata and verified checksums. `python export_data.py --verify <archive>`
validates it offline. See [the export guide](docs/data-export.md) for reproduction,
encoding, consumption and restoration instructions, and
[the rights notice](docs/data-rights.json) for source-specific licensing.
The combined dataset has **no blanket redistribution license**; archives remain
local and Git-ignored pending permission review.

The refreshed 2026-11-27 standings snapshot contains 14 base tables / 527,766
rows, plus 107,714 effective results in the convenience CSV, compressed to
**12,586,236 bytes (12.59 MB)**. Its versioned
[manifest](exports/motogp-data-2026-11-27-standings.manifest.json) records per-file
counts, hashes, source revision and encoding; the data archive itself is local
only. This includes 8,578 championship standings and 37 standings-only import
records. The [original manifest](exports/motogp-data-2026-11-27.manifest.json)
remains available for the earlier 13-table snapshot.

### Rider biographies and infographic assets

`python rider_profiles.py --season 2026` produces a separate local catalog of
official birth date/place, reported height and season/team-scoped media
references, joined only through explicit official profile/results UUID links.
It preserves missing data and holds conflicting identities rather than matching
names or reusing an old team's imagery for a current season.

See [rider profiles and media](docs/rider-profiles.md) for reproduction, the
additive enrichment API, field semantics, image design requirements and rights
limitations. Official photographs/number graphics are not automatically approved
for display. The reviewed references in `media_catalog.json` retain their own
source-specific permissions; no blanket license is asserted.

The shared reviewed biography catalog covers 21 champions selected at the
requested threshold: at least two 500cc/MotoGP titles, or five titles combined
across lower classes. All 21 have sourced birth dates/cities; unavailable
heights and other facts stay null. `build_champion_biographies.py` reproduces
the selection from a verified export without treating incomplete recorded
title counts as complete career totals. Photography permission remains separate.

## API Reference

The script uses these endpoints (all free, no auth required):

| Endpoint | Purpose |
|----------|---------|
| `GET /motogp/v1/results/seasons` | List available seasons |
| `GET /motogp/v1/results/events?seasonUuid=...&isFinished=true` | Finished events |
| `GET /motogp/v1/results/categories?eventUuid=...` | Categories (MotoGP/Moto2/Moto3) |
| `GET /motogp/v1/results/sessions?eventUuid=...&categoryUuid=...` | All sessions |
| `GET /motogp/v1/results/session/{id}/classification` | Session classification |

Base URL: `https://api.motogp.pulselive.com`

Lap-by-lap and sector data is parsed from official PDF timing sheets at `https://resources.motogp.com/files/results/{year}/{event}/{category}/{session}/Analysis.pdf`

## Web Dashboard and SQL Loader: Passwordless Authentication

The Streamlit dashboard (`dashboard.py`) and SQL loader (`load_to_sql.py`) use
Microsoft Entra access tokens, not SQL usernames or passwords. The Excel-only
downloader is unchanged.

Install the full app dependencies with `pip install -r requirements.txt`. The
dashboard and loader also require **ODBC Driver 18 for SQL Server** on the host;
the Docker image installs it.

| Variable | Default / purpose |
|----------|-------------------|
| `MOTOGP_SQL_SERVER` | `motogp-sql-srv.database.windows.net` |
| `MOTOGP_SQL_DATABASE` | `motogpdb` |
| `MOTOGP_SQL_AUTH` | `managed-identity` in ACA; `azure-cli` locally |
| `AZURE_CLIENT_ID` | Optional client ID of an attached user-assigned managed identity; omit for system-assigned identity |

`MOTOGP_SQL_CONN_STR` and the loader's `--conn-str` option are no longer supported.
Remove the old environment variable rather than moving its password elsewhere.
Every new connection, including reconnects after sleep or network interruption,
requests a valid token from Azure Identity.

### One-time Azure setup

1. Sign in using `az login`, select the existing app's subscription, and ensure the
   SQL logical server has a Microsoft Entra administrator configured. Creating
   database users must be done as that administrator or another authorized Entra
   principal, connected to **motogpdb**, not `master`.
2. Enable a system-assigned identity on the existing Container App:

   ```powershell
   az containerapp identity assign --name motogp-data --resource-group motogp --system-assigned
   ```

3. In `motogpdb`, create the app's Entra database user and give it **read-only**
   access. If the user already exists, skip `CREATE USER`.

   ```sql
   CREATE USER [motogp-data] FROM EXTERNAL PROVIDER;
   ALTER ROLE db_datareader ADD MEMBER [motogp-data];
   ```

   The name must resolve to the Container App's managed identity. If Entra
   contains duplicate display names, use the identity's `principalId` with
   `CREATE USER ... FROM EXTERNAL PROVIDER WITH OBJECT_ID = '<principalId>'`.
   If directory lookup fails, an Entra administrator must resolve the directory
   permissions before proceeding. Azure resource roles such as Contributor
   do **not** grant database access.
4. Grant a separate Entra user/group for local imports read/write access. Replace
   `motogp-importers` with your actual Entra group name:

   ```sql
   CREATE USER [motogp-importers] FROM EXTERNAL PROVIDER;
   ALTER ROLE db_datareader ADD MEMBER [motogp-importers];
   ALTER ROLE db_datawriter ADD MEMBER [motogp-importers];
   ```

   The loader updates existing tables; it does not need `db_owner` or DDL rights.
   Do not grant the dashboard identity write permissions.
5. Run `.\scripts\redeploy-app.ps1`. It checks that a system-assigned identity
   exists, builds the new image, selects managed-identity authentication, and
   removes the legacy connection-string environment variable. Existing network
   and firewall restrictions still apply.
6. Verify dashboard queries work through the deployed managed identity and local
   imports work with the authorized Entra identity. Then retire old revisions
   that contain the embedded credential and remove any unused SQL password
   secrets. **Rotate the previously committed SQL password**: removing it from
   current files does not remove it from Git history or old container images.
   Once all SQL clients have migrated, an administrator can enable
   **Microsoft Entra-only authentication** on the SQL server to disable SQL
   password logins entirely. This affects every database/client on that server,
   so check other consumers first.

The existing redeploy script expects a system-assigned identity. A user-assigned
identity is also supported by the Python connection helper, but requires attaching
that identity to ACA, granting it SQL access instead, and deploying with its
`AZURE_CLIENT_ID`.

### Local development and imports

Use your own authorized Entra identity, not the dashboard's managed identity:

```powershell
az login
streamlit run dashboard.py
python load_to_sql.py --year 2026
```

For a different server/database, set `MOTOGP_SQL_SERVER` and
`MOTOGP_SQL_DATABASE`. Token acquisition failures are reported explicitly; the
app never falls back to password authentication. Azure CLI credentials expire,
so run `az login` again if Entra requests a fresh sign-in.

## License

MIT
