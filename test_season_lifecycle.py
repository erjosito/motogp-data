from copy import deepcopy
import argparse
from datetime import datetime
from decimal import Decimal
import json
import requests
import unittest
from unittest.mock import MagicMock, patch

import season_lifecycle as lifecycle
from test_import_standings import fixture


def standing_rows(data):
    rows = []
    for entry in data["standings"]["classification"]:
        constructor = entry.get("constructor") or {}
        rows.append((entry["rider"]["id"], entry["position"], Decimal(str(entry["points"])),
                     constructor.get("id"), constructor.get("name"), data["source_url"],
                     json.dumps(entry)))
    return rows


class SeasonLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.data = fixture(2026)
        self.rows = standing_rows(self.data)
        self.standings_hash = lifecycle.standings_digest(self.rows)
        self.import_hash = lifecycle.snapshot_digest(self.data, "standings")
        self.review_hash = lifecycle.review_digest("standings", self.standings_hash, self.import_hash, None)
        self.conn = MagicMock()
        self.conn.execute.return_value.fetchone.return_value = (
            self.standings_hash, "standings", self.import_hash, None,
            "https://www.motogp.com/evidence", "a" * 64, "2026 MotoGP final",
            datetime(2026, 12, 1), None,
        )
        patches = [
            patch.object(lifecycle, "_installed", return_value=True),
            patch.object(lifecycle, "_import_payload", side_effect=self.payload),
            patch.object(lifecycle, "_standing_rows", side_effect=lambda *a, **k: self.rows),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def payload(self, conn, year, category, kind, lock=False):
        return self.data if kind == "standings" else None

    def test_confirmed_status_and_absent_schema(self):
        result = lifecycle.read_season_status(self.conn, 2026, "MotoGP™")
        self.assertEqual(result["status"], "official_final")
        self.assertEqual(result["evidence"]["standings_sha256"], self.standings_hash)
        self.assertEqual(result["evidence"]["confirmed_at"], "2026-12-01T00:00:00Z")
        with patch.object(lifecycle, "_installed", return_value=False):
            self.assertEqual(lifecycle.read_season_status(self.conn, 2026, "MotoGP™"),
                             {"status": "unknown", "evidence": None})

    def test_source_and_standings_changes_are_unknown(self):
        self.data["events"][0]["status"] = "CANCELLED"
        self.assertEqual(lifecycle.read_season_status(self.conn, 2026, "MotoGP™")["status"], "unknown")
        self.data = fixture(2026)
        self.rows[0] = (*self.rows[0][:2], Decimal("300"), *self.rows[0][3:])
        self.assertEqual(lifecycle.read_season_status(self.conn, 2026, "MotoGP™")["status"], "unknown")

    def test_new_other_import_invalidates_even_if_standings_unchanged(self):
        other = {"year": 2026, "category": "MotoGP™", "season_id": "season",
                 "events": [], "skipped_events": [], "standings_url": "url",
                 "standings": {}, "standings_available": True}
        with patch.object(lifecycle, "_other_import_hash",
                          return_value=lifecycle.snapshot_digest(other, "historical")):
            self.assertEqual(lifecycle.read_season_status(self.conn, 2026, "MotoGP™")["status"], "unknown")

    def test_confirmation_requires_reviewed_exact_snapshot_and_evidence(self):
        with patch.object(lifecycle, "evidence_digest", return_value="b" * 64):
            lifecycle.confirm_final(self.conn, 2026, "MotoGP™", "standings",
                                    self.standings_hash, self.review_hash, "https://www.motogp.com/evidence",
                                    "b" * 64, "Reviewed 2026 MotoGP final standings")
            merge = self.conn.execute.call_args
            self.assertIn("MERGE dbo.season_lifecycle", merge.args[0])
            self.assertIn("b" * 64, merge.args)
            self.conn.execute.reset_mock()
            with self.assertRaisesRegex(ValueError, "hash differs"):
                lifecycle.confirm_final(self.conn, 2026, "MotoGP™", "standings",
                                        "0" * 64, self.review_hash, "https://www.motogp.com/evidence",
                                        "b" * 64, "Reviewed 2026 MotoGP final standings")
            self.conn.execute.assert_not_called()
            self.rows[0] = (*self.rows[0][:2], Decimal("300"), *self.rows[0][3:])
            with self.assertRaisesRegex(ValueError, "differ"):
                lifecycle.confirm_final(self.conn, 2026, "MotoGP™", "standings",
                                        self.standings_hash, self.review_hash, "https://www.motogp.com/evidence",
                                        "b" * 64, "Reviewed 2026 MotoGP final standings")

    def test_unrelated_or_empty_snapshot_cannot_be_confirmed(self):
        with patch.object(lifecycle, "evidence_digest", return_value="b" * 64):
            with self.assertRaisesRegex(ValueError, "season and class"):
                lifecycle.confirm_final(self.conn, 2025, "MotoGP™", "standings",
                                        self.standings_hash, self.review_hash, "https://www.motogp.com/evidence",
                                        "b" * 64, "Reviewed 2025 MotoGP final standings")
            self.data["standings"]["classification"] = []
            with self.assertRaisesRegex(ValueError, "empty or incomplete"):
                lifecycle.confirm_final(self.conn, 2026, "MotoGP™", "standings",
                                        self.standings_hash, self.review_hash, "https://www.motogp.com/evidence",
                                        "b" * 64, "Reviewed 2026 MotoGP final standings")

    def test_confirmation_rejects_changed_evidence_and_snapshots(self):
        with patch.object(lifecycle, "evidence_digest", return_value="b" * 64):
            with self.assertRaisesRegex(ValueError, "evidence differs"):
                lifecycle.confirm_final(self.conn, 2026, "MotoGP™", "standings",
                                        self.standings_hash, self.review_hash,
                                        "https://www.motogp.com/evidence", "c" * 64,
                                        "Reviewed 2026 MotoGP final standings")
            self.data["events"][0]["status"] = "CANCELLED"
            with self.assertRaisesRegex(ValueError, "snapshots differ"):
                lifecycle.confirm_final(self.conn, 2026, "MotoGP™", "standings",
                                        self.standings_hash, self.review_hash,
                                        "https://www.motogp.com/evidence", "b" * 64,
                                        "Reviewed 2026 MotoGP final standings")
            self.assertFalse(any("MERGE dbo.season_lifecycle" in str(call)
                                 for call in self.conn.execute.call_args_list))

    def test_historical_confirmation_checks_exact_source(self):
        entry = self.data["standings"]["classification"][0]
        data = {"year": 1966, "category": "500cc", "season_id": "season",
                "events": [], "skipped_events": [], "standings_available": True,
                "standings": {"classification": [entry]},
                "standings_url": "https://api.motogp.pulselive.com/motogp/v1/results/standings?"
                                 "seasonUuid=season&categoryUuid=premier"}
        rows = [(entry["rider"]["id"], entry["position"], Decimal(str(entry["points"])),
                 (entry.get("constructor") or {}).get("id"),
                 (entry.get("constructor") or {}).get("name"), data["standings_url"], json.dumps(entry))]
        standings_hash = lifecycle.standings_digest(rows)
        review_hash = lifecycle.review_digest("historical", standings_hash,
                                               lifecycle.snapshot_digest(data, "historical"), None)
        with patch.object(lifecycle, "_import_payload",
                          side_effect=lambda conn, year, category, kind, lock=False:
                          data if kind == "historical" else None), \
                patch.object(lifecycle, "_standing_rows", return_value=rows), \
                patch.object(lifecycle, "evidence_digest", return_value="b" * 64):
            lifecycle.confirm_final(self.conn, 1966, "500cc", "historical", standings_hash,
                                    review_hash, "https://www.fim-moto.com/evidence",
                                    "b" * 64, "Reviewed 1966 500cc final standings")
            data["standings_url"] += "&seasonUuid=another"
            with self.assertRaisesRegex(ValueError, "source identity"):
                lifecycle.confirm_final(self.conn, 1966, "500cc", "historical", standings_hash,
                                        review_hash, "https://www.fim-moto.com/evidence",
                                        "b" * 64, "Reviewed 1966 500cc final standings")

    def test_confirmation_arguments_require_all_review_inputs(self):
        parser = argparse.ArgumentParser()
        lifecycle.add_import_arguments(parser)
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--refresh", action="store_true")
        parser.add_argument("--years", nargs="+", type=int)
        args = parser.parse_args(["--confirm-final", "--apply", "--refresh", "--years", "2026"])
        with patch.object(parser, "error", side_effect=ValueError("invalid arguments")):
            with self.assertRaisesRegex(ValueError, "invalid arguments"):
                lifecycle.validate_import_arguments(parser, args)
            args.confirm_final = False
            args.final_review_note = "2026 MotoGP"
            with self.assertRaisesRegex(ValueError, "invalid arguments"):
                lifecycle.validate_import_arguments(parser, args)

    def test_changed_import_invalidates_and_unchanged_does_not(self):
        self.conn.execute.return_value.fetchone.return_value = (
            self.standings_hash, "standings", self.import_hash, None,
        )
        lifecycle.invalidate_changed_confirmation(self.conn, 2026, "MotoGP™")
        self.assertEqual(self.conn.execute.call_count, 1)
        self.data["events"][0]["date_end"] = "2026-11-25"
        lifecycle.invalidate_changed_confirmation(self.conn, 2026, "MotoGP™")
        self.assertIn("invalidated_at=SYSUTCDATETIME()", self.conn.execute.call_args.args[0])

    def test_invalidated_confirmation_does_not_revive_when_source_reverts(self):
        self.data["events"][0]["status"] = "CANCELLED"
        self.conn.execute.return_value.fetchone.return_value = (
            self.standings_hash, "standings", self.import_hash, None,
        )
        lifecycle.invalidate_changed_confirmation(self.conn, 2026, "MotoGP™")
        self.assertIn("invalidated_at=SYSUTCDATETIME()", self.conn.execute.call_args.args[0])
        self.data = fixture(2026)
        self.conn.execute.return_value.fetchone.return_value = (
            self.standings_hash, "standings", self.import_hash, None,
            "https://www.motogp.com/evidence", "a" * 64, "2026 MotoGP final",
            datetime(2026, 12, 1), datetime(2026, 12, 2),
        )
        self.assertEqual(lifecycle.read_season_status(self.conn, 2026, "MotoGP™"),
                         {"status": "unknown", "evidence": None})

    def test_checked_time_and_source_row_order_do_not_change_hash(self):
        newer = deepcopy(self.data)
        newer["checked_on"] = "2026-12-01"
        newer["fetched_at"] = "2026-12-01T00:00:00Z"
        self.assertEqual(lifecycle.snapshot_digest(newer, "standings"), self.import_hash)
        self.assertEqual(lifecycle.standings_digest(list(reversed(self.rows))), self.standings_hash)

    def test_unfinalization_requires_existing_record_and_reason(self):
        self.conn.execute.return_value.rowcount = 1
        lifecycle.unfinalize(self.conn, 2026, "MotoGP™", "Final result corrected")
        self.assertIn("UPDATE dbo.season_lifecycle", self.conn.execute.call_args.args[0])
        self.conn.execute.return_value.rowcount = 0
        with self.assertRaisesRegex(ValueError, "No active confirmation"):
            lifecycle.unfinalize(self.conn, 2026, "MotoGP™", "Correction")
        with self.assertRaisesRegex(ValueError, "reason"):
            lifecycle.unfinalize(self.conn, 2026, "MotoGP™", " ")

    def test_evidence_rejects_unofficial_hosts_and_redirects(self):
        with self.assertRaisesRegex(ValueError, "MotoGP or FIM"):
            lifecycle.evidence_digest("https://evil.example/motogp.com/final")
        response = MagicMock(is_redirect=True, content=b"")
        with patch.object(requests, "get", return_value=response):
            with self.assertRaisesRegex(ValueError, "directly"):
                lifecycle.evidence_digest("https://www.motogp.com/final")


if __name__ == "__main__":
    unittest.main()
