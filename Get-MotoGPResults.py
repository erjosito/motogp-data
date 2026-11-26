#!/usr/bin/env python3
"""
Get-MotoGPResults.py

Downloads comprehensive MotoGP weekend data (all sessions, lap-by-lap times,
sector splits) from the free public PulseLive API and official PDF timing
sheets. Saves everything to a multi-sheet Excel workbook.

Usage:
    python Get-MotoGPResults.py                   # Latest GP, MotoGP class, all sessions
    python Get-MotoGPResults.py --year 2025       # Latest GP of 2025 season
    python Get-MotoGPResults.py --category Moto2  # Moto2 class
    python Get-MotoGPResults.py --output my.xlsx  # Custom output file

Data sources:
    - API:  https://api.motogp.pulselive.com (free, no API key)
    - PDFs: https://resources.motogp.com     (official timing sheets)
"""

import argparse
import io
import re
import sys
from pathlib import Path

import pdfplumber
import requests
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

BASE_URL = "https://api.motogp.pulselive.com/motogp/v1/results"

# Session types in weekend order
SESSION_ORDER = ["FP", "PR", "Q", "SPR", "WUP", "RAC"]
SESSION_LABELS = {
    "FP": "Free Practice",
    "PR": "Practice",
    "Q": "Qualifying",
    "SPR": "Sprint Race",
    "WUP": "Warm Up",
    "RAC": "Race",
}

# Excel styles (created once, reused)
HEADER_FONT = Font(name="Calibri", bold=True, color="FFFFFF", size=10)
HEADER_FILL = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")
TITLE_FONT = Font(name="Calibri", bold=True, size=13, color="C00000")
SUBTITLE_FONT = Font(name="Calibri", size=10, color="555555")
RIDER_FONT = Font(name="Calibri", bold=True, size=10)
THIN_BORDER = Border(
    left=Side(style="thin", color="CCCCCC"),
    right=Side(style="thin", color="CCCCCC"),
    top=Side(style="thin", color="CCCCCC"),
    bottom=Side(style="thin", color="CCCCCC"),
)
PODIUM_FILLS = {
    1: PatternFill(start_color="FFF4CC", end_color="FFF4CC", fill_type="solid"),
    2: PatternFill(start_color="E8E8E8", end_color="E8E8E8", fill_type="solid"),
    3: PatternFill(start_color="F5DEB3", end_color="F5DEB3", fill_type="solid"),
}
BEST_LAP_FONT = Font(name="Calibri", bold=True, color="7B2D8B", size=10)


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def api_get(endpoint: str, params: dict | None = None) -> list | dict:
    url = f"{BASE_URL}/{endpoint}"
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_season_id(year: int | None) -> tuple[str, int]:
    seasons = api_get("seasons")
    if year:
        for s in seasons:
            if s["year"] == year:
                return s["id"], s["year"]
        raise SystemExit(f"Season {year} not found. Available: {[s['year'] for s in seasons[:10]]}")
    current = next((s for s in seasons if s.get("current")), seasons[0])
    return current["id"], current["year"]


def get_latest_race_event(season_id: str) -> dict:
    events = api_get("events", {"seasonUuid": season_id, "isFinished": "true"})
    race_events = [e for e in events if not e.get("test", False)]
    if not race_events:
        raise SystemExit("No finished race events found for this season.")
    race_events.sort(key=lambda e: e["date_end"], reverse=True)
    return race_events[0]


def get_category_id(event_id: str, category_name: str) -> tuple[str, str]:
    categories = api_get("categories", {"eventUuid": event_id})
    cat_map = {c["name"].replace("\u2122", "").strip().lower(): c for c in categories}
    key = category_name.lower().strip()
    if key in cat_map:
        c = cat_map[key]
        return c["id"], c["name"]
    # "MotoGP" was called "500cc" before 2002
    if key == "motogp" and "500cc" in cat_map:
        c = cat_map["500cc"]
        return c["id"], c["name"]
    raise SystemExit(
        f"Category '{category_name}' not found. Available: {[c['name'] for c in categories]}"
    )


def get_all_sessions(event_id: str, category_id: str) -> list[dict]:
    """Return all finished sessions for the event/category, ordered by weekend schedule."""
    sessions = api_get("sessions", {"eventUuid": event_id, "categoryUuid": category_id})
    finished = [s for s in sessions if s["status"] == "FINISHED"]
    finished.sort(key=lambda s: s.get("date", ""))
    return finished


