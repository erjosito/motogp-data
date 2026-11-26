# MotoGP Race Results Downloader

Downloads comprehensive MotoGP weekend data — **all sessions, lap-by-lap times, and sector splits** — from the official public API and timing PDFs, and exports everything to a formatted Excel workbook.

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

## License

MIT
