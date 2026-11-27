"""Backfill independent official premier standings without importing race data."""

import argparse
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse

from category_scope import canonical_category, normalize_category
from import_historical import ArchiveSource, STANDINGS_SQL, parse_years, validate_riders
import load_to_sql as loader
from sql_connection import connect_to_sql


ROOT = Path(__file__).parent
MIGRATION = ROOT / "migrations" / "20261127_02_standings_imports.sql"
# Official 2001 XML header names the Cinzano Rio GP but uses country code BRA;
# the events API uses RIO. No rider or result identity is inferred from this alias.
DOCUMENT_EVENT_ALIASES = {(2001, "BRA"): "RIO"}


def event_finished(event, today):
    return event.get("status") == "FINISHED" and date.fromisoformat(event["date_end"]) < today


def document_evidence(data):
    candidates = []
    for kind in ("file", "xmlFile"):
        document = data["standings"].get(kind)
        if not document:
            continue
        parsed = urlparse(document)
        parts = parsed.path.split("/")
        if (parsed.scheme != "https" or parsed.netloc != "resources.motogp.com"
                or len(parts) < 7 or parts[1:3] != ["files", "results"]
                or parts[3] != str(data["year"])):
            raise ValueError("Official standings document does not establish season/as-of identity")
        if normalize_category(parts[4]) == normalize_category(data["category"]):
            source_category, source_event = parts[4], parts[5]
        else:
            source_event, source_category = parts[4], parts[5]
        source_event = DOCUMENT_EVENT_ALIASES.get((data["year"], source_event), source_event)
        matching = [event for event in data["events"] if event["short_name"] == source_event
                    and event_finished(event, date.fromisoformat(data["checked_on"]))]
        if len(matching) != 1:
            raise ValueError("Standings document points to a future or unknown weekend")
        if normalize_category(source_category) != normalize_category(data["category"]):
            raise ValueError("Standings document category mismatch")
        candidates.append({
            "url": document, "kind": kind, "event_id": matching[0]["id"],
            "event_short": source_event, "event_end": matching[0]["date_end"],
            "session": parts[6] if normalize_category(parts[5]) == normalize_category(data["category"])
            else None,
        })
    if not candidates:
        raise ValueError("Official standings document does not establish season/as-of identity")
    # Neither reference is always freshest: legacy PDFs and modern XML links
    # both sometimes lag. Prefer the latest round, then the race over the sprint.
    return max(candidates, key=lambda item: (
        item["event_end"], item["session"] not in {"SPR"}, item["kind"] == "file",
    ))


def validate_snapshot(data):
    year = data["year"]
    expected_category = "500cc" if year < 2002 else "MotoGP"
    if (data["version"] != 1 or year < 1990
            or canonical_category(data["category"]) != expected_category):
        raise ValueError("Standings-only snapshot version/year/category mismatch")
    if data["season"]["year"] != year:
        raise ValueError("Standings season identity mismatch")
    events = data["events"]
    if not events or any(
        (event.get("season") or {}).get("id") != data["season"]["id"]
        or (event.get("season") or {}).get("year") != year
        or event.get("test")
        for event in events
    ):
        raise ValueError("Standings event-season identity mismatch")
    today = date.fromisoformat(data["checked_on"])
    expected_final = year < today.year and data["season"].get("current") is False
    if data["is_final"] != expected_final:
        raise ValueError("Current or active season cannot be silently marked final")
    parsed_source = urlparse(data["source_url"])
    expected_source = urlparse(f"{loader.API_BASE_URL}/standings")
    if ((parsed_source.scheme, parsed_source.netloc, parsed_source.path)
            != (expected_source.scheme, expected_source.netloc, expected_source.path)
            or sorted(parse_qsl(parsed_source.query)) != sorted(data["params"].items())
            or data["params"]["seasonUuid"] != data["season"]["id"]
            or data["params"]["categoryUuid"] != data["source_category"]["id"]
            or data["source_category"]["name"] != data["category"]):
        raise ValueError("Standings query provenance mismatch")
    entries = data["standings"]["classification"]
    if not entries:
        if data.get("standings_available") is not False:
            raise ValueError("Empty standings require an explicit source-gap marker")
        return data
    if not data["standings_available"]:
        raise ValueError("Source-gap marker conflicts with supplied standings")
    validate_riders(entries)
    if sum(entry.get("position") == 1 for entry in entries) != 1:
        raise ValueError("Official standings need exactly one rank-one rider")
    for entry in entries:
        position = entry.get("position")
        points = Decimal(str(entry["points"]))
        if type(position) is not int or position < 1 or not points.is_finite() or points < 0:
            raise ValueError("Invalid official standing rank/points")
        team_season = (entry.get("team") or {}).get("season")
        if team_season and (team_season.get("id") != data["season"]["id"]
                            or team_season.get("year") != year):
            raise ValueError("Standing entry belongs to another season")
    if Decimal(str(next(entry["points"] for entry in entries if entry["position"] == 1))) <= 0:
        raise ValueError("Official rank-one points unavailable")
    # Current API can mark future events FINISHED. A source document must identify
    # an elapsed, finished weekend, without inspecting/upserting race results.
    evidence = document_evidence(data)
    if data["is_final"] and any(
        event["date_end"] > evidence["event_end"]
        and event.get("status") not in {"CANCELLED", "CANCELED"}
        for event in events
    ):
        raise ValueError("Historical standings document is not from the last uncancelled weekend")
    if data["is_final"] and evidence["session"] == "SPR":
        raise ValueError("A sprint-only document cannot establish final weekend standings")
    return data


