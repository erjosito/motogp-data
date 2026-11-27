# MotoGP Race Results Downloader

Downloads comprehensive MotoGP weekend data — **all sessions, lap-by-lap times, and sector splits** — from the official public API and timing PDFs, and exports everything to a formatted Excel workbook.

## New-engine dashboard preview

[Classic dashboard](https://motogp-data.com/) ·
[Paddock — new engine](https://motogp-data.com/paddock/) ·
[Preview revision](https://motogp-data---preview.bluehill-35b09ccb.swedencentral.azurecontainerapps.io/)

The React/TypeScript + FastAPI preview runs alongside the classic Streamlit app,
using the same read-only, managed-identity Azure SQL connection. Its four views
cover the premier-class championship, session results, rider lap comparisons,
and sector analysis. Every season has an evidence-backed story: dominance,
consistency, narrow margins or a turnaround, with the actual supporting metric.
The 2026 championship highlights Marc Marquez's recovery from the verified
102-point deficit, including every imported Sprint and Grand Prix. His 2025
story combines the recorded dominance with a clearly attributed MotoGP article
for the injury-recovery context; injury history is not inferred from race data.
Stories are generated deterministically from stored results, with no AI API calls.

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
or new-versus-used tyre flags. The UI explicitly warns that raw timing comparisons
may include cancelled times; it does not claim official valid-lap rankings or
infer tyre age. These limitations require a separate importer/schema enhancement.

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
350cc, 50cc and 80cc championships. Premier remains the default. Source labels are
preserved; predicates ignore the trademark suffix, surrounding spaces and case.
These were independent world championships, not a universal feeder ladder.
Points and standings must never be summed across categories.

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

**Coverage is not completeness.** The API sometimes labels a historical race
`FINISHED` but returns an empty classification. Those sessions remain empty:
no winner, zero score, or lap timing is invented. Some weekends do not list
the selected class at all; the snapshot records that source limitation without
asserting that its race never took place. Zero placeholders for unavailable historical
race points, lap counts and top speeds become SQL `NULL`. Official final
standings are stored separately and must not be derived by summing those gaps.
The pilots, for example, provide Agostini's official 36 points in 1966 and
84 in 1975, but only part of each season's race classifications.

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

The expanded six-class external audit stages 16,941 candidates: 5,892 accepted,
42 corroborated without augmentation and 11,007 held. Unmatched lower-class rows
can be reconsidered only after their official identities/races are imported and
the same corroboration checks pass.

Lower-class expansion is staged. The first milestone includes **51 verified
season/class archives**: 40 in 250cc, six in 125cc, historical 50/350/80cc pilots,
and 2026 Moto2/Moto3 through Portugal. All advertised 2026 race PDFs were
field-verified: **9,097 Moto2 laps across 22 race parts** and **8,053 Moto3 laps
across 21 race parts**. Eight laps have unavailable sector cells; elapsed times
are preserved but ambiguous collapsed sector values are not guessed.
Practice/qualifying timing backfill is a separate stage.

The broader uncached expansion encountered an official API rate limit and must
resume after cooldown. The complete premier archive is preserved. Lower-class
coverage is not yet a claim of complete careers or all 13 Nieto/15 Agostini titles.

```powershell
python -m unittest test_import_historical test_load_to_sql test_dashboard
```

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
