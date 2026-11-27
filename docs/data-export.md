# Portable data export

`export_data.py` creates a **local, compressed preservation snapshot** and an
analysis-ready CSV. It does not publish a dataset, change SQL data, create cloud
resources, or assign a blanket open-data license. See [data-rights.json](data-rights.json).

## Reproduce an export

Use the repository's Python dependencies and ODBC Driver 18 for SQL Server.
Authenticate with an Entra account that can read the application tables and view
schema definitions. The normal passwordless `sql_connection.py` configuration
applies: `MOTOGP_SQL_SERVER`, `MOTOGP_SQL_DATABASE`, and `MOTOGP_SQL_AUTH` (normally
`azure-cli` locally). Never place credentials or tokens in the output.

```powershell
python -m pip install -r requirements.txt
az login
python export_data.py --output exports\motogp-data-2026-11-27.tar.xz
python export_data.py --verify exports\motogp-data-2026-11-27.tar.xz
Get-FileHash exports\motogp-data-2026-11-27.tar.xz -Algorithm SHA256
```

Choose a new filename for each snapshot: existing outputs and metadata are never
overwritten. Output consists of the archive, its `.tar.xz.sha256` checksum, and a
small `.manifest.json` sidecar. The archive is deliberately ignored by Git;
the sidecar may be versioned to record counts, provenance and integrity.
Verification is offline and does not extract files.

SQL SNAPSHOT isolation must already be enabled. One read transaction pins all
base tables, the convenience results and quality metadata to the same database
snapshot; concurrent writers may continue without a table-locking backup.
The exporter refuses to silently fall back to inconsistent per-table reads.
Its table allowlist must be reviewed when the application schema changes,
preventing accidental export of an unrelated newly added table. Unsupported
types, computed or identity columns also fail explicitly rather than losing data.

The read transaction closes before compression. Python's standard-library XZ
encoder uses preset 9 plus extreme mode and a shared compression stream for all
files, reducing repeated UUIDs and JSON significantly. Allow several minutes,
roughly 700 MiB of compression memory, and temporary disk space for the
uncompressed CSVs plus compressed output. Temporary files are cleaned on normal
success or failure. No third-party compression package is required.

If SQL access is blocked by its firewall, obtain approved narrow access first;
the exporter does not change firewall rules. A task-created temporary single-IP
rule must be removed after use; never replace an existing user's rule.

## Contents and schema

| Path | Meaning |
|---|---|
| `tables/dbo.*.csv` | All 14 current application tables, including raw provenance and migrations; older pre-backfill databases have 13 |
| `views/results.csv` | Convenient denormalized results for **all imported session types**, with names, context, stable IDs and effective-source labels |
| `schema.json` | Live column order, SQL types/precision/scale, nullability, collation/defaults, primary/unique/foreign keys, check constraints and view definitions |
| `schema.sql` | Live logical SQL Server DDL for an empty database; base tables first, foreign keys and views afterwards |
| `quality.json` | Source-standing gaps, empty finished race classifications and non-monotonic official point tables |
| `manifest.json` | Format version, snapshot time, generator commit/hash, encoding rules, file sizes, SHA-256 hashes and CSV row counts |
| `data-rights.json` | Source attribution, rights status and redistribution decision |
| `README.md` | This guide |

This is a portable logical data backup, **not** a BACPAC or physical disaster
recovery backup. SQL permissions, firewall rules, Azure resources and
non-constraint performance indexes are not recreated. Existing PDF files,
images and redundant HTTP caches are not bundled; JSON source snapshots stored
in the database are included. Views can be regenerated from their definitions.
`views/results.csv` is redundant convenience data, not another authoritative table.

### Table dictionary

| Table | Grain and interpretation |
|---|---|
| `events` | One shared Grand Prix weekend; season, circuit, country and dates |
| `sessions` | One category/session at a weekend; source label, type, weather and status |
| `riders` | Official rider ID and profile; profile number is not necessarily the session number |
| `teams` | Team identity **and season**; names and constructors can change |
| `team_aliases` | Stored display-name normalization; original team values remain in `teams` |
| `classifications` | One official session/rider result; includes session-specific rider number and constructor |
| `laps` | One session/rider/lap; available elapsed time, sectors, speed, pit/run and tyre fields |
| `championship_standings` | Independent source-provided season/category/rider standings, final flag and original JSON |
| `historical_imports` | Verified season/class source payload, fingerprint, counts and import timestamp |
| `standings_imports` | Independent standings-only backfill: official season/category/calendar/document evidence, full payload, fingerprint, finality and row count; does not claim race-archive coverage |
| `external_sources` | Supplemental source URL, declared license and pinned content hash |
| `external_candidates` | Every candidate's raw facts, mapping, evidence and accepted/corroborated/held decision |
| `external_classifications` | Accepted supplemental fields only; not replacements for the official base table |
| `schema_migrations` | Applied additive database migration versions and timestamps |

SQL column names, data types and relationships are authoritative in
`schema.json`; SQL type names are not pandas dtype names. CSV headers match their
schema column order. Base tables are ordered by their complete primary key.
Temporal values are converted on the SQL server, retaining all fractional
digits (including SQL `datetime2(7)`, which Python datetime alone cannot retain).
SQL dates are ISO 8601; a timestamp without an offset stays without an offset.
Do not assume every session timestamp is UTC. Manifest snapshot timestamps
explicitly refer to database UTC time.

## CSV contract (format version 1)

