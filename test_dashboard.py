import ast
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import numpy as np
import streamlit as st
from streamlit.testing.v1 import AppTest
from translations import get_translator


DASHBOARD = Path(__file__).with_name("dashboard.py")


def sample_query(sql, conn=None, params=None):
    """Supply explicit test data; never open a database connection."""
    sql = " ".join(sql.split())
    if "SELECT DISTINCT category" in sql:
        return pd.DataFrame(columns=["category"])
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
            "session_id": params[0] if params else "sample",
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
    if "AS Constructor, COUNT(*) AS Wins" in sql:
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

    def test_coverage_explanations_follow_their_charts_in_each_language(self):
        app = self.start_app()
        app.radio(key="home_view").set_value("home_coverage").run()
        for label, language in [
            ("🇬🇧 English", "en"), ("🇪🇸 Español", "es"), ("🇮🇹 Italiano", "it")
        ]:
            with self.subTest(language=language):
                app.selectbox(key="language").select(label).run()
                self.assertFalse(app.exception)
                columns = app.get("column")
                translator = get_translator(language)
                self.assertIn(
                    translator("data_quality_caption"), [caption.value for caption in app.caption]
                )
                for key in ["races_coverage_explanation", "laps_coverage_explanation"]:
                    explanation = translator(key)
                    matching = [
                        column for column in columns
                        if any(caption.value == explanation for caption in column.caption)
                    ]
                    self.assertEqual(len(matching), 1)
                    elements = list(matching[0])
                    chart_index = next(i for i, element in enumerate(elements) if element.type == "plotly_chart")
                    caption_index = next(
                        i for i, element in enumerate(elements)
                        if element.type == "caption" and element.value == explanation
                    )
                    self.assertEqual(caption_index, chart_index + 1)

    def test_championship_shortcut_opens_the_current_season(self):
        app = self.start_app()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="nav_group").value, "nav_season")
        self.assertEqual(app.radio(key="view_nav_season").value, "viz_championship")
        self.assertEqual(app.selectbox(key="sb_year").value, 2026)
        self.assertEqual(app.dataframe[0].value["Points"].tolist(), [66, 61, 46, 11])

    def test_historical_championship_uses_official_order_and_fractional_points(self):
        def historical_query(sql, conn=None, params=None):
            if "SELECT DISTINCT season_year" in sql:
                return pd.DataFrame({"season_year": [2026, 1989]})
            if "FROM championship_standings" in sql:
                return pd.DataFrame({
                    "position": [1, 2, 3], "rider": ["Lawson", "Rainey", "Sarron"],
                    "points": [228, 210.5, 165.5], "constructor": ["Honda", "Yamaha", "Yamaha"],
                })
            if params == [1989] and "SUM(cl.points)" in sql:
                raise AssertionError("Historical standings must not be reconstructed from race points")
            return sample_query(sql, conn, params)
        self.read_sql.side_effect = historical_query
        app = self.start_app()
        app.button[0].click().run()
        app.selectbox(key="sb_year").set_value(1989).run()
        self.assertFalse(app.exception)
        standings = app.dataframe[0].value
        self.assertEqual(standings["Points"].tolist(), [228, 210.5, 165.5])
        self.assertEqual(standings["Position"].tolist(), [1, 2, 3])
        self.assertFalse(app.get("plotly_chart"))
        self.assertIn("counting rules", " ".join(c.value for c in app.caption))

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
        app.radio(key="view_nav_race").set_value("viz_speed").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["sel_event_id"], "por")
        app.radio(key="view_nav_race").set_value("viz_laptimes").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["sel_event_id"], "por")

    def test_pace_views_require_one_session_while_speed_keeps_aggregation(self):
        app = self.start_race_analysis()
        for view in ["viz_rhythm", "viz_sectors"]:
            app.radio(key="view_nav_race").set_value(view).run()
            self.assertFalse(app.exception)
            self.assertNotIn("All", app.selectbox(key="sb_year").options)
            self.assertNotIn("All", app.selectbox(key="sb_sess").options)
            self.assertEqual(len(app.selectbox(key="sb_gp").options), 3)
            self.assertTrue(app.get("plotly_chart"))
        app.radio(key="view_nav_race").set_value("viz_speed").run()
        self.assertFalse(app.exception)
        self.assertIn("All", app.selectbox(key="sb_sess").options)
        self.assertEqual(len(app.selectbox(key="sb_gp").options), 4)
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

    def test_excluded_source_categories_are_visible(self):
        def excluded(sql, conn=None, params=None):
            if "SELECT DISTINCT category" in sql:
                return pd.DataFrame({"category": ["Moto2", "Unrecognized", None]})
            return sample_query(sql, conn, params)
        self.read_sql.side_effect = excluded
        app = self.start_app()
        self.assertIn("Unrecognized", app.warning[0].value)
        self.assertIn("Moto2", app.warning[0].value)

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
        names = {"race_elapsed", "reconstructed_positions", "clean_laps"}
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
        timing = self.helpers["race_elapsed"](laps)
        self.assertTrue(timing["elapsed"].iloc[1:].isna().all())
        pivot = timing.pivot(index="lap_number", columns="rider", values="elapsed")
        self.assertEqual(pivot.index.tolist(), [1, 2, 3])

    def test_retirement_and_missing_active_rider_have_distinct_outcomes(self):
        laps = pd.DataFrame({"rider": ["A", "A", "A", "B"],
                             "lap_number": [1, 2, 3, 1], "lap_sec": [100., 100., 100., 101.]})
        classification = pd.DataFrame({"rider": ["A", "B"], "total_laps": [3, 1]})
        positions = self.helpers["reconstructed_positions"](laps, classification)
        self.assertEqual(positions.groupby("lap_number").size().tolist(), [2, 1, 1])
        classification.loc[1, "total_laps"] = 3
        positions = self.helpers["reconstructed_positions"](laps, classification)
        self.assertEqual(positions["lap_number"].unique().tolist(), [1])

    def test_pace_cleaning_keeps_valid_laps_from_different_sessions(self):
        laps = pd.DataFrame({
            "session_id": ["fast"] * 4 + ["slow"] * 4,
            "lap_sec": [60., 61., 62., 100., 120., 121., 122., 200.],
            "is_pit": [False] * 8,
        })
        cleaned = self.helpers["clean_laps"](laps)
        self.assertEqual(cleaned.groupby("session_id").size().to_dict(), {"fast": 3, "slow": 3})
        self.assertEqual(cleaned["lap_sec"].tolist(), [60., 61., 62., 120., 121., 122.])

    def test_pace_cleaning_rejects_invalid_times_and_pit_only_sessions(self):
        laps = pd.DataFrame({
            "session_id": ["valid"] * 6 + ["pit", "invalid"],
            "lap_sec": [60., np.nan, np.inf, 0., -1., 61., 120., np.nan],
            "is_pit": [False] * 6 + [True, False],
        })
        self.assertEqual(self.helpers["clean_laps"](laps)["lap_sec"].tolist(), [60., 61.])
        missing = pd.DataFrame({"session_id": ["missing"], "lap_sec": [None], "is_pit": [False]})
        self.assertTrue(self.helpers["clean_laps"](missing).empty)
        missing["rider"] = "A"
        missing["lap_number"] = 1
        self.assertTrue(self.helpers["race_elapsed"](missing)["elapsed"].isna().all())


class PremierScopeTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.execute("ATTACH DATABASE ':memory:' AS dbo")
        self.db.execute("CREATE TABLE dbo.sessions (session_id TEXT, category TEXT)")
        self.db.executemany("INSERT INTO dbo.sessions VALUES (?, ?)", [
            ("modern", "MotoGP™"), ("plain", "MotoGP"), ("variant", " motogp "),
            ("historic", "500cc"), ("moto2", "Moto2"), ("moto3", "Moto3"),
            ("unknown", "Unrecognized"), ("missing", None),
        ])
        self.db.execute("CREATE TABLE classifications (session_id TEXT, points REAL, status TEXT)")
        self.db.executemany("INSERT INTO classifications VALUES (?, ?, ?)", [
            ("modern", 25, "INSTND"), ("historic", 20, "OUTSTND"),
            ("moto2", 100, "OUTSTND"), ("moto3", 100, "OUTSTND"),
        ])
        tree = ast.parse(DASHBOARD.read_text(encoding="utf-8"))
        nodes = [
            node for node in tree.body
            if (isinstance(node, ast.FunctionDef) and node.name == "premier_q")
            or (isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "PREMIER_CATEGORY" for target in node.targets
            ))
        ]
        self.queries = []
        def execute(sql, params=None):
            self.queries.append(sql)
            # SQLite accepts the same relational query without SQL Server's Unicode literal prefix.
            return pd.read_sql_query(sql.replace("N'", "'"), self.db, params=params)
        self.helpers = {"q": execute}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(DASHBOARD), "exec"), self.helpers)

    def test_supported_aliases_and_historical_sessions_share_the_same_scope(self):
        result = self.helpers["premier_q"]("SELECT session_id FROM sessions ORDER BY session_id")
        self.assertEqual(result["session_id"].tolist(), ["historic", "modern", "plain", "variant"])

    def test_other_classes_cannot_change_points_or_race_denominators(self):
        result = self.helpers["premier_q"](
            "SELECT SUM(c.points) AS points, COUNT(*) AS races FROM classifications c "
            "JOIN sessions s ON c.session_id = s.session_id"
        )
        self.assertEqual(result.iloc[0].to_dict(), {"points": 45, "races": 2})
        historic = self.helpers["premier_q"](
            "SELECT session_id FROM sessions WHERE session_id = ?", ["historic"]
        )
        self.assertEqual(historic["session_id"].tolist(), ["historic"])


if __name__ == "__main__":
    unittest.main()
