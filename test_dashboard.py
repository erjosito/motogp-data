import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest


DASHBOARD = Path(__file__).with_name("dashboard.py")


def sample_query(sql, conn=None, params=None):
    """Supply explicit test data; never open a database connection."""
    sql = " ".join(sql.split())
    if "SELECT DISTINCT season_year" in sql:
        return pd.DataFrame({"season_year": [2026, 2025]})
    if "SUM(cl.points) AS race_pts" in sql:
        return pd.DataFrame([
            {"short_name": gp, "date_end": date, "rider": f"Sample Rider {rider}", "race_pts": points}
            for gp, date, rider, points in [
                ("QAT", "2026-11-08", 1, 37), ("QAT", "2026-11-08", 2, 29),
                ("QAT", "2026-11-08", 3, 23), ("POR", "2026-11-22", 1, 29),
                ("POR", "2026-11-22", 2, 32), ("POR", "2026-11-22", 3, 23),
                ("POR", "2026-11-22", 4, 11),
            ]
        ])
    if "SELECT event_id, short_name" in sql:
        return pd.DataFrame([{
            "event_id": event_id, "short_name": event_id.upper(),
            "event_name": f"Sample {event_id.upper()} GP",
            "sponsored_name": f"Sample {event_id.upper()} GP",
            "circuit_name": "Sample Circuit", "circuit_place": "Sample City",
            "country_name": "Sample Country", "date_end": date, "season_year": 2026,
        } for event_id, date in [("qat", "2026-11-08"), ("por", "2026-11-22"), ("val", "2026-11-29")]])
    if "SELECT session_id, session_type" in sql:
        event_id = params[0]
        return pd.DataFrame([{
            "session_id": f"{event_id}-race", "session_type": "RAC",
            "session_number": None, "session_label": "Race",
            "session_date": "2026-11-22", "weather": "Dry",
            "air_temp": "22 C", "ground_temp": "30 C",
        }])
    if "SELECT c.position" in sql:
        return pd.DataFrame([{
            "position": position, "rider": f"Sample Rider {position}",
            "num": position * 10, "team_name": f"Sample Team {position}",
            "constructor": "Sample Bike", "total_laps": 3,
            "time_text": "5:03.000", "gap_first": "" if position == 1 else f"+{position}.000",
            "best_lap_time": None, "top_speed": None, "points": 26 - position,
            "status": "INSTND",
        } for position in range(1, 4)])
    if "l.lap_number, l.lap_time" in sql:
        return pd.DataFrame([{
            "rider": f"Sample Rider {rider}", "num": rider * 10,
            "lap_number": lap, "lap_time": f"1:{40 + rider + lap:02d}.000",
            "t1": "23.000", "t2": "30.000", "t3": "16.000", "t4": "34.000",
            "speed_kmh": 320.0 + rider, "is_pit": False, "run_number": 1,
            "front_tyre": "Slick-Medium", "rear_tyre": "Slick-Medium",
        } for rider in range(1, 4) for lap in range(1, 4)])
    if "AS n_events" in sql:
        return pd.DataFrame([dict(
            n_events=3, n_sessions=3, n_classifications=9, n_laps=27,
            n_riders=3, n_teams=3, n_seasons=2, min_year=2025, max_year=2026,
            n_circuits=2, n_countries=2,
        )])
    if "COUNT(*) AS Events FROM events" in sql:
        return pd.DataFrame({"Year": [2025, 2026], "Events": [1, 2]})
    if "AS With_Sectors" in sql:
        return pd.DataFrame({"Year": [2025, 2026], "Laps": [9, 18], "With_Sectors": [9, 18]})
    if "SELECT TOP 10 r.full_name AS Rider" in sql:
        return pd.DataFrame({"Rider": ["Sample Rider 1"], "Wins": [3]})
    if "SELECT t.constructor AS Constructor" in sql:
        return pd.DataFrame({"Constructor": ["Sample Bike"], "Wins": [3]})
    if "SELECT country_name AS Country" in sql:
        return pd.DataFrame({"Country": ["Sample Country"], "Races": [3]})
    if "COUNT(*) AS Count FROM sessions" in sql:
        return pd.DataFrame({"Type": ["RAC"], "Label": ["Race"], "Count": [3]})
    if "AS Sectors FROM events" in sql:
        return pd.DataFrame({
            "Year": [2025, 2026], "Events": [1, 2], "Sessions": [1, 2],
            "Classifications": [3, 6], "Laps": [9, 18], "Sectors": [9, 18],
        })
    raise AssertionError(f"Unmocked dashboard query: {sql}")


