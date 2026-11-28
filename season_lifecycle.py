"""Explicit, snapshot-bound championship finality; not race-archive coverage."""

import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

MIGRATION_VERSION = "20261128_02_season_lifecycle"
UNKNOWN = {"status": "unknown", "evidence": None}


def _digest(value):
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def standings_digest(rows):
    """Hash the displayed source facts and provenance, not derived final flags."""
    normalized = []
    for row in rows:
        rider, position, points, constructor_id, constructor_name, url, source_json = row
        value = Decimal(str(points))
        if not value.is_finite():
            raise ValueError("Non-finite standing points")
        normalized.append([rider, position, format(value.normalize(), "f"), constructor_id,
                           constructor_name, url, json.loads(source_json)])
    if not normalized or len({row[0] for row in normalized}) != len(normalized):
        raise ValueError("Empty standings or duplicate riders")
    if sum(row[1] == 1 for row in normalized) != 1:
        raise ValueError("Standings require exactly one first-place rider")
    return _digest(sorted(normalized, key=lambda row: row[0]))


def snapshot_digest(data, kind):
    """Bind the confirmation to source standings and source calendar evidence."""
    if kind == "standings":
        keys = ("year", "category", "season", "source_category", "events", "params",
                "source_url", "standings", "standings_available")
    elif kind == "historical":
        keys = ("year", "category", "season_id", "events", "skipped_events",
                "standings_url", "standings", "standings_available")
    else:
        raise ValueError("Unsupported standings importer")
    return _digest({key: data[key] for key in keys})


def _installed(conn):
    return bool(conn.execute("SELECT OBJECT_ID('dbo.season_lifecycle', 'U')").fetchone()[0])


def _standing_rows(conn, year, category, lock=False):
    hint = " WITH (UPDLOCK, HOLDLOCK)" if lock else ""
    return conn.execute(f"""
        SELECT rider_id,position,points,constructor_id,constructor_name,source_url,source_json
        FROM dbo.championship_standings{hint} WHERE season_year=? AND category=? ORDER BY rider_id
    """, year, category).fetchall()


def _import_payload(conn, year, category, kind, lock=False):
    table = {"standings": "dbo.standings_imports", "historical": "dbo.historical_imports"}[kind]
    if not conn.execute("SELECT OBJECT_ID(?, 'U')", table).fetchone()[0]:
        return None
    hint = " WITH (UPDLOCK, HOLDLOCK)" if lock else ""
    row = conn.execute(
        f"SELECT source_payload FROM {table}{hint} WHERE season_year=? AND category=?",
        year, category,
    ).fetchone()
    return json.loads(row[0]) if row else None


def _other_import_hash(conn, year, category, kind, lock=False):
    other = "historical" if kind == "standings" else "standings"
    payload = _import_payload(conn, year, category, other, lock=lock)
    return snapshot_digest(payload, other) if payload else None


def review_digest(kind, standings_hash, import_hash, other_import_hash):
    """Bind the operator's review to both source snapshots and the stored rows."""
    return _digest([kind, standings_hash, import_hash, other_import_hash])


def _matches(conn, year, category, kind, expected_standings, expected_import, expected_other):
    data = _import_payload(conn, year, category, kind)
    if data is None or data.get("year") != year or data.get("category") != category:
        return False
    rows = _standing_rows(conn, year, category)
    if not rows:
        return False
    return (snapshot_digest(data, kind) == expected_import
            and _other_import_hash(conn, year, category, kind) == expected_other
            and standings_digest(rows) == expected_standings)


def read_season_status(conn, season_year, category):
    """Read status for one exact stored class; absent or stale confirmation is unknown."""
    if not _installed(conn):
        return dict(UNKNOWN)
    row = conn.execute("""
        SELECT standings_hash,import_kind,import_hash,other_import_hash,evidence_url,evidence_hash,review_note,
               confirmed_at,invalidated_at
        FROM dbo.season_lifecycle WHERE season_year=? AND category=?
    """, season_year, category).fetchone()
    if not row or row[8] is not None or not _matches(
        conn, season_year, category, row[1], row[0], row[2], row[3]
    ):
        return dict(UNKNOWN)
    return {"status": "official_final", "evidence": {
        "url": row[4], "sha256": row[5], "review_note": row[6],
        "confirmed_at": row[7].isoformat() + "Z", "standings_sha256": row[0],
        "import_kind": row[1], "import_sha256": row[2],
    }}


def invalidate_changed_confirmation(conn, year, category):
    """Permanently invalidate a confirmation when its imported source changes."""
    if not _installed(conn):
        return
    row = conn.execute("""
        SELECT standings_hash,import_kind,import_hash,other_import_hash FROM dbo.season_lifecycle
        WHERE season_year=? AND category=? AND invalidated_at IS NULL
    """, year, category).fetchone()
    if row and not _matches(conn, year, category, row[1], row[0], row[2], row[3]):
        conn.execute("""
            UPDATE dbo.season_lifecycle SET invalidated_at=SYSUTCDATETIME(),
                invalidation_reason='Imported source or standings changed'
            WHERE season_year=? AND category=? AND invalidated_at IS NULL
        """, year, category)