- UTF-8 without a BOM, comma-delimited, header row, double-quoted when needed,
  embedded quotes doubled, LF record terminators. Quoted cells may span lines.
- SQL NULL is the literal cell `\N`. Empty strings remain empty strings.
- Every **non-NULL** value starting with a backslash has one extra leading
  backslash. Decode `\N` as NULL first, then remove exactly one backslash from
  cells starting with two. Other backslashes are unchanged. This preserves even
  a literal `\N`, JSON, multiline text and Windows paths without ambiguity.
- Boolean values are `0`/`1`. Integers and exact decimals are locale-independent
  strings; retain decimals as strings or `decimal.Decimal` to avoid precision loss.
  Floating point uses Python's round-trip representation.
- Raw timing strings remain strings. In particular, `classifications.time_ms`
  is a **legacy raw timing field, not a numeric millisecond value**.
  Lap/sector/time-gap strings must not be blindly converted to decimal seconds.
- Source category labels (including trademark suffixes) and UUIDs are preserved.
  The app groups MotoGP/500cc, Moto2/250cc and Moto3/125cc into three lineages;
  350cc, 50cc and 80cc remain independent championships.

## Read without SQL or extracting the archive

This standard-library example reads the useful flat results file. Substitute a
base table member to consume normalized data.

```python
import csv
import io
import tarfile

def decode(value):
    if value == "\\N":
        return None
    return value[1:] if value.startswith("\\\\") else value

csv.field_size_limit(256 * 1024 * 1024)  # Raw source payload cells can be large.
with tarfile.open("exports/motogp-data-2026-11-27.tar.xz", "r:xz") as archive:
    with archive.extractfile("views/results.csv") as binary:
        with io.TextIOWrapper(binary, encoding="utf-8", newline="") as text:
            for raw in csv.DictReader(text):
                row = {key: decode(value) for key, value in raw.items()}
                # Filter session_type == "RAC" for race results, or "SPR" for sprints.
                print(row["season_year"], row["rider"], row["points"])
                break
```

For pandas, use `dtype=str, keep_default_na=False, na_filter=False` when loading
the CSV, then apply the same decoder before explicit schema-driven type
conversions. This prevents legitimate strings such as country code `NA` or
empty text from being interpreted as missing data. Treat text columns as text
when opening in a spreadsheet: formula-like source strings are preserved,
not rewritten for spreadsheet execution.

## Integrity and restoration

The producer validates every member's SHA-256 hash, size, CSV columns and logical
row count after compression, before publishing the local archive. Verification
rejects duplicate or unsafe archive paths and never extracts untrusted paths.
Compare the outer SHA-256 with a trusted `.sha256` sidecar to detect changes to
the manifest itself; internal checksums alone are not a digital signature.
The outer `.manifest.json` additionally records the compressed size/hash.

To restore data into an empty SQL Server database:

1. Verify the archive and trusted outer checksum. Review `schema.json`.
2. Execute the base-table section of `schema.sql`; do not add foreign keys yet.
3. Decode the base CSVs using the contract above and insert with parameterized,
   type-aware SQL. Preserve decimal precision, NULL versus empty text and full
   temporal precision. Do not load convenience view data as official base rows.
4. Add foreign keys, then the supplied views; validate keys, counts and values.
   Views may need dependency ordering. Reapply repository performance indexes
   separately if required.

This repository does not automatically restore or overwrite an existing
database. The export can also seed SQLite, DuckDB or Parquet using explicit
schema mappings; no vendor database is required for analysis.

## Scientific limitations and redistribution

Available coverage is not complete historical coverage. Do not derive final
championships by summing incomplete race results or combine scores across classes.
`is_final=false` must not be presented as an official final title table.
Source-supplied ranks and points may disagree with each other; preserve the
supplied values and consult `quality.json`, rather than computing misleading
winning margins. An absent standings table is not proof that no title existed.
A provisional rank-one table is not by itself a confirmed title, and a clinched
title does not make all season standings final. Career title counts require
independently evidenced coverage and confirmation. The 2026 standings remain
provisional while Valencia (2026-11-29) is pending, even though Marc's title
has been confirmed separately. `quality.json` includes the standings-only
backfill inventory as well as race-archive source gaps.

Historical placeholder zeroes and all-zero legacy 125cc/250cc race tables with
a winner are represented as NULL where the importer has established unavailable
data. Genuine zero-point scores and unawarded modern race parts stay zero.
Missing or ambiguous sector cells are not guessed.

The effective results view uses official positions, timing and non-NULL points
first; accepted external facts can fill permitted gaps. Held candidates are
**not** accepted results. Keep their decision/evidence columns when auditing.
The export is not endorsed by MotoGP or its rights holders.

**Redistribution decision: no blanket dataset license is granted.** Public access
does not establish redistribution permission. The [MotoGP legal notice](https://www.motogp.com/en/legal-notice)
(reviewed 2026-11-27, notably clauses 1 and 3) restricts copying and transmission;
its precise application to factual records and API/database rights requires
review before publishing a bulk export. The Kaggle publisher's CC0 declaration
is retained as a separate upstream claim, not extended to MotoGP data.
This notice neither claims ownership of unprotectable facts nor overrides valid
upstream permissions or statutory exceptions. No new license is assigned to
existing repository code or documentation.

Accordingly, keep `.tar.xz` snapshots out of Git and public release assets until
rights are established. Version the exporter and metadata now; if redistribution
is later cleared, choose a compatible data license and an appropriate release
location without erasing upstream attribution or provenance.