def get_classification(session_id: str) -> list[dict]:
    data = api_get(f"session/{session_id}/classification")
    return data.get("classification", [])


def get_session_label(session: dict) -> str:
    """Human-readable label like 'Free Practice 1' or 'Qualifying 2'."""
    stype = session.get("type", "")
    num = session.get("number")
    base = SESSION_LABELS.get(stype, stype)
    if num is not None:
        return f"{base} {num}"
    return base


def get_session_short_label(session: dict) -> str:
    """Short label for sheet names like 'FP1', 'Q2', 'RAC'."""
    stype = session.get("type", "")
    num = session.get("number")
    if num is not None:
        return f"{stype}{num}"
    return stype


# ---------------------------------------------------------------------------
# PDF Analysis parser — extracts lap-by-lap + sector times from official PDFs
# ---------------------------------------------------------------------------

# Regex for a lap data line:
#   lap_number  lap_time  T1  T2  T3  T4  speed
# Lap time format: m'ss.mmm  (e.g. 2'02.534)
# Sector times: ss.mmm (e.g. 34.492)
# Lines may contain * (cancelled time) or P (pit)
LAP_RE = re.compile(
    r"^(\d+)\s+"                                  # lap number
    r"(\d+[':]\d+\.\d+)\s+"                       # lap time (m'ss.mmm or m:ss.mmm)
    r"(?:[*P]\s+)?"                               # optional cancelled(*) / pit(P) marker after lap time
    r"(\*?\s*\d+\.\d+)\s+"                        # T1
    r"(\*?\s*\d+\.\d+)\s+"                        # T2
    r"(\*?\s*\d+\.\d+)\s+"                        # T3
    r"(\*?\s*\d+\.\d+)\s+"                        # T4
    r"(?:\*\s+)?"                                 # optional trailing * (cancelled lap time) before speed
    r"(\d+\.?\d*)"                                 # speed
)

# Rider header: "Firstname SURNAME CONSTRUCTOR NAT"
# Name must have at least two words (first + last) to avoid matching team names
# like "Pro Honda LCR" as a rider.
RIDER_HEADER_RE = re.compile(
    r"^([A-Z][a-zA-ZÀ-ÿ]+\s+[A-Za-zÀ-ÿ\s\-']+?)\s+"  # rider name (2+ words)
    r"(APRILIA|DUCATI|HONDA|KTM|YAMAHA|"
    r"Aprilia|Ducati|Honda|KTM|Yamaha|"
    r"KALEX|Kalex|BOSCOSCURO|Boscoscuro|"
    r"HUSQVARNA|Husqvarna|GASGAS|GasGas|CFMOTO|CFMoto)\s+"
    r"([A-Z]{1,3})$"                               # nationality code (1-3 chars; cropped pages may truncate)
)

# Older format (pre-2024): "1st 12 Maverick VIÑALES YAMAHA S"
# Position + number + name + constructor + nationality all on one line
RIDER_HEADER_OLD_RE = re.compile(
    r"^(\d+)\w*\s+"                                # position (1st, 2nd, 3rd, 4, 5...)
    r"(\d+)\s+"                                    # rider number
    r"([A-Z][a-zA-ZÀ-ÿ]+\s+[A-Za-zÀ-ÿ\s\-']+?)\s+"  # rider name (2+ words)
    r"(APRILIA|DUCATI|HONDA|KTM|YAMAHA|"
    r"Aprilia|Ducati|Honda|KTM|Yamaha|"
    r"KALEX|Kalex|BOSCOSCURO|Boscoscuro|"
    r"HUSQVARNA|Husqvarna|GASGAS|GasGas|CFMOTO|CFMoto)"
    r"(?:\s+([A-Z]{1,3}))?$"                       # optional nationality (may be cropped)
)

