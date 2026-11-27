from copy import deepcopy
from datetime import date
from decimal import Decimal
import json
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import urlencode

import import_standings as standings


def fixture(year=2013):
    season = {"id": "season", "year": year, "current": year == 2026}
    params = {"seasonUuid": "season", "categoryUuid": "category"}
    return {
        "version": 1, "year": year, "category": "MotoGP\u2122",
        "season": season, "source_category": {"id": "category", "name": "MotoGP\u2122"},
        "events": [{
            "id": "event", "season": season, "short_name": "POR",
            "date_end": f"{year}-11-22", "status": "FINISHED", "test": False,
        }],
        "checked_on": "2026-11-27", "fetched_at": "2026-11-27T20:00:00Z",
        "is_final": year != 2026, "params": params,
        "source_url": standings.loader.API_BASE_URL + "/standings?" + urlencode(params),
        "standings_available": True,
        "standings": {
            "file": f"https://resources.motogp.com/files/results/{year}/POR/MotoGP/RAC/worldstanding.pdf",
            "classification": [{
                "rider": {"id": "marc", "full_name": "Marc Marquez", "number": 93},
                "position": 1, "points": 334, "constructor": {"id": "honda", "name": "Honda"},
                "team": {"season": season},
            }],
        },
    }


class StandingsImportTests(unittest.TestCase):
    def test_sorted_snapshot_cache_round_trip_preserves_query_identity(self):
        data = json.loads(json.dumps(fixture(), sort_keys=True))
        standings.validate_snapshot(data)
        data["source_url"] += "&seasonUuid=other"
        with self.assertRaisesRegex(ValueError, "provenance"):
            standings.validate_snapshot(data)

    def test_current_clinched_title_does_not_make_final_table(self):
        data = fixture(2026)
        data["events"].append({
            "id": "future", "season": data["season"], "short_name": "VAL",
            "date_end": "2026-11-29", "status": "FINISHED", "test": False,
        })
        self.assertEqual(standings.validate_snapshot(data), data)
        data["is_final"] = True
        with self.assertRaisesRegex(ValueError, "marked final"):
            standings.validate_snapshot(data)

    def test_rejects_future_document_even_when_api_calls_event_finished(self):
        data = fixture(2026)
        data["events"][0]["date_end"] = "2026-11-29"
        with self.assertRaisesRegex(ValueError, "future or unknown"):
            standings.validate_snapshot(data)

    def test_historical_document_must_match_last_uncancelled_event(self):
        data = fixture()
        data["events"].append({
            **data["events"][0], "id": "last", "short_name": "VAL", "date_end": "2013-11-29",
        })
        with self.assertRaisesRegex(ValueError, "last uncancelled"):
            standings.validate_snapshot(data)
        data["events"][-1]["status"] = "CANCELLED"
        standings.validate_snapshot(data)

    def test_empty_official_table_is_explicit_source_gap(self):
        data = fixture()
        data["standings"]["classification"] = []
        with self.assertRaisesRegex(ValueError, "source-gap"):
            standings.validate_snapshot(data)
        data["standings_available"] = False
        standings.validate_snapshot(data)

    def test_legacy_xml_document_layout_is_verified_when_pdf_absent(self):
        data = fixture(1990)
        data["category"] = data["source_category"]["name"] = "500cc"
        data["standings"]["file"] = None
        data["standings"]["xmlFile"] = (
            "https://resources.motogp.com/files/results/1990/500cc/POR/world%2Bstanding.xml"
        )
        standings.validate_snapshot(data)

    def test_api_xml_round_takes_precedence_over_stale_legacy_pdf_link(self):
        data = fixture(2000)
        data["category"] = data["source_category"]["name"] = "500cc"
        data["standings"]["file"] = (
            "https://resources.motogp.com/files/results/2000/500cc/VAL/world%2Bstanding.pdf"
        )
        data["standings"]["xmlFile"] = (
            "https://resources.motogp.com/files/results/2000/500cc/POR/world+standing.xml"
        )
        data["events"].append({
            **data["events"][0], "id": "earlier", "short_name": "VAL", "date_end": "2000-09-17",
        })
        standings.validate_snapshot(data)

    def test_latest_race_pdf_takes_precedence_over_stale_modern_xml(self):
        data = fixture()
        data["standings"]["xmlFile"] = (
            "https://resources.motogp.com/files/results/2013/VAL/MotoGP/RAC/worldstanding.XML"
        )
        data["events"].append({
            **data["events"][0], "id": "earlier", "short_name": "VAL", "date_end": "2013-09-17",
        })
        self.assertEqual(standings.document_evidence(data)["event_short"], "POR")
        standings.validate_snapshot(data)

    def test_explicit_2001_xml_rio_country_code_alias_does_not_generalize(self):
        data = fixture(2001)
        data["category"] = data["source_category"]["name"] = "500cc"
        data["standings"]["file"] = None
        data["events"][0]["short_name"] = "RIO"
        data["standings"]["xmlFile"] = (
            "https://resources.motogp.com/files/results/2001/500cc/BRA/world+standing.xml"
        )
        standings.validate_snapshot(data)
        data["standings"]["xmlFile"] = data["standings"]["xmlFile"].replace("/BRA/", "/XYZ/")
        with self.assertRaisesRegex(ValueError, "future or unknown"):
            standings.validate_snapshot(data)

    def test_preserves_official_anomalies_fractional_scores_and_source_payload(self):
        data = fixture()
        entries = data["standings"]["classification"]
        entries[0]["points"] = 9
        entries.append({
            **deepcopy(entries[0]), "rider": {"id": "other", "full_name": "Other"},
            "position": 2, "points": 28.5,
        })
        original = deepcopy(data)
        standings.validate_snapshot(data)
        values = standings.standings_values(data)
        self.assertEqual(values[1][2], Decimal("28.5"))
        self.assertEqual(data, original)

    def test_rejects_wrong_season_category_duplicate_rider_and_invalid_scores(self):
        for mutation in ("season", "category", "duplicate", "points"):
            with self.subTest(mutation=mutation):
                data = fixture()
                if mutation == "season":
                    data["events"][0]["season"] = {"id": "other", "year": 2013}
                elif mutation == "category":
                    data["category"] = "Moto2"
                elif mutation == "duplicate":
                    data["standings"]["classification"].append(
                        deepcopy(data["standings"]["classification"][0]),
                    )
                else:
                    data["standings"]["classification"][0]["points"] = float("nan")
                with self.assertRaises(ValueError):
                    standings.validate_snapshot(data)

    def test_fetch_only_calls_calendar_categories_and_standings(self):
        data = fixture(2026)
        calls = []

        def source(endpoint, params=None):
            calls.append(endpoint)
            return {
                "seasons": [data["season"]],
                "events": data["events"],
                "categories": [data["source_category"]],
                "standings": data["standings"],
            }[endpoint]

        result = standings.fetch_snapshot(2026, source, today=date(2026, 11, 27))
        self.assertFalse(result["is_final"])
        self.assertEqual(calls, ["seasons", "events", "categories", "standings"])

    def test_persistence_never_calls_race_loaders_or_overwrites_existing_profiles(self):
        data = fixture()
        conn = MagicMock()

        def execute(query, *args):
            cursor = MagicMock()
            cursor.fetchone.return_value = None
            cursor.fetchall.return_value = [("marc",)] if query == "SELECT rider_id FROM riders" else []
            return cursor

        conn.execute.side_effect = execute
        with patch.object(standings, "verify_standings") as verify, \
                patch.object(standings.loader, "upsert_rider") as rider, \
                patch.object(standings.loader, "upsert_event") as event, \
                patch.object(standings.loader, "upsert_session") as session:
            self.assertEqual(standings.persist(conn, data), "imported")
        verify.assert_called_once()
        rider.assert_not_called()
        event.assert_not_called()
        session.assert_not_called()
        sql, parameters = conn.cursor.return_value.executemany.call_args.args
        self.assertEqual(sql, standings.STANDINGS_SQL)
        self.assertEqual(parameters[0][4], Decimal("334"))
        self.assertEqual(parameters[0][7], True)
        sql_text = " ".join(
            call.args[0] for call in conn.execute.call_args_list
        ) + " ".join(call.args[0] for call in conn.cursor.return_value.execute.call_args_list)
        self.assertNotIn("historical_imports", sql_text)
        self.assertNotIn("UPDATE events", sql_text)

    def test_unowned_existing_conflicting_standings_stop_before_writes(self):
        conn = MagicMock()

        def execute(query, *args):
            cursor = MagicMock()
            cursor.fetchone.return_value = None
            cursor.fetchall.return_value = (
                [("marc", 1, Decimal("333"), "honda", "Honda", True)]
                if query.startswith("SELECT rider_id,position") else []
            )
            return cursor

        conn.execute.side_effect = execute
        with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
            standings.persist(conn, fixture())
        conn.cursor.assert_not_called()

    def test_verification_rejects_missing_or_different_stored_rows(self):
        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = []
        with self.assertRaisesRegex(ValueError, "differ"):
            standings.verify_standings(conn, fixture())
        conn.execute.return_value.fetchall.return_value = standings.standings_values(fixture())
        standings.verify_standings(conn, fixture())


if __name__ == "__main__":
    unittest.main()