def evidence_digest(url):
    import requests

    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port:
        raise ValueError("Finality evidence must be an official HTTPS URL")
    host = (parsed.hostname or "").lower()
    if not any(host == domain or host.endswith("." + domain)
               for domain in ("motogp.com", "fim-moto.com")):
        raise ValueError("Finality evidence must be hosted by MotoGP or FIM")
    response = requests.get(url, timeout=60, allow_redirects=False)
    response.raise_for_status()
    if response.is_redirect or not response.content:
        raise ValueError("Finality evidence must resolve directly to nonempty content")
    return hashlib.sha256(response.content).hexdigest()


def validate_imported_standings(data, rows, kind):
    entries = data["standings"]["classification"]
    url = data["source_url" if kind == "standings" else "standings_url"]
    parsed = urlparse(url)
    query = parse_qsl(parsed.query)
    params = dict(query)
    season_id = data["season"]["id"] if kind == "standings" else data["season_id"]
    if (parsed.scheme != "https" or parsed.netloc != "api.motogp.pulselive.com"
            or parsed.path != "/motogp/v1/results/standings"
            or len(query) != 2 or set(params) != {"seasonUuid", "categoryUuid"}
            or params["seasonUuid"] != season_id or not params["categoryUuid"]):
        raise ValueError("Imported standings have invalid official source identity")
    if kind == "standings" and params != data["params"]:
        raise ValueError("Imported standings category identity differs from source")
    if not data["standings_available"] or not entries or len(entries) != len(rows):
        raise ValueError("Imported standings are empty or incomplete")
    expected = {entry["rider"]["id"]: entry for entry in entries}
    if len(expected) != len(entries):
        raise ValueError("Duplicate riders in imported snapshot")
    for rider, position, points, constructor_id, constructor_name, source_url, source_json in rows:
        entry = expected.get(rider)
        if not entry or source_url != url or json.loads(source_json) != entry:
            raise ValueError("Stored standings do not match the imported source snapshot")
        constructor = entry.get("constructor") or {}
        if (position != entry["position"] or Decimal(str(points)) != Decimal(str(entry["points"]))
                or constructor_id != constructor.get("id") or constructor_name != constructor.get("name")):
            raise ValueError("Stored standings differ from the imported source snapshot")


def confirm_final(conn, year, category, kind, expected_hash, expected_review_hash,
                  url, expected_evidence_hash, note):
    if not _installed(conn):
        raise ValueError(f"Apply migration {MIGRATION_VERSION} before confirming finality")
    if not note.strip() or len(note) > 2000:
        raise ValueError("A review note identifying final season, class and evidence is required")
    if str(year) not in note or category.replace("™", "").lower() not in note.lower():
        raise ValueError("The review note must identify the season year and class")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        raise ValueError("Reviewed standings hash must be lowercase SHA-256")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_review_hash):
        raise ValueError("Reviewed snapshot hash must be lowercase SHA-256")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_evidence_hash):
        raise ValueError("Reviewed evidence hash must be lowercase SHA-256")
    evidence_hash = evidence_digest(url)
    if evidence_hash != expected_evidence_hash:
        raise ValueError("Finality evidence differs from the reviewed content")
    with conn:
        data = _import_payload(conn, year, category, kind, lock=True)
        if data is None or data.get("year") != year or data.get("category") != category:
            raise ValueError("Matching imported season and class snapshot not found")
        imported_hash = snapshot_digest(data, kind)
        other_hash = _other_import_hash(conn, year, category, kind, lock=True)
        rows = _standing_rows(conn, year, category, lock=True)
        validate_imported_standings(data, rows, kind)
        actual_hash = standings_digest(rows)
        if actual_hash != expected_hash:
            raise ValueError("Reviewed standings hash differs from the imported standings")
        if review_digest(kind, actual_hash, imported_hash, other_hash) != expected_review_hash:
            raise ValueError("Imported snapshots differ from the reviewed snapshots")
        conn.execute("""
            MERGE dbo.season_lifecycle WITH (HOLDLOCK) AS t
            USING (SELECT ? AS season_year, ? AS category) AS s
            ON t.season_year=s.season_year AND t.category=s.category
            WHEN MATCHED THEN UPDATE SET standings_hash=?,import_kind=?,import_hash=?,other_import_hash=?,
                evidence_url=?,evidence_hash=?,review_note=?,confirmed_at=SYSUTCDATETIME(),
                invalidated_at=NULL,invalidation_reason=NULL
            WHEN NOT MATCHED THEN INSERT
                (season_year,category,standings_hash,import_kind,import_hash,other_import_hash,
                 evidence_url,evidence_hash,review_note)
                VALUES (?,?,?,?,?,?,?,?,?);
        """, year, category, actual_hash, kind, imported_hash, other_hash, url, evidence_hash, note,
             year, category, actual_hash, kind, imported_hash, other_hash, url, evidence_hash, note)


