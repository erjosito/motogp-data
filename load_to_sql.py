#!/usr/bin/env python3
"""
load_to_sql.py

Loads MotoGP weekend data (all sessions, classifications, lap-by-lap times
with sector splits) into Azure SQL Database.

Uses the same API + PDF parsing as Get-MotoGPResults.py but writes to SQL
instead of Excel.

Usage:
    python load_to_sql.py                          # Latest event, MotoGP
    python load_to_sql.py --year 2026 --all-events # All finished events in 2026
    python load_to_sql.py --category Moto2         # Moto2 class
    python load_to_sql.py --conn-str "DRIVER=..."  # Custom connection string

Environment variable:
    MOTOGP_SQL_CONN_STR — connection string (overridden by --conn-str)
"""

import argparse
import importlib.util
import os
import sys
from pathlib import Path

import pyodbc

# Import functions from the main script
_spec = importlib.util.spec_from_file_location(
    "motogp", Path(__file__).parent / "Get-MotoGPResults.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

api_get = _mod.api_get
get_season_id = _mod.get_season_id
get_latest_race_event = _mod.get_latest_race_event
get_category_id = _mod.get_category_id
get_all_sessions = _mod.get_all_sessions
get_classification = _mod.get_classification
get_session_label = _mod.get_session_label
get_session_short_label = _mod.get_session_short_label
get_analysis_pdf_url = _mod.get_analysis_pdf_url
download_pdf = _mod.download_pdf
parse_analysis_pdf = _mod.parse_analysis_pdf
format_time_api = _mod.format_time_api

DEFAULT_CONN_STR = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=motogp-sql-srv.database.windows.net;"
    "DATABASE=motogpdb;"
    "UID=motogpadmin;"
    "PWD=MotoGP2026data!;"
    "Encrypt=yes;TrustServerCertificate=no;"
    "Connection Timeout=120;"
)

_conn_str_override = None
_conn = None


def get_connection(conn_str: str | None = None) -> pyodbc.Connection:
    """Get a connection, reconnecting if needed (survives sleep/hibernate)."""
    global _conn_str_override, _conn
    if conn_str:
        _conn_str_override = conn_str
    cs = _conn_str_override or os.environ.get("MOTOGP_SQL_CONN_STR") or DEFAULT_CONN_STR
    if _conn is not None:
        try:
            _conn.execute("SELECT 1")
            return _conn
        except Exception:
            print("   (reconnecting to database...)")
            try:
                _conn.close()
            except Exception:
                pass
            _conn = None
    _conn = pyodbc.connect(cs)
    return _conn


def reconnect():
    """Force a fresh connection."""
    global _conn
    try:
        if _conn:
            _conn.close()
    except Exception:
        pass
    _conn = None
    return get_connection()


def upsert_event(cursor, event: dict, year: int):
    cursor.execute("""
        MERGE events AS target
        USING (SELECT ? AS event_id) AS source ON target.event_id = source.event_id
        WHEN MATCHED THEN UPDATE SET
            season_year=?, short_name=?, event_name=?, sponsored_name=?,
            circuit_name=?, circuit_place=?, country_name=?, country_iso=?,
            date_start=?, date_end=?
        WHEN NOT MATCHED THEN INSERT
            (event_id, season_year, short_name, event_name, sponsored_name,
             circuit_name, circuit_place, country_name, country_iso,
             date_start, date_end)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """,
        event["id"],
        year, event.get("short_name"), event.get("name"), event.get("sponsored_name"),
        event.get("circuit", {}).get("name"), event.get("circuit", {}).get("place"),
        event.get("country", {}).get("name"), event.get("country", {}).get("iso"),
        event.get("date_start"), event.get("date_end"),
        # INSERT values
        event["id"],
        year, event.get("short_name"), event.get("name"), event.get("sponsored_name"),
        event.get("circuit", {}).get("name"), event.get("circuit", {}).get("place"),
        event.get("country", {}).get("name"), event.get("country", {}).get("iso"),
        event.get("date_start"), event.get("date_end"),
    )


def upsert_rider(cursor, rider: dict):
    cursor.execute("""
        MERGE riders AS target
        USING (SELECT ? AS rider_id) AS source ON target.rider_id = source.rider_id
        WHEN MATCHED THEN UPDATE SET
            full_name=?, number=?, nationality_iso=?, nationality=?
        WHEN NOT MATCHED THEN INSERT
            (rider_id, full_name, number, nationality_iso, nationality)
        VALUES (?, ?, ?, ?, ?);
    """,
        rider["id"],
        rider.get("full_name"), rider.get("number"),
        rider.get("country", {}).get("iso"), rider.get("country", {}).get("name"),
        # INSERT values
        rider["id"],
        rider.get("full_name"), rider.get("number"),
        rider.get("country", {}).get("iso"), rider.get("country", {}).get("name"),
    )


