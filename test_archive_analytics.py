import unittest

import numpy as np
import pandas as pd

from archive_analytics import (
    archive_availability, career_seasons, constructor_eras, complete_points,
    nominal_maximum, points_efficiency, qualifying_proxy,
)
from category_scope import recorded_q2_poles


class ArchiveAnalyticsTests(unittest.TestCase):
    def test_recorded_poles_keep_class_year_and_observed_event_coverage(self):
        base = dict(event_id="one", season_year=2026, category="MotoGP",
                    session_type="Q", session_number=2, session_status="FINISHED", position=1)
        rows = [
            base, base.copy(), {**base, "event_id": "two", "position": 3},
            {**base, "category": " MotoGP\u2122 ", "event_id": "two", "position": 3},
            {**base, "category": "Moto2", "position": 5},
            {**base, "season_year": 2025, "category": "Moto3", "position": 1},
        ]
        self.assertEqual(recorded_q2_poles(rows), {
            (2026, "MotoGP"): {"gp_poles": 1, "gp_poles_q2_events": 2},
            (2026, "Moto2"): {"gp_poles": 0, "gp_poles_q2_events": 1},
            (2025, "Moto3"): {"gp_poles": 1, "gp_poles_q2_events": 1},
        })

    def test_recorded_poles_withhold_unsupported_missing_and_conflicting_evidence(self):
        base = dict(event_id="one", season_year=2026, category="MotoGP",
                    session_type="Q", session_number=2, session_status="FINISHED", position=1)
        for changes in [
            {"category": "500cc"}, {"category": "350cc"}, {"category": "50cc"},
            {"category": "80cc"}, {"season_year": 2012},
            {"category": "Moto2", "season_year": 2018},
            {"category": "Moto3", "season_year": 2018},
            {"session_type": "SPR"}, {"session_number": 1},
            {"session_status": "NOTSTARTED"}, {"position": None},
            {"position": np.nan}, {"position": 0}, {"position": 13}, {"position": 1.5},
        ]:
            with self.subTest(changes=changes):
                self.assertEqual(recorded_q2_poles([{**base, **changes}]), {})
        self.assertEqual(recorded_q2_poles([base, {**base, "position": 2}]), {})
        self.assertEqual(recorded_q2_poles([{**base, "season_year": 2013}])[(2013, "MotoGP")]["gp_poles"], 1)
        self.assertEqual(recorded_q2_poles([{**base, "category": "Moto2", "season_year": 2019}])[(2019, "Moto2")]["gp_poles"], 1)

    def test_career_keeps_actual_classes_official_only_ranks_and_standings_only_seasons(self):
        races = pd.DataFrame([
            dict(season_year=1970, category=category, rider_id="ago", session_id=session, position=position)
            for category, session, position in [("500cc", "a", 1), ("500cc", "b", 2), ("350cc", "c", 1)]
        ])
        finals = pd.DataFrame([
            dict(season_year=year, category=category, rider_id="ago", position=rank,
                 is_final=final, source_url="https://example.test/official")
            for year, category, rank, final in [
                (1970, "500cc", 1, True), (1970, "350cc", 2, True),
                (1971, "500cc", 3, True), (1972, "500cc", 1, False),
            ]
        ])
        result = career_seasons(races, finals).set_index(["season_year", "category"])
        self.assertEqual(len(result), 3)
        self.assertEqual(result.loc[(1970, "500cc"), ["races", "wins", "podiums"]].tolist(), [2, 1, 2])
        self.assertEqual(result["position"].eq(1).sum(), 1)
        self.assertEqual(result.loc[(1971, "500cc"), "races"], 0)
        self.assertEqual(result.loc[(1971, "500cc"), "position"], 3)
        standings_only = career_seasons(pd.DataFrame(columns=races.columns), finals)
        self.assertEqual(len(standings_only), 3)
        self.assertEqual(standings_only["races"].sum(), 0)

    def test_constructor_shares_retain_unknowns_and_other_wins_without_combining_classes(self):
        rows = pd.DataFrame([
            dict(season_year=year, category=category, constructor=constructor, wins=wins)
            for year, category, constructor, wins in [
                (1970, "500cc", "MV Agusta", 6), (1971, "500cc", None, 2),
                (1972, "500cc", " ", 1), (1972, "500cc", "Yamaha", 1),
                (1970, "350cc", "Yamaha", 4), (1980, "500cc", "Suzuki", 2),
            ]
        ])
        result = constructor_eras(rows, 1, "Unknown", "Others")
        self.assertEqual(result["wins"].sum(), rows["wins"].sum())
        np.testing.assert_allclose(result.groupby(["category", "decade"])["share"].sum(), 100)
        premier = result[result["category"].eq("500cc") & result["decade"].eq(1970)].set_index("constructor")
        self.assertEqual(premier.loc["Unknown", "share"], 30)
        self.assertEqual(premier.loc["Others", "share"], 10)

    def test_availability_keeps_empty_years_and_independent_source_counts(self):
        rows = pd.DataFrame([
            dict(season_year=1970, category="500cc", laps=0, standings=3),
            dict(season_year=1970, category="500cc", laps=4, standings=0),
            dict(season_year=1972, category="500cc", laps=0, standings=0),
            dict(season_year=1972, category="350cc", laps=0, standings=2),
        ])
        counts = archive_availability(rows, "laps")
        self.assertEqual(counts.columns.tolist(), [1970, 1971, 1972])
        self.assertEqual(counts.loc["500cc"].tolist(), [4, 0, 0])
        self.assertEqual(archive_availability(rows, "standings").loc["500cc", 1970], 3)

    def test_efficiency_requires_supported_rules_and_complete_scores(self):
        self.assertTrue(np.isnan(complete_points(pd.Series([None, 3.0]))))
        maximum = nominal_maximum([1972, 1993, 2026, 2026, 2022], [2, 2, 1, 1, 1],
                                  [0, 0, 1, 0, 1], [0, 0, 0, 1, 0])
        np.testing.assert_allclose(maximum, [np.nan, 50, 37, np.nan, np.nan], equal_nan=True)
        np.testing.assert_allclose(points_efficiency([3, 32.5, 37, 25, 30], maximum),
                                   [np.nan, 65, 100, np.nan, np.nan], equal_nan=True)
        self.assertTrue(np.isnan(points_efficiency(26, 25)))

    def qualifying_data(self):
        qualifying = pd.DataFrame([
            dict(event_id="event", category="MotoGP", season_year=2026,
                 session_number=stage, rider_id=rider, position=position)
            for stage, riders in [(1, ["a", "b", "q1-only", "dns"]), (2, ["a", "b", *map(str, range(10))])]
            for position, rider in enumerate(riders, 1)
        ])
        races = pd.DataFrame([
            dict(event_id="event", category="MotoGP", season_year=2026, session_id=session,
                 rider_id=rider, finish_pos=position, status=status)
            for session in ["race", "sprint"]
            for rider, position, status in [
                ("a", 1, "INSTND"), ("b", None, "OUTSTND"),
                ("q1-only", 3, "INSTND"), ("dns", None, "NOTSTARTED"),
            ]
        ])
        return qualifying, races

    def test_proxy_keeps_q1_riders_dnf_and_distinct_races_without_duplicate_promotions(self):
        qualifying, races = self.qualifying_data()
        result = qualifying_proxy(qualifying, races)
        self.assertEqual(len(result), 6)
        self.assertEqual(result.groupby("session_id")["rider_id"].count().tolist(), [3, 3])
        self.assertEqual(result.loc[result["rider_id"].eq("q1-only"), "grid_pos"].tolist(), [13, 13])
        self.assertEqual(result["finish_pos"].isna().sum(), 2)

    def test_proxy_rejects_missing_starters_q1_q2_and_historical_formats(self):
        qualifying, races = self.qualifying_data()
        for removed in ["q1-only", "a", "0"]:
            with self.subTest(removed=removed):
                self.assertTrue(qualifying_proxy(
                    qualifying[~qualifying["rider_id"].eq(removed)], races
                ).empty)
        historical = qualifying.assign(category="500cc", season_year=1984)
        self.assertTrue(qualifying_proxy(historical, races.assign(category="500cc")).empty)
        unknown = races.copy()
        unknown.loc[unknown["rider_id"].eq("b"), "status"] = None
        self.assertTrue(qualifying_proxy(qualifying, unknown).empty)


if __name__ == "__main__":
    unittest.main()