# 2016-2017 format: "Jorge LORENZO Movistar Yamaha Mot S"
# Name + team name (no constructor keyword) + optional nationality
# Detected by: starts with FirstName SURNAME (surname has 2+ consecutive uppercase letters),
# followed by team text, optionally ending with a 1-3 char nationality code.
# Must be followed by a position line ("1st 99") on the next line.
RIDER_HEADER_TEAM_RE = re.compile(
    r"^([A-Z][a-zÀ-ÿ]+\s+"                        # first name (capitalized)
    r"[A-ZÀ-Ÿ][A-ZÀ-Ÿa-zà-ÿ\-']+)"              # surname (starts uppercase)
    r"\s+(.+?)"                                     # team name (anything)
    r"(?:\s+([A-Z]{1,3}))?$"                        # optional nationality code
)

POSITION_RE = re.compile(r"^(\d+)\w*\s+(\d+)$")   # "1st 72" or "3 72"
TEAM_RE = re.compile(r"^[A-Z].*(?:Racing|Team|Factory|Honda|Ducati|Aprilia|KTM|Yamaha|Castrol|Gresini|VR46|Trackhouse|Pertamina|Tech3|BK8|LCR|Pramac).*$", re.IGNORECASE)
RUN_RE = re.compile(r"^Run\s*#\s*(\d+)\s+Front\s+Tyre\s*(\S+(?:-\S+)?)\s+Rear\s+Tyre\s*(\S+(?:-\S+)?)")
RUNS_META_RE = re.compile(r"Runs=(\d+)\s+Total laps=(\d+)")
TYRE_STATUS_RE = re.compile(r"^(New|[0-9]+Laps at start)\s+Tyre\s+(New|[0-9]+Laps at start)\s+Tyre$")


def download_pdf(url: str) -> bytes | None:
    """Download a PDF, return bytes or None on failure."""
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200 and len(resp.content) > 100:
            return resp.content
    except Exception:
        pass
    return None


def parse_analysis_column(text: str) -> list[dict]:
    """Parse one column of the Analysis PDF into rider data blocks."""
    riders = []
    lines = text.split("\n")
    current_rider = None
    current_run = 0
    front_tyre = ""
    rear_tyre = ""
    front_status = ""
    rear_status = ""
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # Check for OLD format rider header (pre-2024):
        # "1st 12 Maverick VIÑALES YAMAHA S"
        m = RIDER_HEADER_OLD_RE.match(line)
        if m:
            if current_rider and current_rider["laps"]:
                riders.append(current_rider)
            current_rider = {
                "rider": m.group(3).strip(),
                "constructor": m.group(4).strip().upper(),
                "nationality": (m.group(5) or "").strip(),
                "position": int(m.group(1)),
                "number": int(m.group(2)),
                "team": "",
                "laps": [],
            }
            current_run = 0
            front_tyre = rear_tyre = ""
            front_status = rear_status = ""
            i += 1
            continue

        # Check for NEW format rider header (2024+):
        # "Marco BEZZECCHI APRILIA ITA"
        m = RIDER_HEADER_RE.match(line)
        if m:
            if current_rider and current_rider["laps"]:
                riders.append(current_rider)
            current_rider = {
                "rider": m.group(1).strip(),
                "constructor": m.group(2).strip().upper(),
                "nationality": m.group(3).strip(),
                "position": None,
                "number": None,
                "team": "",
                "laps": [],
            }
            current_run = 0
            front_tyre = rear_tyre = ""
            front_status = rear_status = ""
            i += 1
            continue

        # Check for 2016-2017 format: "Jorge LORENZO Movistar Yamaha Mot S"
        # Confirmed by next line being a position line ("1st 99")
        m = RIDER_HEADER_TEAM_RE.match(line)
        if m and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            m_pos = POSITION_RE.match(next_line)
            if m_pos:
                if current_rider and current_rider["laps"]:
                    riders.append(current_rider)
                current_rider = {
                    "rider": m.group(1).strip(),
                    "constructor": "",
                    "nationality": (m.group(3) or "").strip(),
                    "position": int(m_pos.group(1)),
                    "number": int(m_pos.group(2)),
                    "team": m.group(2).strip(),
                    "laps": [],
                }
                current_run = 0
                front_tyre = rear_tyre = ""
                front_status = rear_status = ""
                i += 2  # skip both the rider line and position line
                continue

        # Check for position line (e.g. "1st 72") — only for new format
        m = POSITION_RE.match(line)
        if m and current_rider and current_rider["position"] is None:
            current_rider["position"] = int(m.group(1))
            current_rider["number"] = int(m.group(2))
            i += 1
            continue

        # Team name
        if current_rider and not current_rider["team"] and TEAM_RE.match(line):
            current_rider["team"] = line.strip()
            i += 1
            continue

        # Run header with tyre info
        m = RUN_RE.match(line)
        if m:
            current_run = int(m.group(1))
            front_tyre = m.group(2)
            rear_tyre = m.group(3)
            front_status = rear_status = ""
            i += 1
            # Next line might be tyre status
            if i < len(lines):
                ts = TYRE_STATUS_RE.match(lines[i].strip())
                if ts:
                    front_status = ts.group(1)
                    rear_status = ts.group(2)
                    i += 1
            continue

        # Lap data line
        m = LAP_RE.match(line)
        if m and current_rider:
            pit = "P" in line
            cancelled_sectors = []
            raw_parts = line.split()
            for idx, part in enumerate(raw_parts):
                if part == "*":
                    cancelled_sectors.append(idx)

            current_rider["laps"].append({
                "lap": int(m.group(1)),
                "lap_time": m.group(2).replace("'", ":"),
                "T1": m.group(3).replace("*", "").strip(),
                "T2": m.group(4).replace("*", "").strip(),
                "T3": m.group(5).replace("*", "").strip(),
                "T4": m.group(6).replace("*", "").strip(),
                "speed": float(m.group(7)),
                "pit": pit,
                "run": current_run,
                "front_tyre": front_tyre,
                "rear_tyre": rear_tyre,
                "front_tyre_status": front_status,
                "rear_tyre_status": rear_status,
            })
            i += 1
            continue

        i += 1

    if current_rider and current_rider["laps"]:
        riders.append(current_rider)

    return riders