def upsert_team(cursor, team: dict, constructor: dict, year: int):
    team_id = team.get("id")
    if not team_id:
        return
    cursor.execute("""
        MERGE teams AS target
        USING (SELECT ? AS team_id, ? AS season_year) AS source
            ON target.team_id = source.team_id AND target.season_year = source.season_year
        WHEN MATCHED THEN UPDATE SET
            team_name=?, constructor=?, constructor_id=?
        WHEN NOT MATCHED THEN INSERT
            (team_id, season_year, team_name, constructor, constructor_id)
        VALUES (?, ?, ?, ?, ?);
    """,
        team_id, year,
        team.get("name"), constructor.get("name"), constructor.get("id"),
        # INSERT values
        team_id, year,
        team.get("name"), constructor.get("name"), constructor.get("id"),
    )


def upsert_session(cursor, session: dict, event_id: str, category_name: str):
    label = get_session_label(session)
    condition = session.get("condition", {})
    cursor.execute("""
        MERGE sessions AS target
        USING (SELECT ? AS session_id) AS source ON target.session_id = source.session_id
        WHEN MATCHED THEN UPDATE SET
            event_id=?, category=?, session_type=?, session_number=?,
            session_label=?, session_date=?, track_condition=?, weather=?,
            air_temp=?, ground_temp=?, humidity=?, status=?
        WHEN NOT MATCHED THEN INSERT
            (session_id, event_id, category, session_type, session_number,
             session_label, session_date, track_condition, weather,
             air_temp, ground_temp, humidity, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """,
        session["id"],
        event_id, category_name, session.get("type"), session.get("number"),
        label, session.get("date"), condition.get("track"), condition.get("weather"),
        condition.get("air"), condition.get("ground"), condition.get("humidity"),
        session.get("status"),
        # INSERT values
        session["id"],
        event_id, category_name, session.get("type"), session.get("number"),
        label, session.get("date"), condition.get("track"), condition.get("weather"),
        condition.get("air"), condition.get("ground"), condition.get("humidity"),
        session.get("status"),
    )


def upsert_classification(cursor, session_id: str, entry: dict, year: int):
    rider = entry.get("rider", {})
    rider_id = rider.get("id")
    if not rider_id:
        return

    # Upsert rider and team
    upsert_rider(cursor, rider)
    team = entry.get("team") or {}
    constructor = entry.get("constructor") or {}
    if team:
        upsert_team(cursor, team, constructor, year)

    gap = entry.get("gap") or {}
    best_lap = entry.get("best_lap") or {}

    cursor.execute("""
        MERGE classifications AS target
        USING (SELECT ? AS session_id, ? AS rider_id) AS source
            ON target.session_id = source.session_id AND target.rider_id = source.rider_id
        WHEN MATCHED THEN UPDATE SET
            position=?, team_id=?, total_laps=?, time_ms=?, time_text=?,
            gap_first=?, gap_prev=?, best_lap_number=?, best_lap_time=?,
            top_speed=?, points=?, status=?
        WHEN NOT MATCHED THEN INSERT
            (session_id, rider_id, position, team_id, total_laps, time_ms,
             time_text, gap_first, gap_prev, best_lap_number, best_lap_time,
             top_speed, points, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """,
        session_id, rider_id,
        entry.get("position"), team.get("id"), entry.get("total_laps"),
        str(entry.get("time") or ""), format_time_api(entry.get("time")),
        gap.get("first"), gap.get("prev"),
        best_lap.get("number"), best_lap.get("time"),
        entry.get("top_speed"), entry.get("points"), entry.get("status"),
        # INSERT values
        session_id, rider_id,
        entry.get("position"), team.get("id"), entry.get("total_laps"),
        str(entry.get("time") or ""), format_time_api(entry.get("time")),
        gap.get("first"), gap.get("prev"),
        best_lap.get("number"), best_lap.get("time"),
        entry.get("top_speed"), entry.get("points"), entry.get("status"),
    )


def build_rider_lookup(cursor, session_id: str) -> dict:
    """Build a number→rider_id map from the classification we already loaded."""
    cursor.execute(
        "SELECT r.rider_id, r.number, r.full_name FROM classifications c "
        "JOIN riders r ON c.rider_id = r.rider_id WHERE c.session_id = ?",
        session_id,
    )
    by_number = {}
    by_surname = {}
    for row in cursor.fetchall():
        rid, num, name = row
        if num:
            by_number[num] = rid
        # Index by uppercase surname (last word)
        parts = name.split()
        if parts:
            by_surname[parts[-1].upper()] = rid
    return by_number, by_surname


