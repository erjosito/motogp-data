# MotoGP Race Results Downloader

Downloads comprehensive MotoGP weekend data — **all sessions, lap-by-lap times, and sector splits** — from the official public API and timing PDFs, and exports everything to a formatted Excel workbook.

## New-engine dashboard preview

[Classic dashboard](https://motogp-data.com/) ·
[New-engine preview](https://motogp-data---preview.bluehill-35b09ccb.swedencentral.azurecontainerapps.io/)

The React/TypeScript + FastAPI preview runs alongside the classic Streamlit app,
using the same read-only, managed-identity Azure SQL connection. Its four views
cover the premier-class championship, session results, rider lap comparisons,
and sector analysis. The championship highlights Marc Marquez's recovery from
the verified 102-point deficit, including every imported Sprint and Grand Prix.

The preview supports dark/light themes and shareable season/event/session URLs.
It is English-only; Classic retains the full analysis suite and EN/ES/IT support.
Coverage is reported from imported results, not assumed complete. Scoring
weekends and GP race results are counted separately: a cancelled GP can still
have a completed Sprint. Restarted race classifications remain on the timeline,
but sessions awarding no points do not add a phantom GP win or countback finish.
Lap-only sessions remain available even when the
official classification is empty. Historical comparisons are not called
"all-time" until the database genuinely covers the earlier premier-class era.
Seasons with only missing or placeholder-zero race points do not produce invented
zero-point standings; official historical championship records need a separate
read contract, including historic dropped-score and half-point rules.

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

Open `http://127.0.0.1:8502`. For frontend hot reload, run `npm run dev` from
`preview-web` in another terminal; Vite proxies `/api` to port 8502.

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

The script prints the label URL after checking revision health and the unchanged
production traffic allocation. A prebuilt image can be deployed with
`.\scripts\deploy-preview.ps1 -Tag <existing-tag> -SkipBuild`.
The existing `redeploy-app.ps1` now moves the `classic` label and named production
traffic together when releasing future Streamlit updates, preserving preview
isolation. Do not reset ingress to `latest=100` or switch back to single revision
mode while both engines are in use. Multiple active revisions can incur
additional compute charges.

For rollback, move the `preview` label back to a known-good **passwordless**
preview revision; main-domain traffic does not need to change. To remove the
preview, remove its label and deactivate its revision without touching the
production classic revision. Never roll back to an old password-based image.

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

The shared light theme is configured in `.streamlit/config.toml` and included
in the Docker image. Database schema, ingestion, and analysis calculations are
unchanged. Both championship views share the same Race + Sprint points
calculation. Both views show tied points as shared positions, without
claiming to apply official championship countback rules.

Dashboard interaction tests use sample data and never connect to Azure SQL:

```powershell
python -m unittest test_dashboard test_motogp_results
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