def fetch_snapshot(year, source, today=None):
    today = today or datetime.now(timezone.utc).date()
    if not 1990 <= year <= today.year:
        raise ValueError("Use premier seasons from 1990 through the current year")
    # Avoid stale current-season HTTP cache while retaining paced historical reads.
    def api(endpoint, params=None):
        if year == today.year and isinstance(source, ArchiveSource):
            refresh = source.refresh
            source.refresh = True
            try:
                return source(endpoint, params)
            finally:
                source.refresh = refresh
        return source(endpoint, params)

    season = next((item for item in api("seasons") if item["year"] == year), None)
    if season is None:
        raise ValueError(f"{year}: official season unavailable")
    events = [event for event in api("events", {"seasonUuid": season["id"]})
              if not event.get("test")]
    finished = [event for event in events if event_finished(event, today)]
    if not finished:
        raise ValueError(f"{year}: no elapsed finished weekend")
    last_event = max(finished, key=lambda event: event["date_end"])
    expected_category = "500cc" if year < 2002 else "MotoGP"
    category = next((
        item for item in api("categories", {"eventUuid": last_event["id"]})
        if normalize_category(item["name"]) == normalize_category(expected_category)
    ), None)
    if category is None:
        raise ValueError(f"{year}: premier class not supplied")
    params = {"seasonUuid": season["id"], "categoryUuid": category["id"]}
    standings = api("standings", params)
    data = {
        "version": 1, "year": year, "category": category["name"],
        "season": season, "source_category": category, "events": events,
        "checked_on": today.isoformat(),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        # A current-season clinched title is not a completed final table.
        "is_final": year < today.year and season.get("current") is False,
        "params": params, "source_url": f"{loader.API_BASE_URL}/standings?{urlencode(params)}",
        "standings": standings, "standings_available": bool(standings["classification"]),
    }
    return validate_snapshot(data)


def standings_values(data):
    return sorted((
        entry["rider"]["id"], entry["position"], Decimal(str(entry["points"])),
        (entry.get("constructor") or {}).get("id"),
        (entry.get("constructor") or {}).get("name"), data["is_final"],
    ) for entry in data["standings"]["classification"])


def verify_standings(conn, data):
    actual = conn.execute(
        "SELECT rider_id,position,points,constructor_id,constructor_name,is_final "
        "FROM championship_standings WHERE season_year=? AND category=? ORDER BY rider_id",
        data["year"], data["category"],
    ).fetchall()
    if list(map(tuple, actual)) != standings_values(data):
        raise ValueError(f"{data['year']}: stored official standings differ from source")