def parse_analysis_pdf(pdf_bytes: bytes) -> list[dict]:
    """Parse a full Analysis PDF into a list of rider dicts with lap data.

    The Analysis PDF lays riders out in two columns per page, and a single
    rider's lap block can overflow from the bottom of one column to the top of
    the next column (or next page). All column texts are therefore concatenated
    in reading order and parsed as a single stream so that rider state carries
    across column/page boundaries; parsing each column independently would drop
    every continuation lap that appears before the next rider header.
    """
    chunks = []
    pdf = pdfplumber.open(io.BytesIO(pdf_bytes))
    for page in pdf.pages:
        w = page.width
        h = page.height
        # Split into left and right columns
        for x0, x1 in [(0, w / 2), (w / 2, w)]:
            cropped = page.crop((x0, 0, x1, h))
            text = cropped.extract_text()
            if text:
                chunks.append(text)
    pdf.close()
    return parse_analysis_column("\n".join(chunks))


def get_analysis_pdf_url(session: dict) -> str | None:
    """Extract the Analysis PDF URL from session metadata."""
    files = session.get("session_files", {})
    analysis = files.get("analysis", {})
    url = analysis.get("url", "")
    return url if url else None


# ---------------------------------------------------------------------------
# Classification helpers (for the summary sheet)
# ---------------------------------------------------------------------------

def format_time_api(ms) -> str:
    if ms is None:
        return ""
    try:
        ms = int(ms)
    except (TypeError, ValueError):
        return str(ms)
    total_seconds = ms / 1000
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    if minutes > 0:
        return f"{minutes}:{seconds:06.3f}"
    return f"{seconds:.3f}"


def build_classification_rows(classification: list[dict]) -> list[dict]:
    rows = []
    for entry in classification:
        rider = entry.get("rider", {})
        constructor = entry.get("constructor", {})
        team = entry.get("team", {})
        full_name = rider.get("full_name", "")
        gap_data = entry.get("gap")
        gap_first = gap_data.get("first", "") if isinstance(gap_data, dict) else ""
        bl_data = entry.get("best_lap")
        best_lap = bl_data.get("time", "") if isinstance(bl_data, dict) else ""

        rows.append({
            "Pos": entry.get("position", ""),
            "#": rider.get("number", ""),
            "Rider": full_name,
            "Team": team.get("name", ""),
            "Bike": constructor.get("name", ""),
            "Laps": entry.get("total_laps", ""),
            "Time": format_time_api(entry.get("time")),
            "Gap": gap_first,
            "Best Lap": best_lap,
            "Top Speed": entry.get("top_speed", ""),
            "Points": entry.get("points", ""),
            "Status": entry.get("status", ""),
        })
    return rows


