import unittest
from unittest.mock import patch

import pyodbc
from fastapi.testclient import TestClient

import preview_api


def result(session, rider, points, position, kind="RAC"):
    return {
        "session_id": session, "event_id": session.split("-")[0],
        "short_name": session, "session_type": kind, "session_label": kind,
        "session_date": None, "date_end": "2026-06-01",
        "rider_id": rider, "rider": rider, "number": 93 if rider == preview_api.MARC_ID else 1,
        "team": "Team", "constructor": "Bike", "position": position, "points": points,
    }


class ChampionshipTests(unittest.TestCase):
    def test_comeback_tracks_102_point_low_and_recovery_after_sprint_and_race(self):
        marc, rival = preview_api.MARC_ID, "rival"
        rows = [
            result("ITA-race", rival, 102, 1),
            result("ITA-race", marc, 0, None),
            result("HUN-sprint", marc, 12, 1, "SPR"),
            result("HUN-sprint", rival, 7, 3, "SPR"),
            result("HUN-race", marc, 25, 1),
            result("HUN-race", rival, 0, None),
        ]
        data = preview_api.build_championship(rows, 2026)
        story = data["comeback"]
        self.assertEqual(story["max_deficit"], 102)
        self.assertEqual([point["margin"] for point in story["history"]], [-102, -97, -72])
        self.assertEqual(story["recovered"], 30)
        self.assertTrue(story["verified_102"])
        self.assertEqual(data["gp_results"], 2)

    def test_margin_turns_positive_when_marc_takes_the_lead(self):
        rows = [
            result("one", preview_api.MARC_ID, 20, 2),
            result("one", "rival", 25, 1),
            result("two", preview_api.MARC_ID, 25, 1),
            result("two", "rival", 0, None),
        ]
        story = preview_api.build_championship(rows, 2026)["comeback"]
        self.assertEqual(story["current_margin"], 20)
        self.assertEqual(story["recovered"], 25)

    def test_points_ties_use_grand_prix_countback_not_sprint_wins(self):
        rows = [
            result("race", "rider-a", 25, 1),
            result("race", "rider-b", 20, 2),
            result("sprint", "rider-b", 5, 1, "SPR"),
            result("sprint", "rider-a", 0, None, "SPR"),
        ]
        standings = preview_api.build_championship(rows, 2026)["standings"]
        self.assertEqual([rider["rider_id"] for rider in standings], ["rider-a", "rider-b"])
        self.assertEqual(standings[1]["wins"], 0)

    def test_empty_season_does_not_invent_a_comeback(self):
        data = preview_api.build_championship([], 1990)
        self.assertIsNone(data["comeback"])
        self.assertEqual(data["standings"], [])

    def test_sprint_only_weekend_counts_without_inventing_a_grand_prix_result(self):
        data = preview_api.build_championship([
            result("JPN-race", "rider", 25, 1),
            result("AUS-sprint", "rider", 12, 1, "SPR"),
        ], 2026)
        self.assertEqual(data["weekends"], 2)
        self.assertEqual(data["gp_results"], 1)
        self.assertEqual(data["standings"][0]["points"], 37)

    def test_restart_retains_source_timeline_without_awarding_a_phantom_gp_win(self):
        data = preview_api.build_championship([
            result("CAT-original", "rider-a", 0, 1),
            result("CAT-original", "rider-b", 0, 2),
            result("CAT-restart", "rider-b", 25, 1),
            result("CAT-restart", "rider-a", 20, 2),
        ], 2026)
        self.assertEqual(len(data["rounds"]), 2)
        self.assertEqual(data["scoring_sessions"], 1)
        self.assertEqual(data["gp_results"], 1)
        self.assertEqual(data["standings"][1]["wins"], 0)

    def test_missing_or_placeholder_points_do_not_invent_historical_standings(self):
        data = preview_api.build_championship([
            result("old-race", preview_api.MARC_ID, None, 1),
            result("old-race", "rival", 0, 2),
        ], 1975)
        self.assertEqual(data["standings"], [])
        self.assertIsNone(data["comeback"])
        self.assertEqual(data["scoring_sessions"], 0)
        self.assertEqual(len(data["rounds"]), 1)


class PreviewApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(preview_api.app)

    def test_invalid_season_and_unknown_session_report_errors(self):
        self.assertEqual(self.client.get("/api/championship?season=invalid").status_code, 422)
        with patch.object(preview_api, "query", return_value=[]):
            self.assertEqual(self.client.get("/api/sessions/missing/analysis").status_code, 404)

    def test_database_failure_is_explicit_and_does_not_expose_details(self):
        with patch.object(preview_api, "query", side_effect=pyodbc.OperationalError("private detail")):
            response = self.client.get("/api/seasons")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private detail", response.text)

    def test_numeric_timing_handles_minutes_sectors_and_invalid_source_values(self):
        self.assertEqual(preview_api.seconds("1'02.345"), 62.345)
        self.assertEqual(preview_api.seconds("32.125"), 32.125)
        for value in [None, "", "P", "nan", "inf", "1:65", "-1", "0"]:
            self.assertIsNone(preview_api.seconds(value))

    def test_prefixed_apis_and_canonical_redirect_preserve_query(self):
        self.assertEqual(self.client.get("/paddock/api/health").json(), {"status": "ok"})
        with patch.object(preview_api, "query", return_value=[{"season": 2025}]):
            self.assertEqual(self.client.get("/paddock/api/seasons").json(), [2025])
        response = self.client.get("/paddock?season=2025&view=laps", follow_redirects=False)
        self.assertEqual(response.status_code, 308)
        self.assertEqual(response.headers["location"], "/paddock/?season=2025&view=laps")

    def test_historical_story_preserves_official_tied_ranks_and_has_no_curve(self):
        rows = [
            {"position": 1, "rider_id": "ago", "rider": "Giacomo Agostini", "number": None,
             "points": 46, "constructor": "MV Agusta", "source_url": "https://example.com"},
            {"position": 2, "rider_id": "hailwood", "rider": "Mike Hailwood", "number": None,
             "points": 46, "constructor": "Honda", "source_url": "https://example.com"},
        ]
        with patch.object(preview_api, "query", return_value=rows):
            data = self.client.get("/paddock/api/championship?season=1967").json()
        self.assertEqual([r["rider_id"] for r in data["standings"]], ["ago", "hailwood"])
        self.assertEqual(data["standings_source"], "official")
        self.assertEqual(data["story"]["headline"], "Equal points.")
        self.assertEqual(data["story"]["metric"], 0)
        self.assertEqual(data["rounds"], [])
        self.assertIsNone(data["standings"][0]["wins"])

    def test_season_stories_follow_the_data_rather_than_always_claiming_a_comeback(self):
        rows = [
            result("one", preview_api.MARC_ID, 25, 1),
            result("one", "rival", 20, 2),
            result("two", preview_api.MARC_ID, 25, 1),
            result("two", "rival", 20, 2),
        ]
        data = preview_api.build_championship(rows, 2025)
        data["standings_source"] = "computed"
        story = preview_api.season_story(data)
        self.assertEqual(story["accent"], "Victory became the pattern.")
        self.assertIsNone(story["context_url"])
        data["standings"][0].update(rider="Marc Marquez", wins=11)
        story = preview_api.season_story(data)
        self.assertEqual(story["headline"], "Back to the summit.")
        self.assertEqual(story["metric"], 11)
        self.assertIn("motogp.com", story["context_url"])

    def test_final_session_turnaround_gets_a_decisive_finale_story(self):
        data = preview_api.build_championship([
            result("one", "rival", 25, 1),
            result("one", "winner", 20, 2),
            result("two", "winner", 25, 1),
            result("two", "rival", 18, 3),
        ], 2015)
        data["standings_source"] = "computed"
        self.assertEqual(preview_api.season_story(data)["headline"], "The last race changed everything.")


if __name__ == "__main__":
    unittest.main()