def persist(conn, data):
    validate_snapshot(data)
    year, category = data["year"], data["category"]
    payload = json.dumps(data, ensure_ascii=True, sort_keys=True)
    fingerprint = hashlib.sha256(json.dumps(
        {key: value for key, value in data.items() if key != "fetched_at"},
        ensure_ascii=True, sort_keys=True,
    ).encode()).hexdigest()
    with conn:
        existing = conn.execute(
            "SELECT source_hash FROM standings_imports WHERE season_year=? AND category=?",
            year, category,
        ).fetchone()
        if existing and existing[0] == fingerprint:
            verify_standings(conn, data)
            return "unchanged"
        aliases = conn.execute(
            "SELECT DISTINCT category FROM championship_standings WHERE season_year=?", year,
        ).fetchall()
        if any(normalize_category(row[0]) == normalize_category(category) and row[0] != category
               for row in aliases):
            raise ValueError(f"{year}: existing alternative source category label needs review")
        current = conn.execute(
            "SELECT rider_id,position,points,constructor_id,constructor_name,is_final "
            "FROM championship_standings WHERE season_year=? AND category=? ORDER BY rider_id",
            year, category,
        ).fetchall()
        if current and not existing and list(map(tuple, current)) != standings_values(data):
            raise ValueError(f"{year}: unowned existing standings differ; refusing to overwrite")
        expected_ids = {row[0] for row in standings_values(data)}
        if any(row[0] not in expected_ids for row in current):
            raise ValueError(f"{year}: existing standings riders absent from source; review required")
        known_riders = {row[0] for row in conn.execute("SELECT rider_id FROM riders").fetchall()}
        cursor = conn.cursor()
        for entry in data["standings"]["classification"]:
            rider = entry["rider"]
            if rider["id"] not in known_riders:
                # The loader's rider MERGE is insert-only; existing profiles stay unchanged.
                loader.upsert_rider(cursor, rider)
                known_riders.add(rider["id"])
        parameters = []
        for rider_id, position, points, constructor_id, constructor_name, is_final in standings_values(data):
            entry = next(item for item in data["standings"]["classification"] if item["rider"]["id"] == rider_id)
            key = (year, category, rider_id)
            values = (
                position, points, constructor_id, constructor_name, is_final,
                data["source_url"], json.dumps(entry, ensure_ascii=True),
            )
            parameters.append((*key, *values, *key, *values))
        if parameters and (existing or not current):
            cursor.fast_executemany = True
            cursor.executemany(STANDINGS_SQL, parameters)
            cursor.fast_executemany = False
        verify_standings(conn, data)
        cursor.execute("""
            MERGE standings_imports AS t
            USING (SELECT ? AS season_year,? AS category) AS s
            ON t.season_year=s.season_year AND t.category=s.category
            WHEN MATCHED THEN UPDATE SET source_hash=?,standings_count=?,is_final=?,
                source_url=?,source_payload=?,imported_at=SYSUTCDATETIME()
            WHEN NOT MATCHED THEN INSERT
                (season_year,category,source_hash,standings_count,is_final,source_url,source_payload)
            VALUES (?,?,?,?,?,?,?);
        """, year, category, fingerprint, len(expected_ids), data["is_final"], data["source_url"], payload,
            year, category, fingerprint, len(expected_ids), data["is_final"], data["source_url"], payload)
    return "imported" if expected_ids else "source-gap"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=parse_years, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    if min(args.years) < 1990:
        parser.error("Use import_historical.py for pre-1990 race archives; this command starts at 1990")
    source = ArchiveSource(ROOT / "historical_cache" / "http", refresh=args.refresh)
    conn = connect_to_sql() if args.apply else None
    try:
        if args.migrate:
            if conn is None:
                parser.error("--migrate requires --apply")
            with conn:
                conn.execute(MIGRATION.read_text(encoding="utf-8"))
                conn.execute(
                    "IF NOT EXISTS(SELECT 1 FROM schema_migrations WHERE version=?) "
                    "INSERT INTO schema_migrations(version) VALUES (?)", MIGRATION.stem, MIGRATION.stem,
                )
        for year in args.years:
            data = fetch_snapshot(year, source)
            cache = ROOT / "historical_cache" / f"standings_{year}.json"
            cache.write_text(json.dumps(data, ensure_ascii=True, sort_keys=True), encoding="utf-8")
            state = persist(conn, data) if conn is not None else "read-only"
            print(f"{year} {data['category']}: {len(data['standings']['classification'])} rows; "
                  f"{'final' if data['is_final'] else 'provisional'}; {state}", flush=True)
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()