# ---------------------------------------------------------------------------
# Excel writing
# ---------------------------------------------------------------------------

def auto_width(ws, start_row: int, num_cols: int):
    for col_idx in range(1, num_cols + 1):
        max_len = 5
        for row in ws.iter_rows(min_row=start_row, max_row=ws.max_row, min_col=col_idx, max_col=col_idx):
            for cell in row:
                if cell.value is not None:
                    max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 2, 22)


def write_classification_sheet(ws, session: dict, event: dict, category_name: str, classification: list[dict]):
    """Write a classification summary sheet."""
    session_label = get_session_label(session)
    sponsored = event.get("sponsored_name", event.get("name", ""))
    condition = session.get("condition", {})

    ws.merge_cells("A1:L1")
    cell = ws["A1"]
    cell.value = f"{sponsored} - {category_name} {session_label}"
    cell.font = TITLE_FONT

    ws.merge_cells("A2:L2")
    cell = ws["A2"]
    circuit = event.get("circuit", {}).get("name", "")
    place = event.get("circuit", {}).get("place", "")
    date_str = session.get("date", "")[:10]
    weather = condition.get("weather", "")
    temp_air = condition.get("air", "")
    temp_ground = condition.get("ground", "")
    cell.value = f"{circuit}, {place} | {date_str} | {weather}, Air {temp_air}, Track {temp_ground}"
    cell.font = SUBTITLE_FONT

    ws.append([])

    rows = build_classification_rows(classification)
    if not rows:
        ws.append(["No classification data available"])
        return

    headers = list(rows[0].keys())
    ws.append(headers)
    header_row = ws.max_row
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_idx)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center")
        cell.border = THIN_BORDER

    for row_data in rows:
        ws.append(list(row_data.values()))
        r = ws.max_row
        pos = row_data.get("Pos", "")
        for col_idx in range(1, len(headers) + 1):
            c = ws.cell(row=r, column=col_idx)
            c.border = THIN_BORDER
            c.alignment = Alignment(horizontal="center")
            if isinstance(pos, int) and pos in PODIUM_FILLS:
                c.fill = PODIUM_FILLS[pos]

    ws.freeze_panes = f"A{header_row + 1}"
    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(len(headers))}{ws.max_row}"
    auto_width(ws, header_row, len(headers))


