"""Export a consistent, lossless CSV snapshot without changing the database."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import lzma
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

from category_scope import official_points_inconsistent


ROOT = Path(__file__).resolve().parent
TABLES = {
    "championship_standings", "classifications", "events", "external_candidates",
    "external_classifications", "external_sources", "historical_imports", "laps",
    "riders", "schema_migrations", "sessions", "team_aliases", "teams",
}
FORMAT_VERSION = 1
TEMPORAL_TYPES = {"date", "datetime", "datetime2", "datetimeoffset", "time", "smalldatetime"}
SUPPORTED_TYPES = TEMPORAL_TYPES | {
    "bit", "tinyint", "smallint", "int", "bigint", "decimal", "numeric",
    "float", "real", "money", "smallmoney", "char", "varchar", "nchar", "nvarchar",
    "uniqueidentifier",
}
RESULTS_SQL = """
SELECT e.season_year,s.category,e.short_name AS event_short,e.event_name,e.circuit_name,
       e.country_iso,s.session_id,s.event_id,s.session_type,s.session_number,s.session_label,
       CONVERT(nvarchar(48),s.session_date,126) AS session_date,
       c.rider_id,r.full_name AS rider,COALESCE(c.rider_number,r.number) AS rider_number,
       r.nationality_iso,t.team_name,COALESCE(c.constructor_name,t.constructor) AS constructor,
       c.position,c.total_laps,c.time_ms AS time_raw,c.time_text,c.gap_first,c.gap_prev,
       c.best_lap_number,c.best_lap_time,c.top_speed,c.points,c.status,c.source_kind