def unfinalize(conn, year, category, reason):
    if not reason.strip() or len(reason) > 200:
        raise ValueError("An unfinalization reason of at most 200 characters is required")
    if not _installed(conn):
        raise ValueError(f"Apply migration {MIGRATION_VERSION} before unfinalizing")
    with conn:
        cursor = conn.execute("""
            UPDATE dbo.season_lifecycle SET invalidated_at=SYSUTCDATETIME(),invalidation_reason=?
            WHERE season_year=? AND category=? AND invalidated_at IS NULL
        """, reason, year, category)
        if cursor.rowcount != 1:
            raise ValueError("No active confirmation for this season and class")


def apply_migration(conn):
    migration = Path(__file__).parent / "migrations" / f"{MIGRATION_VERSION}.sql"
    with conn:
        conn.execute(migration.read_text(encoding="utf-8"))
        conn.execute(
            "IF NOT EXISTS(SELECT 1 FROM schema_migrations WHERE version=?) "
            "INSERT INTO schema_migrations(version) VALUES (?)", MIGRATION_VERSION, MIGRATION_VERSION,
        )


def add_import_arguments(parser):
    parser.add_argument("--confirm-final", action="store_true",
                        help="Confirm reviewed class finality after importing one fresh snapshot")
    parser.add_argument("--reviewed-standings-sha256",
                        help="Hash of the previously reviewed stored standings")
    parser.add_argument("--reviewed-snapshot-sha256",
                        help="Hash of the previously reviewed standings and import snapshots")
    parser.add_argument("--final-evidence-url", help="Direct official MotoGP/FIM evidence URL")
    parser.add_argument("--reviewed-evidence-sha256", help="SHA-256 of the reviewed evidence content")
    parser.add_argument("--final-review-note", help="Review rationale identifying season and class")


def validate_import_arguments(parser, args):
    fields = (args.reviewed_standings_sha256, args.reviewed_snapshot_sha256, args.final_evidence_url,
              args.reviewed_evidence_sha256, args.final_review_note)
    if args.confirm_final:
        if not args.apply or not args.refresh or len(args.years) != 1 or not all(fields):
            parser.error("--confirm-final requires --apply, --refresh, one year, and all five review fields")
    elif any(fields):
        parser.error("Final review fields require --confirm-final")


def main():
    import argparse
    from sql_connection import connect_to_sql

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--category", required=True, help="Exact stored source class label")
    parser.add_argument("--import-kind", choices=("standings", "historical"),
                        help="Importer whose snapshot is being reviewed (required for --inspect)")
    parser.add_argument("--show-snapshots", action="store_true",
                        help="Print complete stored import snapshots when inspecting")
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--inspect", action="store_true")
    actions.add_argument("--unfinalize", metavar="REASON")
    args = parser.parse_args()
    if args.inspect and not args.import_kind:
        parser.error("--inspect requires --import-kind")
    if args.unfinalize and (args.import_kind or args.show_snapshots):
        parser.error("--import-kind and --show-snapshots are only used with --inspect")
    conn = connect_to_sql()
    try:
        if args.inspect:
            rows = _standing_rows(conn, args.year, args.category)
            data = _import_payload(conn, args.year, args.category, args.import_kind)
            if data is None or data.get("year") != args.year or data.get("category") != args.category:
                raise ValueError("Matching imported season and class snapshot not found")
            validate_imported_standings(data, rows, args.import_kind)
            standings_hash = standings_digest(rows)
            imported_hash = snapshot_digest(data, args.import_kind)
            other_kind = "historical" if args.import_kind == "standings" else "standings"
            other = _import_payload(conn, args.year, args.category, other_kind)
            other_hash = snapshot_digest(other, other_kind) if other else None
            print(f"Standings SHA-256: {standings_hash}")
            print(f"Reviewed snapshot SHA-256: {review_digest(args.import_kind, standings_hash, imported_hash, other_hash)}")
            if args.show_snapshots:
                print(json.dumps({args.import_kind: data, other_kind: other}, ensure_ascii=True, indent=2))
            for rider, position, points, _, name, url, source_json in rows:
                rider_name = json.loads(source_json)["rider"]["full_name"]
                print(f"{position}: {rider_name} ({rider}) {points} {name or ''} [{url}]")
            print(json.dumps(read_season_status(conn, args.year, args.category)))
        else:
            unfinalize(conn, args.year, args.category, args.unfinalize)
            print("Confirmation invalidated; status is unknown.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