def write_lap_analysis_sheet(ws, session: dict, event: dict, category_name: str, riders_data: list[dict]):
    """Write a lap-by-lap analysis sheet with sector times for all riders."""
    session_label = get_session_label(session)
    sponsored = event.get("sponsored_name", event.get("name", ""))

    ws.merge_cells("A1:K1")
    cell = ws["A1"]
    cell.value = f"{sponsored} - {category_name} {session_label} - Lap Analysis"
    cell.font = TITLE_FONT

    condition = session.get("condition", {})
    ws.merge_cells("A2:K2")
    cell = ws["A2"]
    circuit = event.get("circuit", {}).get("name", "")
    date_str = session.get("date", "")[:10]
    weather = condition.get("weather", "")
    cell.value = f"{circuit} | {date_str} | {weather}"
    cell.font = SUBTITLE_FONT

    ws.append([])

    headers = ["Rider", "#", "Pos", "Lap", "Lap Time", "T1", "T2", "T3", "T4",
               "Speed (km/h)", "Pit", "Run", "Front Tyre", "Rear Tyre"]

    ws.append(headers)
    header_row = ws.max_row
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_idx)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center")
        cell.border = THIN_BORDER

    for rider in riders_data:
        # Find the best lap time for this rider
        best_time = None
        best_lap_num = None
        for lap in rider["laps"]:
            lt = lap["lap_time"]
            if best_time is None or lt < best_time:
                best_time = lt
                best_lap_num = lap["lap"]

        for lap in rider["laps"]:
            row = [
                rider["rider"],
                rider.get("number", ""),
                rider.get("position", ""),
                lap["lap"],
                lap["lap_time"],
                lap["T1"],
                lap["T2"],
                lap["T3"],
                lap["T4"],
                lap["speed"],
                "P" if lap.get("pit") else "",
                lap.get("run", ""),
                lap.get("front_tyre", ""),
                lap.get("rear_tyre", ""),
            ]
            ws.append(row)
            r = ws.max_row
            for col_idx in range(1, len(headers) + 1):
                c = ws.cell(row=r, column=col_idx)
                c.border = THIN_BORDER
                c.alignment = Alignment(horizontal="center")
            # Bold the rider name column
            ws.cell(row=r, column=1).alignment = Alignment(horizontal="left")
            # Highlight best lap
            if lap["lap"] == best_lap_num:
                for col_idx in range(4, 10):
                    ws.cell(row=r, column=col_idx).font = BEST_LAP_FONT

    ws.freeze_panes = f"A{header_row + 1}"
    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(len(headers))}{ws.max_row}"
    auto_width(ws, header_row, len(headers))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Download full MotoGP weekend data (all sessions, lap times, sectors) to Excel"
    )
    parser.add_argument("--year", type=int, help="Season year (default: current)")
    parser.add_argument("--category", default="MotoGP",
                        help="Category: MotoGP, Moto2, Moto3 (default: MotoGP)")
    parser.add_argument("--output", "-o", help="Output .xlsx file path (auto-generated if omitted)")
    args = parser.parse_args()

    print("MotoGP Full Weekend Data Downloader")
    print("Sources: api.motogp.pulselive.com + resources.motogp.com (free, no API key)\n")

    # 1. Resolve season
    print(f"Finding season {'(current)' if not args.year else args.year}...")
    season_id, year = get_season_id(args.year)
    print(f"   Season {year}")

    # 2. Get latest finished race event
    print("Finding latest race event...")
    event = get_latest_race_event(season_id)
    print(f"   {event['sponsored_name']} ({event['date_end']})")
    print(f"   {event['circuit']['name']}, {event['circuit']['place']}")

    # 3. Resolve category
    category_id, category_name = get_category_id(event["id"], args.category)
    print(f"   Category: {category_name}")

    # 4. Get all sessions
    print("Fetching all sessions...")
    sessions = get_all_sessions(event["id"], category_id)
    print(f"   {len(sessions)} finished sessions found")
    for s in sessions:
        print(f"      {get_session_short_label(s):>5}  {get_session_label(s):<25} {s['date'][:16]}")

    # 5. Build workbook
    wb = Workbook()
    wb.remove(wb.active)  # remove default sheet

    total_laps_parsed = 0

    for session in sessions:
        short = get_session_short_label(session)
        label = get_session_label(session)
        print(f"\n--- {label} ({short}) ---")

        # 5a. Classification from API
        print(f"   Downloading classification...")
        classification = get_classification(session["id"])
        print(f"   {len(classification)} riders classified")

        # Create classification sheet
        safe_name = f"{short} Results"[:31]
        ws_class = wb.create_sheet(title=safe_name)
        write_classification_sheet(ws_class, session, event, category_name, classification)

        # 5b. Lap analysis from PDF
        pdf_url = get_analysis_pdf_url(session)
        if pdf_url:
            print(f"   Downloading analysis PDF...")
            pdf_bytes = download_pdf(pdf_url)
            if pdf_bytes:
                print(f"   Parsing lap-by-lap data ({len(pdf_bytes):,} bytes)...")
                riders_data = parse_analysis_pdf(pdf_bytes)
                lap_count = sum(len(r["laps"]) for r in riders_data)
                total_laps_parsed += lap_count
                print(f"   {len(riders_data)} riders, {lap_count} lap entries extracted")

                if riders_data:
                    safe_name = f"{short} Laps"[:31]
                    ws_laps = wb.create_sheet(title=safe_name)
                    write_lap_analysis_sheet(ws_laps, session, event, category_name, riders_data)
            else:
                print(f"   (Analysis PDF not available)")
        else:
            print(f"   (No analysis PDF URL)")

    # 6. Save
    if not args.output:
        short_name = event.get("short_name", "race")
        cat = args.category.lower()
        args.output = f"MotoGP_{year}_{short_name}_{cat}_full.xlsx"

    wb.save(args.output)

    sheet_count = len(wb.sheetnames)
    print(f"\nSaved to: {Path(args.output).resolve()}")
    print(f"   {sheet_count} sheets | {total_laps_parsed} total lap entries")
    print(f"   Sheets: {', '.join(wb.sheetnames)}")


if __name__ == "__main__":
    main()