def resolve_rider_id_fast(by_number: dict, by_surname: dict, rider_name: str, rider_number: int | None) -> str | None:
    """Fast rider lookup using pre-built maps from session classification."""
    if rider_number and rider_number in by_number:
        return by_number[rider_number]
    # Try surname match
    parts = rider_name.split()
    surname = parts[-1].upper() if parts else ""
    if surname in by_surname:
        return by_surname[surname]
    # Try any word match (for multi-word surnames like DI GIANNANTONIO)
    for word in reversed(parts):
        w = word.upper()
        if w in by_surname and len(w) > 3:
            return by_surname[w]
    return None


def insert_laps(cursor, session_id: str, riders_data: list[dict]):
    """Insert lap data, resolving rider names to IDs via session classification."""
    cursor.execute("DELETE FROM laps WHERE session_id = ?", session_id)

    by_number, by_surname = build_rider_lookup(cursor, session_id)

    inserted = 0
    skipped_riders = []
    seen_keys = set()
    for rider in riders_data:
        rider_id = resolve_rider_id_fast(by_number, by_surname, rider["rider"], rider.get("number"))
        if not rider_id:
            skipped_riders.append(rider["rider"])
            continue

        for lap in rider["laps"]:
            key = (session_id, rider_id, lap["lap"])
            if key in seen_keys:
                continue  # skip duplicate lap entries
            seen_keys.add(key)
            cursor.execute("""
                INSERT INTO laps (session_id, rider_id, lap_number, lap_time,
                    t1, t2, t3, t4, speed_kmh, is_pit, run_number,
                    front_tyre, rear_tyre)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                session_id, rider_id, lap["lap"], lap["lap_time"],
                lap["T1"], lap["T2"], lap["T3"], lap["T4"],
                lap["speed"], 1 if lap.get("pit") else 0, lap.get("run"),
                lap.get("front_tyre"), lap.get("rear_tyre"),
            )
            inserted += 1
    if skipped_riders:
        print(f"   (unmatched riders: {', '.join(skipped_riders)})")
    return inserted


def load_event(conn, event: dict, year: int, category_name_input: str):
    """Load all data for a single event into the database."""
    cursor = conn.cursor()

    event_name = event.get("sponsored_name", event.get("name"))
    print(f"\n{'='*60}")
    print(f"Loading: {event_name} ({event.get('date_end')})")
    print(f"{'='*60}")

    # Upsert event
    upsert_event(cursor, event, year)
    conn.commit()

    # Resolve category — skip event if category not available (e.g. COVID cancellations)
    try:
        category_id, category_name = get_category_id(event["id"], category_name_input)
    except SystemExit:
        print(f"   Category '{category_name_input}' not available for this event, skipping")
        cursor.close()
        return
    print(f"   Category: {category_name}")

    # Get all sessions
    sessions = get_all_sessions(event["id"], category_id)
    print(f"   {len(sessions)} sessions")

    total_classifications = 0
    total_laps = 0

    for session in sessions:
        short = get_session_short_label(session)
        label = get_session_label(session)
        print(f"\n   --- {label} ({short}) ---")

        # Upsert session
        upsert_session(cursor, session, event["id"], category_name)
        conn.commit()

        # Load classification
        print(f"   Loading classification...")
        classification = get_classification(session["id"])
        for entry in classification:
            upsert_classification(cursor, session["id"], entry, year)
        conn.commit()
        total_classifications += len(classification)
        print(f"   {len(classification)} riders classified")

        # Load lap analysis from PDF
        pdf_url = get_analysis_pdf_url(session)
        if pdf_url:
            print(f"   Downloading analysis PDF...")
            pdf_bytes = download_pdf(pdf_url)
            if pdf_bytes:
                print(f"   Parsing lap-by-lap data...")
                riders_data = parse_analysis_pdf(pdf_bytes)
                lap_count = insert_laps(cursor, session["id"], riders_data)
                conn.commit()
                total_laps += lap_count
                print(f"   {len(riders_data)} riders, {lap_count} laps inserted")
            else:
                print(f"   (Analysis PDF not available)")
        else:
            print(f"   (No analysis PDF URL)")

    print(f"\n   Event totals: {total_classifications} classifications, {total_laps} laps")
    cursor.close()


def main():
    parser = argparse.ArgumentParser(description="Load MotoGP data into Azure SQL")
    parser.add_argument("--year", type=int, help="Season year (default: current)")
    parser.add_argument("--years", type=str,
                        help="Range of years to load, e.g. '2021-2026'")
    parser.add_argument("--category", default="MotoGP",
                        help="Category: MotoGP, Moto2, Moto3 (default: MotoGP)")
    parser.add_argument("--all-events", action="store_true",
                        help="Load all finished events (not just latest)")
    parser.add_argument("--conn-str", help="SQL connection string (or set MOTOGP_SQL_CONN_STR)")
    args = parser.parse_args()

    print("MotoGP Data Loader -> Azure SQL")
    print("="*40 + "\n")

    conn = get_connection(args.conn_str)
    print("Connected to Azure SQL\n")

    # Determine which years to load
    if args.years:
        parts = args.years.split("-")
        year_list = list(range(int(parts[0]), int(parts[1]) + 1))
    elif args.year:
        year_list = [args.year]
    else:
        _, current_year = get_season_id(None)
        year_list = [current_year]

    for year in year_list:
        print(f"\n{'#'*60}")
        print(f"# Season {year}")
        print(f"{'#'*60}")

        try:
            season_id, _ = get_season_id(year)
        except SystemExit:
            print(f"   Season {year} not found, skipping")
            continue

        events = api_get("events", {"seasonUuid": season_id, "isFinished": "true"})
        race_events = [e for e in events if not e.get("test", False)]
        race_events.sort(key=lambda e: e["date_start"])

        if not race_events:
            print(f"   No finished events for {year}")
            continue

        if args.all_events or args.years:
            print(f"   {len(race_events)} finished events")
            for event in race_events:
                for attempt in range(3):
                    try:
                        conn = get_connection()
                        load_event(conn, event, year, args.category)
                        break
                    except Exception as ex:
                        err = str(ex)[:120]
                        print(f"   ERROR (attempt {attempt+1}/3) {event.get('short_name')}: {err}")
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                        if attempt < 2:
                            print("   Reconnecting...")
                            import time
                            time.sleep(5)
                            conn = reconnect()
                        else:
                            print(f"   SKIPPING {event.get('short_name')} after 3 failures")
        else:
            event = get_latest_race_event(season_id, args.category)
            load_event(conn, event, year, args.category)

    # Summary
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM events")
    n_events = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM sessions")
    n_sessions = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM classifications")
    n_class = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM laps")
    n_laps = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM riders")
    n_riders = cursor.fetchone()[0]

    # Post-import data cleanup
    print("\nRunning post-import cleanup...")

    # Fix bad speed values (PDF parser sometimes confuses sector times with speed)
    cursor.execute("UPDATE laps SET speed_kmh = NULL WHERE speed_kmh IS NOT NULL AND speed_kmh < 150")
    bad_speeds = cursor.rowcount
    if bad_speeds:
        print(f"   Cleaned {bad_speeds} invalid speed values (< 150 km/h)")

    # Fill in historical points for pre-2005 seasons (500cc era has no points in API)
    pts_pre93 = {1:20, 2:17, 3:15, 4:13, 5:11, 6:10, 7:9, 8:8, 9:7, 10:6}
    pts_93_04 = {1:25, 2:20, 3:16, 4:13, 5:11, 6:10, 7:9, 8:8, 9:7, 10:6,
                 11:5, 12:4, 13:3, 14:2, 15:1}
    cursor.execute("""
        SELECT c.session_id, c.rider_id, c.position, e.season_year
        FROM classifications c
        JOIN sessions s ON c.session_id = s.session_id
        JOIN events e ON s.event_id = e.event_id
        WHERE e.season_year BETWEEN 1990 AND 2004
          AND s.session_type = 'RAC'
          AND c.position IS NOT NULL
          AND (c.points IS NULL OR c.points = 0)
    """)
    pts_rows = cursor.fetchall()
    pts_fixed = 0
    for session_id, rider_id, position, year in pts_rows:
        pts_table = pts_pre93 if year < 1993 else pts_93_04
        pts = pts_table.get(int(position), 0)
        if pts > 0:
            cursor.execute("UPDATE classifications SET points = ? WHERE session_id = ? AND rider_id = ?",
                          pts, session_id, rider_id)
            pts_fixed += 1
    if pts_fixed:
        print(f"   Filled {pts_fixed} historical points (1990-2004)")

    conn.commit()
    cursor.close()
    conn.close()

    print(f"\n{'='*40}")
    print(f"Database totals:")
    print(f"   Events:          {n_events}")
    print(f"   Sessions:        {n_sessions}")
    print(f"   Classifications: {n_class}")
    print(f"   Lap entries:     {n_laps}")
    print(f"   Riders:          {n_riders}")
    print(f"{'='*40}")


if __name__ == "__main__":
    main()
