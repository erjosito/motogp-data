import ast
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import numpy as np
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
    def test_podium_highlights_set_readable_foreground_and_background(self):
        tree = ast.parse(DASHBOARD.read_text(encoding="utf-8"))
        highlight = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "hl_champ"
        )
        namespace = {}
        exec(compile(ast.Module(body=[highlight], type_ignores=[]), str(DASHBOARD), "exec"), namespace)
        for position in [1, 2, 3]:
            styles = namespace["hl_champ"](pd.Series({"Pos": position, "Points": 50}))
            self.assertTrue(all("background-color:" in style and "color: #1a1a1a;" in style
                                for style in styles))
        self.assertEqual(namespace["hl_champ"](pd.Series({"Pos": 4})), [""])

    def setUp(self):
        st.cache_data.clear()
        self.addCleanup(st.cache_data.clear)
        self.connection = patch("sql_connection.connect_to_sql").start()
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

    def test_incomplete_sectors_do_not_produce_ideal_laps(self):
        def partial_sectors(sql, conn=None, params=None):
            data = sample_query(sql, conn, params)
            if "l.lap_number, l.lap_time" in sql:
                data.loc[data["rider"] == "Sample Rider 2", "t4"] = None
                data.loc[data["rider"] == "Sample Rider 3", ["t1", "t2", "t3", "t4"]] = None
            return data

        self.read_sql.side_effect = partial_sectors
        app = self.start_race_analysis()
        app.radio(key="view_nav_race").set_value("viz_sectors").run()
        self.assertFalse(app.exception)
        table = app.dataframe[0].value.set_index("rider")
        self.assertEqual(table.loc["Sample Rider 1", "Ideal"], "1:43.000")
        self.assertEqual(table.loc["Sample Rider 1", "Gap"], -1.0)
        for rider in ["Sample Rider 2", "Sample Rider 3"]:
            self.assertEqual(table.loc[rider, "Ideal"], "")
            self.assertTrue(pd.isna(table.loc[rider, "Gap"]))
        self.assertTrue(app.info)

    def test_position_battle_does_not_invent_histories_without_timing(self):
        def missing_rider(sql, conn=None, params=None):
            data = sample_query(sql, conn, params)
            if "l.lap_number, l.lap_time" in sql:
                data = data[data["rider"] != "Sample Rider 3"]
            return data
        self.read_sql.side_effect = missing_rider
        app = self.start_race_analysis()
        app.radio(key="view_nav_race").set_value("viz_position").run()
        self.assertFalse(app.exception)
        self.assertTrue(app.info)
        self.assertFalse(app.get("plotly_chart"))

    def test_position_battle_with_complete_timing(self):
        app = self.start_race_analysis()
        app.radio(key="view_nav_race").set_value("viz_position").run()
        self.assertFalse(app.exception)
        self.assertTrue(app.get("plotly_chart"))

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


class RaceTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tree = ast.parse(DASHBOARD.read_text(encoding="utf-8"))
        names = {"race_elapsed", "reconstructed_positions"}
        nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
        cls.helpers = {"pd": pd, "np": np}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(DASHBOARD), "exec"), cls.helpers)

    def test_missing_lap_invalidates_all_subsequent_elapsed_times(self):
        laps = pd.DataFrame({"rider": ["A"] * 3, "lap_number": [1, 3, 4], "lap_sec": [100., 100., 100.]})
        elapsed = self.helpers["race_elapsed"](laps)["elapsed"]
        self.assertEqual(elapsed.iloc[0], 100.)
        self.assertTrue(elapsed.iloc[1:].isna().all())

    def test_slow_and_pit_laps_count_toward_elapsed_time(self):
        laps = pd.DataFrame({"rider": ["A"] * 3, "lap_number": [3, 1, 2],
                             "lap_sec": [100., 100., 200.], "is_pit": [False, False, True]})
        self.assertEqual(self.helpers["race_elapsed"](laps)["elapsed"].tolist(), [100., 300., 400.])

    def test_invalid_or_duplicate_timing_does_not_resume(self):
        for times in [[100., np.nan, 100.], [100., 0., 100.], [100., np.inf, 100.]]:
            laps = pd.DataFrame({"rider": ["A"] * 3, "lap_number": [1, 2, 3], "lap_sec": times})
            self.assertTrue(self.helpers["race_elapsed"](laps)["elapsed"].iloc[1:].isna().all())
        laps = pd.DataFrame({"rider": ["A"] * 4, "lap_number": [1, 2, 2, 3], "lap_sec": [100.] * 4})
        self.assertTrue(self.helpers["race_elapsed"](laps)["elapsed"].iloc[1:].isna().all())

    def test_retirement_and_missing_active_rider_have_distinct_outcomes(self):
        laps = pd.DataFrame({"rider": ["A", "A", "A", "B"],
                             "lap_number": [1, 2, 3, 1], "lap_sec": [100., 100., 100., 101.]})
        classification = pd.DataFrame({"rider": ["A", "B"], "total_laps": [3, 1]})
        positions = self.helpers["reconstructed_positions"](laps, classification)
        self.assertEqual(positions.groupby("lap_number").size().tolist(), [2, 1, 1])
        classification.loc[1, "total_laps"] = 3
        positions = self.helpers["reconstructed_positions"](laps, classification)
        self.assertEqual(positions["lap_number"].unique().tolist(), [1])


if __name__ == "__main__":
    unittest.main()
