import ast
import base64
import json
import io
import math
import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import numpy as np
import streamlit as st
from PIL import Image
from streamlit.testing.v1 import AppTest
from translations import get_translator
from category_scope import CATEGORY_FAMILIES, category_sql
from circuit_catalog import circuit_details, circuit_key, normalized_name, projected_outline


DASHBOARD = Path(__file__).with_name("dashboard.py")


def sample_query(sql, conn=None, params=None):
    """Supply explicit test data; never open a database connection."""
    sql = " ".join(sql.split())
    if "SELECT DISTINCT category FROM sessions WHERE event_id" in sql or "SELECT DISTINCT category FROM sessions WHERE 1=1" in sql:
        return pd.DataFrame({"category": [labels[0] for labels in CATEGORY_FAMILIES.values()]})
    if "SELECT DISTINCT category" in sql:
        return pd.DataFrame(columns=["category"])
    if "SELECT DISTINCT season_year" in sql:
        return pd.DataFrame({"season_year": [2026, 2025]})
    if "SELECT event_id, circuit_name, circuit_place, country_name" in sql:
        return pd.DataFrame([
            dict(event_id="jerez", circuit_name="Circuito de Jerez - Ángel Nieto", circuit_place="Jerez", country_name="Spain"),
            dict(event_id="montjuic", circuit_name="Montjuïc", circuit_place="Barcelona", country_name="Spain"),
        ])
    if "SELECT e.circuit_name, e.short_name" in sql:
        return pd.DataFrame([
            dict(circuit_name="Circuito de Jerez - Ángel Nieto" if params == ["jerez"] else "Montjuïc",
                 short_name="SPA", circuit_place="Sample City",
                 country_name="Spain", season_year=year, rider=f"Sample Rider {position}",
                 constructor="Sample Bike", team_name="Sample Team",
                 position=position, points=26 - position, best_lap_time=None, top_speed=None)
            for year in [2025, 2026] for position in [1, 2, 3]
        ])
    if "MIN(l.lap_time) AS best_lap" in sql:
        return pd.DataFrame(columns=["season_year", "rider", "best_lap"])
    if "MAX(l.speed_kmh) AS max_speed, AVG" in sql:
        return pd.DataFrame(columns=["season_year", "max_speed", "avg_speed"])
    if "COUNT(DISTINCT CASE WHEN s.session_type" in sql:
        return pd.DataFrame({"Year": [2025, 2026], "Sessions": [1, 2], "Races": [1, 2]})
    if "SELECT r.rider_id, r.full_name FROM riders r WHERE EXISTS" in sql:
        return pd.DataFrame({"rider_id": ["sample-rider", "sample-rider-2"],
                             "full_name": ["Sample Rider 1", "Sample Rider 2"]})
    if "SELECT DISTINCT full_name" in sql:
        return pd.DataFrame({"full_name": ["Sample Rider 1", "Sample Rider 2"]})
    if "SELECT e.season_year, e.short_name, e.date_end, s.session_type" in sql:
        return pd.DataFrame([
            dict(season_year=year, short_name="QAT", date_end=f"{year}-11-08",
                 session_type="RAC", session_label="Race", session_id=f"{year}-{category}",
                 category=category, rider_id="sample-rider", position=position, points=points, best_lap_time=None,
                 top_speed=None, status="INSTND", team_name="Sample Team",
                 constructor="Sample Bike", circuit_name="Sample Circuit")
            for year, category, position, points in [
                (2025, "Moto3", 1, 25), (2026, "Moto2", 2, 20), (2026, "MotoGP", 3, 16)
            ]
        ])
    if "SELECT s.session_id, e.season_year" in sql:
        return pd.DataFrame({
            "session_id": ["2025-Moto3", "2026-Moto2", "2026-MotoGP"],
            "season_year": [2025, 2026, 2026], "short_name": ["QAT"] * 3,
            "date_end": ["2025-11-08", "2026-11-08", "2026-11-08"],
            "position": [2, 1, 4],
        })
    if "COUNT(*) AS standings" in sql:
        return pd.DataFrame([
            dict(season_year=2025, category="Moto3", standings=3, classifications=3, laps=0, sectors=0),
            dict(season_year=2026, category="MotoGP", standings=0, classifications=6, laps=9, sectors=8),
        ])
    if "SELECT cs.season_year, cs.category, cs.rider_id" in sql:
        return pd.DataFrame(columns=[
            "season_year", "category", "rider_id", "rider", "position", "points",
            "constructor", "is_final", "source_url",
        ])
    if "FROM championship_standings" in sql:
        return pd.DataFrame(columns=["position", "rider", "points", "constructor", "is_final", "source_url"])
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
            "status": "INSTND", "source_kind": "official-api",
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
        patch("rider_numbers.DEFAULT_BUNDLE", DASHBOARD.parent / "__no-number-artwork-test-bundle__").start()
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

    def test_paddock_link_is_available_in_the_sidebar_in_each_language(self):
        app = self.start_app()
        for language, label in [
            ("🇬🇧 English", "Open Paddock App"),
            ("🇪🇸 Español", "Abrir la app Paddock"),
            ("🇮🇹 Italiano", "Apri l'app Paddock"),
        ]:
            app.selectbox(key="language").select(language).run()
            self.assertFalse(app.exception)
            links = app.sidebar.get("link_button")
            self.assertEqual(len(links), 1)
            self.assertEqual(links[0].proto.url, "https://motogp-data.com/paddock/")
            self.assertEqual(links[0].proto.label, label)
        app.selectbox(key="nav_group").set_value("nav_riders").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.sidebar.get("link_button")[0].proto.url, "https://motogp-data.com/paddock/")

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

    def test_rider_career_defaults_to_all_classes_and_does_not_merge_points(self):
        app = self.start_app()
        app.selectbox(key="sb_category").set_value("350cc").run()
        app.selectbox(key="nav_group").set_value("nav_riders").run()
        self.assertFalse(app.exception)
        self.assertFalse(any(widget.key == "sb_category" for widget in app.selectbox))
        self.assertEqual(app.selectbox(key="pp_yr").value, "All")
        self.assertEqual(set(app.multiselect(key="profile_categories").value), {"MotoGP", "Moto2", "Moto3"})
        summary = app.dataframe[0].value.set_index("Category")
        self.assertEqual(summary["Points"].to_dict(), {"Moto2": 20, "Moto3": 25, "MotoGP": 16})
        season_table = next(table.value for table in app.dataframe
                            if "Year" in table.value and "Category" in table.value)
        self.assertEqual(len(season_table[season_table["Year"] == 2026]), 2)
        self.assertEqual(app.metric[5].value, "—")
        self.assertEqual(app.metric[2].value, "1")
        career_sql = next(call.args[0] for call in self.read_sql.call_args_list
                          if "SELECT e.season_year, e.short_name, e.date_end, s.session_type" in call.args[0])
        for family in CATEGORY_FAMILIES:
            self.assertIn(category_sql(family), career_sql)
        app.multiselect(key="profile_categories").set_value(["Moto3"]).run()
        self.assertEqual(app.dataframe[0].value["Category"].tolist(), ["Moto3"])

    def test_historical_profile_keeps_partial_scores_and_efficiency_unavailable(self):
        def historical(sql, conn=None, params=None):
            data = sample_query(sql, conn, params)
            if "SELECT e.season_year, e.short_name, e.date_end, s.session_type" in sql:
                data = data.iloc[:2].copy()
                data["category"] = "50cc"
                data["season_year"] = [1971, 1972]
                data["points"] = [None, 3.0]
            return data

        self.read_sql.side_effect = historical
        app = self.start_app()
        app.selectbox(key="nav_group").set_value("nav_riders").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[5].value, "—")
        self.assertTrue(pd.isna(app.dataframe[0].value["Points"].iloc[0]))
        season_points = next(
            figure for figure in (json.loads(chart.proto.spec) for chart in app.get("plotly_chart"))
            if figure["layout"].get("title", {}).get("text") == get_translator("en")(
                "season_points_title", pilot="Sample Rider 1"
            )
        )
        self.assertEqual(season_points["data"][0]["x"], ["1972"])
        self.assertNotIn("NaN", json.dumps(season_points))
        season_table = next(table.value for table in app.dataframe
                            if "Year" in table.value and "Pts %" in table.value)
        self.assertTrue(season_table["Pts %"].isna().all())

    def test_reviewed_rider_identity_uses_ids_and_season_class_gated_portrait(self):
        marc = "f55b433d-38b8-4d1d-bb3a-a709c82a0260"

        def identity_query(sql, conn=None, params=None):
            if "SELECT r.rider_id, r.full_name FROM riders r WHERE EXISTS" in sql:
                return pd.DataFrame({"rider_id": [marc, "unpictured"],
                                     "full_name": ["Marc Marquez", "Marc Marquez"]})
            rows = sample_query(sql, conn, params)
            if "SELECT e.season_year, e.short_name, e.date_end, s.session_type" in sql:
                self.assertIn("WHERE c.rider_id = ?", sql)
                self.assertNotIn("WHERE r.full_name = ?", sql)
                rows["rider_id"] = params[0]
            return rows

        self.read_sql.side_effect = identity_query
        app = self.start_app()
        app.selectbox(key="nav_group").set_value("nav_riders").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="profile_rider").value, marc)
        self.assertFalse(app.get("image"))
        app.selectbox(key="pp_yr").set_value(2026).run()
        for label in ["🇬🇧 English", "🇪🇸 Español", "🇮🇹 Italiano"]:
            app.selectbox(key="language").select(label).run()
            self.assertFalse(app.exception)
            self.assertFalse(app.warning)
            self.assertEqual(len(app.get("image")), 1)
            captions = " ".join(caption.value for caption in app.caption)
            self.assertIn("Denkmit", captions)
            self.assertIn("https://creativecommons.org/licenses/by-sa/4.0/", captions)
            self.assertIn("Ducati Lenovo Team", captions)
            self.assertIn("1993-02-17", " ".join(markdown.value for markdown in app.markdown))
        app.selectbox(key="pp_yr").set_value(2025).run()
        self.assertFalse(app.exception)
        self.assertFalse(app.get("image"))
        app.multiselect(key="profile_categories").set_value(["Moto2"]).run()
        app.selectbox(key="pp_yr").set_value(2026).run()
        self.assertFalse(app.exception)
        self.assertFalse(app.get("image"))
        app.selectbox(key="profile_rider").set_value("unpictured").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="pp_yr").value, "All")
        self.assertFalse(app.get("image"))
        self.assertNotIn("1993-02-17", " ".join(markdown.value for markdown in app.markdown))

    def test_number_artwork_displays_labeled_selected_scope(self):
        image = io.BytesIO()
        Image.new("RGBA", (3, 3), "red").save(image, format="PNG")
        asset = {"season": 2026, "category": "MotoGP", "number": 12,
                 "source_url": "https://photos.motogp.com/test.png"}
        def artwork(rider_id, season, categories):
            return [(asset, image.getvalue())] if rider_id == "sample-rider" and season == 2026 and "MotoGP" in categories else []

        with patch("rider_numbers.list_numbers", side_effect=artwork):
            app = self.start_app()
            app.selectbox(key="nav_group").set_value("nav_riders").run()
            self.assertFalse(app.get("image"))
            app.selectbox(key="pp_yr").set_value(2026).run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.get("image")), 1)
            self.assertIn("2026 · MotoGP · #12", " ".join(c.value for c in app.caption))
            app.multiselect(key="profile_categories").set_value(["Moto2"]).run()
            self.assertFalse(app.get("image"))

    def test_legacy_named_rider_preference_preserves_unique_identity_filters(self):
        app = self.start_app()
        app.selectbox(key="nav_group").set_value("nav_riders").run()
        app.selectbox(key="nav_group").set_value("nav_overview").run()
        saved = app.session_state["_view_filters"]
        saved["viz_profile"].update({
            "profile_rider": "Sample Rider 1", "_profile_rider": "Sample Rider 1",
            "profile_categories": ["Moto3"], "pp_yr": 2025,
        })
        app.session_state["_view_filters"] = saved
        app.selectbox(key="nav_group").set_value("nav_riders").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="profile_rider").value, "sample-rider")
        self.assertEqual(app.multiselect(key="profile_categories").value, ["Moto3"])
        self.assertEqual(app.selectbox(key="pp_yr").value, 2025)

    def test_invalid_rider_catalog_reports_configuration_error_not_a_fallback(self):
        app = self.start_app()
        with patch("rider_profiles.read_enrichment", side_effect=ValueError("Invalid reviewed catalog")):
            app.selectbox(key="nav_group").set_value("nav_riders").run()
        self.assertFalse(app.exception)
        self.assertIn("Invalid reviewed catalog", " ".join(error.value for error in app.error))
        self.assertFalse(app.get("image"))

    def test_career_timeline_uses_official_ranks_and_limits_race_detail_to_one_year(self):
        def career_query(sql, conn=None, params=None):
            if "SELECT cs.season_year, cs.category, cs.rider_id" in sql:
                self.assertEqual(params, ["sample-rider"])
                self.assertIn("cs.is_final=1", sql)
                return pd.DataFrame([
                    dict(season_year=year, category=category, rider_id="sample-rider", rider="Sample Rider 1",
                         position=rank, points=None, constructor=None, is_final=final,
                         source_url="https://example.test/official")
                    for year, category, rank, final in [
                        (2025, "Moto3", 1, True), (2026, "Moto2", 3, True),
                        (2026, "MotoGP", 1, False), (2024, "125cc", 2, True),
                    ]
                ])
            return sample_query(sql, conn, params)

        self.read_sql.side_effect = career_query
        app = self.start_app()
        app.selectbox(key="nav_group").set_value("nav_riders").run()
        for label, language in [("🇬🇧 English", "en"), ("🇪🇸 Español", "es"), ("🇮🇹 Italiano", "it")]:
            app.selectbox(key="language").select(label).run()
            self.assertFalse(app.exception)
            self.assertFalse(app.warning)
            translator = get_translator(language)
            figures = [json.loads(chart.proto.spec) for chart in app.get("plotly_chart")]
            timeline = next(fig for fig in figures if fig["data"][0].get("name") == translator("career_recorded_season"))
            self.assertEqual(set(timeline["data"][0]["y"]), {"125cc", "Moto3", "Moto2", "MotoGP"})
            titles = next(trace for trace in timeline["data"] if trace.get("name") == translator("career_official_title"))
            self.assertEqual(titles["y"], ["Moto3"])
            results = next(fig for fig in figures
                           if fig["layout"].get("title", {}).get("text") == translator(
                               "race_results_title", pilot="Sample Rider 1"))
            self.assertEqual(len(results["data"]), 2)
            self.assertTrue(all("2026" in trace["name"] for trace in results["data"]))
        app.selectbox(key="pp_yr").set_value(2024).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[1].value, "0")
        self.assertEqual(len(app.get("plotly_chart")), 1)

    def test_race_detail_without_classified_finishes_keeps_timeline_not_a_nan_chart(self):
        def retired_query(sql, conn=None, params=None):
            rows = sample_query(sql, conn, params)
            if "SELECT e.season_year, e.short_name, e.date_end, s.session_type" in sql:
                rows["position"] = np.nan
                rows["status"] = "OUTSTND"
            return rows

        self.read_sql.side_effect = retired_query
        app = self.start_app()
        app.selectbox(key="nav_group").set_value("nav_riders").run()
        self.assertFalse(app.exception)
        self.assertIn(get_translator("en")("no_classified_finishes"), [info.value for info in app.info])
        figures = [json.loads(chart.proto.spec) for chart in app.get("plotly_chart")]
        self.assertTrue(any(fig["data"][0].get("name") == "Recorded season" for fig in figures))
        self.assertFalse(any(fig["layout"].get("title", {}).get("text") == get_translator("en")(
            "race_results_title", pilot="Sample Rider 1"
        ) for fig in figures))

    def test_champions_matrix_keeps_gaps_joint_winners_and_final_only_sources(self):
        def champion_query(sql, conn=None, params=None):
            if "SELECT cs.season_year, cs.category, cs.rider_id" in sql:
                self.assertIn(category_sql("premier", "cs.category"), sql)
                self.assertIn("cs.is_final=1", sql)
                return pd.DataFrame([
                    dict(season_year=year, category="500cc", rider_id=rider, rider=rider,
                         position=rank, points=None, constructor=None, is_final=final,
                         source_url="https://example.test/" + rider)
                    for year, rider, rank, final in [
                        (1970, "Alpha", 1, True), (1970, "Beta", 1, True),
                        (1970, "Runner-up", 2, True), (1972, "Gamma", 1, True),
                        (1973, "Provisional", 1, False),
                    ]
                ])
            return sample_query(sql, conn, params)

        self.read_sql.side_effect = champion_query
        app = self.start_app()
        app.session_state["selected_view_nav_history"] = "viz_crossyear"
        app.selectbox(key="nav_group").set_value("nav_history")
        for label, language in [("🇬🇧 English", "en"), ("🇪🇸 Español", "es"), ("🇮🇹 Italiano", "it")]:
            translator = get_translator(language)
            app.selectbox(key="language").select(label)
            with patch("streamlit.selectbox", return_value=translator("cross_champions_matrix")):
                app.run()
            self.assertFalse(app.exception)
            self.assertFalse(app.warning)
            figure = json.loads(app.get("plotly_chart")[0].proto.spec)
            self.assertEqual(figure["data"][0]["x"], [1970, 1971, 1972])
            self.assertEqual(figure["data"][0]["customdata"], [["Alpha & Beta", "", "Gamma"]])
            self.assertEqual(figure["data"][0]["text"][0][0], "Alpha & Beta")
            self.assertEqual(len(app.dataframe[0].value), 3)
        app.toggle(key="champion_year_rows").set_value(True)
        with patch("streamlit.selectbox", return_value=get_translator("it")("cross_champions_matrix")):
            app.run()
        self.assertFalse(app.exception)
        figure = json.loads(app.get("plotly_chart")[0].proto.spec)
        self.assertEqual(figure["data"][0]["x"], ["500cc"])
        self.assertEqual(figure["data"][0]["y"], [1970, 1971, 1972])
        self.assertEqual(figure["data"][0]["customdata"], [["Alpha & Beta"], [""], ["Gamma"]])

    def test_constructor_eras_show_unknown_victories_and_separate_actual_classes(self):
        def constructor_query(sql, conn=None, params=None):
            if "COUNT(*) AS wins" in sql and "GROUP BY e.season_year, s.category" in sql:
                self.assertIn("COALESCE(c.constructor_name, t.constructor)", sql)
                return pd.DataFrame([
                    dict(season_year=1970, category=category, constructor=constructor, wins=wins)
                    for category, constructor, wins in [
                        ("500cc", "MV Agusta", 3), ("500cc", None, 1), ("350cc", "Yamaha", 2),
                    ] if category != "350cc" or category_sql("350cc") in sql
                ])
            return sample_query(sql, conn, params)

        self.read_sql.side_effect = constructor_query
        app = self.start_app()
        app.session_state["selected_view_nav_history"] = "viz_crossyear"
        app.selectbox(key="nav_group").set_value("nav_history")
        with patch("streamlit.selectbox", return_value=get_translator("en")("cross_constructor_eras")):
            app.run()
        app.multiselect(key="scope_categories").set_value(["premier", "350cc"])
        for label, language in [("🇬🇧 English", "en"), ("🇪🇸 Español", "es"), ("🇮🇹 Italiano", "it")]:
            translator = get_translator(language)
            app.selectbox(key="language").select(label)
            with patch("streamlit.selectbox", return_value=translator("cross_constructor_eras")):
                app.run()
            self.assertFalse(app.exception)
            self.assertFalse(app.warning)
            table = next(table.value for table in app.dataframe
                         if translator("constructor_win_share") in table.value)
            self.assertEqual(set(table[translator("category")]), {"500cc", "350cc"})
            self.assertEqual(table[translator("wins")].sum(), 6)
            unknown = table[table[translator("constructor")].eq(translator("constructor_unknown"))]
            self.assertEqual(unknown[translator("constructor_win_share")].tolist(), [25])
            np.testing.assert_allclose(table.groupby(translator("category"))[
                translator("constructor_win_share")].sum(), 100)
            figure = next(
                figure for figure in (json.loads(chart.proto.spec) for chart in app.get("plotly_chart"))
                if any(trace.get("name") == translator("constructor_unknown") for trace in figure["data"])
            )
            self.assertEqual(figure["layout"]["xaxis"]["type"], "category")
            self.assertEqual({annotation["text"] for annotation in figure["layout"]["annotations"]},
                             {"500cc", "350cc"})

    def test_availability_heatmap_is_quality_only_and_localized(self):
        app = self.start_app()
        self.assertNotIn("Archive availability by year and class", [heading.value for heading in app.subheader])
        app.radio(key="home_view").set_value("home_coverage").run()
        app.radio(key="archive_availability_metric").set_value("sectors").run()
        for label, language in [("🇬🇧 English", "en"), ("🇪🇸 Español", "es"), ("🇮🇹 Italiano", "it")]:
            app.selectbox(key="language").select(label).run()
            self.assertFalse(app.exception)
            translator = get_translator(language)
            self.assertIn(translator("archive_availability_title"), [heading.value for heading in app.subheader])
            figure = next(json.loads(chart.proto.spec) for chart in app.get("plotly_chart")
                          if json.loads(chart.proto.spec)["layout"].get("title", {}).get("text")
                          == translator("archive_metric_sectors"))
            self.assertEqual(figure["data"][0]["x"], [2025, 2026])
            self.assertEqual(figure["data"][0]["y"], ["MotoGP", "Moto3"])
        app.selectbox(key="nav_group").set_value("nav_riders").run()
        self.assertFalse(app.exception)
        self.assertNotIn(get_translator("it")("archive_availability_title"), [h.value for h in app.subheader])
        self.assertFalse(app.warning)

    def test_archive_availability_query_counts_sources_without_join_fanout(self):
        tree = ast.parse(DASHBOARD.read_text(encoding="utf-8"))
        loader = next(node for node in tree.body
                      if isinstance(node, ast.FunctionDef) and node.name == "load_archive_availability")
        loader.decorator_list = []
        with closing(sqlite3.connect(":memory:")) as connection:
            connection.executescript("""
                ATTACH DATABASE ':memory:' AS dbo;
                CREATE TABLE events(event_id TEXT, season_year INT);
                CREATE TABLE sessions(session_id TEXT, event_id TEXT, category TEXT, session_type TEXT, status TEXT);
                CREATE TABLE championship_standings(season_year INT, category TEXT);
                CREATE TABLE dbo.vw_effective_classifications(session_id TEXT);
                CREATE TABLE laps(session_id TEXT, t1 TEXT, t2 TEXT, t3 TEXT, t4 TEXT);
                INSERT INTO events VALUES ('a',1970),('b',1972),('c',1973);
                INSERT INTO sessions VALUES ('race','a','500cc','RAC','FINISHED'),
                    ('empty','b','500cc','RAC','FINISHED'),('pending','c','500cc','RAC','PENDING');
                INSERT INTO championship_standings VALUES (1970,'500cc'),(1970,'500cc'),(1970,'500cc'),(1975,'350cc');
                INSERT INTO dbo.vw_effective_classifications VALUES ('race'),('race'),('pending');
                INSERT INTO laps VALUES ('race','1','2','3','4'),('race','1','2','3','4'),
                    ('race','1','2','3',NULL),('pending','1','2','3','4');
            """)
            namespace = {
                "scope_predicate": lambda families, column="category": " OR ".join(
                    "(" + category_sql(family, column) + ")" for family in families),
                "q": lambda sql: pd.io.sql.read_sql(sql.replace("N'", "'"), connection),
            }
            exec(compile(ast.Module(body=[loader], type_ignores=[]), str(DASHBOARD), "exec"), namespace)
            rows = namespace["load_archive_availability"](("premier",))
        counts = rows.groupby("season_year")[["standings", "classifications", "laps", "sectors"]].sum()
        self.assertEqual(counts.loc[1970].tolist(), [3, 2, 3, 2])
        self.assertEqual(counts.loc[1972].tolist(), [0, 0, 0, 0])
        self.assertEqual(counts.index.tolist(), [1970, 1972])

    def test_constructor_only_history_and_recorded_winner_pace_render(self):
        def historical(sql, conn=None, params=None):
            if "COUNT(DISTINCT r.rider_id) AS riders" in sql:
                self.assertIn("COALESCE(c.constructor_name, t.constructor)", sql)
                return pd.DataFrame([
                    dict(season_year=1984, constructor="Zundapp", riders=2,
                         total_pts=None, wins=1, race_entries=3)
                ])
            if "c.best_lap_time, l.lap_time" in sql:
                return pd.DataFrame([
                    dict(season_year=2026, date_end="2026-11-22", circuit_name=name,
                         circuit_place=name, session_id=identity, rider="Winner",
                         best_lap_time=None, lap_time=lap)
                    for name, identity, lap in [
                        ("Estoril", "estoril", "1:45.000"),
                        ("Algarve", "algarve", "1:42.000"),
                        ("Algarve", "algarve", "1:43.000"),
                    ]
                ])
            return sample_query(sql, conn, params)

        self.read_sql.side_effect = historical
        app = self.start_app()
        app.session_state["selected_view_nav_history"] = "viz_crossyear"
        app.selectbox(key="nav_group").set_value("nav_history")
        for chart in ["cross_constructor_evolution", "cross_circuit_pace"]:
            with self.subTest(chart=chart):
                with patch("streamlit.selectbox", return_value=get_translator("en")(chart)):
                    app.run()
                self.assertFalse(app.exception)
                self.assertTrue(app.get("plotly_chart"))
        figure = json.loads(app.get("plotly_chart")[0].proto.spec)
        self.assertEqual({trace["name"] for trace in figure["data"]}, {"Estoril", "Algarve"})
        coordinates = next(trace for trace in figure["data"] if trace["name"] == "Algarve")["x"]
        count = (np.frombuffer(base64.b64decode(coordinates["bdata"]), dtype=coordinates["dtype"]).size
                 if isinstance(coordinates, dict) else len(coordinates))
        self.assertEqual(count, 1)

    def test_titles_are_official_only_and_missing_poles_stay_unavailable(self):
        def rankings(sql, conn=None, params=None):
            if "AS race_starts" in sql:
                return pd.DataFrame([dict(
                    rider="Historical Rider", nationality="IT", race_starts=12, sprint_starts=0,
                    race_wins=10, sprint_wins=0, race_podiums=12, sprint_podiums=0,
                    poles=0, qualifying_entries=0, race_finishes=12, dnfs=0, total_pts=150,
                    seasons=1, first_year=1970, last_year=1970,
                )])
            if "COUNT(*) AS championships" in sql:
                self.assertIn("cs.is_final=1", sql)
                self.assertNotIn("UNION ALL", sql)
                self.assertNotIn("SUM(c.points)", sql)
                return pd.DataFrame([dict(rider="Historical Rider", championships=1)])
            return sample_query(sql, conn, params)

        self.read_sql.side_effect = rankings
        app = self.start_app()
        app.session_state["selected_view_nav_riders"] = "viz_rankings"
        app.selectbox(key="nav_group").set_value("nav_riders").run()
        self.assertFalse(app.exception)
        full = next(table.value for table in app.dataframe if "Nationality" in table.value)
        self.assertEqual(full["Titles"].tolist(), [1])
        self.assertTrue(full["Poles"].isna().all())
        self.assertTrue(full["Pts %"].isna().all())

    def test_concentration_does_not_divide_official_full_season_scores_by_imported_starts(self):
        def partial(sql, conn=None, params=None):
            if "SELECT cs.position" in sql:
                return pd.DataFrame([
                    dict(position=rank, rider=f"Rider {rank}", points=1000 - 100 * rank,
                         constructor="Bike", is_final=True, source_url=None)
                    for rank in [1, 2, 3]
                ])
            if "SUM(c.points) AS pts" in sql:
                return pd.DataFrame([
                    dict(season_year=2026, rider=f"Rider {rank}", pts=points, races=1, sprints=0)
                    for rank, points in [(1, 25), (2, 20), (3, 16)]
                ])
            return sample_query(sql, conn, params)
        self.read_sql.side_effect = partial
        app = self.start_app()
        app.session_state["selected_view_nav_history"] = "viz_crossyear"
        app.selectbox(key="nav_group").set_value("nav_history")
        with patch("streamlit.selectbox", return_value=get_translator("en")("cross_championship_concentration")):
            app.run()
        self.assertFalse(app.exception)
        table = next(table.value for table in app.dataframe if "Champion %" in table.value)
        self.assertEqual(table["Champion %"].tolist(), [100])
        self.assertEqual(table["Champion Pts"].tolist(), [900])

    def test_grid_proxy_includes_unclassified_starters_in_conversion_denominator(self):
        def qualifying(sql, conn=None, params=None):
            if "s.category, s.session_number" in sql:
                return pd.DataFrame([
                    dict(event_id="por", season_year=2026, category="MotoGP",
                         session_number=stage, rider_id=rider, position=position)
                    for stage, riders in [(1, ["a", "b", "q1-only", "dns"]),
                                          (2, ["a", "b", *map(str, range(10))])]
                    for position, rider in enumerate(riders, 1)
                ])
            if "c.position AS finish_pos, c.status" in sql:
                return pd.DataFrame([
                    dict(event_id="por", season_year=2026, short_name="POR", category="MotoGP",
                         session_id="por-race", session_type="RAC", rider_id=rider,
                         rider=rider, finish_pos=position, status=status)
                    for rider, position, status in [
                        ("a", 1, "INSTND"), ("b", None, "OUTSTND"),
                        ("q1-only", 3, "INSTND"), ("dns", None, "NOTSTARTED"),
                    ]
                ])
            return sample_query(sql, conn, params)
        self.read_sql.side_effect = qualifying
        app = self.start_app()
        app.session_state["selected_view_nav_season"] = "viz_grid"
        app.selectbox(key="nav_group").set_value("nav_season").run()
        self.assertFalse(app.exception)
        self.assertIn("50.0%", " ".join(element.value for element in app.markdown))
        app.slider[1].set_value(13).run()
        self.assertFalse(app.exception)
        self.assertIn("66.7%", " ".join(element.value for element in app.markdown))

    def test_views_restore_their_own_filters_without_inheriting_category(self):
        app = self.start_race_analysis()
        app.selectbox(key="sb_category").set_value("lightweight").run()
        app.selectbox(key="sb_gp").set_value("qat").run()
        app.selectbox(key="nav_group").set_value("nav_riders").run()
        app.multiselect(key="profile_categories").set_value(["Moto2"]).run()
        app.selectbox(key="nav_group").set_value("nav_season").run()
        self.assertEqual(app.selectbox(key="sb_category").value, "premier")
        app.selectbox(key="sb_category").set_value("intermediate").run()
        app.selectbox(key="nav_group").set_value("nav_race").run()
        self.assertEqual(app.selectbox(key="sb_category").value, "lightweight")
        self.assertEqual(app.selectbox(key="sb_gp").value, "qat")
        app.selectbox(key="nav_group").set_value("nav_riders").run()
        self.assertEqual(app.multiselect(key="profile_categories").value, ["Moto2"])
        app.selectbox(key="language").select("🇮🇹 Italiano").run()
        self.assertEqual(app.multiselect(key="profile_categories").value, ["Moto2"])

    def test_race_category_choices_are_bound_to_the_selected_event(self):
        def available_categories(sql, conn=None, params=None):
            if "SELECT DISTINCT category FROM sessions WHERE event_id" in sql:
                return pd.DataFrame({"category": ["Moto2"] if params == ["qat"] else ["MotoGP", "Moto3"]})
            return sample_query(sql, conn, params)
        self.read_sql.side_effect = available_categories
        app = self.start_race_analysis()
        self.assertEqual(app.selectbox(key="sb_category").options, ["MotoGP / 500cc", "Moto3 / 125cc"])
        app.selectbox(key="sb_gp").set_value("qat").run()
        self.assertEqual(app.selectbox(key="sb_category").value, "intermediate")
        self.assertEqual(app.selectbox(key="sb_gp").value, "qat")
        self.assertEqual(app.selectbox(key="sb_category").options, ["Moto2 / 250cc"])

    def test_coverage_can_compare_classes_without_pooling_the_detailed_views(self):
        app = self.start_app()
        app.radio(key="home_view").set_value("home_coverage").run()
        app.multiselect(key="scope_categories").set_value(["premier", "intermediate"]).run()
        self.assertFalse(app.exception)
        comparison = app.dataframe[0].value
        self.assertEqual(set(comparison["Category"]), {"MotoGP / 500cc", "Moto2 / 250cc"})
        app.selectbox(key="sb_category").set_value("intermediate").run()
        self.assertEqual(app.multiselect(key="scope_categories").value, ["premier", "intermediate"])
        app.radio(key="home_view").set_value("home_championship").run()
        self.assertEqual(app.selectbox(key="sb_category").value, "premier")

    def test_circuit_details_match_names_not_reused_grand_prix_codes(self):
        record = {"id": "jerez", "name": "Circuito de Jerez - Ángel Nieto"}
        with patch("circuit_catalog.catalog", return_value={
            normalized_name(record["name"]): record,
            normalized_name("Circuito de Jerez"): record,
        }):
            self.assertEqual(circuit_details("CIRCUITO DE JEREZ – ANGEL NIETO"), record)
            self.assertEqual(circuit_key("Circuito de Jerez", "Jerez"), "jerez")
            self.assertIsNone(circuit_details("SPA"))
            self.assertNotEqual(circuit_key("Montjuïc", "Barcelona"), "jerez")
            self.assertNotEqual(circuit_key("Sample Circuit", "City A"),
                                circuit_key("Sample Circuit", "City B"))

    def test_circuit_diagram_preserves_proportions_and_rejects_invalid_geometry(self):
        x, y = projected_outline([[0, 60], [1, 60], [1, 60], [0, 60]])
        self.assertAlmostEqual(x[1], 0.5)
        self.assertEqual(y, [0, 0, 0, 0])
        for outline in [[], [[0, 0]], [[0, 0], [1, 0], [0, 1]],
                        [[0, 0], [181, 0], [0, 1], [0, 0]],
                        [[0, 0], [float("nan"), 0], [0, 1], [0, 0]]]:
            with self.assertRaises(ValueError):
                projected_outline(outline)

    def test_bundled_outlines_are_closed_and_match_the_modern_track_length(self):
        records = json.loads(DASHBOARD.with_name("circuit_catalog.json").read_text(encoding="utf-8"))["circuits"]
        for record in records:
            with self.subTest(circuit=record["id"]):
                outline = record["outline"]
                projected_outline(outline)
                self.assertTrue(record["outline_way_ids"])
                metres = 0
                for (lon1, lat1), (lon2, lat2) in zip(outline, outline[1:]):
                    a = math.sin(math.radians(lat2 - lat1) / 2) ** 2
                    a += (math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
                          * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
                    metres += 2 * 6371008.8 * math.asin(math.sqrt(min(1, a)))
                self.assertLess(abs(metres / (record["length_km"] * 1000) - 1), 0.03)

    def test_circuit_page_shows_sourced_facts_and_independent_fallbacks(self):
        record = dict(
            id="jerez", name="Circuito de Jerez - Ángel Nieto", aliases=[],
            length_km=4.423, turns=13, facts_source="https://example.com/facts",
            outline=[[0, 0], [1, 0], [0, 1], [0, 0]],
            outline_source="https://example.com/geometry", outline_license="ODbL",
            outline_license_url="https://opendatacommons.org/licenses/odbl/1-0/",
            attendance_record=dict(count=100000, year=2025, scope="weekend",
                                   source="https://example.com/attendance"),
        )
        with patch("circuit_catalog.catalog", return_value={normalized_name(record["name"]): record}):
            app = self.start_app()
            app.selectbox(key="nav_group").set_value("nav_history").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.selectbox(key="circuit_selection").value, "jerez")
            self.assertEqual([metric.value for metric in app.metric[:3]], ["4.423 km", "13", "100,000"])
            diagram = json.loads(app.get("plotly_chart")[0].proto.spec)
            self.assertEqual(diagram["layout"]["title"]["text"], "Circuit layout")
            self.assertEqual(diagram["layout"]["yaxis"]["scaleanchor"], "x")
            self.assertEqual(diagram["data"][0]["line"]["width"], 6)
            self.assertIn("2025 · GP weekend", " ".join(caption.value for caption in app.caption))
            for label, language in [("🇬🇧 English", "en"), ("🇪🇸 Español", "es"), ("🇮🇹 Italiano", "it")]:
                app.selectbox(key="language").select(label).run()
                self.assertFalse(app.exception)
                self.assertIn(get_translator(language)("circuit_layout_help"),
                              [caption.value for caption in app.caption])
            app.multiselect(key="scope_categories").set_value(["50cc"]).run()
            self.assertEqual(app.metric[0].value, "4.423 km")
            self.assertEqual(len(app.selectbox(key="circuit_selection").options), 2)
            circuit_sql = [call for call in self.read_sql.call_args_list
                           if "e.event_id IN" in call.args[0]]
            self.assertTrue(circuit_sql)
            for call in circuit_sql:
                self.assertNotIn("e.short_name = ?", call.args[0])
                self.assertEqual(call.kwargs["params"], ["jerez"])
            unknown = circuit_key("Montjuïc", "Barcelona")
            app.selectbox(key="circuit_selection").set_value(unknown).run()
            self.assertFalse(app.exception)
            self.assertIn(get_translator("it")("circuit_facts_unavailable"), [item.value for item in app.info])
            self.assertIn(get_translator("it")("circuit_diagram_unavailable"), [item.value for item in app.info])
            app.selectbox(key="circuit_selection").set_value("jerez").run()
            record.pop("attendance_record")
            record.pop("outline")
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.metric[2].value, get_translator("it")("circuit_not_available"))
            self.assertIn(get_translator("it")("circuit_diagram_unavailable"), [item.value for item in app.info])

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
                explanation = translator("session_types_explainer")
                self.assertNotEqual(explanation, "session_types_explainer")
                matching = [
                    column for column in columns
                    if any(markdown.value == explanation for markdown in column.markdown)
                ]
                self.assertEqual(len(matching), 1)
                elements = list(matching[0])
                chart_index = next(i for i, element in enumerate(elements) if element.type == "plotly_chart")
                self.assertEqual(elements[chart_index + 1].value, explanation)
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

    def test_charts_and_cards_defer_appearance_to_the_browser(self):
        app = self.start_app()
        for view in ["home_championship", "home_coverage"]:
            app.radio(key="home_view").set_value(view).run()
            self.assertFalse(app.exception)
            for chart in app.get("plotly_chart"):
                self.assertEqual(chart.proto.theme, "streamlit")
                layout = json.loads(chart.proto.spec)["layout"]
                self.assertNotIn("paper_bgcolor", layout)
                self.assertNotIn("plot_bgcolor", layout)
                self.assertNotIn("color", layout.get("font", {}))
                template = layout["template"]["layout"]
                self.assertNotEqual(template.get("paper_bgcolor"), "#ffffff")
                self.assertNotEqual(template.get("font", {}).get("color"), "#172033")
        styles = "\n".join(markdown.value for markdown in app.markdown)
        self.assertIn("background: color-mix(in srgb, currentColor 5%, transparent)", styles)
        for label, language in [
            ("🇬🇧 English", "en"), ("🇪🇸 Español", "es"), ("🇮🇹 Italiano", "it")
        ]:
            app.selectbox(key="language").select(label).run()
            self.assertIn(
                get_translator(language)("appearance_help"),
                [caption.value for caption in app.sidebar.caption],
            )

    def test_historical_championship_uses_official_order_and_fractional_points(self):
        def historical_query(sql, conn=None, params=None):
            if "SELECT DISTINCT season_year" in sql:
                return pd.DataFrame({"season_year": [2026, 1989]})
            if "FROM championship_standings" in sql:
                return pd.DataFrame({
                    "position": [1, 2, 3], "rider": ["Lawson", "Rainey", "Sarron"],
                    "points": [228, 210.5, 165.5], "constructor": ["Honda", "Yamaha", "Yamaha"],
                    "is_final": [True] * 3, "source_url": [None] * 3,
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

    def test_1970_350cc_anomalous_official_points_remain_raw_without_analytic_warnings(self):
        supplied = pd.DataFrame({
            "position": [1, 2, 3], "rider": ["Ago", "Carruthers", "Pasolini"],
            "points": [9, 28, 46], "constructor": ["MV Agusta", "Yamaha", "Benelli"],
            "is_final": [True] * 3, "source_url": [None] * 3,
        })

        def anomaly_query(sql, conn=None, params=None):
            if "SELECT DISTINCT season_year" in sql:
                return pd.DataFrame({"season_year": [1970]})
            if "SELECT cs.position" in sql and category_sql("350cc", "cs.category") in sql:
                return supplied.copy()
            if "SUM(cl.points)" in sql:
                raise AssertionError("Never reconstruct the anomalous official final")
            return sample_query(sql, conn, params)

        self.read_sql.side_effect = anomaly_query
        app = self.start_app()
        app.selectbox(key="sb_category").set_value("350cc").run()
        for label, language in [
            ("🇬🇧 English", "en"), ("🇪🇸 Español", "es"), ("🇮🇹 Italiano", "it")
        ]:
            with self.subTest(language=language):
                app.selectbox(key="language").select(label).run()
                translator = get_translator(language)
                self.assertFalse(app.exception)
                self.assertFalse(app.warning)
                table = app.dataframe[0].value
                self.assertEqual(table[translator("position")].tolist(), [1, 2, 3])
                self.assertEqual(table[translator("rider")].tolist(), ["Ago", "Carruthers", "Pasolini"])
                self.assertEqual(table[translator("points")].tolist(), [9, 28, 46])
                self.assertNotIn(translator("home_gap_to_leader"), table.columns)
                self.assertNotIn(translator("official_standings_method"), [c.value for c in app.caption])
                self.assertFalse(app.metric)
                self.assertFalse(app.get("plotly_chart"))
        app.selectbox(key="nav_group").set_value("nav_season").run()
        app.selectbox(key="sb_category").set_value("350cc").run()
        self.assertFalse(app.exception)
        self.assertFalse(app.warning)
        self.assertFalse(app.get("plotly_chart"))
        self.assertEqual(supplied["points"].tolist(), [9, 28, 46])

    def test_flagged_finals_suppress_modern_gaps_progression_and_title_margins(self):
        def anomaly_query(sql, conn=None, params=None):
            if "SELECT cs.position" in sql and category_sql("350cc", "cs.category") in sql:
                return pd.DataFrame({
                    "position": [1, 2, 3], "rider": ["Ago", "Carruthers", "Pasolini"],
                    "points": [9, 28, 46], "constructor": ["Bike"] * 3,
                    "is_final": [True] * 3, "source_url": [None] * 3,
                })
            if "SUM(cl.points)" in sql and category_sql("350cc") in sql:
                raise AssertionError("Flagged finals must not produce progression")
            if "SUM(c.points) AS pts" in sql:
                return pd.DataFrame({
                    "season_year": [2026] * 3, "rider": ["Ago", "Carruthers", "Pasolini"],
                    "pts": [9, 28, 46], "races": [3] * 3, "sprints": [0] * 3,
                    "wins": [2, 1, 0], "podiums": [3] * 3,
                })
            return sample_query(sql, conn, params)

        self.read_sql.side_effect = anomaly_query
        app = self.start_app()
        app.selectbox(key="sb_category").set_value("350cc").run()
        self.assertFalse(app.exception)
        self.assertFalse(app.warning)
        self.assertFalse(app.metric)
        self.assertFalse(app.get("plotly_chart"))
        app.selectbox(key="nav_group").set_value("nav_season").run()
        app.selectbox(key="sb_category").set_value("350cc").run()
        self.assertFalse(app.exception)
        self.assertFalse(app.get("plotly_chart"))
        app.session_state["selected_view_nav_history"] = "viz_crossyear"
        app.selectbox(key="nav_group").set_value("nav_history")
        translator = get_translator("en")
        for chart, selections in [
            ("cross_bump_chart", [translator("cross_bump_chart"), 2026]),
            ("cross_championship_concentration", [translator("cross_championship_concentration")]),
            ("cross_season_dominance", [translator("cross_season_dominance")]),
        ]:
            with self.subTest(chart=chart):
                if chart == "cross_bump_chart":
                    with patch("streamlit.selectbox", side_effect=selections):
                        app.run()
                    app.multiselect(key="scope_categories").set_value(["350cc"])
                with patch("streamlit.selectbox", side_effect=selections):
                    app.run()
                self.assertFalse(app.exception)
                self.assertFalse(app.warning)
                self.assertFalse(app.get("plotly_chart"))
                self.assertEqual(app.dataframe[0].value[translator("points")].tolist(),
                                 [9, 28, 46])

    def test_official_score_warnings_are_confined_to_category_scoped_data_quality(self):
        def quality_query(sql, conn=None, params=None):
            if "SELECT cs.season_year, cs.category, cs.position" in sql and category_sql("350cc", "cs.category") in sql:
                return pd.DataFrame([
                    dict(season_year=year, category="350cc", position=rank, points=points,
                         is_final=True, rider=f"Rider {rank}", source_url=None)
                    for year, scores in [(1970, [9, 28, 46]), (1969, [46, 28, 9])]
                    for rank, points in enumerate(scores, 1)
                ])
            return sample_query(sql, conn, params)
        self.read_sql.side_effect = quality_query
        app = self.start_app()
        self.assertFalse(app.warning)
        app.radio(key="home_view").set_value("home_coverage").run()
        self.assertFalse(app.warning)
        app.multiselect(key="scope_categories").set_value(["350cc"]).run()
        for label, language in [
            ("🇬🇧 English", "en"), ("🇪🇸 Español", "es"), ("🇮🇹 Italiano", "it")
        ]:
            app.selectbox(key="language").select(label).run()
            translator = get_translator(language)
            self.assertFalse(app.exception)
            self.assertIn(translator("official_points_verification_warning"),
                          [warning.value for warning in app.warning])
            self.assertFalse(app.sidebar.warning)
            table = next(table.value for table in app.dataframe
                         if translator("source_points_verification") in table.value)
            self.assertEqual(table[translator("season")].tolist(), [1970] * 3)
            self.assertEqual(table[translator("category")].tolist(), ["350cc"] * 3)
            self.assertEqual(table[translator("source_points_verification")].tolist(), [9, 28, 46])
        app.selectbox(key="nav_group").set_value("nav_riders").run()
        self.assertFalse(app.exception)
        self.assertFalse(app.warning)

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
        self.assertFalse(app.info)

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

    def test_unsupported_source_categories_are_only_visible_in_data_quality(self):
        def excluded(sql, conn=None, params=None):
            if "SELECT DISTINCT category" in sql and "category IS NULL" in sql:
                self.assertIn(category_sql("intermediate"), sql)
                return pd.DataFrame({"category": ["Unrecognized", None]})
            return sample_query(sql, conn, params)
        self.read_sql.side_effect = excluded
        app = self.start_app()
        self.assertFalse(app.warning)
        app.radio(key="home_view").set_value("home_coverage").run()
        self.assertIn("Unrecognized", app.warning[0].value)
        self.assertNotIn("Moto2", app.warning[0].value)
        self.assertFalse(app.sidebar.warning)
        app.selectbox(key="nav_group").set_value("nav_race").run()
        self.assertFalse(app.exception)
        self.assertFalse(app.warning)

    def test_category_changes_bind_queries_and_invalidate_cached_results(self):
        def category_query(sql, conn=None, params=None):
            data = sample_query(sql, conn, params)
            if "SUM(cl.points) AS race_pts" in sql and category_sql("intermediate") in sql:
                data["race_pts"] *= 2
            return data
        self.read_sql.side_effect = category_query
        app = self.start_app()
        app.selectbox(key="sb_category").set_value("intermediate").run()
        self.assertFalse(app.exception)
        self.assertIn("2026 Moto2 World Championship", [h.value for h in app.subheader])
        self.assertEqual(app.dataframe[0].value["Points"].tolist(), [132, 122, 92, 22])
        app.selectbox(key="language").select("🇪🇸 Español").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="sb_category").value, "intermediate")
        app.selectbox(key="sb_category").set_value("premier").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.dataframe[0].value["Puntos"].tolist(), [66, 61, 46, 11])

    def test_category_change_resets_event_session_and_rider_filters(self):
        app = self.start_race_analysis()
        app.radio(key="view_nav_race").set_value("viz_position").run()
        app.multiselect(key="pos_r").set_value(["Sample Rider 1"]).run()
        app.selectbox(key="sb_category").set_value("lightweight").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.radio(key="view_nav_race").value, "viz_position")
        self.assertEqual(app.selectbox(key="sb_gp").value, "por")
        self.assertEqual(app.selectbox(key="sb_sess").value, "Race")
        self.assertEqual(len(app.multiselect(key="pos_r").value), 3)
        lap_queries = [call.args[0] for call in self.read_sql.call_args_list
                       if "l.lap_number, l.lap_time" in call.args[0]]
        self.assertIn(category_sql("lightweight"), lap_queries[-1])
        self.assertIn("COALESCE(c.rider_number, r.number)", lap_queries[-1])
        self.assertIn("dbo.vw_effective_classifications", lap_queries[-1])

    def test_lower_class_official_current_standings_override_incomplete_race_totals(self):
        def official_query(sql, conn=None, params=None):
            if "FROM championship_standings" in sql and "SELECT cs.position" in sql:
                if category_sql("intermediate", "cs.category") in sql:
                    return pd.DataFrame({
                        "position": [1, 2], "rider": ["Sample Rider 2", "Sample Rider 1"],
                        "points": [200.5, 190], "constructor": ["Sample Bike"] * 2,
                        "is_final": [False] * 2, "source_url": [None] * 2,
                    })
            return sample_query(sql, conn, params)
        self.read_sql.side_effect = official_query
        app = self.start_app()
        app.selectbox(key="sb_category").set_value("intermediate").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.dataframe[0].value["Points"].tolist(), [200.5, 190])
        self.assertIn("Official current standings (not final)", [h.value for h in app.subheader])
        self.assertEqual(app.metric[0].value, "200.5")
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.dataframe[0].value["Rider"].tolist(), ["Sample Rider 2", "Sample Rider 1"])

    def test_standings_only_historical_category_and_missing_final_do_not_infer_points(self):
        def historical_query(sql, conn=None, params=None):
            if "SELECT DISTINCT season_year" in sql:
                return pd.DataFrame({"season_year": [1969]})
            if "SELECT event_id, short_name" in sql:
                return pd.DataFrame()
            if "SELECT cs.position" in sql:
                if category_sql("lightweight", "cs.category") in sql:
                    return pd.DataFrame({
                        "position": [1, 2], "rider": ["A", "B"], "points": [90, 70.5],
                        "constructor": ["Yamaha"] * 2, "is_final": [True] * 2,
                        "source_url": [None] * 2,
                    })
                return pd.DataFrame()
            if "SUM(cl.points)" in sql:
                raise AssertionError("Do not reconstruct historical finals")
            return sample_query(sql, conn, params)
        self.read_sql.side_effect = historical_query
        app = self.start_app()
        self.assertTrue(app.info)
        app.selectbox(key="sb_category").set_value("lightweight").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.dataframe[0].value["Points"].tolist(), [90, 70.5])
        self.assertIn("1969 125cc World Championship", [h.value for h in app.subheader])
        self.assertFalse(app.get("plotly_chart"))
        app.selectbox(key="sb_category").set_value("350cc").run()
        self.assertFalse(app.exception)
        self.assertFalse(app.dataframe)
        self.assertTrue(app.info)

    def test_lower_class_coverage_and_classification_without_laps(self):
        def no_laps(sql, conn=None, params=None):
            data = sample_query(sql, conn, params)
            if "l.lap_number, l.lap_time" in sql or "AS With_Sectors" in sql:
                return data.iloc[:0]
            if "AS n_events" in sql:
                data["n_laps"] = 0
            if "AS Sectors FROM events" in sql:
                data[["Laps", "Sectors"]] = 0
            if "SELECT c.position" in sql:
                data["source_kind"] = "external"
                data["points"] = None
                data["num"] = None
            return data
        self.read_sql.side_effect = no_laps
        app = self.start_app()
        app.selectbox(key="sb_category").set_value("80cc").run()
        app.radio(key="home_view").set_value("home_coverage").run()
        app.multiselect(key="scope_categories").set_value(["80cc"]).run()
        self.assertFalse(app.exception)
        app.selectbox(key="nav_group").set_value("nav_race").run()
        app.selectbox(key="sb_category").set_value("80cc").run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe[0].value), 3)
        self.assertTrue(any("external-derived" in caption.value for caption in app.caption))
        app.radio(key="view_nav_race").set_value("viz_laptimes").run()
        self.assertFalse(app.exception)
        self.assertTrue(app.info)

    def test_historical_bump_view_never_derives_standings(self):
        def historical_query(sql, conn=None, params=None):
            if "SELECT DISTINCT season_year" in sql:
                return pd.DataFrame({"season_year": [1969]})
            if "SELECT cs.position" in sql:
                return pd.DataFrame()
            if "SUM(cl.points)" in sql or "SUM(c.points) AS pts" in sql:
                raise AssertionError("Historical title/progression cannot be inferred")
            return sample_query(sql, conn, params)
        self.read_sql.side_effect = historical_query
        app = self.start_app()
        app.selectbox(key="sb_category").set_value("50cc").run()
        app.selectbox(key="nav_group").set_value("nav_history").run()
        app.radio(key="view_nav_history").set_value("viz_crossyear")
        # Skip the animation (the first chart) to inspect historical championship dispatch.
        with patch("streamlit.selectbox", side_effect=[
            get_translator("en")("cross_bump_chart"), 1969
        ]):
            app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any("unavailable" in info.value for info in app.info))
        self.assertFalse(app.get("plotly_chart"))

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
        self.db.execute("CREATE TABLE dbo.vw_effective_classifications AS SELECT * FROM classifications")
        tree = ast.parse(DASHBOARD.read_text(encoding="utf-8"))
        nodes = [
            node for node in tree.body
            if (isinstance(node, ast.FunctionDef) and node.name in ("premier_q", "scope_predicate"))
            or (isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "PREMIER_CATEGORY" for target in node.targets
            ))
        ]
        self.queries = []
        def execute(sql, params=None):
            self.queries.append(sql)
            # SQLite accepts the same relational query without SQL Server's Unicode literal prefix.
            return pd.read_sql_query(sql.replace("N'", "'"), self.db, params=params)
        self.helpers = {"q": execute, "category_sql": category_sql, "st": st}
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

    def test_each_family_binds_nested_queries_and_parameters(self):
        for family, labels in CATEGORY_FAMILIES.items():
            with self.subTest(family=family):
                for label in labels:
                    self.db.execute("INSERT INTO dbo.sessions VALUES (?, ?)", (label, f" {label}™ "))
                result = self.helpers["premier_q"](
                    "SELECT session_id FROM sessions WHERE session_id IN "
                    "(SELECT session_id FROM sessions WHERE session_id=?)",
                    [labels[0]], family=family,
                )
                self.assertEqual(result["session_id"].tolist(), [labels[0]])
                self.assertIn(category_sql(family), self.queries[-1])
        with self.assertRaises(ValueError):
            self.helpers["premier_q"]("SELECT * FROM sessions", family="unrecognized")

    def test_explicit_family_ignores_another_selected_family(self):
        with patch.object(st, "session_state", {"selected_category": "lightweight"}):
            result = self.helpers["premier_q"](
                "SELECT session_id FROM sessions WHERE session_id=?", ["moto2"], family="intermediate"
            )
        self.assertEqual(result["session_id"].tolist(), ["moto2"])

    def test_effective_results_override_raw_points_without_cross_class_leakage(self):
        self.db.execute(
            "UPDATE dbo.vw_effective_classifications SET points=24.5 WHERE session_id='modern'"
        )
        result = self.helpers["premier_q"](
            "SELECT SUM(points) AS points FROM classifications", family="premier"
        )
        self.assertEqual(result.iloc[0]["points"], 44.5)
        self.assertEqual(
            self.db.execute("SELECT points FROM classifications WHERE session_id='modern'").fetchone()[0],
            25,
        )

    def test_historical_loader_returns_no_reconstructed_points(self):
        tree = ast.parse(DASHBOARD.read_text(encoding="utf-8"))
        loader = next(node for node in tree.body
                      if isinstance(node, ast.FunctionDef) and node.name == "load_championship")
        loader.decorator_list = []
        queries = []
        namespace = {"pd": pd, "premier_q": lambda *args, **kwargs: queries.append((args, kwargs))}
        exec(compile(ast.Module(body=[loader], type_ignores=[]), str(DASHBOARD), "exec"), namespace)
        for family in CATEGORY_FAMILIES:
            self.assertTrue(namespace["load_championship"](1969, family).empty)
        self.assertEqual(queries, [])
        namespace["load_championship"](2026, "intermediate")
        self.assertEqual(queries[-1][1], {"family": "intermediate"})
        self.assertEqual(queries[-1][0][1], [2026])

    def test_scope_reset_removes_only_dependent_selections(self):
        tree = ast.parse(DASHBOARD.read_text(encoding="utf-8"))
        names = {"reset_category_selection", "reset_analysis_selection"}
        nodes = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name in names
                 or isinstance(node, ast.Assign) and any(
                     isinstance(target, ast.Name) and target.id == "DEPENDENT_WIDGETS"
                     for target in node.targets)]
        namespace = {}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(DASHBOARD), "exec"), namespace)
        state = {"_category_scope": "premier", "sel_year": 2026, "sel_event_id": "old",
                 "sel_session_label": "Race", "sb_gp": "old", "pos_r": ["Old rider"],
                 "language": "🇮🇹 Italiano", "selected_nav_group": "nav_race"}
        namespace["reset_category_selection"](state, "lightweight")
        self.assertEqual(state, {
            "_category_scope": "lightweight", "language": "🇮🇹 Italiano",
            "selected_nav_group": "nav_race",
        })
        state["sel_year"] = 1969
        namespace["reset_category_selection"](state, "lightweight")
        self.assertEqual(state["sel_year"], 1969)
        state["pos_r"] = ["Old rider"]
        namespace["reset_analysis_selection"](state, ("lightweight", 1969, "new-session"))
        self.assertNotIn("pos_r", state)


if __name__ == "__main__":
    unittest.main()
