"""Import official Grand Prix race archives and standings, one season/class transaction at a time."""

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode

import load_to_sql as loader
from sql_connection import connect_to_sql
from category_scope import CATEGORY_YEARS, canonical_category, normalize_category


MIGRATION = Path(__file__).parent / "migrations" / "20261126_01_historical_archive.sql"
CATEGORY = "500cc"
STANDINGS_SQL = """
    MERGE championship_standings AS target
    USING (SELECT ? AS season_year, ? AS category, ? AS rider_id) AS source
    ON target.season_year=source.season_year AND target.category=source.category
        AND target.rider_id=source.rider_id
    WHEN MATCHED THEN UPDATE SET position=?,points=?,constructor_id=?,constructor_name=?,
        is_final=?,source_url=?,source_json=?,fetched_at=SYSUTCDATETIME()
    WHEN NOT MATCHED THEN INSERT
        (season_year,category,rider_id,position,points,constructor_id,constructor_name,
         is_final,source_url,source_json)
    VALUES (?,?,?,?,?,?,?,?,?,?);
"""


def parse_years(value):
    years = set()
    try:
        for part in value.split(","):
            bounds = [int(n) for n in part.split("-")]
            if len(bounds) == 1:
                years.add(bounds[0])
            elif len(bounds) == 2 and bounds[0] <= bounds[1]:
                years.update(range(bounds[0], bounds[1] + 1))
            else:
                raise ValueError
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use years such as 1966,1975 or 1949-1959") from exc
    if not years or min(years) < 1949 or max(years) > datetime.now(timezone.utc).year:
        raise argparse.ArgumentTypeError("Use Grand Prix seasons from 1949 through the current year")
    return sorted(years)


def validate_snapshot(data, year, category=CATEGORY):
    if data["version"] != 1 or data["year"] != year or normalize_category(data["category"]) != normalize_category(category):
        raise ValueError("Historical snapshot version/year/category mismatch")
    if not data["events"] or not data["standings"]["classification"]:
        raise ValueError(f"{year}: empty race archive or official standings")
    session_ids = set()
    for event in data["events"]:
        event_year = (event["event"].get("season") or {}).get("year")
        if event_year is not None and event_year != year:
            raise ValueError(f"{year}: event belongs to another season")
        for item in event["sessions"]:
            session = item["session"]
            if session["id"] in session_ids or session["type"] not in ("RAC", "SPR") or session["status"] != "FINISHED":
                raise ValueError(f"{year}: duplicate or unsupported historical session")
            source_event = (session.get("event") or {}).get("id")
            if source_event is not None and source_event != event["event"]["id"]:
                raise ValueError(f"{year}: session belongs to another event")
            session_ids.add(session["id"])
            entries = item["classification"]
            if not entries:
                # FINISHED does not guarantee that the legacy archive has results.
                continue
            validate_riders(entries)
            if not any(entry.get("position") == 1 for entry in entries):
                raise ValueError(f"{year}: session {session['id']} has no classified winner")
    standings = data["standings"]["classification"]
    validate_riders(standings)
    champions = [entry for entry in standings if entry.get("position") == 1]
    if len(champions) != 1 or Decimal(str(champions[0]["points"])) <= 0:
        raise ValueError(f"{year}: official champion/points unavailable")
    for entry in standings:
        if not isinstance(entry.get("position"), int) or entry["position"] < 1:
            raise ValueError(f"{year}: official standing has no valid position")
        points = Decimal(str(entry["points"]))
        if not points.is_finite() or points < 0:
            raise ValueError(f"{year}: invalid official points")
    return data


def validate_riders(entries):
    ids = []
    for entry in entries:
        rider = entry["rider"]
        if not rider.get("id") or not rider.get("full_name"):
            raise ValueError("Historical entry has no rider identity")
        ids.append(rider["id"])
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Empty classification or duplicate rider IDs")


