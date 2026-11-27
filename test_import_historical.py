import argparse
import contextlib
from copy import deepcopy
from decimal import Decimal
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import import_historical as historical
import load_to_sql as loader


def snapshot():
    rider = {"id": "ago", "full_name": "Giacomo Agostini", "number": None}
    constructor = {"id": "mv", "name": "MV Agusta"}
    return {
        "version": 1, "year": 1966, "category": "500cc",
        "events": [{
            "event": {"id": "ned", "name": "Dutch TT", "short_name": "NED"},
            "sessions": [{
                "session": {"id": "race", "type": "RAC", "status": "FINISHED"},
                "classification": [{
                    "rider": rider, "position": 1, "constructor": constructor,
                    "team": None, "points": 0, "total_laps": 0, "top_speed": 0,
                }],
            }],
        }],
        "standings": {"classification": [{
            "rider": rider, "position": 1, "points": 36, "constructor": constructor,
        }]},
        "standings_url": "https://api.motogp.pulselive.com/motogp/v1/results/standings",
    }


class HistoricalImportTests(unittest.TestCase):
    def test_historical_unknowns_and_teamless_constructor_are_preserved(self):
        entry = snapshot()["events"][0]["sessions"][0]["classification"][0]
        original = deepcopy(entry)
        params = loader.classification_parameters("race", entry, 1966)
        self.assertIsNone(params[4])
        self.assertIsNone(params[11])
        self.assertIsNone(params[12])
        self.assertEqual(params[14:16], ("mv", "MV Agusta"))
        self.assertEqual(entry, original)

    def test_modern_zero_points_and_zero_laps_are_not_reinterpreted(self):
        entry = snapshot()["events"][0]["sessions"][0]["classification"][0]
        params = loader.classification_parameters("race", entry, 2026)
        self.assertEqual(params[4], 0)
        self.assertEqual(params[12], 0)

    def test_fetch_excludes_other_classes_and_retains_independent_standings(self):
        data = snapshot()

        def api(endpoint, params):
            if endpoint == "events":
                return [
                    {"id": "ned", "short_name": "NED", "date_end": "1966-06-25"},
                    {"id": "other", "short_name": "OTHER", "date_end": "1966-07-01"},
                ]
            if endpoint == "categories":
                return ([{"id": "premier", "name": "500cc"}] if params["eventUuid"] == "ned"
                        else [{"id": "smaller", "name": "350cc"}])
            if endpoint == "standings":
                return data["standings"]
            raise AssertionError(endpoint)

        race = data["events"][0]["sessions"][0]
        with patch.object(loader, "get_season_id", return_value=("season", 1966)), \
                patch.object(loader, "api_get", side_effect=api), \
                patch.object(loader, "get_all_sessions", return_value=[race["session"]]), \
                patch.object(loader, "get_classification", return_value=race["classification"]):
            result = historical.fetch_snapshot(1966)
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["skipped_events"][0]["reason"], "500cc not listed by source")
        self.assertEqual(result["standings"]["classification"][0]["points"], 36)
        self.assertEqual(result["events"][0]["sessions"][0]["classification"][0]["points"], 0)

    def test_half_points_reach_sql_as_exact_decimals(self):
        data = snapshot()
        data["standings"]["classification"][0]["points"] = 210.5
        connection = MagicMock()
        connection.execute.return_value.fetchone.return_value = None
        with patch.object(historical, "verify_season"), contextlib.redirect_stdout(io.StringIO()):
            historical.persist_season(connection, data)
        calls = connection.cursor.return_value.executemany.call_args_list
        standing_rows = next(call.args[1] for call in calls if call.args[0] == historical.STANDINGS_SQL)
        self.assertEqual(standing_rows[0][4], Decimal("210.5"))

    def test_rejects_empty_or_duplicate_official_rankings(self):
        for mutation in ["empty", "duplicate", "zero_champion"]:
            with self.subTest(mutation=mutation):
                data = snapshot()
                entries = data["standings"]["classification"]
                if mutation == "empty":
                    entries.clear()
                elif mutation == "duplicate":
                    entries.append(deepcopy(entries[0]))
                else:
                    entries[0]["points"] = 0
                with self.assertRaises(ValueError):
                    historical.validate_snapshot(data, 1966)

    def test_empty_race_archive_is_preserved_without_inventing_a_winner(self):
        data = snapshot()
        data["events"][0]["sessions"][0]["classification"] = []
        self.assertEqual(historical.validate_snapshot(data, 1966), data)
        self.assertEqual(historical.race_entries(data), [])

    def test_year_ranges_are_bounded_and_can_resume_in_batches(self):
        self.assertEqual(historical.parse_years("1966,1975-1976,1966"), [1966, 1975, 1976])
        for value in ["1948", "3001", "1975-1966", "1966-3001", "invalid"]:
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                historical.parse_years(value)

    def test_lower_class_retains_label_and_is_not_prematurely_final(self):
        data = snapshot()
        data["year"] = 2026
        data["category"] = "Moto2\u2122"
        data["is_final"] = False
        historical.validate_snapshot(data, 2026, "Moto2")
        connection = MagicMock()
        connection.execute.return_value.fetchone.return_value = None
        with patch.object(historical, "verify_season"), contextlib.redirect_stdout(io.StringIO()):
            historical.persist_season(connection, data)
        calls = connection.cursor.return_value.executemany.call_args_list
        rows = next(c.args[1] for c in calls if c.args[0] == historical.STANDINGS_SQL)
        self.assertEqual(rows[0][1], "Moto2\u2122")
        self.assertFalse(rows[0][7])

    def test_session_number_is_independent_of_shared_rider_profile(self):
        entry = snapshot()["events"][0]["sessions"][0]["classification"][0]
        entry["rider"]["number"] = 12
        first = loader.classification_parameters("first", entry, 2026)
        entry["rider"]["number"] = 63
        second = loader.classification_parameters("second", entry, 2026)
        self.assertEqual((first[16], second[16]), (12, 63))
        cursor = MagicMock()
        loader.upsert_rider(cursor, entry["rider"])
        sql = cursor.execute.call_args.args[0]
        self.assertNotIn("number=COALESCE", sql)

    def test_category_family_scope_is_allowlisted_and_keeps_lineages_separate(self):
        from category_scope import category_sql, canonical_category
        self.assertIn("'moto2','250cc'", category_sql("intermediate", "s.category"))
        self.assertNotIn("'motogp'", category_sql("lightweight"))
        self.assertEqual(canonical_category(" Moto3\u2122 "), "Moto3")
        for value in ["all", "sidecar", "'; DROP TABLE riders;--"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                category_sql(value)

    def test_explicit_official_standings_gap_preserves_available_race_archive(self):
        data = snapshot()
        data["standings"]["classification"] = []
        data["standings_available"] = False
        self.assertEqual(historical.validate_snapshot(data, 1966), data)
        connection = MagicMock()
        connection.execute.return_value.fetchone.return_value = None
        with patch.object(historical, "verify_season"), contextlib.redirect_stdout(io.StringIO()):
            historical.persist_season(connection, data)
        self.assertFalse(any(
            call.args[0] == historical.STANDINGS_SQL
            for call in connection.cursor.return_value.executemany.call_args_list
        ))

    def test_archive_cache_does_not_store_or_retry_rate_limit_responses(self):
        with tempfile.TemporaryDirectory() as directory:
            source = historical.ArchiveSource(Path(directory))
            response = MagicMock(status_code=200)
            response.json.return_value = [{"id": "season"}]
            with patch.object(historical.requests, "get", return_value=response) as get:
                self.assertEqual(source("seasons"), source("seasons"))
                self.assertEqual(get.call_count, 1)
            response.status_code = 429
            response.headers = {"Retry-After": "300"}
            with patch.object(historical.requests, "get", return_value=response) as get, \
                    patch.object(historical.time, "sleep"):
                with self.assertRaisesRegex(historical.requests.HTTPError, "300"):
                    source("events", {"seasonUuid": "season"})
                self.assertEqual(get.call_count, 1)
            self.assertEqual(len(list(Path(directory).glob("*.json"))), 1)

    def test_official_rank_point_disagreement_is_flagged_without_reordering_source(self):
        from category_scope import official_points_inconsistent
        raw = [(1, Decimal("9")), (2, Decimal("28")), (3, Decimal("46"))]
        self.assertTrue(official_points_inconsistent(raw))
        self.assertFalse(official_points_inconsistent([(3, 40), (1, 76), (2, 76)]))
        self.assertEqual(raw[0], (1, Decimal("9")))


if __name__ == "__main__":
    unittest.main()