class DashboardTests(unittest.TestCase):
    def setUp(self):
        st.cache_data.clear()
        self.addCleanup(st.cache_data.clear)
        self.connection = patch("pyodbc.connect").start()
        self.addCleanup(patch.stopall)
        self.read_sql = patch("pandas.read_sql", side_effect=sample_query).start()

    def start_app(self):
        app = AppTest.from_file(str(DASHBOARD), default_timeout=30).run()
        self.assertFalse(app.exception)
        return app

    def start_race_analysis(self):
        app = self.start_app()
        app.selectbox(key="nav_group").set_value("nav_race").run()
        app.radio(key="view_nav_race").set_value("viz_laptimes")
        app.selectbox(key="sb_gp").set_value("por").run()
        self.assertFalse(app.exception)
        return app

    def test_championship_and_coverage_are_both_accessible(self):
        app = self.start_app()
        self.assertIn("2026 MotoGP World Championship", [h.value for h in app.subheader])
        standings = app.dataframe[0].value
        self.assertEqual(standings["Points"].tolist(), [66, 61, 46, 11])
        self.assertEqual(standings["Gap to leader"].tolist(), [0, 5, 20, 55])
        self.assertIn("POR", " ".join(c.value for c in app.caption))
        app.radio(key="home_view").set_value("home_coverage").run()
        self.assertFalse(app.exception)
        self.assertTrue(app.dataframe)
        self.assertTrue(app.get("plotly_chart"))
        app.selectbox(key="language").select("🇮🇹 Italiano").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.radio(key="home_view").value, "home_coverage")
        app.radio(key="home_view").set_value("home_championship").run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.button), 1)

    def test_championship_shortcut_opens_the_current_season(self):
        app = self.start_app()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="nav_group").value, "nav_season")
        self.assertEqual(app.radio(key="view_nav_season").value, "viz_championship")
        self.assertEqual(app.selectbox(key="sb_year").value, 2026)
        self.assertEqual(app.dataframe[0].value["Points"].tolist(), [66, 61, 46, 11])

    def test_event_selection_survives_switching_to_all_capable_view(self):
        app = self.start_race_analysis()
        app.radio(key="view_nav_race").set_value("viz_rhythm").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["sel_event_id"], "por")
        app.radio(key="view_nav_race").set_value("viz_laptimes").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["sel_event_id"], "por")

    def test_repeated_event_changes_and_language_switch_keep_the_selection(self):
        app = self.start_race_analysis()
        for event_id in ["qat", "val", "por"]:
            with self.subTest(event_id=event_id):
                app.selectbox(key="sb_gp").set_value(event_id).run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state["sel_event_id"], event_id)
        app.selectbox(key="language").select("🇪🇸 Español").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="sb_gp").value, "por")

    def test_language_switch_preserves_navigation_and_filters(self):
        app = self.start_race_analysis()
        for language in ["🇪🇸 Español", "🇮🇹 Italiano", "🇬🇧 English"]:
            with self.subTest(language=language):
                app.selectbox(key="language").select(language).run()
                self.assertFalse(app.exception)
                self.assertEqual(app.radio(key="view_nav_race").value, "viz_laptimes")
                self.assertEqual(app.session_state["sel_event_id"], "por")
                self.assertTrue(app.get("plotly_chart"))

    def test_returning_to_a_workspace_preserves_its_analysis(self):
        app = self.start_race_analysis()
        app.selectbox(key="nav_group").set_value("nav_overview").run()
        app.selectbox(key="nav_group").set_value("nav_race").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.radio(key="view_nav_race").value, "viz_laptimes")
        self.assertEqual(app.session_state["sel_event_id"], "por")

    def test_missing_championship_results_show_an_explicit_empty_state(self):
        def no_race(sql, conn=None, params=None):
            if "SUM(cl.points) AS race_pts" in sql:
                return pd.DataFrame()
            return sample_query(sql, conn, params)
        self.read_sql.side_effect = no_race
        app = self.start_app()
        self.assertTrue(app.info)
        self.assertFalse(app.button)

    def test_championship_does_not_depend_on_lap_data(self):
        def no_laps(sql, conn=None, params=None):
            if "l.lap_number, l.lap_time" in sql:
                raise AssertionError("The championship overview should not load lap data")
            return sample_query(sql, conn, params)
        self.read_sql.side_effect = no_laps
        app = self.start_app()
        self.assertEqual(len(app.button), 1)
        self.assertIn("Sample Rider 1", [h.value for h in app.subheader])

    def test_championship_preserves_fractional_points_and_shared_ranks(self):
        def tied_points(sql, conn=None, params=None):
            data = sample_query(sql, conn, params)
            if "SUM(cl.points) AS race_pts" in sql:
                data["race_pts"] = data["race_pts"].astype(float)
                data.loc[(data["rider"] == "Sample Rider 2") & (data["short_name"] == "POR"), "race_pts"] = 37
                data.loc[data["rider"] == "Sample Rider 4", "race_pts"] = 11.5
            return data
        self.read_sql.side_effect = tied_points
        app = self.start_app()
        standings = app.dataframe[0].value
        self.assertEqual(standings["Position"].tolist(), [1, 1, 3, 4])
        self.assertEqual(standings["Points"].tolist(), [66, 66, 46, 11.5])
        app.button[0].click().run()
        self.assertFalse(app.exception)
        detailed_standings = app.dataframe[0].value
        self.assertEqual(detailed_standings["Pos"].tolist(), [1, 1, 3, 4])
        self.assertEqual(detailed_standings["Points"].tolist(), [66, 66, 46, 11.5])


if __name__ == "__main__":
    unittest.main()