FROM dbo.vw_effective_classifications c
JOIN dbo.sessions s ON s.session_id=c.session_id
JOIN dbo.events e ON e.event_id=s.event_id
JOIN dbo.riders r ON r.rider_id=c.rider_id
LEFT JOIN dbo.teams t ON t.team_id=c.team_id AND t.season_year=e.season_year
ORDER BY e.season_year,s.category,s.session_id,c.rider_id
"""


def quote(name):
    return "[" + name.replace("]", "]]") + "]"


def records(cursor):
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def encode_cell(value):
    if value is None:
        return r"\N"
    if isinstance(value, bool):
        return "1" if value else "0"
    text = str(value)
    return "\\" + text if text.startswith("\\") else text


def decode_cell(text):
    if text == r"\N":
        return None
    return text[1:] if text.startswith("\\\\") else text


def sql_type(column):
    kind = column["sql_type"]
    if kind in {"char", "varchar", "nchar", "nvarchar"}:
        length = column["max_length"]
        if length == -1:
            length = "max"
        elif kind.startswith("n"):
            length //= 2
        return f"{kind}({length})"
    if kind in {"decimal", "numeric"}:
        return f"{kind}({column['precision']},{column['scale']})"
    if kind in {"datetime2", "datetimeoffset", "time"}:
        return f"{kind}({column['scale']})"
    if kind == "float":
        return f"float({column['precision']})"
    return kind


def discover_schema(conn):
    tables = records(conn.execute("""
        SELECT t.object_id,SCHEMA_NAME(t.schema_id) AS schema_name,t.name AS name
        FROM sys.tables t WHERE t.is_ms_shipped=0 ORDER BY t.name
    """))
    if {(table["schema_name"], table["name"]) for table in tables} != {
        ("dbo", name) for name in TABLES
    }:
        raise ValueError("Application tables changed; review the explicit export allowlist before exporting")
    for table in tables:
        object_id = table.pop("object_id")
        table["columns"] = records(conn.execute("""
            SELECT c.name,TYPE_NAME(c.system_type_id) AS sql_type,c.max_length,
                   c.precision,c.scale,c.is_nullable,c.is_identity,c.is_computed,
                   c.collation_name,dc.definition AS default_definition
            FROM sys.columns c
            LEFT JOIN sys.default_constraints dc ON dc.object_id=c.default_object_id
            WHERE c.object_id=? ORDER BY c.column_id
        """, object_id))
        for column in table["columns"]:
            if (column["sql_type"] not in SUPPORTED_TYPES
                    or column["is_identity"] or column["is_computed"]):
                raise ValueError(f"Unsupported lossless export column: {table['name']}.{column['name']}")
        table["keys"] = []
        key_rows = records(conn.execute("""
            SELECT kc.name,kc.type,c.name AS column_name
            FROM sys.key_constraints kc
            JOIN sys.index_columns ic ON ic.object_id=kc.parent_object_id
                 AND ic.index_id=kc.unique_index_id
            JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
            WHERE kc.parent_object_id=? ORDER BY kc.name,ic.key_ordinal
        """, object_id))
        for row in key_rows:
            if not table["keys"] or table["keys"][-1]["name"] != row["name"]:
                table["keys"].append({"name": row["name"], "type": row["type"].strip(), "columns": []})
            table["keys"][-1]["columns"].append(row["column_name"])
        table["primary_key"] = next(
            (key["columns"] for key in table["keys"] if key["type"] == "PK"), None,
        )
        if not table["primary_key"]:
            raise ValueError(f"Cannot deterministically export a table without a primary key: {table['name']}")
        table["checks"] = records(conn.execute("""
            SELECT name,definition,is_disabled,is_not_trusted
            FROM sys.check_constraints WHERE parent_object_id=? ORDER BY name
        """, object_id))
        foreign_rows = records(conn.execute("""
            SELECT fk.name,c.name AS column_name,SCHEMA_NAME(rt.schema_id) AS referenced_schema,
                   rt.name AS referenced_table,rc.name AS referenced_column,
                   fk.delete_referential_action_desc AS on_delete,
                   fk.update_referential_action_desc AS on_update,
                   fk.is_disabled,fk.is_not_trusted
            FROM sys.foreign_keys fk
            JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id=fk.object_id
            JOIN sys.columns c ON c.object_id=fkc.parent_object_id AND c.column_id=fkc.parent_column_id
            JOIN sys.tables rt ON rt.object_id=fkc.referenced_object_id
            JOIN sys.columns rc ON rc.object_id=fkc.referenced_object_id
                 AND rc.column_id=fkc.referenced_column_id
            WHERE fk.parent_object_id=? ORDER BY fk.name,fkc.constraint_column_id
        """, object_id))
        table["foreign_keys"] = []
        for row in foreign_rows:
            if not table["foreign_keys"] or table["foreign_keys"][-1]["name"] != row["name"]:
                table["foreign_keys"].append({
                    key: value for key, value in row.items()
                    if key not in {"column_name", "referenced_column"}
                } | {"columns": [], "referenced_columns": []})
            key = table["foreign_keys"][-1]
            key["columns"].append(row["column_name"])
            key["referenced_columns"].append(row["referenced_column"])
    views = records(conn.execute("""
        SELECT SCHEMA_NAME(v.schema_id) AS schema_name,v.name,m.definition
        FROM sys.views v JOIN sys.sql_modules m ON m.object_id=v.object_id
        WHERE v.is_ms_shipped=0 ORDER BY v.name
    """))
    return {"format_version": FORMAT_VERSION, "tables": tables, "views": views}


def schema_ddl(schema):
    lines = [
        "-- Generated from the live schema. For an empty Azure SQL / SQL Server database.",
        "-- Load base CSVs before adding foreign keys; see README.md for type and NULL rules.",
        "-- Non-constraint performance indexes, permissions and Azure resources are not reproduced.",
        "",
    ]
    foreign_keys = []
    for table in schema["tables"]:
        full_name = f"{quote(table['schema_name'])}.{quote(table['name'])}"
        definitions = []
        for column in table["columns"]:
            definition = f"    {quote(column['name'])} {sql_type(column)}"
            if column["collation_name"]:
                definition += " COLLATE " + column["collation_name"]
            definition += " NULL" if column["is_nullable"] else " NOT NULL"
            if column["default_definition"] is not None:
                definition += " DEFAULT " + column["default_definition"]
            definitions.append(definition)
        for key in table["keys"]:
            kind = "PRIMARY KEY" if key["type"] == "PK" else "UNIQUE"
            columns = ",".join(map(quote, key["columns"]))
            definitions.append(f"    CONSTRAINT {quote(key['name'])} {kind} ({columns})")
        lines.extend([f"CREATE TABLE {full_name} (", ",\n".join(definitions), ");", "GO"])
        for check in table["checks"]:
            trust = "NOCHECK" if check["is_not_trusted"] else "CHECK"
            lines.append(f"ALTER TABLE {full_name} WITH {trust} ADD CONSTRAINT "
                         f"{quote(check['name'])} CHECK {check['definition']};")
            if check["is_disabled"]:
                lines.append(f"ALTER TABLE {full_name} NOCHECK CONSTRAINT {quote(check['name'])};")
        for key in table["foreign_keys"]:
            columns = ",".join(map(quote, key["columns"]))
            referenced = f"{quote(key['referenced_schema'])}.{quote(key['referenced_table'])}"
            ref_columns = ",".join(map(quote, key["referenced_columns"]))
            trust = "NOCHECK" if key["is_not_trusted"] else "CHECK"
            statement = (
                f"ALTER TABLE {full_name} WITH {trust} ADD CONSTRAINT {quote(key['name'])} "
                f"FOREIGN KEY ({columns}) REFERENCES {referenced} ({ref_columns}) "
                f"ON DELETE {key['on_delete'].replace('_', ' ')} "
                f"ON UPDATE {key['on_update'].replace('_', ' ')};"
            )
            foreign_keys.append(statement)
            if key["is_disabled"]:
                foreign_keys.append(
                    f"ALTER TABLE {full_name} NOCHECK CONSTRAINT {quote(key['name'])};",
                )
    lines.extend(["", "-- Apply after base data has been loaded.", *foreign_keys, "GO"])
    for view in schema["views"]:
        if view["definition"] is None:
            raise ValueError(f"View definition unavailable: {view['name']}")
        lines.extend([view["definition"].rstrip(";") + ";", "GO"])
    return "\n".join(lines) + "\n"


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_csv(path, cursor, expected_columns=None):
    columns = [column[0] for column in cursor.description]
    if expected_columns is not None and columns != expected_columns:
        raise ValueError(f"Export query columns differ from schema: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(columns)
        while batch := cursor.fetchmany(1000):
            for row in batch:
                writer.writerow(map(encode_cell, row))
                count += 1
    return {"rows": count, "columns": columns}


def quality_report(conn):
    standings = records(conn.execute(
        "SELECT season_year,category,position,points FROM dbo.championship_standings "
        "ORDER BY season_year,category,position",
    ))
    groups = {}
    for row in standings:
        groups.setdefault((row["season_year"], row["category"]), []).append(
            (row["position"], row["points"]),
        )
    return {
        "not_a_complete_career_archive": True,
        "official_points_not_silently_corrected": True,
        "non_monotonic_official_points": [
            {"season_year": year, "category": category}
            for (year, category), values in groups.items()
            if official_points_inconsistent(values)
        ],
        "archives_without_supplied_standings": records(conn.execute(
            "SELECT season_year,category FROM dbo.historical_imports "
            "WHERE standings_count=0 ORDER BY season_year,category",
        )),
        "finished_race_sessions_without_official_classifications": records(conn.execute("""
            SELECT e.season_year,s.category,COUNT_BIG(*) AS sessions
            FROM dbo.sessions s JOIN dbo.events e ON e.event_id=s.event_id
            WHERE s.session_type='RAC' AND s.status='FINISHED' AND s.source_kind='official-api'
              AND NOT EXISTS (SELECT 1 FROM dbo.classifications c WHERE c.session_id=s.session_id)
            GROUP BY e.season_year,s.category ORDER BY e.season_year,s.category
        """)),
    }


def git_revision():
    result = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        text=True, capture_output=True, check=True,
    )
    return result.stdout.strip()


def build_payload(conn, directory):
    enabled = conn.execute(
        "SELECT snapshot_isolation_state FROM sys.databases WHERE database_id=DB_ID()",
    ).fetchone()[0]
    conn.rollback()
    if enabled != 1:
        raise ValueError("SNAPSHOT isolation is required; the exporter never changes database settings")
    if conn.autocommit:
        raise ValueError("Autocommit must be disabled for a transactionally consistent snapshot")
    # ODBC otherwise starts the SET itself in a transaction at the old isolation level.
    conn.autocommit = True
    try:
        conn.execute("SET TRANSACTION ISOLATION LEVEL SNAPSHOT")
    finally:
        conn.autocommit = False
    # Pin the row-version snapshot with a real application-table read.
    snapshot_time = conn.execute("SELECT SYSUTCDATETIME(),COUNT_BIG(*) FROM dbo.events").fetchone()[0]
    schema = discover_schema(conn)
    csv_metadata = {}
    for table in schema["tables"]:
        name = f"tables/{table['schema_name']}.{table['name']}.csv"
        expressions = [
            f"CONVERT(nvarchar(48),{quote(column['name'])},126) AS {quote(column['name'])}"
            if column["sql_type"] in TEMPORAL_TYPES else quote(column["name"])
            for column in table["columns"]
        ]
        query = (f"SELECT {','.join(expressions)} FROM "
                 f"{quote(table['schema_name'])}.{quote(table['name'])} ORDER BY "
                 + ",".join(map(quote, table["primary_key"])))
        csv_metadata[name] = write_csv(
            directory / name, conn.execute(query), [column["name"] for column in table["columns"]],
        )
        print(f"{name}: {csv_metadata[name]['rows']:,} rows", flush=True)
    csv_metadata["views/results.csv"] = write_csv(directory / "views/results.csv", conn.execute(RESULTS_SQL))
    schema["derived_exports"] = [{
        "path": "views/results.csv", "columns": csv_metadata["views/results.csv"]["columns"],
        "query": RESULTS_SQL.strip(),
        "description": "Convenience export of effective results for all imported session types, not just races.",
    }]
    write_json(directory / "schema.json", schema)
    (directory / "schema.sql").write_text(schema_ddl(schema), encoding="utf-8")
    write_json(directory / "quality.json", quality_report(conn))
    conn.rollback()
    for source, target in [
        (ROOT / "docs" / "data-export.md", "README.md"),
        (ROOT / "docs" / "data-rights.json", "data-rights.json"),
    ]:
        (directory / target).write_bytes(source.read_bytes())
    return {
        "format_version": FORMAT_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_database_time_utc": snapshot_time.isoformat(),
        "isolation": "SNAPSHOT",
        "generator": "export_data.py",
        "generator_sha256": file_hash(Path(__file__)),
        "repository_commit": git_revision(),
        "repository_dirty": bool(subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain"],
            text=True, capture_output=True, check=True,
        ).stdout.strip()),
        "compression": {"format": "tar.xz", "lzma_preset": 9, "extreme": True},
        "csv": {
            "encoding": "UTF-8", "delimiter": ",", "quotechar": '"',
            "lineterminator": "LF", "header": True, "null": r"\N",
            "escape": "Prefix one backslash to every non-NULL cell starting with a backslash.",
            "dates": "ISO 8601; SQL temporal precision retained via server-side conversion",
            "decimals": "Exact decimal strings; do not parse as binary floating point",
            "booleans": "0 or 1",
        },
        "data_license": "NOASSERTION",
        "redistribution_clearance": "not-established",
        "scope": "All allowlisted application base tables, raw provenance, and a derived results CSV; no PDFs.",
        "files": [
            {"path": path.relative_to(directory).as_posix(), "bytes": path.stat().st_size,
             "sha256": file_hash(path), **csv_metadata.get(path.relative_to(directory).as_posix(), {})}
            for path in sorted(directory.rglob("*")) if path.is_file()
        ],
    }


def pack_payload(directory, output):
    with lzma.open(output, "wb", preset=9 | lzma.PRESET_EXTREME) as compressed:
        with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT) as archive:
            for path in sorted(directory.rglob("*")):
                if path.is_file():
                    info = tarfile.TarInfo(path.relative_to(directory).as_posix())
                    info.size = path.stat().st_size
                    info.mode = 0o644
                    with path.open("rb") as stream:
                        archive.addfile(info, stream)


class HashingReader(io.RawIOBase):
    def __init__(self, source):
        self.source = source
        self.digest = hashlib.sha256()
        self.bytes_read = 0

    def readable(self):
        return True

    def readinto(self, buffer):
        data = self.source.read(len(buffer))
        buffer[:len(data)] = data
        self.digest.update(data)
        self.bytes_read += len(data)
        return len(data)


def verify_export(path):
    manifest = None
    observed = {}
    old_limit = csv.field_size_limit()
    csv.field_size_limit(256 * 1024 * 1024)
    try:
        with tarfile.open(path, "r|xz") as archive:
            for member in archive:
                if (not member.isfile() or member.name in observed or member.name.startswith("/")
                        or any(part in {"", ".", ".."} for part in member.name.split("/"))
                        or "\\" in member.name):
                    raise ValueError(f"Unsafe or duplicate archive member: {member.name}")
                source = archive.extractfile(member)
                reader = HashingReader(source)
                result = {}
                if member.name.endswith(".csv"):
                    with io.TextIOWrapper(io.BufferedReader(reader), encoding="utf-8", newline="") as text:
                        rows = csv.reader(text, strict=True)
                        header = next(rows)
                        count = 0
                        for row in rows:
                            if len(row) != len(header):
                                raise ValueError(f"Malformed CSV row in {member.name}")
                            count += 1
                        result.update(columns=header, rows=count)
                elif member.name == "manifest.json":
                    with io.BufferedReader(reader) as stream:
                        manifest = json.load(stream)
                else:
                    with io.BufferedReader(reader) as stream:
                        while stream.read(1024 * 1024):
                            pass
                observed[member.name] = {
                    "sha256": reader.digest.hexdigest(), "bytes": reader.bytes_read, **result,
                }
    finally:
        csv.field_size_limit(old_limit)
    if manifest is None or manifest.get("format_version") != FORMAT_VERSION:
        raise ValueError("Unsupported or missing export manifest")
    expected = manifest["files"]
    if len({item["path"] for item in expected}) != len(expected):
        raise ValueError("Duplicate manifest paths")
    if set(observed) != {"manifest.json"} | {item["path"] for item in expected}:
        raise ValueError("Archive members differ from manifest")
    for item in expected:
        if observed[item["path"]] != {key: value for key, value in item.items() if key != "path"}:
            raise ValueError(f"Checksum, byte count, columns or row count mismatch: {item['path']}")
    return manifest


def export_database(conn, output):
    output = Path(output)
    if not output.name.endswith(".tar.xz"):
        raise ValueError("Use a .tar.xz output filename")
    output.parent.mkdir(parents=True, exist_ok=True)
    sidecar = output.with_name(output.name + ".sha256")
    public_manifest = output.with_name(output.name.removesuffix(".tar.xz") + ".manifest.json")
    if any(path.exists() for path in (output, sidecar, public_manifest)):
        raise FileExistsError("Export or sidecar exists; choose a new snapshot filename")
    with tempfile.TemporaryDirectory(prefix=".export-", dir=output.parent) as temporary:
        directory = Path(temporary)
        payload = directory / "payload"
        payload.mkdir()
        try:
            manifest = build_payload(conn, payload)
        finally:
            conn.rollback()
        write_json(payload / "manifest.json", manifest)
        compressed = directory / output.name
        pack_payload(payload, compressed)
        if verify_export(compressed) != manifest:
            raise ValueError("Verified manifest differs from the exported snapshot")
        digest = file_hash(compressed)
        staged_sidecar = directory / sidecar.name
        staged_sidecar.write_text(f"{digest}  {output.name}\n", encoding="ascii")
        staged_manifest = directory / public_manifest.name
        write_json(staged_manifest, {
            **manifest, "archive": {"name": output.name, "bytes": compressed.stat().st_size, "sha256": digest},
        })
        published = []
        try:
            for source, target in [
                (compressed, output), (staged_sidecar, sidecar), (staged_manifest, public_manifest),
            ]:
                # Same-volume hard links publish complete files atomically, without overwriting.
                os.link(source, target)
                published.append(target)
        except BaseException:
            for path in reversed(published):
                path.unlink()
            raise
    return public_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path, help="Create a new local .tar.xz snapshot; never overwrites")
    mode.add_argument("--verify", type=Path, help="Verify an existing archive offline, without extracting")
    args = parser.parse_args()
    if args.verify:
        manifest = verify_export(args.verify)
        print(f"Verified {len(manifest['files'])} payload files, including all CSV hashes and row counts.")
        return
    from sql_connection import connect_to_sql

    conn = connect_to_sql()
    try:
        manifest_path = export_database(conn, args.output)
    finally:
        conn.close()
    print(f"Verified compressed export: {args.output}\nPublic metadata: {manifest_path}", flush=True)


if __name__ == "__main__":
    main()