def fetch_snapshot(year, category=CATEGORY):
    canonical = canonical_category(category)
    first, last = CATEGORY_YEARS[canonical]
    if not first <= year <= last:
        raise ValueError(f"{canonical} did not run in {year}")
    season_id, _ = loader.get_season_id(year)
    events = loader.api_get("events", {"seasonUuid": season_id, "isFinished": "true"})
    data = {
        "version": 1, "year": year, "category": canonical, "season_id": season_id,
        "is_final": year < datetime.now(timezone.utc).year,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "events": [], "skipped_events": [],
    }
    category_id = None
    for event in sorted(events, key=lambda e: e["date_end"]):
        if event.get("test"):
            continue
        categories = loader.api_get("categories", {"eventUuid": event["id"]})
        source_category = next((c for c in categories if normalize_category(c["name"]) == normalize_category(canonical)), None)
        if source_category is None:
            data["skipped_events"].append({
                "event": event["short_name"], "reason": f"{canonical} not listed by source",
                "source_event": event,
            })
            continue
        category_id = source_category["id"]
        data["category"] = source_category["name"]
        sessions = [
            s for s in loader.get_all_sessions(event["id"], category_id) if s["type"] in ("RAC", "SPR")
        ]
        if not sessions:
            data["skipped_events"].append({"event": event["short_name"], "reason": f"no finished {canonical} race"})
            continue
        items = [
            {"session": session, "classification": loader.get_classification(session["id"])}
            for session in sessions
        ]
        if not data["is_final"]:
            # Some future current-season races are incorrectly flagged FINISHED.
            items = [item for item in items if item["classification"]]
            if not items:
                data["skipped_events"].append({
                    "event": event["short_name"], "reason": "no current-season race results",
                })
                continue
        data["events"].append({"event": event, "sessions": items})
    if category_id is None:
        raise ValueError(f"{year}: no {canonical} category found")
    params = {"seasonUuid": season_id, "categoryUuid": category_id}
    data["standings"] = loader.api_get("standings", params)
    data["standings_url"] = f"{loader.API_BASE_URL}/standings?{urlencode(params)}"
    return validate_snapshot(data, year, canonical)


def apply_migration(conn):
    with conn:
        cursor = conn.cursor()
        for migration in sorted(MIGRATION.parent.glob("*.sql")):
            cursor.execute(migration.read_text(encoding="utf-8"))
            cursor.execute(
                "IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version=?) "
                "INSERT INTO schema_migrations(version) VALUES (?)",
                migration.stem, migration.stem,
            )
    print("Archive schema migrations verified", flush=True)


def race_entries(data):
    return [
        (item["session"]["id"], entry)
        for event in data["events"] for item in event["sessions"]
        for entry in item["classification"]
    ]


def verify_season(conn, data):
    year = data["year"]
    category = data["category"]
    actual = conn.execute("""
        SELECT c.session_id,c.rider_id,c.position,c.team_id,c.total_laps,
               c.time_ms,c.time_text,c.gap_first,c.gap_prev,c.best_lap_number,
               c.best_lap_time,c.top_speed,c.points,c.status,c.constructor_id,c.constructor_name,
               c.rider_number
        FROM classifications c JOIN sessions s ON s.session_id=c.session_id
        JOIN events e ON e.event_id=s.event_id
        WHERE e.season_year=? AND s.category=? AND s.source_kind='official-api'
            AND s.session_type IN ('RAC','SPR')
    """, year, category).fetchall()
    expected = []
    for sid, entry in race_entries(data):
        p = loader.classification_parameters(sid, entry, year)
        expected.append(p[:17])
    if sorted(map(tuple, actual)) != sorted(expected):
        raise ValueError(f"{year}: stored race classifications differ from official source")
    actual_standings = conn.execute("""
        SELECT rider_id,position,points,constructor_id,constructor_name,is_final
        FROM championship_standings WHERE season_year=? AND category=?
    """, year, category).fetchall()
    expected_standings = [
        (entry["rider"]["id"], entry["position"], Decimal(str(entry["points"])),
         (entry.get("constructor") or {}).get("id"), (entry.get("constructor") or {}).get("name"),
         data.get("is_final", True))
        for entry in data["standings"]["classification"]
    ]
    if sorted(map(tuple, actual_standings)) != sorted(expected_standings):
        raise ValueError(f"{year}: stored final standings differ from official source")
    expected_sessions = {
        (event["event"]["id"], item["session"]["id"])
        for event in data["events"] for item in event["sessions"]
    }
    actual_sessions = conn.execute("""
        SELECT e.event_id,s.session_id
        FROM events e JOIN sessions s ON s.event_id=e.event_id
        WHERE e.season_year=? AND s.category=? AND s.source_kind='official-api'
            AND s.session_type IN ('RAC','SPR')
    """, year, category).fetchall()
    if set(map(tuple, actual_sessions)) != expected_sessions:
        raise ValueError(f"{year}: GP/session coverage differs from official archive")


