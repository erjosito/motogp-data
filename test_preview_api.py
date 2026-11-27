import unittest
import sqlite3
import re
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

    def test_marc_features_are_scoped_to_premier_even_for_a_shared_rider_id(self):
        rows = [result("one", "rival", 102, 1), result("one", preview_api.MARC_ID, 0, 2)]
        data = preview_api.build_championship(rows, 2026, "intermediate")
        data["standings_source"] = "computed"
        self.assertIsNone(data["comeback"])
        self.assertNotEqual(preview_api.season_story(data)["headline"], "102 points behind.")


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


class CategoryApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(preview_api.app)
        self.db = sqlite3.connect(":memory:", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            ATTACH DATABASE ':memory:' AS dbo;
            CREATE TABLE events (event_id TEXT, season_year INT, short_name TEXT,
                event_name TEXT, circuit_name TEXT, country_name TEXT, date_end TEXT);
            CREATE TABLE sessions (session_id TEXT, event_id TEXT, category TEXT,
                session_type TEXT, session_label TEXT, session_date TEXT, session_number INT,
                status TEXT, weather TEXT, air_temp TEXT, ground_temp TEXT);
            CREATE TABLE riders (rider_id TEXT, full_name TEXT, number INT);
            CREATE TABLE teams (team_id TEXT, season_year INT, team_name TEXT, constructor TEXT);
            CREATE TABLE dbo.vw_effective_classifications (
                session_id TEXT, rider_id TEXT, position INT, team_id TEXT,
                total_laps INT, time_ms INT, time_text TEXT, gap_first TEXT, gap_prev TEXT,
                best_lap_number INT, best_lap_time TEXT, top_speed REAL, points REAL,
                status TEXT, constructor_id TEXT, constructor_name TEXT, rider_number INT, source_kind TEXT);
            CREATE TABLE laps (session_id TEXT, rider_id TEXT, lap_number INT, lap_time TEXT,
                t1 TEXT, t2 TEXT, t3 TEXT, t4 TEXT, speed_kmh REAL, is_pit INT,
                run_number INT, front_tyre TEXT, rear_tyre TEXT);
            CREATE TABLE championship_standings (season_year INT, category TEXT, position INT,
                rider_id TEXT, points REAL, constructor_name TEXT, source_url TEXT, is_final INT);
            INSERT INTO events VALUES ('gp',2026,'GP','Grand Prix',NULL,NULL,'2026-06-01');
            INSERT INTO riders VALUES ('rider','Shared rider',99);
            INSERT INTO teams VALUES ('team',2026,'Team','Bike');
        """)
        for index, category in enumerate(["MotoGP™", " Moto2™ ", "Moto3", "350cc", "50cc", "80cc"]):
            self.db.execute("INSERT INTO sessions VALUES (?, 'gp', ?, 'RAC', 'Race', NULL, ?, 'FINISHED', NULL, NULL, NULL)",
                            (f"session-{index}", category, index))
            self.db.execute("INSERT INTO dbo.vw_effective_classifications VALUES (?, 'rider', 1, 'team', 1, NULL, NULL, NULL, NULL, NULL, '1:02.345', NULL, ?, NULL, NULL, 'Bike', ?, ?)",
                            (f"session-{index}", 10 + index, 20 + index, "official-api+external" if index == 1 else "official-api"))
        self.db.execute("INSERT INTO laps VALUES ('session-1','rider',1,'1:02.345',NULL,NULL,NULL,NULL,NULL,0,1,NULL,NULL)")
        self.db.execute("INSERT INTO championship_standings VALUES (2026,'Moto2',1,'rider',123,'Bike','https://example.com/standings',0)")
        self.mock = patch.object(preview_api, "query", side_effect=self.query)
        self.mock.start()
        self.addCleanup(self.mock.stop)
        self.addCleanup(self.db.close)

    def query(self, sql, params=()):
        sql = re.sub(r"\bN'", "'", sql)
        return [dict(row) for row in self.db.execute(sql, params)]

    def test_every_family_isolates_sessions_and_both_mounts(self):
        for prefix in ["", "/paddock"]:
            for index, family in enumerate(preview_api.CATEGORY_FAMILIES):
                with self.subTest(prefix=prefix, family=family):
                    query = f"?category={family}"
                    self.assertEqual(self.client.get(f"{prefix}/api/seasons{query}").json(), [2026])
                    events = self.client.get(f"{prefix}/api/events?season=2026&category={family}").json()
                    self.assertEqual([event["event_id"] for event in events], ["gp"])
                    sessions = self.client.get(f"{prefix}/api/events/gp/sessions{query}").json()
                    self.assertEqual([session["session_id"] for session in sessions], [f"session-{index}"])
                    response = self.client.get(f"{prefix}/api/sessions/session-{index}/analysis{query}")
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()["results"][0]["number"], 20 + index)
                    self.assertEqual(self.client.get(f"{prefix}/api/sessions/session-{(index + 1) % 6}/analysis{query}").status_code, 404)
        self.assertEqual(self.client.get("/api/sessions/session-1/analysis").status_code, 404)

    def test_unsupported_keys_are_rejected_before_database_access(self):
        with patch.object(preview_api, "query") as query:
            for endpoint in ["/seasons", "/events?season=2026", "/events/gp/sessions",
                             "/championship?season=2026", "/sessions/session-1/analysis"]:
                separator = "&" if "?" in endpoint else "?"
                for key in ["Moto2", "unknown", "premier' OR 1=1", ""]:
                    response = self.client.get(f"/api{endpoint}{separator}category={key}")
                    self.assertEqual(response.status_code, 422)
            query.assert_not_called()

    def test_official_current_standings_are_independent_not_a_final_title(self):
        data = self.client.get("/api/championship?season=2026&category=intermediate").json()
        self.assertEqual(data["standings"][0]["points"], 123)
        self.assertFalse(data["is_final"])
        self.assertEqual(data["standings_source"], "official")
        self.assertEqual(data["standings"][0]["series"], [])
        self.assertEqual(data["standings"][0]["wins"], 1)
        self.assertEqual(data["standings"][0]["number"], 21)
        self.assertIsNone(data["comeback"])
        self.assertIn("not a final", data["story"]["summary"])
        self.assertTrue(data["external_sources_used"])
        premier = self.client.get("/api/championship?season=2026").json()
        self.assertEqual(premier["standings"][0]["points"], 10)

    def test_external_supplementation_and_laps_preserve_source_specific_number(self):
        data = self.client.get("/api/sessions/session-1/analysis?category=intermediate").json()
        self.assertEqual(data["results"][0]["source_kind"], "official-api+external")
        self.assertEqual(data["laps"][0]["number"], 21)
        self.assertEqual(data["laps"][0]["lap_seconds"], 62.345)
        self.assertTrue({"time_ms", "gap_prev", "best_lap_number", "constructor_id",
                         "rider_number", "source_kind"}.issubset(data["results"][0]))
        self.db.execute("UPDATE dbo.vw_effective_classifications SET source_kind='external' WHERE session_id='session-1'")
        self.assertEqual(self.client.get("/api/sessions/session-1/analysis?category=intermediate").json()["results"][0]["source_kind"], "external")

    def test_historical_lineages_do_not_mix_with_distinct_extinct_classes(self):
        for index, label in enumerate(["500cc", "250cc", "125cc"]):
            self.db.execute("UPDATE sessions SET category=? WHERE session_id=?", (label, f"session-{index}"))
        for index, family in enumerate(["premier", "intermediate", "lightweight"]):
            rows = self.client.get(f"/api/events/gp/sessions?category={family}").json()
            self.assertEqual([row["session_id"] for row in rows], [f"session-{index}"])

    def test_official_current_table_does_not_hide_verified_premier_comeback(self):
        self.db.execute("INSERT INTO riders VALUES (?, 'Marc Marquez',93)", (preview_api.MARC_ID,))
        self.db.execute("UPDATE dbo.vw_effective_classifications SET points=102 WHERE session_id='session-0'")
        self.db.execute("INSERT INTO dbo.vw_effective_classifications VALUES ('session-0', ?, 2, 'team', 1, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, NULL, NULL, 'Bike', 93, 'official-api')",
                        (preview_api.MARC_ID,))
        self.db.execute("INSERT INTO championship_standings VALUES (2026,'MotoGP',1,'rider',102,'Bike','https://example.com',0)")
        self.db.execute("INSERT INTO championship_standings VALUES (2026,'MotoGP',2,?,0,'Bike','https://example.com',0)",
                        (preview_api.MARC_ID,))
        data = self.client.get("/api/championship?season=2026").json()
        self.assertTrue(data["comeback"]["verified_102"])
        self.assertEqual(data["story"]["headline"], "102 points behind.")
        self.assertFalse(data["is_final"])

    def test_official_2025_table_preserves_evidence_backed_marc_story(self):
        self.db.execute("UPDATE events SET season_year=2025")
        self.db.execute("UPDATE riders SET rider_id=?, full_name='Marc Marquez'", (preview_api.MARC_ID,))
        self.db.execute("UPDATE dbo.vw_effective_classifications SET rider_id=?", (preview_api.MARC_ID,))
        for index in range(1, 11):
            self.db.execute("INSERT INTO sessions VALUES (?, 'gp', 'MotoGP', 'RAC', 'Race', NULL, ?, 'FINISHED', NULL, NULL, NULL)",
                            (f"race-{index}", index))
            self.db.execute("INSERT INTO dbo.vw_effective_classifications VALUES (?, ?, 1, 'team', 1, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 25, NULL, NULL, 'Bike', 93, 'official-api')",
                            (f"race-{index}", preview_api.MARC_ID))
        self.db.execute("INSERT INTO championship_standings VALUES (2025,'MotoGP',1,?,500,'Bike','https://example.com',1)",
                        (preview_api.MARC_ID,))
        data = self.client.get("/api/championship?season=2025").json()
        self.assertTrue(data["is_final"])
        self.assertEqual(data["standings"][0]["points"], 500)
        self.assertEqual(data["story"]["headline"], "Back to the summit.")
        self.assertIn("motogp.com", data["story"]["context_url"])

    def test_missing_historical_finals_never_become_titles_from_race_points(self):
        self.db.execute("UPDATE events SET season_year=1969")
        self.db.execute("UPDATE sessions SET category='250cc' WHERE session_id='session-1'")
        data = self.client.get("/api/championship?season=1969&category=intermediate").json()
        self.assertEqual(data["standings"], [])
        self.assertFalse(data["is_final"])
        self.assertIn("Official final standings are unavailable", data["story"]["summary"])
        self.assertEqual(len(self.client.get("/api/events?season=1969&category=intermediate").json()), 1)

    def test_historical_official_rank_and_points_win_over_augmented_race_totals(self):
        self.db.execute("UPDATE events SET season_year=1969")
        self.db.execute("UPDATE sessions SET category='125cc' WHERE session_id='session-2'")
        self.db.execute("INSERT INTO championship_standings VALUES (1969,'125cc',1,'rider',46,'Bike','https://example.com',1)")
        data = self.client.get("/api/championship?season=1969&category=lightweight").json()
        self.assertTrue(data["is_final"])
        self.assertEqual(data["standings"][0]["points"], 46)
        self.assertEqual(data["rounds"], [])
        self.assertIsNone(data["standings"][0]["wins"])

    def test_standings_only_season_and_known_empty_family(self):
        self.db.execute("INSERT INTO championship_standings VALUES (1967,'80cc',1,'rider',40,'Bike','https://example.com',1)")
        self.assertEqual(self.client.get("/api/seasons?category=80cc").json(), [2026, 1967])
        self.assertEqual(self.client.get("/api/events?season=2000&category=80cc").json(), [])


if __name__ == "__main__":
    unittest.main()
