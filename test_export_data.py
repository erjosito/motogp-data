import csv
from decimal import Decimal
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import export_data as export


def fast_pack(directory, output):
    with tarfile.open(output, "w:xz", preset=0) as archive:
        for path in sorted(directory.rglob("*")):
            if path.is_file():
                archive.add(path, arcname=path.relative_to(directory).as_posix())


def payload(directory):
    cursor = MagicMock()
    cursor.description = [("id",), ("value",)]
    cursor.fetchmany.side_effect = [
        [(1, None), (2, ""), (3, r"\N"), (4, "quoted,\"line\nnext"),
         (5, "\u00c1ngel Nieto"), (6, "\\"), (7, "x" * 150000),
         (8, Decimal("1234567.890")), (9, "2026-11-27T18:11:12.1234567")],
        [],
    ]
    name = "tables/dbo.sample.csv"
    metadata = export.write_csv(directory / name, cursor)
    return {
        "format_version": export.FORMAT_VERSION,
        "files": [{
            "path": name, "bytes": (directory / name).stat().st_size,
            "sha256": export.file_hash(directory / name), **metadata,
        }],
    }


class ExportTests(unittest.TestCase):
    def test_cells_round_trip_null_empty_unicode_backslashes_and_exact_decimals(self):
        values = [None, "", r"\N", "\\", r"\\N", r"C:\timing\data", "\u00c1ngel",
                  'comma,"quote"\nnewline', Decimal("210.500"), False, True]
        encoded = [export.encode_cell(value) for value in values]
        decoded = [export.decode_cell(value) for value in encoded]
        self.assertEqual(decoded, [
            None, "", r"\N", "\\", r"\\N", r"C:\timing\data", "\u00c1ngel",
            'comma,"quote"\nnewline', "210.500", "0", "1",
        ])

    def test_compressed_csv_verifies_large_multiline_and_precise_temporal_cells(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            data = directory / "payload"
            data.mkdir()
            manifest = payload(data)
            export.write_json(data / "manifest.json", manifest)
            output = directory / "sample.tar.xz"
            export.pack_payload(data, output)
            self.assertEqual(export.verify_export(output), manifest)
            with tarfile.open(output, "r:xz") as archive:
                text = io.TextIOWrapper(archive.extractfile("tables/dbo.sample.csv"), encoding="utf-8")
                old_limit = csv.field_size_limit(256 * 1024 * 1024)
                try:
                    rows = list(csv.DictReader(text))
                finally:
                    csv.field_size_limit(old_limit)
                self.assertEqual(rows[-1]["value"], "2026-11-27T18:11:12.1234567")
                self.assertEqual(manifest["files"][0]["rows"], 9)

    def test_corrupted_hash_or_logical_row_count_is_rejected(self):
        for field, value in [("sha256", "0" * 64), ("rows", 123)]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                data = directory / "payload"
                data.mkdir()
                manifest = payload(data)
                manifest["files"][0][field] = value
                export.write_json(data / "manifest.json", manifest)
                output = directory / "sample.tar.xz"
                fast_pack(data, output)
                with self.assertRaisesRegex(ValueError, "mismatch"):
                    export.verify_export(output)

    def test_unsafe_duplicate_and_extra_members_are_rejected_without_extraction(self):
        for names in [("../escape.csv",), ("same", "same"), ("/absolute",)]:
            with self.subTest(names=names), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "sample.tar.xz"
                with tarfile.open(output, "w:xz", preset=0) as archive:
                    for name in names:
                        info = tarfile.TarInfo(name)
                        info.size = 1
                        archive.addfile(info, io.BytesIO(b"x"))
                with self.assertRaisesRegex(ValueError, "Unsafe or duplicate"):
                    export.verify_export(output)
                self.assertEqual(list(Path(temporary).iterdir()), [output])

    def test_schema_drift_refuses_unrelated_tables(self):
        conn = MagicMock()
        cursor = conn.execute.return_value
        cursor.description = [("object_id",), ("schema_name",), ("name",)]
        cursor.fetchall.return_value = [(1, "dbo", "credentials")]
        with self.assertRaisesRegex(ValueError, "allowlist"):
            export.discover_schema(conn)

    def test_requires_existing_snapshot_isolation_and_no_autocommit(self):
        with tempfile.TemporaryDirectory() as temporary:
            for enabled, autocommit in [(0, False), (1, True)]:
                with self.subTest(enabled=enabled, autocommit=autocommit):
                    conn = MagicMock()
                    conn.autocommit = autocommit
                    conn.execute.return_value.fetchone.return_value = (enabled,)
                    with self.assertRaisesRegex(ValueError, "SNAPSHOT|Autocommit"):
                        export.build_payload(conn, Path(temporary))
                    self.assertFalse(any(
                        "SET TRANSACTION" in call.args[0] for call in conn.execute.call_args_list
                    ))

    def test_export_is_verified_before_publication_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "sample.tar.xz"
            conn = MagicMock()
            with patch.object(export, "build_payload", side_effect=lambda c, d: payload(d)), \
                    patch.object(export, "pack_payload", side_effect=fast_pack):
                manifest_path = export.export_database(conn, output)
                actual = json.loads(manifest_path.read_text(encoding="utf-8"))
                self.assertEqual(actual["archive"]["sha256"], export.file_hash(output))
                self.assertEqual(export.verify_export(output)["files"], actual["files"])
                with self.assertRaises(FileExistsError):
                    export.export_database(conn, output)
            self.assertFalse(any(path.name.startswith(".export-") for path in output.parent.iterdir()))
            conn.rollback.assert_called_once()

    def test_failed_verification_never_publishes_an_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "sample.tar.xz"
            with patch.object(export, "build_payload", side_effect=lambda c, d: payload(d)), \
                    patch.object(export, "pack_payload", side_effect=fast_pack), \
                    patch.object(export, "verify_export", side_effect=ValueError("injected checksum failure")):
                with self.assertRaisesRegex(ValueError, "checksum failure"):
                    export.export_database(MagicMock(), output)
            self.assertEqual(list(output.parent.iterdir()), [])

    def test_failed_publication_removes_only_its_own_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "sample.tar.xz"
            unrelated = output.parent / "unrelated"
            unrelated.write_text("keep", encoding="utf-8")
            real_link = export.os.link

            def link(source, target):
                if str(target).endswith(".sha256"):
                    raise OSError("injected publication failure")
                real_link(source, target)

            with patch.object(export, "build_payload", side_effect=lambda c, d: payload(d)), \
                    patch.object(export, "pack_payload", side_effect=fast_pack), \
                    patch.object(export.os, "link", side_effect=link):
                with self.assertRaisesRegex(OSError, "publication failure"):
                    export.export_database(MagicMock(), output)
            self.assertEqual(list(output.parent.iterdir()), [unrelated])
            self.assertEqual(unrelated.read_text(encoding="utf-8"), "keep")

    def test_ddl_preserves_unicode_lengths_decimal_precision_keys_and_checks(self):
        schema = {
            "tables": [{
                "schema_name": "dbo", "name": "sample",
                "columns": [
                    {"name": "id", "sql_type": "nvarchar", "max_length": 100,
                     "is_nullable": False, "collation_name": "Latin1_General_CI_AS",
                     "default_definition": None},
                    {"name": "points", "sql_type": "decimal", "precision": 10, "scale": 3,
                     "is_nullable": True, "collation_name": None, "default_definition": "((0))"},
                    {"name": "fetched", "sql_type": "datetime2", "scale": 7,
                     "is_nullable": False, "collation_name": None, "default_definition": None},
                ],
                "keys": [{"name": "pk", "type": "PK", "columns": ["id"]}],
                "checks": [{"name": "positive", "definition": "([points]>=(0))",
                            "is_disabled": False, "is_not_trusted": False}],
                "foreign_keys": [{
                    "name": "fk", "columns": ["id"], "referenced_schema": "dbo",
                    "referenced_table": "riders", "referenced_columns": ["rider_id"],
                    "on_delete": "NO_ACTION", "on_update": "CASCADE",
                    "is_disabled": False, "is_not_trusted": False,
                }],
            }],
            "views": [],
        }
        ddl = export.schema_ddl(schema)
        self.assertIn("[id] nvarchar(50) COLLATE Latin1_General_CI_AS NOT NULL", ddl)
        self.assertIn("decimal(10,3) NULL DEFAULT ((0))", ddl)
        self.assertIn("datetime2(7) NOT NULL", ddl)
        self.assertIn("CHECK ([points]>=(0))", ddl)
        self.assertIn("REFERENCES [dbo].[riders] ([rider_id]) ON DELETE NO ACTION ON UPDATE CASCADE", ddl)
        self.assertEqual(export.quote("odd]name"), "[odd]]name]")


if __name__ == "__main__":
    unittest.main()