def persist_season(conn, data):
    year = data["year"]
    category = data["category"]
    validate_snapshot(data, year, category)
    payload = json.dumps(data, ensure_ascii=True, sort_keys=True)
    fingerprint = hashlib.sha256(json.dumps(
        {key: value for key, value in data.items() if key != "fetched_at"},
        ensure_ascii=True, sort_keys=True,
    ).encode("utf-8")).hexdigest()
    with conn:
        existing = conn.execute(
            "SELECT source_hash FROM historical_imports WHERE season_year=? AND category=?",
            year, category,
        ).fetchone()
        if existing and existing[0] == fingerprint:
            verify_season(conn, data)
            print(f"{year}: unchanged archive verified", flush=True)
            return
        entries = race_entries(data)
        all_entries = [entry for _, entry in entries] + data["standings"]["classification"]
        riders = {entry["rider"]["id"]: entry["rider"] for entry in all_entries}
        cursor = conn.cursor()
        existing_riders = {row[0] for row in conn.execute("SELECT rider_id FROM riders").fetchall()}
        for rider in riders.values():
            if rider["id"] not in existing_riders:
                loader.upsert_rider(cursor, {**rider, "number": rider.get("number") or None})
        teams = {
            entry["team"]["id"]: (entry["team"], entry.get("constructor") or {})
            for entry in all_entries if (entry.get("team") or {}).get("id")
        }
        for team, constructor in teams.values():
            loader.upsert_team(cursor, team, constructor, year)
        for event in data["events"]:
            loader.upsert_event(cursor, event["event"], year)
            for item in event["sessions"]:
                loader.upsert_session(cursor, item["session"], event["event"]["id"], category)
        cursor.fast_executemany = True
        if entries:
            cursor.executemany(
                loader.CLASSIFICATION_SQL,
                [loader.classification_parameters(sid, entry, year) for sid, entry in entries],
            )
        standings_rows = []
        for entry in data["standings"]["classification"]:
            constructor = entry.get("constructor") or {}
            values = (
                entry["position"], Decimal(str(entry["points"])), constructor.get("id"),
                constructor.get("name"), data.get("is_final", True),
                data["standings_url"], json.dumps(entry, ensure_ascii=True),
            )
            key = (year, category, entry["rider"]["id"])
            standings_rows.append((*key, *values, *key, *values))
        cursor.executemany(STANDINGS_SQL, standings_rows)
        verify_season(conn, data)
        cursor.fast_executemany = False
        cursor.execute("""
            MERGE historical_imports AS t
            USING (SELECT ? AS season_year,? AS category) AS s
            ON t.season_year=s.season_year AND t.category=s.category
            WHEN MATCHED THEN UPDATE SET source_hash=?,event_count=?,session_count=?,
                classification_count=?,standings_count=?,source_payload=?,imported_at=SYSUTCDATETIME()
            WHEN NOT MATCHED THEN INSERT
                (season_year,category,source_hash,event_count,session_count,
                 classification_count,standings_count,source_payload)
            VALUES (?,?,?,?,?,?,?,?);
        """, year, category,
            fingerprint, len(data["events"]), sum(len(e["sessions"]) for e in data["events"]),
            len(entries), len(standings_rows), payload,
            year, category, fingerprint, len(data["events"]),
            sum(len(e["sessions"]) for e in data["events"]), len(entries), len(standings_rows), payload)
    champion = next(entry for entry in data["standings"]["classification"] if entry["position"] == 1)
    print(f"{year}: verified {len(data['events'])} GPs, {len(entries)} race results, "
          f"{len(standings_rows)} standings; champion {champion['rider']['full_name']} "
          f"({champion['points']} points)", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=parse_years, required=True)
    parser.add_argument("--category", type=canonical_category, default=CATEGORY,
                        help="Source class: 500cc, MotoGP, 250cc, Moto2, 125cc, Moto3, 350cc, 50cc, 80cc")
    parser.add_argument("--apply", action="store_true", help="Write verified seasons to Azure SQL")
    parser.add_argument("--migrate", action="store_true", help="Apply the additive schema migration")
    parser.add_argument("--refresh", action="store_true", help="Refetch cached official archives")
    parser.add_argument("--cache-dir", type=Path, default=Path("historical_cache"))
    args = parser.parse_args()
    if args.migrate and not args.apply:
        parser.error("--migrate requires --apply")
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    conn = connect_to_sql() if args.apply else None
    try:
        if args.migrate:
            apply_migration(conn)
        for year in args.years:
            path = args.cache_dir / f"{year}_{args.category}.json"
            if path.exists() and not args.refresh:
                data = validate_snapshot(json.loads(path.read_text(encoding="utf-8")), year, args.category)
            else:
                data = fetch_snapshot(year, args.category)
                path.write_text(json.dumps(data, ensure_ascii=True, sort_keys=True), encoding="utf-8")
            missing = [
                event["event"]["short_name"] for event in data["events"]
                for item in event["sessions"] if not item["classification"]
            ]
            print(f"{year} {data['category']}: source verified; {len(data['events'])} listed GPs; "
                  f"weekends without a listed finished class race: {len(data['skipped_events'])}; "
                  f"empty race classifications: {','.join(missing) or 'none'}", flush=True)
            if conn is not None:
                persist_season(conn, data)
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()
